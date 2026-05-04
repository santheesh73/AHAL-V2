from __future__ import annotations

from app.docs.prd_engine import PRDEngine
from app.docs.template_engine import PRDTemplateEngine
from app.intelligence.intelligence_engine import IntelligenceEngine
from app.graph.graph_engine import KnowledgeGraphEngine
from tests.intelligence.conftest import python_fastapi_scan


def _prd():
    scan = python_fastapi_scan()
    intelligence = IntelligenceEngine().analyze(scan, include_llm_explanation=False)
    graph = KnowledgeGraphEngine().build(scan_result=scan, intelligence_result=intelligence, session_id="template")
    return PRDEngine().generate(scan_result=scan, intelligence_result=intelligence, graph_result=graph, session_id="template")


def test_valid_template_accepted():
    template = PRDTemplateEngine().validate_template(
        {
            "name": "Engineering Handoff",
            "sections": [
                {"section_id": "overview", "title": "Overview", "source": "overview", "required": True, "render_as": "paragraph"},
            ],
        }
    )
    assert template.name == "Engineering Handoff"
    assert template.sections[0].source == "overview"


def test_invalid_source_rejected():
    try:
        PRDTemplateEngine().validate_template(
            {
                "name": "Bad",
                "sections": [
                    {"section_id": "x", "title": "X", "source": "filesystem", "required": True, "render_as": "paragraph"},
                ],
            }
        )
    except Exception as exc:
        assert "source" in str(exc).lower()
    else:
        raise AssertionError("Expected invalid source rejection")


def test_template_renders_markdown_and_custom_static_text():
    prd = _prd()
    engine = PRDTemplateEngine()
    template = engine.validate_template(
        {
            "name": "API Review",
            "sections": [
                {"section_id": "intro", "title": "Intro", "source": "custom_static", "required": True, "render_as": "paragraph", "static_text": "Team handoff only."},
                {"section_id": "apis", "title": "API Surface", "source": "api_surface", "required": True, "render_as": "table"},
            ],
        }
    )
    rendered = engine.render_markdown(prd, template)
    assert "# API Review" in rendered.markdown
    assert "Team handoff only." in rendered.markdown
    assert "| Column 1 |" in rendered.markdown


def test_missing_data_gets_safe_fallback_and_no_code_execution():
    prd = _prd()
    engine = PRDTemplateEngine()
    template = engine.validate_template(
        {
            "name": "Onboarding Brief",
            "sections": [
                {"section_id": "onboarding", "title": "Onboarding", "source": "onboarding", "required": True, "render_as": "bullets"},
                {"section_id": "static", "title": "Static", "source": "custom_static", "required": True, "render_as": "paragraph", "static_text": "{{ dangerous_code() }}"},
            ],
        }
    )
    rendered = engine.render_markdown(prd, template, extra_context={})
    assert "Insufficient evidence from codebase." in rendered.markdown
    assert "dangerous_code()" in rendered.markdown
    assert "{{" not in rendered.markdown


def test_no_raw_repr_leakage_or_ignored_paths():
    prd = _prd()
    template = PRDTemplateEngine().validate_template(
        {
            "name": "Evidence",
            "sections": [
                {"section_id": "evidence", "title": "Evidence", "source": "evidence", "required": False, "render_as": "bullets"},
            ],
        }
    )
    rendered = PRDTemplateEngine().render_markdown(prd, template)
    payload = rendered.markdown.lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
    assert "node_modules" not in payload
