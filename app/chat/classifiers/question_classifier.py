"""Deterministic question classification for chat retrieval."""

from __future__ import annotations

import re

from app.chat.models import QuestionClassification

_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("architecture", ("architecture", "structure", "overview", "how is this built")),
    ("workflow", ("flow", "workflow", "execution", "request lifecycle", "data flow")),
    ("dependency", ("dependency", "package", "library")),
    ("database", ("database", "db", "mongo", "postgres", "sql", "redis")),
    ("module", ("module", "layer", "service", "component")),
    ("file", ("file", "where", "which file")),
    ("security", ("auth", "jwt", "login", "permission", "security")),
    ("testing", ("test", "pytest", "jest", "coverage")),
    ("api", ("api", "endpoint", "route", "request", "response")),
]


class QuestionClassifier:
    def classify(self, question: str) -> QuestionClassification:
        text = (question or "").strip().lower()
        if not text:
            return QuestionClassification(category="general", confidence="low")

        entities = self._extract_entities(question)
        for category, keywords in _CATEGORY_RULES:
            for keyword in keywords:
                if keyword in text:
                    return QuestionClassification(
                        category=category,
                        entities=entities,
                        confidence="high" if len(keyword) > 3 else "medium",
                    )

        return QuestionClassification(category="general", entities=entities, confidence="low")

    def _extract_entities(self, question: str) -> list[str]:
        matches = re.findall(r"[A-Za-z0-9_./:-]{3,}", question or "")
        seen: set[str] = set()
        entities: list[str] = []
        for match in matches:
            token = match.strip(".,:;()[]{}\"'")
            lowered = token.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            entities.append(token)
        return entities[:10]
