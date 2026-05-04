"""
AHAL AI — Safe Utilities
Defensive helpers that must NEVER raise unhandled exceptions.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("ahal.utils")


def safe_decode(raw: bytes, max_bytes: int | None = None) -> Optional[str]:
    """
    Attempt to decode raw bytes to a string.
    Returns None on failure — never raises.
    Normalizes line endings to Unix \\n on all platforms.
    """
    try:
        if max_bytes is not None:
            raw = raw[:max_bytes]
        # Try UTF‑8 first (covers ~95 % of source code)
        text = raw.decode("utf-8")
        return text.replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError:
        pass
    try:
        text = raw.decode("latin-1")
        return text.replace("\r\n", "\n").replace("\r", "\n")
    except Exception:
        return None


def safe_read_file(path: str, max_bytes: int) -> Optional[str]:
    """
    Read up to *max_bytes* from a file on disk and decode.
    Returns None on any error — never raises.
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read(max_bytes)
        return safe_decode(raw)
    except Exception as exc:
        logger.warning("safe_read_file failed for %s: %s", path, exc)
        return None


def is_likely_binary(data: bytes, sample_size: int = 8192) -> bool:
    """
    Heuristic: if the first *sample_size* bytes contain a null byte
    or a high ratio of non‑text bytes, treat the file as binary.
    """
    sample = data[:sample_size]
    if b"\x00" in sample:
        return True
    # If > 30 % of bytes are outside printable ASCII + common whitespace
    non_text = sum(
        1 for b in sample
        if b < 0x09 or (0x0D < b < 0x20) or b > 0x7E
    )
    return (non_text / max(len(sample), 1)) > 0.30


def normalize_path(path: str) -> str:
    """
    Normalize a file path to forward slashes, strip leading ./ or /
    """
    p = path.replace("\\", "/")
    while p.startswith("./") or p.startswith("/"):
        p = p[1:] if p.startswith("/") else p[2:]
    return p


def safe_extension(path: str) -> str:
    """Return the lowercase file extension, e.g. '.py'. Never raises."""
    try:
        _, ext = os.path.splitext(path)
        return ext.lower()
    except Exception:
        return ""


def clamp(value: int, lo: int, hi: int) -> int:
    """Clamp an integer between lo and hi."""
    return max(lo, min(hi, value))
