from __future__ import annotations

import re

from app.intelligence.presentation_models import (
    CanonicalAPI,
    CanonicalEvidence,
    CanonicalIssue,
    CanonicalProjectIntelligence,
    CanonicalStatusItem,
    CanonicalWorkflowStep,
)


class CanonicalOutputGuard:
    _FORBIDDEN_PATTERNS = (
        re.compile(r"content management application", re.IGNORECASE),
        re.compile(r"content management system", re.IGNORECASE),
        re.compile(r"\bcms\b", re.IGNORECASE),
        re.compile(r"\bcrm\b", re.IGNORECASE),
        re.compile(r"\becommerce\b", re.IGNORECASE),
        re.compile(r"analytics platform", re.IGNORECASE),
        re.compile(r"devops platform", re.IGNORECASE),
        re.compile(r"chatbot platform", re.IGNORECASE),
        re.compile(r"ai_hallucination_detection", re.IGNORECASE),
    )
    _EMOJI_PREFIX_RE = re.compile(r"^[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF\s]+")
    _AHAL_LEAK_PATTERNS = (
        re.compile(r"unfamiliar codebases", re.IGNORECASE),
        re.compile(r"repository-aware questions", re.IGNORECASE),
        re.compile(r"generate technical documentation", re.IGNORECASE),
        re.compile(r"project intelligence", re.IGNORECASE),
    )

    @classmethod
    def sanitize_canonical(cls, canonical: CanonicalProjectIntelligence) -> CanonicalProjectIntelligence:
        sanitized = canonical.model_copy(deep=True)
        sanitized.product_summary = cls._sanitize_field_text(sanitized.product_summary, sanitized, prefer_summary=True)
        sanitized.what = cls._sanitize_field_text(sanitized.what, sanitized, prefer_summary=False)
        sanitized.why = cls._sanitize_field_text(sanitized.why, sanitized, prefer_summary=False)
        if cls._should_strip_ahal_why(sanitized):
            sanitized.why = "The business or user-facing reason is not fully specified in the analyzed evidence."
        sanitized.architecture_summary = cls.sanitize_text(sanitized.architecture_summary, sanitized)
        sanitized.product_domain = cls.sanitize_text(sanitized.product_domain, sanitized)
        sanitized.warnings = [cls.sanitize_text(item, sanitized) for item in sanitized.warnings if cls.sanitize_text(item, sanitized)]
        sanitized.completed = [
            CanonicalStatusItem(
                title=cls.sanitize_text(item.title, sanitized),
                description=cls._sanitize_field_text(item.description, sanitized, prefer_summary=False),
                evidence_ids=item.evidence_ids,
                confidence=item.confidence,
            )
            for item in sanitized.completed
        ]
        sanitized.remaining = [
            CanonicalStatusItem(
                title=cls.sanitize_text(item.title, sanitized),
                description=cls._sanitize_field_text(item.description, sanitized, prefer_summary=False),
                evidence_ids=item.evidence_ids,
                confidence=item.confidence,
            )
            for item in sanitized.remaining
        ]
        sanitized.issues = [
            CanonicalIssue(
                severity=cls.sanitize_text(item.severity, sanitized),
                title=cls._sanitize_field_text(item.title, sanitized, prefer_summary=False),
                recommendation=cls._sanitize_field_text(item.recommendation, sanitized, prefer_summary=False),
                evidence_ids=item.evidence_ids,
            )
            for item in sanitized.issues
        ]
        sanitized.api_surface = [
            CanonicalAPI(
                method=cls.sanitize_text(item.method, sanitized),
                path=cls.sanitize_text(item.path, sanitized),
                purpose=cls._sanitize_field_text(item.purpose, sanitized, prefer_summary=False),
                source=cls.sanitize_text(item.source, sanitized),
                evidence_ids=item.evidence_ids,
            )
            for item in sanitized.api_surface
        ]
        sanitized.workflow = [
            CanonicalWorkflowStep(
                step=item.step,
                title=cls.sanitize_text(item.title, sanitized),
                description=cls._sanitize_field_text(item.description, sanitized, prefer_summary=False),
                evidence_ids=item.evidence_ids,
            )
            for item in sanitized.workflow
        ]
        sanitized.evidence = [
            CanonicalEvidence(
                id=item.id,
                label=cls._sanitize_field_text(item.label, sanitized, prefer_summary=False),
                source_type=cls.sanitize_text(item.source_type, sanitized),
                reason=cls._sanitize_field_text(item.reason, sanitized, prefer_summary=False),
                confidence=item.confidence,
            )
            for item in sanitized.evidence
        ]
        cls.assert_no_forbidden_terms(sanitized.product_summary, sanitized)
        cls.assert_no_forbidden_terms(sanitized.what, sanitized)
        return sanitized

    @classmethod
    def sanitize_text(cls, text: str, canonical: CanonicalProjectIntelligence | None = None) -> str:
        value = str(text or "").replace("**", "").strip()
        value = cls._EMOJI_PREFIX_RE.sub("", value).strip()
        if canonical is not None and cls._is_developer_project(canonical) and cls._contains_forbidden_terms(value):
            replacement = cls._fallback_text(canonical, prefer_summary=False)
            value = replacement if replacement else value
        if canonical is not None and cls._should_strip_ahal_why_for_text(value, canonical):
            value = "The business or user-facing reason is not fully specified in the analyzed evidence."
        return value

    @classmethod
    def assert_no_forbidden_terms(cls, text: str, canonical: CanonicalProjectIntelligence | None = None) -> None:
        if canonical is None or not cls._is_developer_project(canonical):
            return
        if cls._contains_forbidden_terms(str(text or "")):
            raise ValueError("Forbidden wrong-domain text detected in canonical developer/code intelligence output.")

    @classmethod
    def _sanitize_field_text(cls, text: str, canonical: CanonicalProjectIntelligence, prefer_summary: bool) -> str:
        value = str(text or "").replace("**", "").strip()
        value = cls._EMOJI_PREFIX_RE.sub("", value).strip()
        if cls._is_developer_project(canonical) and cls._contains_forbidden_terms(value):
            replacement = cls._fallback_text(canonical, prefer_summary=prefer_summary)
            value = replacement if replacement else value
        return value

    @classmethod
    def _fallback_text(cls, canonical: CanonicalProjectIntelligence, prefer_summary: bool) -> str:
        if prefer_summary and str(getattr(canonical, "product_summary", "") or "").strip():
            return str(canonical.product_summary).replace("**", "").strip()
        if str(getattr(canonical, "what", "") or "").strip():
            return str(canonical.what).replace("**", "").strip()
        if str(getattr(canonical, "product_summary", "") or "").strip():
            return str(canonical.product_summary).replace("**", "").strip()
        return ""

    @classmethod
    def _contains_forbidden_terms(cls, text: str) -> bool:
        return any(pattern.search(str(text or "")) for pattern in cls._FORBIDDEN_PATTERNS)

    @classmethod
    def _is_developer_project(cls, canonical: CanonicalProjectIntelligence) -> bool:
        joined = " ".join(
            [
                str(getattr(canonical, "product_domain", "") or ""),
                str(getattr(canonical, "product_summary", "") or ""),
                str(getattr(canonical, "what", "") or ""),
            ]
        ).lower()
        return any(token in joined for token in ("developer", "code intelligence", "repository intelligence", "queryable knowledge", "code changes"))

    @classmethod
    def _should_strip_ahal_why(cls, canonical: CanonicalProjectIntelligence) -> bool:
        project_name = str(getattr(canonical, "project_name", "") or "").lower()
        if project_name in {"ahal", "ahal ai"}:
            return False
        if cls._is_developer_project(canonical):
            return False
        return any(pattern.search(str(getattr(canonical, "why", "") or "")) for pattern in cls._AHAL_LEAK_PATTERNS)

    @classmethod
    def _should_strip_ahal_why_for_text(cls, text: str, canonical: CanonicalProjectIntelligence) -> bool:
        project_name = str(getattr(canonical, "project_name", "") or "").lower()
        if project_name in {"ahal", "ahal ai"}:
            return False
        if cls._is_developer_project(canonical):
            return False
        return any(pattern.search(str(text or "")) for pattern in cls._AHAL_LEAK_PATTERNS)
