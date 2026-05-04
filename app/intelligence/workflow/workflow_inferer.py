"""
AHAL AI — Workflow Inferer (Phase 2, Step 11)

Infer execution workflow from evidence-backed intelligence.
Only claims steps that have supporting evidence.
Pure, deterministic.
"""

from __future__ import annotations

from typing import List, Optional, Set

from app.intelligence.models import (
    ArchitectureResult,
    ConfidenceLevel,
    DetectedAPIEndpoint,
    DetectedDatabase,
    DetectedEntryPoint,
    DetectedFramework,
    DetectedModule,
    WorkflowResult,
    WorkflowStep,
)
from app.intelligence.utils.evidence import make_evidence
from app.models.file_schema import ScanResult


class WorkflowInferer:
    """Infer execution workflow from intelligence signals."""

    def infer(
        self,
        scan_result: ScanResult,
        architecture: ArchitectureResult | None = None,
        frameworks: List[DetectedFramework] | None = None,
        entry_points: List[DetectedEntryPoint] | None = None,
        modules: List[DetectedModule] | None = None,
        api_endpoints: List[DetectedAPIEndpoint] | None = None,
        databases: List[DetectedDatabase] | None = None,
    ) -> WorkflowResult:
        arch = architecture or ArchitectureResult()
        fws = frameworks or []
        eps = entry_points or []
        mods = modules or []
        apis = api_endpoints or []
        dbs = databases or []

        fw_names: Set[str] = {f.name.lower() for f in fws}
        fw_cats: Set[str] = {f.category for f in fws}
        ep_types: Set[str] = {e.type for e in eps}
        mod_cats: Set[str] = {m.category for m in mods}

        steps: List[WorkflowStep] = []
        warnings: List[str] = []
        order = 1

        has_frontend = "frontend" in fw_cats or "frontend" in ep_types
        has_backend = "backend" in fw_cats or "backend" in ep_types
        has_api = len(apis) > 0
        has_db = len(dbs) > 0
        has_service = "service" in mod_cats

        # ── Layer 1: Frontend entrypoint ─────────────────────────
        if has_frontend:
            frontend_fws = [f.name for f in fws if f.category == "frontend"]
            frontend_eps = [e for e in eps if e.type == "frontend"]
            source = frontend_eps[0].file if frontend_eps else "frontend"
            fw_name = frontend_fws[0] if frontend_fws else "UI"

            steps.append(WorkflowStep(
                order=order,
                source="User",
                action=f"Accesses {fw_name} application",
                target=source,
                evidence=[make_evidence(
                    source,
                    f"Frontend entry point: {source}",
                    confidence="high" if frontend_eps else "medium",
                )],
                confidence="high" if frontend_eps else "medium",
            ))
            order += 1

        # ── Layer 2: HTTP API call (frontend → backend) ──────────
        if has_frontend and has_api:
            first_api = apis[0]
            steps.append(WorkflowStep(
                order=order,
                source="Frontend UI",
                action=f"HTTP {first_api.method} request",
                target=first_api.path,
                evidence=[make_evidence(
                    first_api.file,
                    f"API endpoint: {first_api.method} {first_api.path}",
                    confidence="high",
                )],
                confidence="high",
            ))
            order += 1

        # ── Layer 3: Backend entrypoint / app init ───────────────
        if has_backend:
            backend_eps = [e for e in eps if e.type == "backend"]
            backend_fws = [f.name for f in fws if f.category == "backend"]
            source = backend_eps[0].file if backend_eps else "backend"
            fw_name = backend_fws[0] if backend_fws else "Server"

            steps.append(WorkflowStep(
                order=order,
                source=source,
                action=f"Initializes {fw_name} application",
                target="route handlers" if has_api else "application logic",
                evidence=[make_evidence(
                    source,
                    f"Backend entry point: {source}",
                    confidence="high" if backend_eps else "medium",
                )],
                confidence="high" if backend_eps else "medium",
            ))
            order += 1

        # ── Layer 3b: Route handling ─────────────────────────────
        if has_api and not has_frontend:
            # Standalone backend — show API handling
            first_api = apis[0]
            steps.append(WorkflowStep(
                order=order,
                source="Client",
                action=f"HTTP {first_api.method} {first_api.path}",
                target=first_api.file,
                evidence=[make_evidence(
                    first_api.file,
                    f"API route handler: {first_api.method} {first_api.path}",
                    confidence="high",
                )],
                confidence="high",
            ))
            order += 1

        # ── Layer 4: Service layer ───────────────────────────────
        if has_service:
            service_mods = [m for m in mods if m.category == "service"]
            if service_mods:
                svc = service_mods[0]
                steps.append(WorkflowStep(
                    order=order,
                    source="Route handler",
                    action="Delegates to service layer",
                    target=svc.name,
                    evidence=[make_evidence(
                        svc.files[0] if svc.files else "",
                        f"Service module: {svc.name}",
                        confidence="medium",
                    )],
                    confidence="medium",
                ))
                order += 1

        # ── Layer 5: Database ────────────────────────────────────
        if has_db:
            db = dbs[0]
            source_layer = "Service layer" if has_service else ("Route handler" if has_api else "Application")
            steps.append(WorkflowStep(
                order=order,
                source=source_layer,
                action=f"Queries {db.name} ({db.usage})",
                target=db.name,
                evidence=db.evidence[:2] if db.evidence else [
                    make_evidence("", f"Database: {db.name}", confidence="medium")
                ],
                confidence=db.confidence,
            ))
            order += 1

        # ── Layer 6: Response ────────────────────────────────────
        if has_api or has_backend:
            steps.append(WorkflowStep(
                order=order,
                source="Backend",
                action="Returns response",
                target="Client" if not has_frontend else "Frontend UI",
                evidence=[make_evidence("", "API response flow", confidence="medium")],
                confidence="medium",
            ))
            order += 1

        # ── Determine completeness ───────────────────────────────
        layers_present = sum([
            has_frontend,
            has_api or has_backend,
            has_service,
            has_db,
        ])

        if layers_present >= 4:
            completeness = "complete"
            confidence: ConfidenceLevel = "high"
        elif layers_present >= 2:
            completeness = "partial"
            confidence = "medium"
            if not has_db:
                warnings.append("No database layer detected — workflow may be incomplete")
            if not has_frontend and not has_backend:
                warnings.append("Missing primary application layer")
        elif layers_present == 1:
            completeness = "minimal"
            confidence = "low"
            warnings.append("Only one application layer detected — workflow is minimal")
        else:
            completeness = "unknown"
            confidence = "low"
            warnings.append("Insufficient evidence to infer execution workflow")

        return WorkflowResult(
            completeness=completeness,
            confidence=confidence,
            steps=steps,
            warnings=warnings,
        )
