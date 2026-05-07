"""
AHAL AI - Chat Message Router (Phase 10E.1)

Pure-Python classifier that routes incoming chat messages into one of four
categories: casual, repo, clarification, or unsupported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

RouteType = Literal["casual", "repo", "clarification", "unsupported"]
ConfidenceLevel = Literal["high", "medium", "low"]


@dataclass
class ChatRoute:
    route: RouteType
    intent: str
    confidence: ConfidenceLevel = "high"
    requires_repo_context: bool = False
    requires_evidence: bool = False


_GREETING_EXACT: frozenset[str] = frozenset({
    "hi", "hello", "hey", "hii", "hiii", "yo", "sup",
    "good morning", "good afternoon", "good evening",
    "gm", "morning", "evening",
})

_ACKNOWLEDGEMENT_EXACT: frozenset[str] = frozenset({
    "thanks", "thank you", "thx", "ty",
    "ok", "okay", "k", "kk",
    "cool", "nice", "great", "awesome", "perfect",
    "got it", "understood", "alright",
    "yes", "yep", "yeah", "yup", "no", "nope", "nah",
})

_META_PATTERNS: tuple[str, ...] = (
    "who are you",
    "what are you",
    "what can you do",
    "what do you do",
    "can you help",
    "how can you help",
    "what is ahal",
    "what's ahal",
    "introduce yourself",
)

_HELP_EXACT: frozenset[str] = frozenset({"help", "start", "begin", "menu", "options"})

_REPO_SIGNALS: tuple[str, ...] = (
    "project", "repo", "repository", "codebase", "code base",
    "architecture", "system design", "layers", "structure",
    "api", "endpoint", "route", "request", "response",
    "module", "service", "component", "class", "function",
    "file", "folder", "directory",
    "risk", "risky", "issue", "problem",
    "test", "coverage", "gap",
    "onboarding", "read first", "new engineer",
    "new to this project", "where do i start", "where should i start",
    "start first", "joining this project", "first 30 minutes",
    "walk me through", "understand this repo", "understand this project",
    "workflow", "flow", "lifecycle",
    "dependency", "dependencies",
    "database", "storage",
    "framework",
    "how do i run", "how to run", "how do i build", "how to build",
    "how do i modify", "how to modify",
    "describe", "summarize", "overview",
    "what is built", "what's built", "what remains", "what's remaining", "what is remaining",
    "what does this", "what are the",
    "debug", "failing", "error", "broken",
    "change impact", "what breaks",
    "delta", "diff",
)

_CLARIFICATION_PATTERNS: tuple[str, ...] = (
    "explain more",
    "tell me more",
    "more detail",
    "more details",
    "elaborate",
    "go on",
    "continue",
    "what about that",
    "what do you mean",
    "which one",
    "why is that",
    "how so",
    "can you clarify",
)

_CLARIFICATION_SHORT: frozenset[str] = frozenset({
    "why", "why?", "how", "how?", "what?", "where?",
    "which", "which?", "and?", "so?", "more", "more?",
})

_UNSUPPORTED_PATTERNS: tuple[str, ...] = (
    "bank password",
    "credit card",
    "social security",
    "medical advice",
    "legal advice",
    "financial advice",
    "investment advice",
    "diagnose me",
    "prescribe",
    "reveal your prompt",
    "system prompt",
    "hidden instructions",
    "ignore previous",
    "ignore all",
    "disregard",
    "jailbreak",
    "bypass",
    "pretend you are",
    "act as if",
    "role play",
)


class ChatMessageRouter:
    def classify(self, message: str, chat_history: Optional[list] = None) -> ChatRoute:
        text = (message or "").strip()
        if not text:
            return ChatRoute("unsupported", "empty", "high", False, False)

        lowered = text.lower().rstrip("!.?")
        lowered_raw = text.lower()

        if any(pattern in lowered_raw for pattern in _UNSUPPORTED_PATTERNS):
            return ChatRoute("unsupported", "out_of_scope", "high", False, False)

        if lowered in _GREETING_EXACT:
            return ChatRoute("casual", "greeting", "high", False, False)

        if lowered in _ACKNOWLEDGEMENT_EXACT:
            return ChatRoute("casual", "acknowledgement", "high", False, False)

        if lowered in _HELP_EXACT:
            return ChatRoute("casual", "help", "high", False, False)

        if any(pattern in lowered_raw for pattern in _META_PATTERNS):
            return ChatRoute("casual", "meta", "high", False, False)

        if lowered in _CLARIFICATION_SHORT or any(pattern in lowered_raw for pattern in _CLARIFICATION_PATTERNS):
            return ChatRoute("clarification", "followup", "medium", bool(chat_history), bool(chat_history))

        if any(signal in lowered_raw for signal in _REPO_SIGNALS):
            if any(
                signal in lowered_raw
                for signal in (
                    "new to this project",
                    "where do i start",
                    "where should i start",
                    "start first",
                    "read first",
                    "onboarding",
                    "new engineer",
                    "joining this project",
                    "first 30 minutes",
                    "walk me through",
                    "understand this repo",
                    "understand this project",
                )
            ):
                return ChatRoute("repo", "onboarding_question", "high", True, True)
            return ChatRoute("repo", "repo_question", "high", True, True)

        if re.search(r"[A-Za-z0-9_/.-]+\.(?:py|ts|tsx|js|jsx|json|yml|yaml|md|toml|txt)\b", text):
            return ChatRoute("repo", "repo_question", "medium", True, True)

        if re.search(r"/[a-z][a-z0-9_/-]*", lowered_raw):
            return ChatRoute("repo", "repo_question", "medium", True, True)

        if len(text.split()) <= 3:
            return ChatRoute("casual", "short_message", "low", False, False)

        return ChatRoute("repo", "repo_question", "low", True, True)
