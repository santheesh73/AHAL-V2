from __future__ import annotations

from app.docs.diff_models import PRDDiffResult
from app.docs.models import APISectionItem, DocEvidence, ModuleSectionItem, PRDResult, PRDSection, ProjectBrief, ProjectStatusItem, RiskItem, WorkflowSectionItem
from app.docs.prd_diff_engine import PRDDiffEngine


def _evidence(source_id: str) -> DocEvidence:
    return DocEvidence(source_type="file", source_id=source_id, file=source_id, reason="evidence", confidence="high")


def _prd(
    api_paths=None,
    modules=None,
    databases="PostgreSQL detected.",
    risks=None,
    remaining=None,
    project_type="backend",
    architecture_text="Backend API with service and database layers.",
):
    api_paths = api_paths or []
    modules = modules or [("UsersAPI", "api", "User API module.")]
    risks = risks or []
    remaining = remaining or []
    return PRDResult(
        session_id="sid",
        title="Project Requirements Document",
        project_type=project_type,
        overview=PRDSection(title="Overview", content="Project overview.", confidence="high", evidence=[_evidence("README.md")]),
        project_brief=ProjectBrief(
            goal=PRDSection(title="Goal", content="Support repository intelligence.", confidence="high", evidence=[_evidence("README.md")]),
            what=PRDSection(title="What", content="Backend API service.", confidence="high", evidence=[_evidence("README.md")]),
            why=PRDSection(title="Why", content="To analyze repositories.", confidence="high", evidence=[_evidence("README.md")]),
            completed=[],
            remaining=[
                ProjectStatusItem(title=item, status="missing", description=item, confidence="medium", evidence=[_evidence("todo.md")])
                for item in remaining
            ],
            issues=[],
            next_steps=[],
            confidence="high",
        ),
        architecture=PRDSection(title="Architecture", content=architecture_text, confidence="high", evidence=[_evidence("main.py")]),
        tech_stack=PRDSection(title="Tech Stack", content="Python, FastAPI, PostgreSQL.", confidence="high", evidence=[_evidence("requirements.txt")]),
        modules=[
            ModuleSectionItem(name=name, category=category, description=description, files=[f"app/{name.lower()}.py"], confidence="high", evidence=[_evidence(f"app/{name.lower()}.py")])
            for name, category, description in modules
        ],
        api_endpoints=[
            APISectionItem(method=method, path=path, framework="FastAPI", description=f"{method} {path}", confidence="high", evidence=[_evidence("app/api/routes.py")])
            for method, path in api_paths
        ],
        databases=PRDSection(title="Database", content=databases, confidence="high", evidence=[_evidence("models.py")]),
        workflow=[WorkflowSectionItem(order=1, source="Client", action="calls API", target="Service", confidence="high", evidence=[_evidence("workflow")])],
        setup_notes=PRDSection(title="Setup", content="Run uvicorn.", confidence="medium", evidence=[_evidence("README.md")]),
        risks=[
            RiskItem(title=title, severity=severity, description=title, recommendation="Review carefully.", evidence=[_evidence("risk.md")])
            for severity, title in risks
        ],
        confidence="high",
        evidence_count=10,
        warnings=[],
    )


def test_same_prd_returns_mostly_unchanged_low_risk_diff():
    base = _prd(api_paths=[("GET", "/health")])
    target = _prd(api_paths=[("GET", "/health")])
    diff = PRDDiffEngine().compare(base, target, "a", "b")
    assert isinstance(diff, PRDDiffResult)
    assert not diff.api_diff
    assert diff.summary


def test_added_api_endpoint_detected():
    diff = PRDDiffEngine().compare(_prd(api_paths=[("GET", "/health")]), _prd(api_paths=[("GET", "/health"), ("POST", "/users")]), "a", "b")
    assert any(item.change_type == "added" and item.path == "/users" for item in diff.api_diff)


def test_removed_api_endpoint_high_risk():
    diff = PRDDiffEngine().compare(_prd(api_paths=[("GET", "/health"), ("POST", "/users")]), _prd(api_paths=[("GET", "/health")]), "a", "b")
    removed = next(item for item in diff.api_diff if item.path == "/users")
    assert removed.change_type == "removed"
    assert removed.risk_level == "high"


def test_added_database_detected_high_risk():
    diff = PRDDiffEngine().compare(_prd(databases="Insufficient evidence from codebase."), _prd(databases="PostgreSQL detected."), "a", "b")
    assert diff.database_diff.added
    assert any("schema compatibility" in item.lower() or "data access" in item.lower() for item in diff.suggested_review_focus)


def test_removed_database_detected_high_risk():
    diff = PRDDiffEngine().compare(_prd(databases="PostgreSQL detected."), _prd(databases="Insufficient evidence from codebase."), "a", "b")
    assert diff.database_diff.removed


def test_added_module_detected():
    diff = PRDDiffEngine().compare(_prd(modules=[("UsersAPI", "api", "User API module.")]), _prd(modules=[("UsersAPI", "api", "User API module."), ("BillingService", "service", "Billing service.")]), "a", "b")
    assert any(item.change_type == "added" and item.name == "BillingService" for item in diff.module_diff)


def test_removed_module_detected():
    diff = PRDDiffEngine().compare(_prd(modules=[("UsersAPI", "api", "User API module."), ("BillingService", "service", "Billing service.")]), _prd(modules=[("UsersAPI", "api", "User API module.")]), "a", "b")
    assert any(item.change_type == "removed" and item.name == "BillingService" for item in diff.module_diff)


def test_new_risk_appears_in_risk_diff():
    diff = PRDDiffEngine().compare(_prd(risks=[]), _prd(risks=[("high", "Auth gap detected")]), "a", "b")
    assert diff.risk_diff.added


def test_resolved_risk_appears_in_risk_diff():
    diff = PRDDiffEngine().compare(_prd(risks=[("high", "Auth gap detected")]), _prd(risks=[]), "a", "b")
    assert diff.risk_diff.removed


def test_suggested_review_focus_includes_api_compatibility_for_api_changes():
    diff = PRDDiffEngine().compare(_prd(api_paths=[("GET", "/health")]), _prd(api_paths=[("GET", "/health"), ("POST", "/users")]), "a", "b")
    assert any("api compatibility" in item.lower() for item in diff.suggested_review_focus)


def test_suggested_review_focus_includes_migration_schema_review_for_database_changes():
    diff = PRDDiffEngine().compare(_prd(databases="Insufficient evidence from codebase."), _prd(databases="PostgreSQL detected."), "a", "b")
    assert any("migration" in item.lower() or "schema" in item.lower() for item in diff.suggested_review_focus)


def test_no_raw_repr_leakage():
    diff = PRDDiffEngine().compare(_prd(), _prd(), "a", "b")
    payload = diff.model_dump_json().lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
