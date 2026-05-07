from __future__ import annotations

from types import SimpleNamespace

from app.chat.answer_composer_v2 import AnswerComposerV2
from app.chat.models import ChatContextPack, ChatIntentResult
from app.intelligence.presentation_models import CanonicalProjectIntelligence, CanonicalConfidence, CanonicalDataQuality, CanonicalTechStack
from app.llm.errors import LLMModelNotFound, LLMRateLimited, LLMTimeout
from app.llm.polish_orchestrator import PolishOrchestrator


def _canonical() -> CanonicalProjectIntelligence:
    return CanonicalProjectIntelligence(
        session_id="session-1",
        project_name="ContextBridge AI",
        repo_type="fullstack_app",
        project_type="fullstack",
        product_domain="code intelligence platform",
        product_summary="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        project_goal="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        what="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        why="It exists to help teams turn code changes into structured, queryable project knowledge.",
        architecture_summary="Fullstack application.",
        completed=[],
        remaining=[],
        issues=[],
        tech_stack=CanonicalTechStack(),
        api_surface=[],
        workflow=[],
        evidence=[],
        warnings=[],
        confidence=CanonicalConfidence(),
        data_quality=CanonicalDataQuality(),
    )


class _FakeClient:
    def __init__(self, text="", exc=None, available=True):
        self._text = text
        self._exc = exc
        self._available = available

    def is_available(self):
        return self._available

    def generate_text(self, *args, **kwargs):
        if self._exc:
            raise self._exc
        return SimpleNamespace(text=self._text)


def test_polish_cannot_change_canonical_what():
    canonical = _canonical()
    orchestrator = PolishOrchestrator(client=_FakeClient(text="This is a different product."))  # type: ignore[arg-type]
    text, warnings = orchestrator.polish_chat_answer(canonical, "What does this project do?", canonical.product_summary)
    assert text == canonical.product_summary
    assert any("rejected by validation" in warning.lower() for warning in warnings)


def test_polish_cannot_change_canonical_why():
    canonical = _canonical()
    orchestrator = PolishOrchestrator(client=_FakeClient(text="It exists to manage ecommerce catalogs."))  # type: ignore[arg-type]
    text, warnings = orchestrator.polish_chat_answer(canonical, "Why does this project exist?", canonical.why)
    assert text == canonical.why
    assert any("rejected by validation" in warning.lower() for warning in warnings)


def test_404_timeout_and_429_fallback_warnings():
    canonical = _canonical()
    for exc, expected in (
        (LLMModelNotFound("404"), "polish unavailable"),
        (LLMRateLimited("429"), "rate limit reached"),
        (LLMTimeout("timeout"), "timed out"),
    ):
        orchestrator = PolishOrchestrator(client=_FakeClient(exc=exc))  # type: ignore[arg-type]
        text, warnings = orchestrator.polish_project_summary(canonical)
        assert text == canonical.product_summary
        assert any(expected in warning.lower() for warning in warnings)


def test_timeout_falls_back_for_chat_and_pdf():
    canonical = _canonical()
    orchestrator = PolishOrchestrator(client=_FakeClient(exc=LLMTimeout("timeout")))  # type: ignore[arg-type]
    chat_text, chat_warnings = orchestrator.polish_chat_answer(canonical, "What does this project do?", canonical.product_summary)
    pdf_text, pdf_warnings = orchestrator.polish_pdf_section(canonical, "what", canonical.what)
    assert chat_text == canonical.product_summary
    assert pdf_text == canonical.what
    assert chat_warnings and pdf_warnings
