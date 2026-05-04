"""Deterministic evidence ranking for chat context."""

from __future__ import annotations

from app.utils.ignored_paths import is_ignored_path


class EvidenceRanker:
    def rank(self, question: str, classification, contexts, max_items: int = 20):
        question_lc = (question or "").lower()
        entities = [entity.lower() for entity in classification.entities]
        category = classification.category

        ranked = []
        for item in contexts:
            if (item.file and is_ignored_path(item.file)) or any(ev.file and is_ignored_path(ev.file) for ev in item.evidence):
                continue
            score = 0.0
            score += self._keyword_score(question_lc, entities, item)
            score += self._category_score(category, item)
            score += self._confidence_score(item.confidence)
            score += self._evidence_score(item)
            score += self._graph_score(item)
            if category == "general" and item.context_id == "project-summary":
                score += 5.0
            if category == "general" and item.source_type == "file":
                score -= 1.0
            item.score = round(score, 4)
            ranked.append(item)

        ranked.sort(key=lambda item: (-item.score, item.context_id))
        return ranked[:max_items]

    def _keyword_score(self, question_lc: str, entities: list[str], item) -> float:
        blob = " ".join([item.title.lower(), item.content.lower(), item.source_id.lower(), *(keyword.lower() for keyword in item.keywords)])
        score = 0.0
        for entity in entities:
            if entity in blob:
                score += 3.0
        for keyword in item.keywords:
            if keyword and keyword.lower() in question_lc:
                score += 1.5
        return score

    def _category_score(self, category: str, item) -> float:
        if item.category == category:
            return 3.0
        if item.category == "general":
            return 0.5
        return 0.0

    def _confidence_score(self, confidence: str) -> float:
        return {"high": 2.0, "medium": 1.0, "low": 0.5}.get(confidence, 0.5)

    def _evidence_score(self, item) -> float:
        score = min(len(item.evidence), 3) * 0.75
        if any(e.source_type == "graph_edge" for e in item.evidence):
            score += 0.5
        return score

    def _graph_score(self, item) -> float:
        if item.source_type == "graph_node":
            return 1.0
        if item.source_type == "graph_edge":
            return 1.5
        if item.source_type in {"api_endpoint", "database", "module"}:
            return 1.0
        return 0.0
