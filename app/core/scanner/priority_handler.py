"""
AHAL AI — Priority Handler
Assigns HIGH / MEDIUM / LOW priority to files based on their path.
"""

from __future__ import annotations

import logging
import os

from app.config import ScannerConfig
from app.models.file_schema import Priority
from app.utils.safe_utils import normalize_path

logger = logging.getLogger("ahal.scanner.priority")


class PriorityHandler:
    """Stateless priority classifier for file paths."""

    def __init__(self, cfg: ScannerConfig) -> None:
        self._cfg = cfg

    def classify(self, path: str) -> Priority:
        """Return the priority level for the given file path."""
        norm = normalize_path(path)
        basename = os.path.basename(norm)
        parts = set(norm.split("/")[:-1])  # directory segments

        # ── HIGH: entry‑point files ──────────────────────────────
        if basename in self._cfg.high_priority_entry_files:
            return Priority.HIGH

        # ── HIGH: lives inside a high‑priority directory ─────────
        if parts & self._cfg.high_priority_directories:
            return Priority.HIGH

        # ── MEDIUM: utility / helper directories ─────────────────
        if parts & self._cfg.medium_priority_directories:
            return Priority.MEDIUM

        # ── LOW: config / test / docs directories ────────────────
        if parts & self._cfg.low_priority_directories:
            return Priority.LOW

        # Default → MEDIUM (unknown dirs are neither critical nor noise)
        return Priority.MEDIUM
