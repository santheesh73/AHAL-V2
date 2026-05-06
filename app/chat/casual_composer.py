"""
AHAL AI — Casual Chat Composer (Phase 10E.1)

Produces friendly ChatAnswer objects for non-repo messages.
No evidence, no sections, no repo context — just natural conversation.
"""

from __future__ import annotations

import re
from typing import Optional

from app.chat.models import ChatAnswer


# ── Suggested repo-focused follow-ups for casual answers ─────────

_REPO_FOLLOWUPS: list[str] = [
    "What does this project do?",
    "What is built?",
    "What APIs exist?",
    "Explain the architecture.",
    "What should a new engineer read first?",
]


class CasualChatComposer:
    """
    Compose friendly, evidence-free responses for casual chat messages.
    """

    def compose(
        self,
        message: str,
        intent: str = "greeting",
        session_summary: Optional[str] = None,
    ) -> ChatAnswer:
        lowered = (message or "").strip().lower().rstrip("!.?")
        response = self._pick_response(lowered, intent)

        return ChatAnswer(
            answer=response,
            short_answer=response,
            sections=[],
            confidence="high",
            evidence=[],
            related_files=[],
            related_nodes=[],
            warnings=[],
            insufficient_context=False,
            suggested_followups=list(_REPO_FOLLOWUPS),
            intent="casual",
            used_llm=False,
            fallback_used=False,
        )

    def compose_clarification_fallback(self) -> ChatAnswer:
        """Return a gentle clarification prompt when no previous topic exists."""
        response = (
            "Sure — what part of the project would you like me to explain? "
            "You can ask about APIs, architecture, risks, tests, or any specific file."
        )
        return ChatAnswer(
            answer=response,
            short_answer=response,
            sections=[],
            confidence="high",
            evidence=[],
            related_files=[],
            related_nodes=[],
            warnings=[],
            insufficient_context=False,
            suggested_followups=list(_REPO_FOLLOWUPS),
            intent="casual",
            used_llm=False,
            fallback_used=False,
        )

    def compose_unsupported(self) -> ChatAnswer:
        """Return a safe refusal for out-of-scope requests."""
        response = (
            "I can help with the analyzed project, but I don't have enough "
            "relevant project evidence to answer that. Try asking about the "
            "project's APIs, architecture, risks, or test coverage instead."
        )
        return ChatAnswer(
            answer=response,
            short_answer=response,
            sections=[],
            confidence="high",
            evidence=[],
            related_files=[],
            related_nodes=[],
            warnings=[],
            insufficient_context=False,
            suggested_followups=list(_REPO_FOLLOWUPS),
            intent="unsupported",
            used_llm=False,
            fallback_used=False,
        )

    def _pick_response(self, lowered: str, intent: str) -> str:
        # ── Greetings ────────────────────────────────────────────
        if intent == "greeting" or lowered in {
            "hi", "hello", "hey", "hii", "hiii", "yo", "sup",
            "good morning", "good afternoon", "good evening",
            "gm", "morning", "evening",
        }:
            return (
                "Hi! I can help you understand this project, explain APIs, "
                "review risks, find test gaps, or create onboarding guidance. "
                "What would you like to explore?"
            )

        # ── Thank-yous ───────────────────────────────────────────
        if intent == "acknowledgement" and lowered in {
            "thanks", "thank you", "thx", "ty",
        }:
            return "You're welcome! Let me know if you have more questions about the project."

        # ── Acknowledgements (ok, cool, nice, etc.) ──────────────
        if intent == "acknowledgement":
            return "Got it! Let me know if you'd like to explore anything about the project."

        # ── Help / capabilities ──────────────────────────────────
        if intent == "help" or lowered in {"help", "start", "begin", "menu", "options"}:
            return (
                "I can help with questions like: what does this project do, "
                "what APIs exist, how the workflow works, what risks exist, "
                "what tests are missing, and what a new engineer should read first."
            )

        # ── Meta questions ───────────────────────────────────────
        if intent == "meta":
            if "who are you" in lowered or "what are you" in lowered:
                return (
                    "I'm AHAL AI's repo chat assistant. I can answer questions about "
                    "the analyzed project using the repository evidence AHAL collected."
                )
            return (
                "I can explain the analyzed project, summarize architecture, list APIs, "
                "identify risks, suggest tests, and provide onboarding guidance from "
                "the available evidence."
            )

        # ── Generic short message fallback ───────────────────────
        return (
            "I'm here to help! You can ask me about the project's architecture, "
            "APIs, risks, test gaps, or anything else about the analyzed codebase."
        )
