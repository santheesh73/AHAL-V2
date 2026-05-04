from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.changes.models import ChangeImpactResult, ChangedFileImpact, ChangedFileInput
from app.docs.models import DocEvidence, RiskItem
from app.docs.utils.production_text import clean_list, clean_sentence, join_capabilities


_ROUTE_PATTERNS = [
    (re.compile(r"@app\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]", re.IGNORECASE), "fastapi"),
    (re.compile(r"@router\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]", re.IGNORECASE), "fastapi"),
    (re.compile(r"app\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]", re.IGNORECASE), "express"),
    (re.compile(r"router\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]", re.IGNORECASE), "express"),
]


@dataclass
class _ParsedDiffFile:
    path: str
    status: str = "modified"
    added_lines: list[str] = field(default_factory=list)
    removed_lines: list[str] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)


class ChangeImpactAnalyzer:
    def parse_unified_diff(self, diff_text: str) -> list[ChangedFileInput]:
        return [
            ChangedFileInput(path=item.path, status=item.status, before="\n".join(item.removed_lines), after="\n".join(item.added_lines))
            for item in self._parse_diff_blocks(diff_text)
        ]

    def analyze(self, request, scan_result=None, intelligence_result=None) -> ChangeImpactResult:
        parsed_inputs = self._resolve_inputs(request)
        changed_impacts: list[ChangedFileImpact] = []
        affected_apis: list[str] = []
        affected_modules: list[str] = []
        affected_workflows: list[str] = []
        risks: list[RiskItem] = []
        suggested_tests: list[str] = []
        review_notes: list[str] = []

        session_api_map = self._session_api_map(intelligence_result)
        session_module_map = self._session_module_map(intelligence_result)
        session_workflow_map = self._session_workflow_map(intelligence_result)

        for item in parsed_inputs:
            impact = self._analyze_file(item, session_api_map, session_module_map, session_workflow_map)
            changed_impacts.append(impact)
            affected_apis.extend(impact.affected_apis)
            affected_modules.extend(impact.affected_modules)
            suggested_tests.extend(impact.suggested_tests)
            if impact.risk_level in {"medium", "high"}:
                risks.append(
                    RiskItem(
                        title=f"{impact.change_type.title()} change in {impact.path}",
                        severity=impact.risk_level,
                        description=impact.summary,
                        recommendation=self._review_recommendation(impact),
                    )
                )
                review_notes.append(self._review_note(impact))
            if impact.affected_modules:
                for module_name in impact.affected_modules:
                    if module_name in session_workflow_map:
                        affected_workflows.extend(session_workflow_map[module_name])

        changed_paths = [item.path for item in parsed_inputs]
        for path in changed_paths:
            if path in session_workflow_map:
                affected_workflows.extend(session_workflow_map[path])

        summary = self._result_summary(changed_impacts, affected_apis, affected_modules)
        warnings = []
        if getattr(request, "include_llm", False):
            warnings.append("LLM review-note polish is disabled in this phase; returned deterministic impact analysis.")
        evidence_count = sum(len(item.evidence) for item in changed_impacts)
        confidence = self._confidence_label(changed_impacts, scan_result, intelligence_result)
        return ChangeImpactResult(
            session_id=getattr(request, "session_id", None),
            source_type=getattr(request, "source_type", "diff"),
            summary=summary,
            changed_files=changed_impacts,
            affected_apis=clean_list(affected_apis, max_items=50),
            affected_modules=clean_list(affected_modules, max_items=50),
            affected_workflows=clean_list(affected_workflows, max_items=20),
            risks=risks[:20],
            suggested_tests=clean_list(suggested_tests, max_items=20),
            review_notes=clean_list(review_notes, max_items=20),
            confidence=confidence,
            warnings=warnings,
            evidence_count=evidence_count,
        )

    def _resolve_inputs(self, request) -> list[ChangedFileInput]:
        changed_files = list(getattr(request, "changed_files", []) or [])
        if changed_files:
            return changed_files
        diff_text = str(getattr(request, "diff_text", "") or "")
        return self.parse_unified_diff(diff_text)

    def _parse_diff_blocks(self, diff_text: str) -> list[_ParsedDiffFile]:
        files: list[_ParsedDiffFile] = []
        current: _ParsedDiffFile | None = None
        for raw_line in str(diff_text or "").splitlines():
            line = raw_line.rstrip("\n")
            if line.startswith("diff --git "):
                if current:
                    files.append(current)
                match = re.search(r" b/(.+)$", line)
                path = match.group(1).strip() if match else "unknown"
                current = _ParsedDiffFile(path=path)
                continue
            if current is None:
                continue
            current.raw_lines.append(line)
            if line.startswith("new file mode"):
                current.status = "added"
            elif line.startswith("deleted file mode"):
                current.status = "deleted"
            elif line.startswith("rename to "):
                current.status = "renamed"
                current.path = line.replace("rename to ", "", 1).strip()
            elif line.startswith("+++ b/"):
                current.path = line.replace("+++ b/", "", 1).strip()
            elif line.startswith("--- a/") and current.path == "unknown":
                current.path = line.replace("--- a/", "", 1).strip()
            elif line.startswith("+") and not line.startswith("+++"):
                current.added_lines.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                current.removed_lines.append(line[1:])
        if current:
            files.append(current)
        return files

    def _analyze_file(self, item: ChangedFileInput, session_api_map: dict, session_module_map: dict, session_workflow_map: dict) -> ChangedFileImpact:
        path = str(item.path or "unknown")
        before = str(item.before or "")
        after = str(item.after or "")
        status = str(item.status or "unknown")
        combined = f"{before}\n{after}"
        change_type = self._classify_change(path, combined)
        affected_symbols = self._extract_symbols(before, after)
        affected_apis = self._extract_apis(path, before, after)
        affected_modules = self._extract_modules(path, change_type, session_module_map)
        risk_level = self._risk_level(path, change_type, combined, affected_apis, status)
        suggested_tests = self._suggest_tests(change_type, affected_apis, affected_modules, risk_level)
        summary = self._file_summary(path, status, change_type, affected_symbols, affected_apis)
        evidence = self._build_evidence(path, before, after, change_type)

        if path in session_api_map:
            affected_apis.extend(session_api_map[path])
        if path in session_workflow_map:
            affected_modules.extend(session_workflow_map[path])

        return ChangedFileImpact(
            path=path,
            status=status,
            change_type=change_type,
            summary=summary,
            affected_symbols=clean_list(affected_symbols, max_items=20),
            affected_apis=clean_list(affected_apis, max_items=20),
            affected_modules=clean_list(affected_modules, max_items=20),
            risk_level=risk_level,
            suggested_tests=clean_list(suggested_tests, max_items=10),
            evidence=evidence[:6],
        )

    def _classify_change(self, path: str, text: str) -> str:
        lowered = path.lower()
        combined = text.lower()
        if lowered.endswith((".md", ".rst", ".txt")) or "readme" in lowered:
            return "documentation"
        if any(token in lowered for token in ["auth", "permission", "security"]):
            return "auth"
        if any(token in lowered for token in ["migration", "schema", "model", "database", "db"]):
            return "database"
        if any(token in lowered for token in ["docker", ".github/workflows", "gitlab-ci", ".env", "config", "settings"]):
            return "configuration"
        if any(token in lowered for token in ["package.json", "requirements.txt", "pyproject.toml", "go.mod", "pom.xml"]):
            return "dependency"
        if any(token in lowered for token in ["/api/", "/routes/", "route", "controller"]) or self._extract_apis(path, "", text):
            return "api"
        if any(token in lowered for token in ["service", "logic", "workflow", "pipeline", "job", "worker"]):
            return "service"
        if any(token in lowered for token in ["/ui/", "/components/", ".tsx", ".jsx", ".css"]):
            return "ui"
        if "/tests/" in lowered or lowered.startswith("tests/") or "test_" in lowered:
            return "tests"
        if any(token in combined for token in ["billing", "payment", "invoice"]):
            return "billing"
        if any(token in combined for token in ["medical", "diagnos", "clinical", "patient"]):
            return "medical"
        return "source"

    def _extract_symbols(self, before: str, after: str) -> list[str]:
        symbols = []
        patterns = [
            r"def\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"class\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"func\s+([A-Za-z_][A-Za-z0-9_]*)",
            r"function\s+([A-Za-z_][A-Za-z0-9_]*)",
        ]
        for pattern in patterns:
            symbols.extend(re.findall(pattern, before))
            symbols.extend(re.findall(pattern, after))
        return clean_list(symbols, max_items=20)

    def _extract_apis(self, path: str, before: str, after: str) -> list[str]:
        found = []
        combined = f"{before}\n{after}"
        for pattern, _ in _ROUTE_PATTERNS:
            for method, route_path in pattern.findall(combined):
                found.append(f"{method.upper()} {route_path}")
        if not found and any(token in path.lower() for token in ["/api/", "routes", "controller"]):
            found.append(path)
        return clean_list(found, max_items=20)

    def _extract_modules(self, path: str, change_type: str, session_module_map: dict) -> list[str]:
        lowered = path.lower()
        modules = []
        if path in session_module_map:
            modules.extend(session_module_map[path])
        for token in ["api", "service", "model", "schema", "auth", "config", "tests", "ui", "database", "worker"]:
            if token in lowered:
                modules.append(token)
        if not modules:
            modules.append(change_type)
        return clean_list(modules, max_items=10)

    def _risk_level(self, path: str, change_type: str, combined: str, affected_apis: list[str], status: str) -> str:
        lowered = f"{path}\n{combined}".lower()
        if change_type in {"auth", "database", "billing", "medical"}:
            return "high"
        if change_type == "configuration":
            return "high"
        if affected_apis:
            return "high"
        if status == "deleted" and change_type in {"service", "source", "api"}:
            return "high"
        if any(token in lowered for token in ["payment", "billing", "diagnos", "clinical", "patient", "legal"]):
            return "high"
        if change_type in {"service", "dependency"}:
            return "medium"
        if change_type == "tests":
            return "medium"
        if change_type == "documentation" and not re.search(r"^\s*[+-]\s*(def|class|func|function)\b", combined, re.MULTILINE):
            return "low"
        return "low"

    def _suggest_tests(self, change_type: str, affected_apis: list[str], affected_modules: list[str], risk_level: str) -> list[str]:
        tests = []
        if affected_apis or change_type == "api":
            tests.append("Run endpoint integration tests for the changed API routes.")
        if change_type in {"database", "model", "schema"} or any(token in affected_modules for token in ["database", "model", "schema"]):
            tests.append("Run serialization and database migration or persistence tests.")
        if change_type == "auth":
            tests.append("Run authorization and authentication regression tests.")
        if change_type == "configuration":
            tests.append("Validate deployment and configuration loading in a clean environment.")
        if change_type == "service":
            tests.append("Add or rerun unit tests for the affected service behavior.")
        if change_type == "ui":
            tests.append("Run component or UI smoke tests for the affected screens.")
        if change_type == "documentation":
            tests.append("No functional tests are strictly required for documentation-only changes.")
        if risk_level == "high":
            tests.append("Run a targeted regression pass across the impacted workflows before merge.")
        return tests

    def _file_summary(self, path: str, status: str, change_type: str, symbols: list[str], apis: list[str]) -> str:
        parts = [f"{status.title()} {change_type} change detected in {path}."]
        if symbols:
            parts.append(f"Affected symbols include {join_capabilities(symbols[:4])}.")
        if apis:
            parts.append(f"Affected APIs include {join_capabilities(apis[:3])}.")
        return clean_sentence(" ".join(parts))

    def _build_evidence(self, path: str, before: str, after: str, change_type: str) -> list[DocEvidence]:
        evidence = []
        if before:
            evidence.append(DocEvidence(source_type="diff", source_id=f"{path}:before", file=path, reason=f"Removed lines indicate a {change_type} change.", snippet=before[:200], confidence="medium"))
        if after:
            evidence.append(DocEvidence(source_type="diff", source_id=f"{path}:after", file=path, reason=f"Added lines indicate a {change_type} change.", snippet=after[:200], confidence="high"))
        if not evidence:
            evidence.append(DocEvidence(source_type="diff", source_id=path, file=path, reason="Changed file path detected from diff metadata.", confidence="low"))
        return evidence

    def _session_api_map(self, intelligence_result) -> dict[str, list[str]]:
        mapping = {}
        for api in getattr(intelligence_result, "api_endpoints", []) if intelligence_result else []:
            mapping.setdefault(getattr(api, "file", ""), []).append(f"{getattr(api, 'method', '').upper()} {getattr(api, 'path', '')}")
        return mapping

    def _session_module_map(self, intelligence_result) -> dict[str, list[str]]:
        mapping = {}
        for module in getattr(intelligence_result, "modules", []) if intelligence_result else []:
            for file_path in getattr(module, "files", []) or []:
                mapping.setdefault(file_path, []).append(getattr(module, "name", "unknown"))
        return mapping

    def _session_workflow_map(self, intelligence_result) -> dict[str, list[str]]:
        mapping = {}
        workflow = getattr(intelligence_result, "workflow", None) if intelligence_result else None
        for step in getattr(workflow, "steps", []) if workflow else []:
            source = getattr(step, "source", "")
            action = getattr(step, "action", "")
            target = getattr(step, "target", "")
            if source:
                mapping.setdefault(source, []).append(action)
            if target:
                mapping.setdefault(target, []).append(action)
        return mapping

    def _review_recommendation(self, impact: ChangedFileImpact) -> str:
        if impact.risk_level == "high":
            return "Request targeted review from an owner of the affected API, data, or security surface."
        return "Review the changed behavior against nearby tests and runtime expectations."

    def _review_note(self, impact: ChangedFileImpact) -> str:
        if impact.risk_level == "high":
            return clean_sentence(f"Review {impact.path} closely because it changes {impact.change_type} behavior with elevated regression risk.")
        return clean_sentence(f"Check {impact.path} for downstream effects on {join_capabilities(impact.affected_modules[:3]) if impact.affected_modules else impact.change_type}.")

    def _result_summary(self, changed_impacts: list[ChangedFileImpact], apis: list[str], modules: list[str]) -> str:
        if not changed_impacts:
            return "No code changes were detected from the provided input."
        high_risk = sum(1 for item in changed_impacts if item.risk_level == "high")
        parts = [f"Detected {len(changed_impacts)} changed file{'s' if len(changed_impacts) != 1 else ''}."]
        if modules:
            parts.append(f"Affected modules include {join_capabilities(clean_list(modules, max_items=4))}.")
        if apis:
            parts.append(f"Affected APIs include {join_capabilities(clean_list(apis, max_items=4))}.")
        if high_risk:
            parts.append(f"{high_risk} change{'s' if high_risk != 1 else ''} appear high risk and should receive targeted review.")
        return clean_sentence(" ".join(parts))

    def _confidence_label(self, changed_impacts: list[ChangedFileImpact], scan_result, intelligence_result) -> str:
        if changed_impacts and intelligence_result:
            return "high"
        if changed_impacts:
            return "medium"
        return "low"
