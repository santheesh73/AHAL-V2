from __future__ import annotations

from typing import Any

from app.config import config
from app.docs.utils.evidence_sanitizer import sanitize_payload as universal_sanitize_payload
from app.docs.utils.evidence_sanitizer import sanitize_text as universal_sanitize_text
from app.utils.ignored_paths import is_ignored_path

_FORBIDDEN_TEXT = ("magicmock", "object at 0x", "repr(", "type='", "confidence='")
_SECRET_TOKENS = ("api_key", "apikey", "password=", "bearer ", "authorization:", ".env")


def sanitize_text(value: Any, fallback: str = "Insufficient evidence from codebase.") -> str:
    text = universal_sanitize_text(value, fallback=fallback)
    lowered = text.lower()
    if any(token in lowered for token in _SECRET_TOKENS):
        return "[REDACTED]"
    return text


def sanitize_payload(value: Any):
    return universal_sanitize_payload(value)


def validate_code_input(code: str) -> tuple[bool, str]:
    normalized = str(code or "")
    if not normalized.strip():
        return False, "Code must not be empty."
    if len(normalized) > config.scanner.code_max_chars:
        return False, f"Code exceeds maximum length of {config.scanner.code_max_chars} characters."
    if len(normalized.encode("utf-8")) > config.scanner.max_single_file_bytes:
        return False, "Code payload exceeds the configured size limit."
    if "\x00" in normalized:
        return False, "Binary-looking payloads are not supported for code analysis."
    return True, ""


def sanitize_filename(filename: str | None) -> str:
    text = str(filename or "snippet.txt").strip().replace("\\", "/")
    if not text:
        return "snippet.txt"
    if "\x00" in text or ":" in text or ".." in text:
        return "snippet.txt"
    text = text.split("/")[-1].strip()
    return sanitize_text(text, fallback="snippet.txt")[: config.scanner.code_max_filename_chars] or "snippet.txt"


def contains_secret_text(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_secret_text(key) or contains_secret_text(item) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_secret_text(item) for item in value)
    text = str(value or "").lower()
    return any(token in text for token in _SECRET_TOKENS)
