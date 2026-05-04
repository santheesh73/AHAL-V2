import pytest
from unittest.mock import MagicMock
from app.docs.models import DocEvidence

def make_doc_evidence(
    source_type="file",
    source_id="README.md",
    file="README.md",
    reason="Test evidence",
    snippet=None,
    confidence="high",
):
    return DocEvidence(
        source_type=source_type,
        source_id=source_id,
        file=file,
        reason=reason,
        snippet=snippet,
        confidence=confidence,
    )

@pytest.fixture
def mock_scan_result():
    scan = MagicMock()
    scan.contents = {
        "README.md": "# Kannadi Med\nKannadi Med is a FastAPI-based backend that appears to provide an offline-first RAG plus diagnosis API.",
        "requirements.txt": "fastapi\nuvicorn"
    }
    return scan

@pytest.fixture
def mock_intelligence_result():
    intel = MagicMock()
    intel.architecture = "backend"
    
    fw = MagicMock()
    fw.name = "FastAPI"
    fw.evidence = [make_doc_evidence(source_type="file", source_id="main.py", file="main.py", reason="import fastapi", confidence="high")]
    intel.frameworks = [fw]
    
    api1 = MagicMock()
    api1.method = "POST"
    api1.path = "/diagnose"
    api1.evidence = [make_doc_evidence(source_type="api_endpoint", source_id="POST:/diagnose", file="app/api.py", reason="route", confidence="high")]
    api1.framework = "FastAPI"
    
    api2 = MagicMock()
    api2.method = "POST"
    api2.path = "/search"
    api2.evidence = [make_doc_evidence(source_type="api_endpoint", source_id="POST:/search", file="app/api.py", reason="route", confidence="high")]
    api2.framework = "FastAPI"
    
    intel.api_endpoints = [api1, api2]
    
    mod = MagicMock()
    mod.name = "AuthModule"
    mod.category = "auth"
    mod.evidence = [make_doc_evidence(source_type="file", source_id="app/auth.py", file="app/auth.py", reason="auth logic", confidence="high")]
    intel.modules = [mod]
    
    db = MagicMock()
    db.name = "PostgreSQL"
    db.evidence = [make_doc_evidence(source_type="file", source_id="models.py", file="models.py", reason="SQLAlchemy", confidence="high")]
    intel.databases = [db]
    
    wf_step = MagicMock()
    wf_step.order = 1
    wf_step.source = "API"
    wf_step.action = "reads"
    wf_step.target = "Database"
    wf_step.evidence = [make_doc_evidence(source_type="function", source_id="read_db", file="app/db.py", reason="call", confidence="high")]
    wf_step.confidence = "high"
    wf = MagicMock()
    wf.steps = [wf_step]
    intel.workflow = wf
    intel.dependencies = []
    
    return intel
