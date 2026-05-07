from __future__ import annotations

import pytest

from app.intelligence.presentation_models import CanonicalAPI, CanonicalConfidence, CanonicalDataQuality, CanonicalProjectIntelligence, CanonicalTechStack
from app.llm.errors import LLMValidationRejected
from app.llm.response_validator import ResponseValidator


def _canonical(api_surface=None, why="It exists to help teams turn code changes into structured, queryable project knowledge."):
    return CanonicalProjectIntelligence(
        session_id="session-1",
        project_name="ContextBridge AI",
        repo_type="fullstack_app",
        project_type="fullstack",
        product_domain="code intelligence platform",
        product_summary="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        project_goal="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        what="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        why=why,
        architecture_summary="Fullstack application.",
        completed=[],
        remaining=[],
        issues=[],
        tech_stack=CanonicalTechStack(),
        api_surface=api_surface or [],
        workflow=[],
        evidence=[],
        warnings=[],
        confidence=CanonicalConfidence(),
        data_quality=CanonicalDataQuality(),
    )


def test_validator_rejects_hallucinated_api():
    validator = ResponseValidator()
    canonical = _canonical(api_surface=[CanonicalAPI(method="POST", path="/ask", purpose="Ask", source="chat")])
    with pytest.raises(LLMValidationRejected):
        validator.validate_text(canonical, "Use POST /not-real to submit the question.")


def test_validator_rejects_unsupported_finance():
    validator = ResponseValidator()
    canonical = _canonical()
    with pytest.raises(LLMValidationRejected):
        validator.validate_text(canonical, "This supports financial research workflows.")


def test_validator_rejects_html_markup():
    validator = ResponseValidator()
    canonical = _canonical()
    with pytest.raises(LLMValidationRejected):
        validator.validate_text(canonical, '<img src="logo.png" alt="logo" />')


def test_validator_rejects_secret_paths():
    validator = ResponseValidator()
    canonical = _canonical()
    with pytest.raises(LLMValidationRejected):
        validator.validate_text(canonical, "Open .env.example and mongodb://localhost to continue.")


def test_validator_rejects_canonical_what_and_why_drift():
    validator = ResponseValidator()
    canonical = _canonical()
    with pytest.raises(LLMValidationRejected):
        validator.validate_text(canonical, "Different what", must_preserve_what=True)
    with pytest.raises(LLMValidationRejected):
        validator.validate_text(canonical, "Different why", must_preserve_why=True)
