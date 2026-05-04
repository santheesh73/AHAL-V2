import pytest
from app.docs.exporters.pdf_exporter import PDFExporter
from app.docs.prd_engine import PRDEngine
from app.docs.models import (
    PRDResult,
    PRDSection,
    ModuleSectionItem,
    APISectionItem,
    WorkflowSectionItem,
    RiskItem,
    DocEvidence,
)
from unittest.mock import MagicMock

def _make_dummy_prd(empty=False):
    if empty:
        return PRDResult(
            session_id="test-session",
            title="Empty PRD",
            project_type="Unknown",
            overview=PRDSection(title="Overview", content="", confidence="low"),
            architecture=PRDSection(title="Architecture", content="", confidence="low"),
            tech_stack=PRDSection(title="Tech Stack", content="", confidence="low"),
            modules=[],
            api_endpoints=[],
            workflow=[],
            databases=PRDSection(title="Database", content="", confidence="low"),
            setup_notes=PRDSection(title="Setup", content="", confidence="low"),
            risks=[],
            confidence="low",
            warnings=[]
        )
    return PRDResult(
        session_id="test-session",
        title="Test Project",
        project_type="Backend Service",
        overview=PRDSection(title="Overview", content="A nice backend service.", confidence="high"),
        architecture=PRDSection(title="Architecture", content="Backend Architecture with API Surface.", confidence="high"),
        tech_stack=PRDSection(title="Tech Stack", content="FastAPI, Python", confidence="high"),
        modules=[
            ModuleSectionItem(
                name="api",
                category="api",
                files=["app/api/routes.py"],
                description="API module",
                evidence=[],
                confidence="high",
            )
        ],
        api_endpoints=[
            APISectionItem(
                method="POST",
                path="/diagnose",
                framework="FastAPI",
                source_file="app/api/routes.py",
                handler="create_user",
                description="Diagnose stuff",
                evidence=[],
                confidence="high",
            )
        ],
        workflow=[
            WorkflowSectionItem(
                order=1,
                source="Client",
                action="POST",
                target="API",
                evidence=[],
                confidence="high",
            )
        ],
        databases=PRDSection(title="Database", content="No database.", confidence="high"),
        setup_notes=PRDSection(title="Setup", content="run uvicorn", confidence="high"),
        risks=[
            RiskItem(
                title="No auth detected",
                severity="medium",
                description="No explicit auth module detected.",
                evidence=[],
                recommendation="Add authentication if required.",
            )
        ],
        confidence="high",
        evidence_count=10,
        warnings=["Some warning about node_modules", "Another warning with type='str'"]
    )

def test_pdf_exporter_returns_bytes():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert isinstance(out, bytes)

def test_pdf_starts_with_pdf_header():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert out.startswith(b"%PDF")

def test_pdf_contains_title():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    # the uncompressed text should contain the title
    assert b"AHAL AI" in out
    assert b"Project Requirement Document" in out
    assert b"Backend Service" in out

def test_pdf_includes_executive_summary():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert b"Executive Summary" in out

def test_pdf_includes_project_intelligence_brief():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert b"Project Intelligence Brief" in out

def test_pdf_exporter_empty_prd_no_crash():
    exporter = PDFExporter()
    prd = _make_dummy_prd(empty=True)
    out = exporter.export(prd)
    assert isinstance(out, bytes)

def test_pdf_exporter_no_gemini_call(monkeypatch):
    import app.intelligence.llm.gemini_client as gemini_module
    def fail_if_called(*args, **kwargs):
        pytest.fail("Gemini was called!")
    monkeypatch.setattr(gemini_module.GeminiClient, "generate", fail_if_called)
    
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert isinstance(out, bytes)

def test_pdf_exporter_excludes_ignored_paths():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert b"node_modules" not in out
    assert b"[REDACTED]" in out

def test_pdf_exporter_excludes_raw_repr_strings():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert b"type='" not in out

def test_pdf_includes_watermark():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert b"Generated by AHAL AI" in out
    assert b"Team Ragnarok" in out

def test_pdf_includes_architecture_diagram():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert b"Architecture Diagram" in out

def test_pdf_includes_workflow_diagram():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert b"Workflow Diagram" in out

def test_pdf_includes_api_endpoints():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd)
    assert b"/diagnose" in out

def test_pdf_exporter_long_text_no_crash():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    prd.overview.content = "long text " * 5000
    out = exporter.export(prd)
    assert isinstance(out, bytes)

def test_pdf_exporter_handles_none_fields():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    prd.api_endpoints[0].handler = None
    prd.api_endpoints[0].source_file = None
    prd.workflow[0].target = None
    prd.modules[0].files = None
    out = exporter.export(prd)
    assert isinstance(out, bytes)
    assert out.startswith(b"%PDF")

def test_pdf_exporter_accepts_polished_text():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    polished_text = {
        "executive_summary": "A polished backend service overview.",
        "project_goal": "Deliver the backend capability clearly.",
        "what": "This is a backend service for diagnosis workflows.",
        "why": "It exists to support the main application workflow safely.",
        "built_summary": "Built components include deterministic API handling and backend modules.",
        "remaining_summary": "Remaining work includes authentication and stronger deployment support.",
        "risk_summary": "Detected issues include no auth detected.",
        "next_steps": ["Add authentication if required."],
        "section_intros": {
            "architecture": "Architecture details below remain deterministic.",
            "tech_stack": "The stack below is preserved from deterministic analysis.",
            "core_modules": "The modules below remain deterministic.",
            "api_surface": "The APIs below remain deterministic.",
            "workflow": "The workflow below remains deterministic.",
            "database_storage": "The storage notes below remain deterministic.",
            "setup_notes": "The setup notes below remain deterministic.",
            "evidence_summary": "The evidence summary below remains deterministic.",
            "warnings": "Warnings below remain deterministic.",
        },
    }
    out = exporter.export(prd, polished_text=polished_text)
    assert b"A polished backend service overview." in out
    assert b"Deliver the backend capability clearly." in out

def test_pdf_exporter_falls_back_without_polished_text():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    out = exporter.export(prd, polished_text=None)
    assert b"A nice backend service." in out

def test_pdf_still_contains_deterministic_api_endpoints():
    exporter = PDFExporter()
    prd = _make_dummy_prd()
    polished_text = {
        "executive_summary": "A polished backend service overview.",
        "project_goal": "Deliver the backend capability clearly.",
        "what": "This is a backend service for diagnosis workflows.",
        "why": "It exists to support the main application workflow safely.",
        "built_summary": "Built components include deterministic API handling and backend modules.",
        "remaining_summary": "Remaining work includes authentication and stronger deployment support.",
        "risk_summary": "Detected issues include no auth detected.",
        "next_steps": ["Add authentication if required."],
        "section_intros": {
            "architecture": "Architecture details below remain deterministic.",
            "tech_stack": "The stack below is preserved from deterministic analysis.",
            "core_modules": "The modules below remain deterministic.",
            "api_surface": "The APIs below remain deterministic.",
            "workflow": "The workflow below remains deterministic.",
            "database_storage": "The storage notes below remain deterministic.",
            "setup_notes": "The setup notes below remain deterministic.",
            "evidence_summary": "The evidence summary below remains deterministic.",
            "warnings": "Warnings below remain deterministic.",
        },
    }
    out = exporter.export(prd, polished_text=polished_text)
    assert b"/diagnose" in out
    assert b"FastAPI" in out


def test_pdf_exporter_does_not_emit_generation_failed_for_dependency_overview():
    engine = PRDEngine()
    exporter = PDFExporter()

    mock_scan = MagicMock()
    mock_scan.contents = {
        "README.md": b"# AHAL AI\n\nAI-Powered Developer Intelligence System.\n",
    }

    mock_api_1 = MagicMock(); mock_api_1.path = "/analyze"
    mock_api_2 = MagicMock(); mock_api_2.path = "/session/status"
    mock_fw_1 = MagicMock(); mock_fw_1.name = "FastAPI"
    mock_fw_2 = MagicMock(); mock_fw_2.name = "Next.js"
    mock_db = MagicMock(); mock_db.name = "MongoDB"
    dep = MagicMock(); dep.name = "openai"

    mock_intel = MagicMock()
    mock_intel.api_endpoints = [mock_api_1, mock_api_2]
    mock_intel.modules = []
    mock_intel.frameworks = [mock_fw_1, mock_fw_2]
    mock_intel.architecture = "Fullstack"
    mock_intel.dependencies = [dep]
    mock_intel.databases = [mock_db]

    prd = engine.generate(mock_scan, mock_intel, MagicMock())
    out = exporter.export(prd)

    assert b"Generation failed" not in out
    assert b"Executive Summary" in out
    assert b"Project Goal" in out
    assert b"What" in out
