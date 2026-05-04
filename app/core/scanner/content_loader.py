"""
AHAL AI — Content Loader
Loads file content with priority‑aware size limits and binary detection.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.config import ScannerConfig
from app.models.file_schema import Priority
from app.utils.safe_utils import is_likely_binary, safe_decode, safe_read_file

logger = logging.getLogger("ahal.scanner.content")


class ContentLoader:
    """Loads file contents respecting size budgets and binary safety."""

    def __init__(self, cfg: ScannerConfig) -> None:
        self._cfg = cfg

    def max_bytes_for(self, priority: Priority) -> int:
        """Return the byte budget for the given priority level."""
        if priority == Priority.HIGH:
            return self._cfg.high_priority_max_bytes
        return self._cfg.default_max_bytes

    # ── Load from disk ───────────────────────────────────────────

    def load_from_disk(self, path: str, priority: Priority) -> Optional[str]:
        """
        Read a file from disk up to the priority‑based byte limit.
        Returns None if binary or unreadable.
        """
        limit = self.max_bytes_for(priority)
        return safe_read_file(path, limit)

    # ── Load from raw bytes (ZIP entries) ────────────────────────

    def load_from_bytes(self, raw: bytes, priority: Priority) -> Optional[str]:
        """
        Decode raw bytes up to the priority‑based byte limit.
        Returns None if binary or decode fails.
        """
        limit = self.max_bytes_for(priority)
        if is_likely_binary(raw):
            return None
        return safe_decode(raw, max_bytes=limit)
