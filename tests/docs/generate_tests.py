import os

test_dir = r"c:\Users\babus\OneDrive\Desktop\AHAL v2\tests\docs"
os.makedirs(test_dir, exist_ok=True)

with open(os.path.join(test_dir, "__init__.py"), "w") as f:
    f.write("")

conftest = """import pytest
from unittest.mock import MagicMock
from app.chat.models import EvidenceReference

@pytest.fixture
def mock_scan_result():
    scan = MagicMock()
    scan.contents = {
        "README.md": "# Kannadi Med\nKannadi Med is a FastAPI-based backend that appears to provide an offline-first RAG plus diagnosis API.",
        "requirements.txt": "fastapi\\nuvicorn"
    }
    return scan

@pytest.fixture
def mock_intelligence_result():
    intel = MagicMock()
    intel.architecture = "backend"
    
    fw = MagicMock()
    fw.name = "FastAPI"
    fw.evidence = [EvidenceReference(source_type="file", source_id="main.py", file="main.py", reason="import fastapi", confidence="high")]
    intel.frameworks = [fw]
    
    api1 = MagicMock()
    api1.method = "POST"
    api1.path = "/diagnose"
    api1.evidence = [EvidenceReference(source_type="api_endpoint", source_id="POST:/diagnose", file="app/api.py", reason="route", confidence="high")]
    api1.framework = "FastAPI"
    
    api2 = MagicMock()
    api2.method = "POST"
    api2.path = "/search"
    api2.evidence = [EvidenceReference(source_type="api_endpoint", source_id="POST:/search", file="app/api.py", reason="route", confidence="high")]
    api2.framework = "FastAPI"
    
    intel.api_endpoints = [api1, api2]
    
    mod = MagicMock()
    mod.name = "AuthModule"
    mod.category = "auth"
    mod.evidence = [EvidenceReference(source_type="file", source_id="app/auth.py", file="app/auth.py", reason="auth logic", confidence="high")]
    intel.modules = [mod]
    
    db = MagicMock()
    db.name = "PostgreSQL"
    db.evidence = [EvidenceReference(source_type="file", source_id="models.py", file="models.py", reason="SQLAlchemy", confidence="high")]
    intel.databases = [db]
    
    wf_step = MagicMock()
    wf_step.order = 1
    wf_step.source = "API"
    wf_step.action = "reads"
    wf_step.target = "Database"
    wf_step.evidence = [EvidenceReference(source_type="function", source_id="read_db", file="app/db.py", reason="call", confidence="high")]
    wf_step.confidence = "high"
    wf = MagicMock()
    wf.steps = [wf_step]
    intel.workflow = wf
    
    return intel
"""
with open(os.path.join(test_dir, "conftest.py"), "w") as f:
    f.write(conftest)

test_overview = """from app.docs.generators.overview_generator import OverviewGenerator

def test_overview_from_readme(mock_scan_result, mock_intelligence_result):
    gen = OverviewGenerator()
    res = gen.generate(mock_scan_result, mock_intelligence_result)
    assert "Kannadi Med is a FastAPI-based backend" in res.content
    assert res.confidence == "high"
"""
with open(os.path.join(test_dir, "test_overview_generator.py"), "w") as f:
    f.write(test_overview)

test_arch = """from app.docs.generators.architecture_generator import ArchitectureGenerator

def test_architecture_from_intelligence(mock_intelligence_result):
    gen = ArchitectureGenerator()
    res = gen.generate(mock_intelligence_result)
    assert "Architecture Type: Backend" in res.content
    assert "Primary Frameworks: FastAPI" in res.content
    assert res.confidence == "high"
"""
with open(os.path.join(test_dir, "test_architecture_generator.py"), "w") as f:
    f.write(test_arch)

test_tech = """from app.docs.generators.tech_stack_generator import TechStackGenerator

def test_tech_stack_section(mock_intelligence_result):
    gen = TechStackGenerator()
    res = gen.generate(mock_intelligence_result)
    assert "FastAPI" in res.content
    assert "PostgreSQL" in res.content
"""
with open(os.path.join(test_dir, "test_tech_stack_generator.py"), "w") as f:
    f.write(test_tech)

test_mod = """from app.docs.generators.module_generator import ModuleGenerator

def test_module_generation(mock_intelligence_result):
    gen = ModuleGenerator()
    res = gen.generate(mock_intelligence_result)
    assert len(res) == 1
    assert res[0].name == "AuthModule"
    assert "app/auth.py" in res[0].files
"""
with open(os.path.join(test_dir, "test_module_generator.py"), "w") as f:
    f.write(test_mod)

test_wf = """from app.docs.generators.workflow_generator import WorkflowGenerator

def test_workflow_generation(mock_intelligence_result):
    gen = WorkflowGenerator()
    res, warnings = gen.generate(mock_intelligence_result)
    assert len(res) == 1
    assert res[0].source == "API"
    assert res[0].target == "Database"
    assert not warnings
"""
with open(os.path.join(test_dir, "test_workflow_generator.py"), "w") as f:
    f.write(test_wf)

test_api = """from app.docs.generators.api_generator import APIGenerator

def test_api_generation_includes_diagnose(mock_intelligence_result):
    gen = APIGenerator()
    res = gen.generate(mock_intelligence_result)
    assert len(res) == 2
    paths = [a.path for a in res]
    assert "/diagnose" in paths
    assert "/search" in paths
"""
with open(os.path.join(test_dir, "test_api_generator.py"), "w") as f:
    f.write(test_api)

test_db = """from app.docs.generators.database_generator import DatabaseGenerator
from unittest.mock import MagicMock

def test_database_absence_message():
    gen = DatabaseGenerator()
    intel = MagicMock()
    intel.databases = []
    res = gen.generate(intel)
    assert "No database/storage layer detected" in res.content
"""
with open(os.path.join(test_dir, "test_database_generator.py"), "w") as f:
    f.write(test_db)

test_setup = """from app.docs.generators.setup_generator import SetupGenerator

def test_setup_notes_from_requirements(mock_scan_result):
    gen = SetupGenerator()
    res = gen.generate(mock_scan_result)
    assert "requirements.txt" in res.content
"""
with open(os.path.join(test_dir, "test_setup_generator.py"), "w") as f:
    f.write(test_setup)

test_risk = """from app.docs.generators.risk_generator import RiskGenerator
from unittest.mock import MagicMock

def test_risk_generation(mock_scan_result, mock_intelligence_result):
    gen = RiskGenerator()
    # It has auth and db, but no deployment config and no test
    risks = gen.generate(mock_scan_result, mock_intelligence_result, [])
    titles = [r.title for r in risks]
    assert "No tests detected" in titles
    assert "No deployment config detected" in titles
"""
with open(os.path.join(test_dir, "test_risk_generator.py"), "w") as f:
    f.write(test_risk)

test_prd = """from app.docs.prd_engine import PRDEngine
from unittest.mock import MagicMock

def test_empty_input_does_not_crash():
    engine = PRDEngine()
    res = engine.generate(MagicMock(), MagicMock(), MagicMock())
    assert res.title == "Project Requirements Document"

def test_prd_engine_returns_prd_result(mock_scan_result, mock_intelligence_result):
    engine = PRDEngine()
    res = engine.generate(mock_scan_result, mock_intelligence_result, MagicMock())
    assert res.overview.content
    # check no raw Pydantic repr
    assert "type=" not in res.overview.content
    assert "EvidenceItem(" not in res.overview.content
    assert "PRDSection(" not in res.overview.content
"""
with open(os.path.join(test_dir, "test_prd_engine.py"), "w") as f:
    f.write(test_prd)

