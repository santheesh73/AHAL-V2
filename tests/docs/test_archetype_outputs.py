from app.docs.exporters.markdown_exporter import MarkdownExporter
from app.docs.exporters.pdf_exporter import PDFExporter
from app.docs.prd_engine import PRDEngine
from app.graph.graph_engine import KnowledgeGraphEngine
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.test_repository_archetypes import _cli_scan, _dataset_scan, _python_package_scan


def _build_prd(scan, session_id: str):
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    return PRDEngine().generate(scan, intelligence, graph, session_id=session_id)


def test_cli_workflow_and_outputs_are_archetype_aware():
    prd = _build_prd(_cli_scan(), "cli-doc-1")
    workflow = " ".join(f"{item.source} {item.action} {item.target or ''}" for item in prd.workflow).lower()
    markdown = MarkdownExporter().export(prd).lower()

    assert prd.canonical_intelligence is not None
    assert prd.canonical_intelligence.repo_type == "cli_tool"
    assert "cli" in workflow or "command" in workflow
    assert "client / api consumer" not in workflow
    assert "database/storage" not in workflow
    assert "backend api layer" not in markdown


def test_package_outputs_use_package_language():
    prd = _build_prd(_python_package_scan(), "pkg-doc-1")
    markdown = MarkdownExporter().export(prd).lower()
    pdf_text = PDFExporter().export(prd).decode("latin-1", errors="ignore").lower()

    for text in (markdown, pdf_text):
        assert "package/api surface" in text
        assert "no http api endpoints were identified" in text or "public api surface" in text
        assert "backend api layer" not in text


def test_dataset_outputs_use_dataset_language():
    prd = _build_prd(_dataset_scan(), "dataset-doc-1")
    markdown = MarkdownExporter().export(prd).lower()

    assert prd.canonical_intelligence is not None
    assert prd.canonical_intelligence.repo_type == "dataset"
    assert "dataset overview" in markdown
    assert "dataset files" in markdown
    assert "backend api layer" not in markdown
