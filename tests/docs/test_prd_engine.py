from app.docs.prd_engine import PRDEngine
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

def test_prd_overview_uses_product_purpose():
    engine = PRDEngine()
    mock_scan = MagicMock()
    mock_scan.contents = {
        "readme.md": b"# Kannadi Med\n\nAI-assisted diagnosis engine.\n",
    }
    
    mock_api = MagicMock()
    mock_api.path = "/diagnose"
    
    mock_intel = MagicMock()
    mock_intel.api_endpoints = [mock_api]
    mock_intel.modules = []
    mock_intel.frameworks = []
    mock_intel.architecture = "Backend"
    mock_intel.dependencies = []
    
    res = engine.generate(mock_scan, mock_intel, MagicMock())
    
    assert "Kannadi Med" in res.overview.content
    assert "diagnosis" in res.overview.content
    assert res.overview.confidence in ("high", "medium")

def test_prd_overview_uses_startup_level_summary_for_ahal_ai():
    engine = PRDEngine()
    mock_scan = MagicMock()
    mock_scan.contents = {
        "README.md": b"# AHAL AI\n\nAI-Powered Developer Intelligence System.\n",
        "frontend/dashboard/page.tsx": b"export default function Dashboard() {}\n",
    }

    mock_api_1 = MagicMock(); mock_api_1.path = "/analyze"
    mock_api_2 = MagicMock(); mock_api_2.path = "/ask"
    mock_api_3 = MagicMock(); mock_api_3.path = "/summarize"
    mock_api_4 = MagicMock(); mock_api_4.path = "/report"

    mock_mod = MagicMock(); mock_mod.name = "chat_service"

    mock_fw_1 = MagicMock(); mock_fw_1.name = "FastAPI"
    mock_fw_2 = MagicMock(); mock_fw_2.name = "Next.js"

    mock_db = MagicMock(); mock_db.name = "MongoDB"

    mock_intel = MagicMock()
    mock_intel.api_endpoints = [mock_api_1, mock_api_2, mock_api_3, mock_api_4]
    mock_intel.modules = [mock_mod]
    mock_intel.frameworks = [mock_fw_1, mock_fw_2]
    mock_intel.architecture = "Fullstack"
    mock_intel.dependencies = []
    mock_intel.databases = [mock_db]

    res = engine.generate(mock_scan, mock_intel, MagicMock())

    content_lower = res.overview.content.lower()
    assert "ahal ai" in content_lower
    assert "repository intelligence" in content_lower or "code intelligence" in content_lower
    assert "fastapi" in content_lower
    assert res.project_brief is not None
    assert res.overview.confidence in ("high", "medium")


def test_prd_engine_survives_dependency_evidence_and_keeps_product_overview():
    engine = PRDEngine()
    mock_scan = MagicMock()
    mock_scan.contents = {
        "README.md": b"# AHAL AI\n\nAI-Powered Developer Intelligence System.\n",
    }

    mock_api_1 = MagicMock(); mock_api_1.path = "/analyze"
    mock_api_2 = MagicMock(); mock_api_2.path = "/report"
    mock_fw_1 = MagicMock(); mock_fw_1.name = "FastAPI"
    mock_fw_2 = MagicMock(); mock_fw_2.name = "React"
    mock_db = MagicMock(); mock_db.name = "SQLite"
    dep = MagicMock(); dep.name = "openai"

    mock_intel = MagicMock()
    mock_intel.api_endpoints = [mock_api_1, mock_api_2]
    mock_intel.modules = []
    mock_intel.frameworks = [mock_fw_1, mock_fw_2]
    mock_intel.architecture = "Fullstack"
    mock_intel.dependencies = [dep]
    mock_intel.databases = [mock_db]

    res = engine.generate(mock_scan, mock_intel, MagicMock())

    assert res.overview.content
    assert "Generation failed" not in res.overview.content
    assert res.project_brief is not None
    assert res.project_brief.goal.content != "Generation failed."
    assert res.project_brief.what.content != "Generation failed."
    assert "ahal ai" in res.overview.content.lower()
    assert any(ev.source_id == "dep:openai" for ev in res.overview.evidence)
    assert all(ev.source_type != "dependency" for ev in res.overview.evidence)
