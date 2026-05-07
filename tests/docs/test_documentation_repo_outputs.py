from app.docs.exporters.markdown_exporter import MarkdownExporter
from app.docs.exporters.pdf_exporter import PDFExporter
from app.docs.prd_engine import PRDEngine
from app.graph.graph_engine import KnowledgeGraphEngine
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.test_repository_type_classifier import _coding_interview_university_scan


def test_curriculum_workflow_is_reader_flow():
    scan = _coding_interview_university_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    prd = PRDEngine().generate(scan, intelligence, graph, session_id="curriculum-docs-1")

    joined = " ".join(f"{item.source} {item.action} {item.target or ''}" for item in prd.workflow).lower()

    assert "reader" in joined
    assert "readme" in joined
    assert "study plan" in joined
    assert "api surface" not in joined
    assert "database/storage" not in joined


def test_curriculum_risks_not_app_risks():
    scan = _coding_interview_university_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    prd = PRDEngine().generate(scan, intelligence, graph, session_id="curriculum-docs-2")

    titles = [item.title.lower() for item in prd.risks]

    assert all("auth" not in title for title in titles)
    assert all("deployment" not in title for title in titles)
    assert all("database" not in title for title in titles)


def test_markdown_counts_as_documentation_language():
    scan = _coding_interview_university_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    prd = PRDEngine().generate(scan, intelligence, graph, session_id="curriculum-docs-3")

    assert prd.canonical_intelligence is not None
    assert "Markdown" in prd.canonical_intelligence.tech_stack.languages


def test_pdf_curriculum_output():
    scan = _coding_interview_university_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    prd = PRDEngine().generate(scan, intelligence, graph, session_id="curriculum-docs-4")

    markdown = MarkdownExporter().export(prd).lower()
    pdf_text = PDFExporter().export(prd).decode("latin-1", errors="ignore").lower()

    for text in (markdown, pdf_text):
        assert "devops" not in text
        assert "automation tool" not in text
        assert "backend api layer" not in text
        assert "client / api consumer" not in text
        assert "study plan" in text or "interview preparation" in text

