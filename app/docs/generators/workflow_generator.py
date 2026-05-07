from app.docs.models import WorkflowSectionItem, DocEvidence
from app.docs.utils.doc_evidence import sanitize_evidence
from app.docs.fact_snapshot import PRDFactSnapshot, build_fact_snapshot
from app.intelligence.repository_type_classifier import is_documentation_repo_type, is_package_like_repo_type

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
        if is_documentation_repo_type(snapshot.repo_type):
            return [
                WorkflowSectionItem(order=1, source="Reader", action="opens", target="Repository documentation", confidence="high"),
                WorkflowSectionItem(order=2, source="README", action="introduces", target="Study plan or guide", confidence="high"),
                WorkflowSectionItem(order=3, source="Sections", action="organize", target="Topics, resources, and learning progression", confidence="high"),
                WorkflowSectionItem(order=4, source="Supporting docs", action="expand", target="Accessibility and supporting context", confidence="medium"),
                WorkflowSectionItem(order=5, source="Learner", action="follows", target="Roadmap independently", confidence="medium"),
            ]
        if snapshot.repo_type == "cli_tool":
            return [
                WorkflowSectionItem(order=1, source="User", action="runs", target="CLI command", confidence="high"),
                WorkflowSectionItem(order=2, source="CLI runtime", action="parses", target="Arguments and flags", confidence="medium"),
                WorkflowSectionItem(order=3, source="Command handler", action="executes", target="Requested logic", confidence="medium"),
                WorkflowSectionItem(order=4, source="Tool runtime", action="uses", target="Configured files or services", confidence="low"),
                WorkflowSectionItem(order=5, source="CLI", action="returns", target="Terminal output", confidence="medium"),
            ]
        if is_package_like_repo_type(snapshot.repo_type):
            return [
                WorkflowSectionItem(order=1, source="Developer", action="installs", target="Package/library", confidence="high"),
                WorkflowSectionItem(order=2, source="Consumer application", action="imports", target="Public APIs", confidence="high"),
                WorkflowSectionItem(order=3, source="Package logic", action="executes", target="Requested functionality", confidence="medium"),
                WorkflowSectionItem(order=4, source="Package runtime", action="uses", target="Optional dependencies or platform clients", confidence="low"),
                WorkflowSectionItem(order=5, source="Package", action="returns", target="Results to caller", confidence="medium"),
            ]
        if snapshot.repo_type == "vscode_extension":
            return [
                WorkflowSectionItem(order=1, source="User", action="installs", target="VS Code extension", confidence="high"),
                WorkflowSectionItem(order=2, source="VS Code", action="triggers", target="Activation event", confidence="medium"),
                WorkflowSectionItem(order=3, source="Extension", action="runs", target="Command or panel logic", confidence="medium"),
                WorkflowSectionItem(order=4, source="Extension logic", action="uses", target="Local logic or optional services", confidence="low"),
                WorkflowSectionItem(order=5, source="Extension", action="updates", target="Editor workflow", confidence="medium"),
            ]
        if snapshot.repo_type == "browser_extension":
            return [
                WorkflowSectionItem(order=1, source="Browser", action="loads", target="Extension manifest", confidence="high"),
                WorkflowSectionItem(order=2, source="Extension runtime", action="starts", target="Background/content scripts", confidence="medium"),
                WorkflowSectionItem(order=3, source="User action", action="triggers", target="Extension behavior", confidence="medium"),
                WorkflowSectionItem(order=4, source="Extension logic", action="uses", target="Browser APIs or optional network calls", confidence="low"),
                WorkflowSectionItem(order=5, source="Extension", action="updates", target="Browser UI or page behavior", confidence="medium"),
            ]
        if snapshot.repo_type in {"ml_model_repo", "data_science_notebooks", "research_code"}:
            return [
                WorkflowSectionItem(order=1, source="Notebook/model workflow", action="loads", target="Data and artifacts", confidence="high"),
                WorkflowSectionItem(order=2, source="Preprocessing", action="prepares", target="Inputs", confidence="medium"),
                WorkflowSectionItem(order=3, source="Training/inference analysis", action="runs", target="Core analytical workflow", confidence="medium"),
                WorkflowSectionItem(order=4, source="Evaluation", action="inspects", target="Metrics and outputs", confidence="medium"),
                WorkflowSectionItem(order=5, source="Repository", action="produces", target="Results or artifacts", confidence="medium"),
            ]
        if snapshot.repo_type == "dataset":
            return [
                WorkflowSectionItem(order=1, source="Consumer", action="downloads", target="Dataset assets", confidence="high"),
                WorkflowSectionItem(order=2, source="Documentation", action="describes", target="Metadata and schema", confidence="high"),
                WorkflowSectionItem(order=3, source="Consumer tooling", action="loads", target="Dataset files", confidence="medium"),
                WorkflowSectionItem(order=4, source="Validation", action="checks", target="Quality and provenance", confidence="low"),
                WorkflowSectionItem(order=5, source="Dataset", action="supports", target="Analysis or training", confidence="medium"),
            ]
        if snapshot.repo_type in {"template", "monorepo"}:
            return [
                WorkflowSectionItem(order=1, source="Developer", action="clones", target="Repository", confidence="high"),
                WorkflowSectionItem(order=2, source="Developer", action="configures", target="Environment and placeholders", confidence="medium"),
                WorkflowSectionItem(order=3, source="Workspace tooling", action="installs", target="Dependencies", confidence="medium"),
                WorkflowSectionItem(order=4, source="Developer", action="adapts", target="Template or package workspace", confidence="medium"),
                WorkflowSectionItem(order=5, source="Repository", action="supports", target="Downstream project development", confidence="medium"),
            ]
        if snapshot.repo_type in {"infrastructure", "devops_automation"}:
            return [
                WorkflowSectionItem(order=1, source="Operator", action="reviews", target="Infrastructure or pipeline config", confidence="high"),
                WorkflowSectionItem(order=2, source="Automation command", action="starts", target="Plan/apply/deploy workflow", confidence="medium"),
                WorkflowSectionItem(order=3, source="Automation engine", action="provisions", target="Resources or pipeline steps", confidence="medium"),
                WorkflowSectionItem(order=4, source="Environment state", action="updates", target="Provisioned infrastructure", confidence="medium"),
                WorkflowSectionItem(order=5, source="Operator", action="reviews", target="Outputs and status", confidence="medium"),
            ]
        if snapshot.repo_type == "design_assets":
            return [
                WorkflowSectionItem(order=1, source="Designer/developer", action="opens", target="Asset repository", confidence="high"),
                WorkflowSectionItem(order=2, source="Asset library", action="organizes", target="Source files and exports", confidence="medium"),
                WorkflowSectionItem(order=3, source="Consumer workflow", action="imports", target="Selected assets", confidence="medium"),
                WorkflowSectionItem(order=4, source="Design pipeline", action="adapts", target="Formats or sizes", confidence="low"),
                WorkflowSectionItem(order=5, source="Assets", action="support", target="Downstream product/media work", confidence="medium"),
            ]
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
