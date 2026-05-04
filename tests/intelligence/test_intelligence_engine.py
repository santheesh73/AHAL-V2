"""Tests for IntelligenceEngine (orchestrator)."""

from unittest.mock import MagicMock, patch

from app.intelligence.intelligence_engine import IntelligenceEngine
from app.intelligence.models import IntelligenceResult, LLMExplanation
from tests.intelligence.conftest import empty_scan_result, fullstack_scan, python_fastapi_scan


def test_fullstack_repo_returns_intelligence_result():
    engine = IntelligenceEngine()
    result = engine.analyze(fullstack_scan(), session_id="test-1")
    assert isinstance(result, IntelligenceResult)
    assert result.session_id == "test-1"
    assert len(result.languages) > 0
    assert len(result.frameworks) > 0


def test_empty_scan_does_not_crash():
    engine = IntelligenceEngine()
    result = engine.analyze(empty_scan_result(), session_id="test-empty")
    assert isinstance(result, IntelligenceResult)
    assert result.languages == []
    assert result.dependencies == []
    assert result.frameworks == []


def test_confidence_score_between_0_and_1():
    engine = IntelligenceEngine()
    result = engine.analyze(python_fastapi_scan())
    assert 0.0 <= result.confidence_score <= 1.0


def test_evidence_count_is_correct():
    engine = IntelligenceEngine()
    result = engine.analyze(python_fastapi_scan())
    assert result.evidence_count > 0
    # Evidence count should be the sum of all evidence lists
    manual_count = 0
    for lang in result.languages:
        manual_count += len(lang.evidence)
    for dep in result.dependencies:
        manual_count += len(dep.evidence)
    for fw in result.frameworks:
        manual_count += len(fw.evidence)
    for ep in result.entry_points:
        manual_count += len(ep.evidence)
    for api in result.api_endpoints:
        manual_count += len(api.evidence)
    for db in result.databases:
        manual_count += len(db.evidence)
    for mod in result.modules:
        manual_count += len(mod.evidence)
    manual_count += len(result.architecture.evidence)
    for step in result.workflow.steps:
        manual_count += len(step.evidence)
    assert result.evidence_count == manual_count


def test_every_detection_has_evidence():
    engine = IntelligenceEngine()
    result = engine.analyze(python_fastapi_scan())

    for fw in result.frameworks:
        assert len(fw.evidence) > 0, f"Framework {fw.name} has no evidence"
    for ep in result.entry_points:
        assert len(ep.evidence) > 0, f"Entry point {ep.file} has no evidence"
    for api in result.api_endpoints:
        assert len(api.evidence) > 0, f"API {api.method} {api.path} has no evidence"
    for db in result.databases:
        assert len(db.evidence) > 0, f"Database {db.name} has no evidence"


def test_project_type_matches_architecture():
    engine = IntelligenceEngine()
    result = engine.analyze(python_fastapi_scan())
    assert result.project_type == result.architecture.type


def test_llm_disabled_by_default():
    engine = IntelligenceEngine()
    result = engine.analyze(python_fastapi_scan(), include_llm_explanation=False)
    assert result.explanation is None


def test_llm_explanation_mocked_when_enabled():
    engine = IntelligenceEngine()
    mock_explanation = LLMExplanation(
        model="gemma3:27b-it",
        content="This is a FastAPI backend.",
        used=True,
        error=None,
    )

    with patch("app.intelligence.intelligence_engine.IntelligenceEngine.analyze") as mock_analyze:
        result = IntelligenceResult(
            session_id="test",
            project_type="backend",
            explanation=mock_explanation,
        )
        mock_analyze.return_value = result
        r = mock_analyze(python_fastapi_scan(), include_llm_explanation=True)
        assert r.explanation is not None
        assert r.explanation.used is True


def test_fullstack_has_frontend_and_backend_frameworks():
    engine = IntelligenceEngine()
    result = engine.analyze(fullstack_scan())
    fw_cats = {f.category for f in result.frameworks}
    assert "frontend" in fw_cats
    assert "backend" in fw_cats


def test_deterministic_output():
    """Same input → same output (when LLM disabled)."""
    engine = IntelligenceEngine()
    scan = python_fastapi_scan()
    r1 = engine.analyze(scan)
    r2 = engine.analyze(scan)
    assert r1.confidence_score == r2.confidence_score
    assert r1.evidence_count == r2.evidence_count
    assert r1.project_type == r2.project_type
    assert len(r1.languages) == len(r2.languages)
    assert len(r1.frameworks) == len(r2.frameworks)
