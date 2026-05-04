from app.docs.models import WorkflowSectionItem, DocEvidence
from app.docs.utils.doc_evidence import sanitize_evidence
from app.docs.fact_snapshot import PRDFactSnapshot, build_fact_snapshot

class WorkflowGenerator:
    def generate(self, intelligence_result, snapshot: PRDFactSnapshot | None = None) -> tuple[list[WorkflowSectionItem], list[str]]:
        items = []
        warnings = []
        snapshot = snapshot or build_fact_snapshot(intelligence_result=intelligence_result)
        
        workflow = getattr(intelligence_result, "workflow", None)
        route_paths = [str(getattr(item, "path", "") or "").lower() for item in getattr(intelligence_result, "api_endpoints", []) or []]
        if not workflow:
            return self._deterministic_workflow(snapshot, route_paths), warnings
            
        steps = getattr(workflow, "steps", [])
        if not steps:
            return self._deterministic_workflow(snapshot, route_paths), warnings
            
        for step in steps:
            evidence = sanitize_evidence(getattr(step, "evidence", []))
            confidence = getattr(step, "confidence", "medium")
            if not evidence and confidence != "low":
                confidence = "low"
                
            items.append(WorkflowSectionItem(
                order=getattr(step, "order", 0),
                source=getattr(step, "source", "unknown"),
                action=getattr(step, "action", "interacts with"),
                target=getattr(step, "target", None),
                evidence=evidence,
                confidence=confidence
            ))

        if snapshot.has_frontend and not snapshot.has_backend:
            joined = " ".join(
                f"{item.source} {item.action} {item.target or ''}".lower()
                for item in items
            )
            if any(token in joined for token in ("server application", "route handler", "service layer", "backend returns response")):
                return self._deterministic_workflow(snapshot, route_paths), warnings
        if snapshot.has_backend and any(token in route_paths for token in ("/diagnose", "/search")):
            joined = " ".join(f"{item.source} {item.action} {item.target or ''}".lower() for item in items)
            if "diagnosis api" not in joined and "retrieval api" not in joined and "search api" not in joined and all(not item.evidence for item in items):
                return self._deterministic_workflow(snapshot, route_paths), warnings
            
        # Check if partial (e.g., missing frontend or db in steps)
        sources = {i.source for i in items}
        targets = {i.target for i in items if i.target}
        entities = sources | targets
        
        has_db = any("db" in str(e).lower() or "database" in str(e).lower() for e in entities)
        if snapshot.has_database and not has_db:
            warnings.append("Partial workflow detected: no database interactions found.")
            
        return items, warnings

    def _deterministic_workflow(self, snapshot: PRDFactSnapshot, route_paths: list[str]) -> list[WorkflowSectionItem]:
        if snapshot.has_frontend and not snapshot.has_backend:
            return [
                WorkflowSectionItem(order=1, source="User", action="opens", target="Frontend application", confidence="medium"),
                WorkflowSectionItem(order=2, source="React/Vite application", action="initializes", target="UI runtime", confidence="medium"),
                WorkflowSectionItem(order=3, source="UI routes/pages", action="render", target="Components", confidence="medium"),
                WorkflowSectionItem(order=4, source="Components", action="call", target="API service when configured", confidence="medium"),
                WorkflowSectionItem(order=5, source="External backend/API", action="may handle", target="Requests", confidence="low"),
            ]
        if snapshot.has_frontend and snapshot.has_backend:
            db_target = "Database/storage" if snapshot.has_database else "Response handling"
            return [
                WorkflowSectionItem(order=1, source="User", action="opens", target="Frontend application", confidence="medium"),
                WorkflowSectionItem(order=2, source="Frontend application", action="calls", target="Backend API", confidence="medium"),
                WorkflowSectionItem(order=3, source="Backend API", action="delegates to", target="Application/service logic", confidence="medium"),
                WorkflowSectionItem(order=4, source="Application/service logic", action="uses", target=db_target, confidence="medium"),
                WorkflowSectionItem(order=5, source="Backend API", action="returns", target="Frontend response", confidence="medium"),
            ]
        steps = [
            WorkflowSectionItem(order=1, source="Client / API Consumer", action="sends request to", target="FastAPI Route Layer", confidence="medium"),
        ]
        order = 2
        if any("/diagnose" in path for path in route_paths):
            steps.append(WorkflowSectionItem(order=order, source="FastAPI Route Layer", action="routes diagnosis requests to", target="Diagnosis API", confidence="medium"))
            order += 1
        if any("/search" in path for path in route_paths):
            steps.append(WorkflowSectionItem(order=order, source="FastAPI Route Layer", action="routes retrieval/search requests to", target="Retrieval API", confidence="medium"))
            order += 1
        if order == 2:
            steps.append(WorkflowSectionItem(order=order, source="FastAPI Route Layer", action="routes request to", target="Application Logic", confidence="medium"))
            order += 1
        else:
            steps.append(WorkflowSectionItem(order=order, source="Diagnosis API / Retrieval API", action="delegates to", target="Application Logic", confidence="medium"))
            order += 1
        if snapshot.has_database:
            steps.append(WorkflowSectionItem(order=order, source="Application Logic", action="uses", target="Database/storage", confidence="medium"))
            order += 1
            steps.append(WorkflowSectionItem(order=order, source="Application Logic", action="returns", target="Response", confidence="medium"))
        else:
            steps.append(WorkflowSectionItem(order=order, source="Application Logic", action="returns", target="Response", confidence="medium"))
        return steps
