from __future__ import annotations

import os
import re

from app.docs.models import DocEvidence
from app.docs.utils.production_text import clean_list, clean_sentence
from app.intelligence.intelligence_engine import IntelligenceEngine
from app.testing.models import TestGapItem, TestGapResult
from app.utils.ignored_paths import is_ignored_path


class TestGapDetector:
    def detect(
        self,
        session_id: str,
        scan_result,
        intelligence_result=None,
        graph_result=None,
        include_low_priority: bool = False,
    ) -> TestGapResult:
        if intelligence_result is None:
            intelligence_result = IntelligenceEngine().analyze(
                scan_result=scan_result,
                session_id=session_id,
                include_llm_explanation=False,
            )

        contents = getattr(scan_result, "contents", {}) or {}
        if not isinstance(contents, dict):
            contents = {}

        files = [
            str(getattr(item, "path", item) or "")
            for item in getattr(scan_result, "files", []) or []
        ]
        all_paths = sorted({path for path in [*contents.keys(), *files] if str(path).strip()})
        test_files = [path for path in all_paths if self._is_test_file(path)]
        ecosystem = self._test_ecosystem_evidence(contents)
        tested_evidence = clean_list(sorted(set(test_files + ecosystem)), max_items=50)

        targets = []
        targets.extend(self._api_targets(intelligence_result))
        targets.extend(self._module_targets(intelligence_result))
        targets.extend(self._workflow_targets(intelligence_result))
        targets.extend(self._doc_targets(all_paths))
        targets = self._dedupe_targets(targets)

        if not targets:
            return TestGapResult(
                session_id=session_id,
                summary="No important code targets could be established confidently for test-gap analysis.",
                total_targets=0,
                tested_targets=0,
                gap_count=0,
                gaps=[],
                tested_evidence=tested_evidence,
                warnings=["Limited structural evidence was available for test-gap detection."],
                confidence="low",
            )

        gaps: list[TestGapItem] = []
        tested_targets = 0
        for target in targets:
            matches = self._matching_tests(target, test_files, contents)
            if matches:
                tested_targets += 1
                continue
            if target.priority == "low" and not include_low_priority:
                continue
            gaps.append(target)

        warnings = []
        if not test_files and not ecosystem:
            warnings.append("No direct test file evidence was found in the analyzed repository.")
        if all(item.priority == "low" for item in gaps) and gaps:
            warnings.append("Only low-priority test gaps were detected from the available evidence.")

        confidence = self._confidence_level(test_files, targets, intelligence_result)
        summary = self._summary(targets, tested_targets, gaps, include_low_priority)
        return TestGapResult(
            session_id=session_id,
            summary=summary,
            total_targets=len(targets),
            tested_targets=tested_targets,
            gap_count=len(gaps),
            gaps=gaps[:50],
            tested_evidence=tested_evidence,
            warnings=clean_list(warnings + list(getattr(intelligence_result, "warnings", []) or [])),
            confidence=confidence,
        )

    def _api_targets(self, intelligence_result) -> list[TestGapItem]:
        rows = []
        for endpoint in getattr(intelligence_result, "api_endpoints", []) or []:
            target = f"{getattr(endpoint, 'method', '').upper()} {getattr(endpoint, 'path', '')}".strip()
            path = str(getattr(endpoint, "file", "") or "")
            if not target or not path:
                continue
            rows.append(
                TestGapItem(
                    target=target,
                    target_type="api",
                    path=path,
                    reason="This public API endpoint appears to have no nearby test evidence.",
                    suggested_test=f"Add endpoint integration tests for {target} including success and error cases.",
                    priority="high",
                    confidence=getattr(endpoint, "confidence", "medium"),
                    evidence=self._doc_evidence(getattr(endpoint, "evidence", [])),
                )
            )
        return rows

    def _module_targets(self, intelligence_result) -> list[TestGapItem]:
        rows = []
        for module in getattr(intelligence_result, "modules", []) or []:
            files = list(getattr(module, "files", []) or [])
            for path in files or [getattr(getattr(module, "evidence", [None])[0], "file", "")]:
                normalized = str(path or "")
                if not normalized or is_ignored_path(normalized) or self._is_test_file(normalized):
                    continue
                target_type, priority, suggested = self._classify_module_target(normalized, getattr(module, "category", "unknown"))
                if target_type not in {"module", "service", "database", "auth", "config"}:
                    continue
                rows.append(
                    TestGapItem(
                        target=getattr(module, "name", os.path.basename(normalized)),
                        target_type=target_type,
                        path=normalized,
                        reason=f"{clean_sentence(getattr(module, 'name', 'This module'))} appears to have no nearby test evidence.",
                        suggested_test=suggested,
                        priority=priority,
                        confidence=getattr(module, "confidence", "medium"),
                        evidence=self._doc_evidence(getattr(module, "evidence", [])),
                    )
                )
        return rows

    def _workflow_targets(self, intelligence_result) -> list[TestGapItem]:
        rows = []
        for step in getattr(getattr(intelligence_result, "workflow", None), "steps", []) or []:
            target = clean_sentence(f"{getattr(step, 'source', '')} -> {getattr(step, 'action', '')} -> {getattr(step, 'target', '')}")
            evidence = self._doc_evidence(getattr(step, "evidence", []))
            path = evidence[0].file if evidence else ""
            if not target or not path:
                continue
            rows.append(
                TestGapItem(
                    target=target,
                    target_type="workflow",
                    path=path,
                    reason="This inferred workflow step appears to lack direct test evidence.",
                    suggested_test="Add end-to-end workflow regression test.",
                    priority="medium",
                    confidence=getattr(step, "confidence", "medium"),
                    evidence=evidence,
                )
            )
        return rows

    def _doc_targets(self, paths: list[str]) -> list[TestGapItem]:
        rows = []
        for path in paths:
            lowered = path.lower()
            if is_ignored_path(path) or self._is_test_file(path):
                continue
            if "readme" in lowered or lowered.endswith((".md", ".rst")):
                rows.append(
                    TestGapItem(
                        target=os.path.basename(path),
                        target_type="module",
                        path=path,
                        reason="Documentation-only paths do not show direct test evidence.",
                        suggested_test="Add configuration validation test.",
                        priority="low",
                        confidence="low",
                        evidence=[],
                    )
                )
        return rows

    def _matching_tests(self, target: TestGapItem, test_files: list[str], contents: dict[str, str]) -> list[str]:
        target_tokens = set(self._keywords(target.target) + self._keywords(target.path))
        basename = self._canonical_basename(target.path)
        matches = []
        for test_path in test_files:
            test_text = f"{test_path}\n{str(contents.get(test_path, '') or '')[:4000]}"
            test_tokens = set(self._keywords(test_path) + self._keywords(test_text))
            if basename and basename == self._canonical_basename(test_path):
                matches.append(test_path)
                continue
            overlap = target_tokens & test_tokens
            if target.target_type == "api" and self._api_match(target, test_text, overlap):
                matches.append(test_path)
                continue
            if len(overlap) >= 2:
                matches.append(test_path)
        return sorted(set(matches))

    def _api_match(self, target: TestGapItem, test_text: str, overlap: set[str]) -> bool:
        method, _, route = target.target.partition(" ")
        route_tokens = set(self._keywords(route))
        lowered = test_text.lower()
        return (method.lower() in lowered and route.lower() in lowered) or len(route_tokens & overlap) >= 1

    def _classify_module_target(self, path: str, category: str) -> tuple[str, str, str]:
        lowered = path.lower()
        category = str(category or "").lower()
        if any(token in lowered or token in category for token in ["auth", "session", "security"]):
            return "auth", "high", "Add authorization, token, and session lifecycle tests."
        if any(token in lowered or token in category for token in ["database", "db", "schema", "model", "migration"]):
            return "database", "high", "Add schema serialization and migration compatibility tests."
        if any(token in lowered or token in category for token in ["service", "worker", "pipeline", "indexer", "diff"]):
            return "service", "medium", "Add unit tests for core behavior and failure paths."
        if any(token in lowered or token in category for token in ["config", "docker", "compose", "settings"]):
            return "config", "low", "Add configuration validation test."
        return "module", "medium", "Add unit tests for core behavior and failure paths."

    def _dedupe_targets(self, targets: list[TestGapItem]) -> list[TestGapItem]:
        seen = {}
        for item in targets:
            key = (item.target_type, item.path, item.target)
            if key not in seen:
                seen[key] = item
        return list(seen.values())

    def _test_ecosystem_evidence(self, contents: dict[str, str]) -> list[str]:
        evidence = []
        for path, content in contents.items():
            lowered = str(path).lower()
            text = str(content or "").lower()
            if lowered.endswith("pytest.ini"):
                evidence.append(path)
            elif lowered.endswith(("vitest.config.ts", "vitest.config.js", "jest.config.js", "jest.config.ts")):
                evidence.append(path)
            elif lowered.endswith(("package.json", "pyproject.toml")) and any(token in text for token in ["pytest", "vitest", "jest"]):
                evidence.append(path)
        return evidence

    def _doc_evidence(self, evidence_items) -> list[DocEvidence]:
        rows = []
        for item in evidence_items[:4]:
            file_path = str(getattr(item, "file", "") or "")
            if not file_path or is_ignored_path(file_path):
                continue
            rows.append(
                DocEvidence(
                    source_type="file",
                    source_id=file_path,
                    file=file_path,
                    reason=clean_sentence(getattr(item, "reason", "Code evidence detected.")),
                    snippet=getattr(item, "snippet", None),
                    confidence=getattr(item, "confidence", "medium"),
                )
            )
        return rows

    def _confidence_level(self, test_files: list[str], targets: list[TestGapItem], intelligence_result) -> str:
        if test_files and targets and getattr(intelligence_result, "api_endpoints", []):
            return "high"
        if test_files or targets:
            return "medium"
        return "low"

    def _summary(self, targets: list[TestGapItem], tested_targets: int, gaps: list[TestGapItem], include_low_priority: bool) -> str:
        gap_count = len(gaps)
        if not targets:
            return "No important code targets were identified for test-gap detection."
        scope = "including low-priority items" if include_low_priority else "excluding low-priority items"
        return clean_sentence(
            f"AHAL reviewed {len(targets)} important targets and found test evidence for {tested_targets}. "
            f"{gap_count} targets appear to lack nearby test evidence, {scope}."
        )

    def _is_test_file(self, path: str) -> bool:
        lowered = str(path).replace("\\", "/").lower()
        name = lowered.rsplit("/", 1)[-1]
        return (
            "/tests/" in f"/{lowered}"
            or "/__tests__/" in f"/{lowered}"
            or name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".spec.js", ".test.js"))
        )

    def _keywords(self, value: str) -> list[str]:
        return [token for token in re.split(r"[^a-z0-9]+", str(value or "").lower()) if len(token) >= 3]

    def _canonical_basename(self, path: str) -> str:
        name = os.path.basename(str(path or "")).lower()
        name = re.sub(r"^(test_)", "", name)
        name = re.sub(r"(_test|\.test|\.spec)", "", name)
        name = re.sub(r"\.[a-z0-9]+$", "", name)
        return name
