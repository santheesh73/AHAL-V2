"""Tests for CasualChatComposer (Phase 10E.1)."""

from app.chat.casual_composer import CasualChatComposer


composer = CasualChatComposer()


# ── Greeting responses ──────────────────────────────────────────


def test_hi_returns_greeting_not_project_summary():
    answer = composer.compose("hi", intent="greeting")

    lowered = answer.answer.lower()
    assert "hi" in lowered
    assert "help" in lowered

    # Must NOT contain repo-analysis content
    for bad in ("project appears", "backend api service", "repository intelligence", "evidence [e1]", "[e1]"):
        assert bad not in lowered, f"Casual greeting should not contain '{bad}'"


def test_hello_returns_greeting():
    answer = composer.compose("hello", intent="greeting")
    assert "hi" in answer.answer.lower() or "hello" in answer.answer.lower()


def test_good_morning_returns_greeting():
    answer = composer.compose("good morning", intent="greeting")
    assert "hi" in answer.answer.lower() or "help" in answer.answer.lower()


# ── Acknowledgement responses ───────────────────────────────────


def test_thanks_returns_short_casual_response():
    answer = composer.compose("thanks", intent="acknowledgement")
    assert "welcome" in answer.answer.lower()


def test_thank_you_returns_short_casual_response():
    answer = composer.compose("thank you", intent="acknowledgement")
    assert "welcome" in answer.answer.lower()


def test_ok_returns_acknowledgement():
    answer = composer.compose("ok", intent="acknowledgement")
    lowered = answer.answer.lower()
    assert "got it" in lowered or "let me know" in lowered


def test_cool_returns_acknowledgement():
    answer = composer.compose("cool", intent="acknowledgement")
    lowered = answer.answer.lower()
    assert "got it" in lowered or "let me know" in lowered


# ── Help / capabilities responses ───────────────────────────────


def test_help_returns_capabilities():
    answer = composer.compose("help", intent="help")
    lowered = answer.answer.lower()
    assert "project" in lowered or "api" in lowered
    assert "risk" in lowered or "test" in lowered


def test_what_can_you_do_returns_capabilities():
    answer = composer.compose("what can you do?", intent="meta")
    lowered = answer.answer.lower()
    assert "project" in lowered or "architecture" in lowered or "api" in lowered


# ── Meta responses ──────────────────────────────────────────────


def test_who_are_you_returns_identity():
    answer = composer.compose("who are you?", intent="meta")
    lowered = answer.answer.lower()
    assert "ahal" in lowered
    assert "repo" in lowered or "project" in lowered or "repository" in lowered


# ── Evidence and structure assertions ────────────────────────────


def test_casual_answer_has_no_evidence_chips():
    answer = composer.compose("hi", intent="greeting")
    assert answer.evidence == []
    assert len(answer.evidence) == 0


def test_casual_answer_has_no_sections():
    answer = composer.compose("hi", intent="greeting")
    assert answer.sections == []


def test_casual_answer_has_no_warnings():
    answer = composer.compose("hi", intent="greeting")
    assert answer.warnings == []


def test_casual_answer_has_suggested_followups():
    answer = composer.compose("hi", intent="greeting")
    assert len(answer.suggested_followups) >= 3
    lowered_followups = [f.lower() for f in answer.suggested_followups]
    assert any("project" in f for f in lowered_followups)


def test_casual_answer_intent_is_casual():
    answer = composer.compose("hi", intent="greeting")
    assert answer.intent == "casual"


def test_casual_answer_confidence_is_high():
    answer = composer.compose("hi", intent="greeting")
    assert answer.confidence == "high"


def test_casual_answer_used_llm_is_false():
    answer = composer.compose("hi", intent="greeting")
    assert answer.used_llm is False


def test_casual_answer_fallback_used_is_false():
    answer = composer.compose("hi", intent="greeting")
    assert answer.fallback_used is False


# ── Unsupported responses ───────────────────────────────────────


def test_unsupported_response_is_safe():
    answer = composer.compose_unsupported()
    lowered = answer.answer.lower()
    assert "project" in lowered
    assert answer.evidence == []
    assert answer.intent == "unsupported"


def test_unsupported_has_suggested_followups():
    answer = composer.compose_unsupported()
    assert len(answer.suggested_followups) >= 3


# ── Clarification fallback ──────────────────────────────────────


def test_clarification_fallback_asks_for_topic():
    answer = composer.compose_clarification_fallback()
    lowered = answer.answer.lower()
    assert "project" in lowered or "explain" in lowered
    assert answer.evidence == []
    assert answer.intent == "casual"
