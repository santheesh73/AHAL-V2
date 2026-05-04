from __future__ import annotations

import re

from app.changes import ChangeAnalysisRequest, ChangeImpactAnalyzer
from app.docs.models import DocEvidence
from app.docs.utils.production_text import clean_list, clean_sentence, join_capabilities
from app.indexing.models import RepoIndex
from app.pr.models import PullRequestAnalysisResult, PullRequestFileImpact
from app.testing import TestGapDetector


class PullRequestAnalyzer:
    def __init__(self) -> None:
        self._change_analyzer = ChangeImpactAnalyzer()
        self._test_gap_detector = TestGapDetector()

    def analyze(
        self,
        request,
        scan_result=None,
        intelligence_result=None,
        graph_result=None,
        repo_index: RepoIndex | None = None,
    ) -> PullRequestAnalysisResult:
        change_request = ChangeAnalysisRequest(
            session_id=getattr(request, "session_id", None),
            diff_text=getattr(request, "diff_text", None),
            changed_files=list(getattr(request, "changed_files", []) or []),
            base_ref=getattr(request, "base_ref", None),
            head_ref=getattr(request, "head_ref", None),
            source_type="github_pr",
            include_llm=False,
        )
        change_result = self._change_analyzer.analyze(
            change_request,
            scan_result=scan_result,
            intelligence_result=intelligence_result,
        )
        test_gap_result = None
        if scan_result is not None and intelligence_result is not None:
            try:
                test_gap_result = self._test_gap_detector.detect(
                    session_id=getattr(request, "session_id", "pr-analysis"),
                    scan_result=scan_result,
                    intelligence_result=intelligence_result,
                    include_low_priority=False,
                )
            except Exception:
                test_gap_result = None

        file_impacts: list[PullRequestFileImpact] = []
        affected_workflows = list(change_result.affected_workflows)
        suggested_tests = list(change_result.suggested_tests)
        reviewer_focus = []

        for item in change_result.changed_files:
            file_workflows = self._workflows_for_file(item, intelligence_result, graph_result)
            affected_workflows.extend(file_workflows)
            file_risk = self._elevate_risk(item, repo_index)
            file_tests = self._file_tests(item, test_gap_result)
            suggested_tests.extend(file_tests)
            reviewer_focus.extend(self._reviewer_focus(item, file_workflows, file_risk))
            file_impacts.append(
                PullRequestFileImpact(
                    path=item.path,
                    status=item.status,
                    summary=self._file_summary(item, file_risk, file_workflows),
                    affected_modules=clean_list(item.affected_modules, max_items=10),
                    affected_apis=clean_list(item.affected_apis, max_items=10),
                    affected_workflows=clean_list(file_workflows, max_items=10),
                    risk_level=file_risk,
                    suggested_tests=clean_list(file_tests, max_items=10),
                    evidence=self._file_evidence(item, file_risk, repo_index),
                )
            )

        risk_level = self._overall_risk(file_impacts)
        breaking_change_risk = self._breaking_change_risk(file_impacts)
        reviewer_focus.extend(self._global_reviewer_focus(file_impacts, change_result, breaking_change_risk))
        warnings = list(change_result.warnings)
        if getattr(request, "include_llm_polish", False):
            warnings.append("LLM PR analysis polish is disabled in this phase; returned deterministic review intelligence.")
        if test_gap_result is not None:
            warnings.extend(getattr(test_gap_result, "warnings", []) or [])
        summary = self._summary(file_impacts, change_result, risk_level, breaking_change_risk)
        confidence = self._confidence(file_impacts, intelligence_result, repo_index)
        evidence_count = sum(len(item.evidence) for item in file_impacts)
        return PullRequestAnalysisResult(
            summary=summary,
            pr_title=getattr(request, "title", None),
            repo_url=getattr(request, "repo_url", None),
            session_id=getattr(request, "session_id", None),
            index_id=getattr(request, "index_id", None),
            changed_files=file_impacts,
            affected_apis=clean_list(change_result.affected_apis, max_items=30),
            affected_modules=clean_list(change_result.affected_modules, max_items=30),
            affected_workflows=clean_list(affected_workflows, max_items=20),
            risk_level=risk_level,
            breaking_change_risk=breaking_change_risk,
            suggested_tests=clean_list(suggested_tests, max_items=20),
            reviewer_focus=clean_list(reviewer_focus, max_items=20),
            warnings=clean_list([clean_sentence(item) for item in warnings], max_items=12),
            confidence=confidence,
            evidence_count=evidence_count,
        )

    def _workflows_for_file(self, item, intelligence_result, graph_result) -> list[str]:
        workflows = []
        path = str(getattr(item, "path", "") or "")
        for step in getattr(getattr(intelligence_result, "workflow", None), "steps", []) if intelligence_result else []:
            sources = [getattr(step, "source", ""), getattr(step, "target", "")]
            evidence_files = [getattr(ev, "file", "") for ev in getattr(step, "evidence", [])]
            if path in sources or path in evidence_files:
                workflows.append(clean_sentence(f"{getattr(step, 'source', '')} -> {getattr(step, 'action', '')} -> {getattr(step, 'target', '')}"))
        for edge in getattr(graph_result, "edges", []) if graph_result is not None else []:
            evidence_files = [getattr(ev, "file", "") for ev in getattr(edge, "evidence", [])]
            if path in evidence_files and getattr(edge, "type", "") in {"routes_to", "part_of_workflow", "calls"}:
                workflows.append(clean_sentence(getattr(edge, "label", "Related workflow change")))
        if not workflows and any(token in path.lower() for token in ("workflow", "pipeline", "worker", "job")):
            workflows.append(clean_sentence(f"{path} appears to participate in a project workflow"))
        return clean_list(workflows, max_items=10)

    def _elevate_risk(self, item, repo_index: RepoIndex | None) -> str:
        base = getattr(item, "risk_level", "low")
        path = str(getattr(item, "path", "") or "").lower()
        status = str(getattr(item, "status", "") or "").lower()
        affected_apis = list(getattr(item, "affected_apis", []) or [])
        summary = str(getattr(item, "summary", "") or "").lower()
        if status == "deleted" and affected_apis:
            return "high"
        if affected_apis and (status == "deleted" or "removed" in summary):
            return "high"
        if any(token in path for token in ("auth", "session", "security", "token", "permission")):
            return "high"
        if any(token in path for token in ("schema", "migration", "database", "/db", "model")):
            return "high"
        if any(token in path for token in ("docker", ".github/workflows", "compose", "deploy", "config", "settings")):
            return "high" if base == "high" else "medium"
        if any(token in path for token in ("payment", "billing", "legal", "medical", "patient", "clinical")):
            return "high"
        if "tests/" in path and status in {"deleted", "modified"}:
            return "high" if status == "deleted" else "medium"
        if repo_index is not None:
            for fingerprint in repo_index.file_fingerprints:
                if fingerprint.path == getattr(item, "path", "") and fingerprint.category in {"api", "model", "config"}:
                    if fingerprint.category in {"api", "model"}:
                        return "high"
                    return "medium" if base == "low" else base
        return base

    def _file_tests(self, item, test_gap_result) -> list[str]:
        tests = list(getattr(item, "suggested_tests", []) or [])
        path = str(getattr(item, "path", "") or "")
        if test_gap_result is not None:
            for gap in getattr(test_gap_result, "gaps", [])[:10]:
                if getattr(gap, "path", "") == path:
                    tests.append(getattr(gap, "suggested_test", "Add targeted regression coverage."))
        if getattr(item, "affected_apis", []):
            tests.append("Verify API backward compatibility and error handling for the affected routes.")
        if getattr(item, "status", "") == "deleted":
            tests.append("Run regression tests that prove deleted behavior is intentionally removed or redirected.")
        return clean_list(tests, max_items=10)

    def _reviewer_focus(self, item, workflows: list[str], risk_level: str) -> list[str]:
        focus = []
        if getattr(item, "affected_apis", []):
            focus.append(f"Review route contract changes in {item.path}, especially method/path compatibility.")
        if any(token in item.path.lower() for token in ("auth", "session", "security", "token")):
            focus.append(f"Review auth/session behavior in {item.path} for regressions or access-control drift.")
        if any(token in item.path.lower() for token in ("schema", "migration", "database", "/db", "model")):
            focus.append(f"Review persistence and schema compatibility in {item.path}.")
        if workflows:
            focus.append(f"Trace the workflow impact around {item.path}.")
        if risk_level == "high":
            focus.append(f"Require a targeted owner review for {item.path} before merge.")
        return focus

    def _global_reviewer_focus(self, file_impacts: list[PullRequestFileImpact], change_result, breaking_change_risk: str) -> list[str]:
        focus = []
        if breaking_change_risk == "high":
            focus.append("Check whether removed or changed APIs require a versioning, redirect, or migration plan.")
        if any(item.risk_level == "high" for item in file_impacts):
            focus.append("Prioritize high-risk files before stylistic or documentation changes.")
        if change_result.affected_workflows:
            focus.append("Walk one end-to-end workflow that covers the changed modules before approving.")
        return focus

    def _file_summary(self, item, risk_level: str, workflows: list[str]) -> str:
        parts = [str(getattr(item, "summary", "") or "Change detected.")]
        if workflows:
            parts.append(f"Related workflows include {join_capabilities(workflows[:2])}.")
        if risk_level == "high":
            parts.append("This file should be treated as high review priority.")
        return clean_sentence(" ".join(parts))

    def _file_evidence(self, item, risk_level: str, repo_index: RepoIndex | None) -> list[DocEvidence]:
        evidence = list(getattr(item, "evidence", []) or [])
        if repo_index is not None:
            for fingerprint in repo_index.file_fingerprints:
                if fingerprint.path == getattr(item, "path", ""):
                    evidence.append(
                        DocEvidence(
                            source_type="repo_index",
                            source_id=repo_index.index_id,
                            file=fingerprint.path,
                            reason=clean_sentence(f"Repo index categorizes this file as {fingerprint.category}."),
                            snippet=None,
                            confidence="medium",
                        )
                    )
                    break
        if risk_level == "high":
            evidence.append(
                DocEvidence(
                    source_type="analysis",
                    source_id=getattr(item, "path", "unknown"),
                    file=getattr(item, "path", None),
                    reason="Risk was elevated by deterministic PR heuristics.",
                    snippet=None,
                    confidence="medium",
                )
            )
        return evidence[:6]

    def _overall_risk(self, file_impacts: list[PullRequestFileImpact]) -> str:
        if any(item.risk_level == "high" for item in file_impacts):
            return "high"
        if any(item.risk_level == "medium" for item in file_impacts):
            return "medium"
        return "low"

    def _breaking_change_risk(self, file_impacts: list[PullRequestFileImpact]) -> str:
        for item in file_impacts:
            if item.status == "deleted" and item.affected_apis:
                return "high"
            if item.risk_level == "high" and item.affected_apis:
                return "high"
            if "method/path compatibility" in " ".join(item.suggested_tests).lower():
                return "high"
        if any(item.risk_level == "medium" and item.affected_apis for item in file_impacts):
            return "medium"
        return "low"

    def _summary(self, file_impacts: list[PullRequestFileImpact], change_result, risk_level: str, breaking_change_risk: str) -> str:
        if not file_impacts:
            return "No pull request changes were detected from the provided input."
        high_risk = sum(1 for item in file_impacts if item.risk_level == "high")
        parts = [f"AHAL reviewed {len(file_impacts)} changed files."]
        if change_result.affected_modules:
            parts.append(f"Affected modules include {join_capabilities(change_result.affected_modules[:4])}.")
        if change_result.affected_apis:
            parts.append(f"Affected APIs include {join_capabilities(change_result.affected_apis[:4])}.")
        parts.append(f"Overall PR risk is {risk_level}.")
        if breaking_change_risk != "low":
            parts.append(f"Breaking-change risk is {breaking_change_risk}.")
        if high_risk:
            parts.append(f"{high_risk} file changes need focused review.")
        return clean_sentence(" ".join(parts))

    def _confidence(self, file_impacts: list[PullRequestFileImpact], intelligence_result, repo_index: RepoIndex | None) -> str:
        if file_impacts and intelligence_result is not None and repo_index is not None:
            return "high"
        if file_impacts and (intelligence_result is not None or repo_index is not None):
            return "medium"
        if file_impacts:
            return "medium"
        return "low"
