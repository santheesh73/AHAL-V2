from __future__ import annotations

import re

from app.chat.models import ChatIntentEntities, ChatIntentResult


class ChatIntentClassifier:
    def classify(self, question: str) -> ChatIntentResult:
        text = (question or "").strip()
        lowered = text.lower()
        if not lowered:
            return ChatIntentResult(intent="unsupported", confidence="low")

        file_match = re.search(r"([A-Za-z0-9_./-]+\.(?:py|ts|tsx|js|jsx|md|json|yml|yaml|toml|txt))", text)
        api_match = re.search(r"(/\S+)", text)
        module_match = re.search(r"(module|service|component|class)\s+([A-Za-z0-9_./-]+)", lowered)
        entities = ChatIntentEntities(
            file=file_match.group(1) if file_match else None,
            api_path=api_match.group(1).rstrip(".,)") if api_match and api_match.group(1).startswith("/") else None,
            module=module_match.group(2) if module_match else None,
            topic=None,
        )

        intent_rules: list[tuple[str, tuple[str, ...]]] = [
            ("what_is_built", ("what is built", "what's built", "already built", "completed", "capabilities")),
            ("project_goal", ("goal of this project", "purpose of this project", "why does this project", "why does it exist")),
            ("project_overview", ("what does this project do", "project overview", "repo overview", "summarize this project", "tell me about this codebase")),
            ("what_remaining", ("what remains", "what is remaining", "left to do", "missing", "not built yet")),
            ("api_explanation", ("what apis exist", "api", "endpoint", "route", "request", "response")),
            ("architecture_explanation", ("architecture", "how is this built", "system design", "layers")),
            ("workflow_explanation", ("workflow", "request flow", "main flow", "how does the main workflow work", "lifecycle")),
            ("file_explanation", ("explain ", "what does this file", "which file", "file does")),
            ("module_explanation", ("module", "service", "component", "layer")),
            ("risk_analysis", ("risk", "risky", "issues", "problem areas")),
            ("test_gap_question", ("what is not tested", "what tests should be added", "test gap", "coverage", "tests are missing")),
            ("onboarding_question", ("new engineer", "read first", "onboarding", "where should i start")),
            ("change_impact_question", ("change impact", "what breaks if", "delta", "affected by this change")),
            ("how_to_run", ("how do i run", "how to run", "start this project", "setup this project")),
            ("how_to_modify", ("how do i modify", "how to modify", "change this safely", "edit this module")),
            ("debugging_help", ("debug", "failing", "error", "broken", "issue with")),
        ]

        for intent, patterns in intent_rules:
            if any(pattern in lowered for pattern in patterns):
                confidence = "high"
                if intent == "api_explanation" and not any(token in lowered for token in ("api", "endpoint", "route", "/")):
                    confidence = "medium"
                if intent == "file_explanation":
                    if entities.file:
                        confidence = "high"
                    elif lowered.startswith("explain "):
                        confidence = "medium"
                entities.topic = entities.topic or intent.replace("_", " ")
                return ChatIntentResult(intent=intent, confidence=confidence, entities=entities)

        if entities.file:
            entities.topic = "file"
            return ChatIntentResult(intent="file_explanation", confidence="medium", entities=entities)
        if entities.api_path:
            entities.topic = "api"
            return ChatIntentResult(intent="api_explanation", confidence="medium", entities=entities)
        return ChatIntentResult(intent="general_repo_question", confidence="low", entities=entities)
