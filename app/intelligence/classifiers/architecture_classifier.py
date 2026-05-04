"""
AHAL AI — Architecture Classifier (Phase 2, Step 10)

Classify the overall project architecture type from intelligence signals.
Pure, deterministic, evidence-backed.
"""

from __future__ import annotations

import re
from typing import List, Optional, Set

from app.intelligence.models import (
    ArchitectureResult,
    ConfidenceLevel,
    DetectedAPIEndpoint,
    DetectedDatabase,
    DetectedDependency,
    DetectedEntryPoint,
    DetectedFramework,
    DetectedLanguage,
    DetectedModule,
)
from app.intelligence.utils.evidence import make_evidence
from app.intelligence.utils.path_utils import content_for, iter_files
from app.models.file_schema import ScanResult


class ArchitectureClassifier:
    """Classify overall project architecture type from detection results."""

    def classify(
        self,
        scan_result: ScanResult,
        languages: List[DetectedLanguage] | None = None,
        frameworks: List[DetectedFramework] | None = None,
        entry_points: List[DetectedEntryPoint] | None = None,
        modules: List[DetectedModule] | None = None,
        api_endpoints: List[DetectedAPIEndpoint] | None = None,
        databases: List[DetectedDatabase] | None = None,
        dependencies: List[DetectedDependency] | None = None,
    ) -> ArchitectureResult:
        langs = languages or []
        fws = frameworks or []
        eps = entry_points or []
        mods = modules or []
        apis = api_endpoints or []
        dbs = databases or []
        deps = dependencies or []

        fw_names: Set[str] = {f.name.lower() for f in fws}
        fw_cats: Set[str] = {f.category for f in fws}
        ep_types: Set[str] = {e.type for e in eps}
        dep_names: Set[str] = {d.name.lower() for d in deps}

        has_frontend_fw = "frontend" in fw_cats
        has_backend_fw = "backend" in fw_cats
        has_frontend_ep = "frontend" in ep_types
        has_backend_ep = "backend" in ep_types
        has_api = len(apis) > 0
        has_db = len(dbs) > 0

        reasoning: List[str] = []
        evidence = []

        # ── Evaluate microservices evidence (but don't return yet) ─
        strong_microservices = self._is_microservices(scan_result, fws, eps, mods, deps)

        # ── Fullstack (takes priority over microservices) ─────────
        if has_frontend_fw and (has_backend_fw or has_api):
            # A normal repo with both frontend and backend is fullstack,
            # NOT microservices — unless there's overwhelming evidence.
            if not strong_microservices:
                reasoning.append(f"Frontend framework detected: {', '.join(f.name for f in fws if f.category == 'frontend')}")
                reasoning.append(f"Backend framework/API detected: {', '.join(f.name for f in fws if f.category == 'backend') or 'API endpoints'}")
                for f in fws:
                    if f.evidence:
                        evidence.append(f.evidence[0])
                confidence: ConfidenceLevel = "high" if (has_frontend_fw and has_backend_fw) else "medium"
                return ArchitectureResult(
                    type="fullstack",
                    confidence=confidence,
                    reasoning=reasoning,
                    evidence=evidence[:5],
                )

        # ── Microservices (only when fullstack didn't match) ──────
        if strong_microservices:
            reasoning.append("Multiple independent service directories or docker-compose with multiple services detected")
            evidence.append(make_evidence("", "Microservices pattern detected", confidence="medium"))
            return ArchitectureResult(
                type="microservices",
                confidence="medium",
                reasoning=reasoning,
                evidence=evidence,
            )

        # ── CLI ──────────────────────────────────────────────────
        if self._is_cli(deps, dep_names, scan_result):
            reasoning.append("CLI tool signals detected (argparse/click/typer/console_scripts)")
            evidence.append(make_evidence("", "CLI tool pattern", confidence="medium"))
            return ArchitectureResult(
                type="cli",
                confidence="medium",
                reasoning=reasoning,
                evidence=evidence,
            )

        # ── Library ──────────────────────────────────────────────
        if self._is_library(scan_result, eps, apis, deps, dep_names):
            reasoning.append("Package config exists without app entrypoint; library pattern")
            evidence.append(make_evidence("", "Library/package pattern", confidence="medium"))
            return ArchitectureResult(
                type="library",
                confidence="medium",
                reasoning=reasoning,
                evidence=evidence,
            )

        # ── Frontend ─────────────────────────────────────────────
        if has_frontend_fw or has_frontend_ep:
            if not has_backend_fw and not has_api:
                reasoning.append(f"Frontend framework: {', '.join(f.name for f in fws if f.category == 'frontend')}")
                reasoning.append("No backend framework or API endpoints detected")
                for f in fws:
                    if f.category == "frontend" and f.evidence:
                        evidence.append(f.evidence[0])
                confidence = "high" if has_frontend_fw else "medium"
                return ArchitectureResult(
                    type="frontend",
                    confidence=confidence,
                    reasoning=reasoning,
                    evidence=evidence[:5],
                )

        # ── Backend ──────────────────────────────────────────────
        if has_backend_fw or has_api or has_backend_ep:
            if not has_frontend_fw:
                backend_fws = [f.name for f in fws if f.category == "backend"]
                reasoning.append(f"Backend framework: {', '.join(backend_fws) or 'API endpoints detected'}")
                reasoning.append("No frontend framework detected")
                for f in fws:
                    if f.category == "backend" and f.evidence:
                        evidence.append(f.evidence[0])
                confidence = "high" if has_backend_fw else "medium"
                return ArchitectureResult(
                    type="backend",
                    confidence=confidence,
                    reasoning=reasoning,
                    evidence=evidence[:5],
                )

        # ── Unknown ──────────────────────────────────────────────
        reasoning.append("Insufficient evidence to determine architecture type")
        return ArchitectureResult(
            type="unknown",
            confidence="low",
            reasoning=reasoning,
            evidence=evidence,
        )

    # ── Heuristic checks ─────────────────────────────────────────

    def _is_microservices(
        self,
        scan_result: ScanResult,
        fws: List[DetectedFramework],
        eps: List[DetectedEntryPoint],
        mods: List[DetectedModule],
        deps: List[DetectedDependency],
    ) -> bool:
        """
        Check for strong microservices evidence.

        A normal monorepo with frontend/ + backend/ + db is NOT microservices.
        Requires either:
          - docker-compose with 4+ named service entries, OR
          - multiple dirs matching explicit service-naming patterns
        """
        # Check docker-compose for many services
        for fm in iter_files(scan_result):
            fname = fm.path.lower().replace("\\", "/")
            if "docker-compose" in fname:
                content = content_for(scan_result, fm.path)
                if content:
                    # Count actual service entries (build: or image:)
                    services = content.count("build:") + content.count("image:")
                    # 3 is common for a normal fullstack app (frontend+backend+db)
                    # Only flag as microservices with 4+ distinct services
                    if services >= 4:
                        return True

        # Check for explicit service-naming patterns in directories
        # (e.g., services/auth-service, services/user-service)
        service_dirs: Set[str] = set()
        for fm in iter_files(scan_result):
            parts = fm.path.lower().replace("\\", "/").split("/")
            for part in parts[:-1]:  # exclude filename
                if (
                    part.endswith("-service")
                    or part.endswith("_service")
                    or (len(parts) >= 3 and parts[0] == "services")
                ):
                    service_dirs.add(part)
        if len(service_dirs) >= 3:
            return True

        return False

    def _is_cli(
        self,
        deps: List[DetectedDependency],
        dep_names: Set[str],
        scan_result: ScanResult,
    ) -> bool:
        """Check for CLI tool signals."""
        cli_libs = {"click", "typer", "argparse", "fire", "docopt"}
        if cli_libs & dep_names:
            return True

        # Check pyproject.toml for console_scripts
        for fm in iter_files(scan_result):
            if fm.path.lower().endswith("pyproject.toml"):
                content = content_for(scan_result, fm.path)
                if content and "console_scripts" in content:
                    return True

        # Check code for argparse usage
        from app.intelligence.utils.path_utils import iter_contents
        for path, content in iter_contents(scan_result):
            if "argparse" in content[:10000] or "ArgumentParser" in content[:10000]:
                return True

        return False

    def _is_library(
        self,
        scan_result: ScanResult,
        eps: List[DetectedEntryPoint],
        apis: List[DetectedAPIEndpoint],
        deps: List[DetectedDependency],
        dep_names: Set[str],
    ) -> bool:
        """Check for library/package pattern."""
        has_package_config = False
        for fm in iter_files(scan_result):
            fname = fm.path.lower().replace("\\", "/")
            if any(fname.endswith(c) for c in ("setup.py", "setup.cfg", "pyproject.toml", "cargo.toml")):
                has_package_config = True
                break

        if not has_package_config:
            return False

        # No app entrypoint, no API endpoints
        app_eps = [e for e in eps if e.type in ("backend", "frontend")]
        return len(app_eps) == 0 and len(apis) == 0
