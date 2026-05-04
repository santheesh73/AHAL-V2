"""
AHAL AI — Stats Collector
Thread‑safe accumulator for scan metrics.
"""

from __future__ import annotations

import threading
import time
from typing import List

from app.models.file_schema import FileMetadata, Priority, ScanStats


class StatsCollector:
    """Collects scan statistics in a thread‑safe manner."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total_discovered = 0
        self._included = 0
        self._skipped = 0
        self._total_bytes = 0
        self._included_bytes = 0
        self._high = 0
        self._medium = 0
        self._low = 0
        self._errors: List[str] = []
        self._start_time: float = time.monotonic()

    # ── Recording ────────────────────────────────────────────────

    def record_discovered(self, size_bytes: int) -> None:
        with self._lock:
            self._total_discovered += 1
            self._total_bytes += size_bytes

    def record_included(self, meta: FileMetadata) -> None:
        with self._lock:
            self._included += 1
            self._included_bytes += meta.size_bytes
            if meta.priority == Priority.HIGH:
                self._high += 1
            elif meta.priority == Priority.MEDIUM:
                self._medium += 1
            else:
                self._low += 1

    def record_skipped(self) -> None:
        with self._lock:
            self._skipped += 1

    def record_error(self, message: str) -> None:
        with self._lock:
            self._errors.append(message)

    # ── Snapshot ─────────────────────────────────────────────────

    @property
    def total_discovered(self) -> int:
        with self._lock:
            return self._total_discovered

    def snapshot(self) -> ScanStats:
        """Return an immutable snapshot of current statistics."""
        with self._lock:
            return ScanStats(
                total_files_discovered=self._total_discovered,
                files_included=self._included,
                files_skipped=self._skipped,
                total_size_bytes=self._total_bytes,
                included_size_bytes=self._included_bytes,
                high_priority_count=self._high,
                medium_priority_count=self._medium,
                low_priority_count=self._low,
                errors=list(self._errors),
                scan_duration_seconds=round(
                    time.monotonic() - self._start_time, 3
                ),
            )
