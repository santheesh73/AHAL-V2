from app.docs.generators.workflow_generator import WorkflowGenerator
from app.docs.fact_snapshot import PRDFactSnapshot
from unittest.mock import MagicMock

def test_workflow_generation(mock_intelligence_result):
    gen = WorkflowGenerator()
    res, warnings = gen.generate(mock_intelligence_result)
    assert len(res) == 1
    assert res[0].source == "API"
    assert res[0].target == "Database"
    assert not warnings


def test_backend_workflow_mentions_diagnose_and_search_routes():
    gen = WorkflowGenerator()
    diagnose = MagicMock(); diagnose.path = "/diagnose"
    search = MagicMock(); search.path = "/search"
    intel = MagicMock()
    intel.api_endpoints = [diagnose, search]
    intel.workflow = None
    snapshot = PRDFactSnapshot(has_backend=True, api_count=2, project_type="backend")
    res, warnings = gen.generate(intel, snapshot=snapshot)
    joined = " ".join(f"{item.source} {item.action} {item.target or ''}" for item in res)
    assert "Diagnosis API" in joined
    assert "Retrieval API" in joined
