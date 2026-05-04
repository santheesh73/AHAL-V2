from __future__ import annotations

import re
from typing import Any

from app.docs.models import DocEvidence
from app.utils.ignored_paths import is_ignored_path

FORBIDDEN_PATH_TOKENS = (
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "private_key",
    "token",
    "secret",
    "password",
    "credential",
)
FORBIDDEN_TEXT_TOKENS = (
    "magicmock",
    "<mock",
    "object at 0x",
    "type='",
    "confidence='",
    "reasoning=[",
    "evidence=[",
    "evidenceitem(",
    "architectureresult(",
)
REDACTED_PATH_LABELS = {
    ".env": "environment configuration evidence",
    ".env.local": "environment configuration evidence",
    ".env.production": "environment configuration evidence",
    "id_rsa": "configuration evidence",
    "private_key": "configuration evidence",
    "token": "configuration evidence",
    "secret": "configuration evidence",
    "password": "configuration evidence",
    "credential": "configuration evidence",
}
IGNORED_PATH_LABEL = "configuration evidence"


def contains_forbidden_path(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(token in lowered for token in FORBIDDEN_PATH_TOKENS)


def sanitize_path(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    if "MagicMock" in text or "<Mock" in text or "object at 0x" in text:
        return fallback
    lowered = text.lower()
    if is_ignored_path(text):
        return ""
    for token, label in REDACTED_PATH_LABELS.items():
        if token in lowered:
            return label
    return text


def sanitize_text(value: Any, fallback: str = "Insufficient evidence from codebase.") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    text = re.sub(r"<Mock[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"MagicMock\([^)]*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"MagicMock object at 0x[0-9a-fA-F]+", "", text, flags=re.IGNORECASE)
    lowered = text.lower()
    if any(token in lowered for token in FORBIDDEN_TEXT_TOKENS):
        return fallback
    if text.lower().endswith("generation failed.") or text.lower() == "generation failed":
        return fallback
    if is_ignored_path(text):
        return ""
    if contains_forbidden_path(text):
        return sanitize_path(text, fallback=IGNORED_PATH_LABEL) or fallback
    text = re.sub(r"\s+", " ", text).strip()
    return text or fallback


def sanitize_evidence_reason(value: Any) -> str:
    return sanitize_text(value, fallback="Evidence detected from the analyzed codebase.")


def sanitize_doc_evidence_item(item: Any) -> DocEvidence | None:
    source_id = sanitize_text(getattr(item, "source_id", "unknown"), fallback="unknown")
    file_path = sanitize_path(getattr(item, "file", None), fallback="")
    reason = sanitize_evidence_reason(getattr(item, "reason", None))
    if not source_id and not file_path:
        return None
    return DocEvidence(
        source_type=sanitize_text(getattr(item, "source_type", "file"), fallback="file"),
        source_id=source_id or "unknown",
        file=file_path or None,
        reason=reason,
        snippet=None,
        confidence=getattr(item, "confidence", "medium"),
    )


def sanitize_doc_evidence_list(items) -> list[DocEvidence]:
    rows: list[DocEvidence] = []
    for item in items or []:
        clean_item = sanitize_doc_evidence_item(item)
        if clean_item is not None:
            rows.append(clean_item)
    return rows


def sanitize_payload(value: Any):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            safe_key = sanitize_text(key, fallback="")
            if not safe_key:
                continue
            safe_item = sanitize_payload(item)
            if safe_item in ("", None):
                if isinstance(item, (list, dict)):
                    cleaned[safe_key] = safe_item
                continue
            cleaned[safe_key] = safe_item
        return cleaned
    if isinstance(value, list):
        rows = []
        for item in value:
            safe_item = sanitize_payload(item)
            if safe_item not in ("", None):
                rows.append(safe_item)
        return rows
    if value is None:
        return ""
    if isinstance(value, str):
        return sanitize_text(value, fallback="")
    if hasattr(value, "model_dump"):
        return sanitize_payload(value.model_dump())
    return value
