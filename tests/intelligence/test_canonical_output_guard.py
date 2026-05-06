from __future__ import annotations

from app.intelligence.output_guard import CanonicalOutputGuard
from app.intelligence.presentation_models import (
    CanonicalConfidence,
    CanonicalDataQuality,
    CanonicalProjectIntelligence,
)


def test_output_guard_replaces_wrong_cms_text():
    canonical = CanonicalProjectIntelligence(
        session_id="session-1",
        project_name="ContextBridge AI",
        project_type="fullstack",
        product_summary="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        product_domain="code intelligence platform",
        architecture_summary="Fullstack application with API-backed intelligence workflows.",
        what="ContextBridge AI is an AI-powered developer tool that transforms code changes into structured, queryable knowledge using Gemma models.",
        why="It exists to reduce the time required to understand unfamiliar codebases.",
        confidence=CanonicalConfidence(architecture="High", product_purpose="High", overall="High"),
        data_quality=CanonicalDataQuality(normalized=True, notes=[]),
    )

    sanitized = CanonicalOutputGuard.sanitize_text(
        "ContextBridge AI appears to be a content management application based on detected chat/query workflows.",
        canonical,
    )

    assert "content management application" not in sanitized.lower()
    assert sanitized == canonical.what
