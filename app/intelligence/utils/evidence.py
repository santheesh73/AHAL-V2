"""
AHAL AI — Evidence helpers (Phase 2)

Factory and dedup utilities for EvidenceItem.
Never raise on bad input.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Sequence, TypeVar

from app.intelligence.models import EvidenceItem, ConfidenceLevel

T = TypeVar("T")


def make_evidence(
    file: str,
    reason: str,
    snippet: Optional[str] = None,
    confidence: ConfidenceLevel = "medium",
) -> EvidenceItem:
    """Create a single EvidenceItem safely."""
    return EvidenceItem(
        file=file or "",
        reason=reason or "",
        snippet=_truncate(snippet, 300) if snippet else None,
        confidence=confidence,
    )


def dedupe_evidence(items: Sequence[EvidenceItem]) -> List[EvidenceItem]:
    """Remove duplicate evidence by (file, reason)."""
    seen: set[tuple[str, str]] = set()
    out: List[EvidenceItem] = []
    for item in items:
        key = (item.file, item.reason)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def dedupe_by_key(
    items: Sequence[T],
    key_func: Callable[[T], Any],
) -> List[T]:
    """Generic dedup preserving first occurrence."""
    seen: set = set()
    out: List[T] = []
    for item in items:
        k = key_func(item)
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out


def _truncate(s: Optional[str], max_len: int) -> Optional[str]:
    """Truncate string to max_len chars."""
    if s is None:
        return None
    return s[:max_len] if len(s) > max_len else s
