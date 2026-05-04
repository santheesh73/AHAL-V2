"""
AHAL AI — Streaming Scanner
Processes files one‑by‑one from ZIP or disk, applying filter → priority → content loading.
Designed for thread‑pool execution with a shared StatsCollector.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from app.config import ScannerConfig
from app.core.scanner.content_loader import ContentLoader
from app.core.scanner.file_filter import FileFilter
from app.core.scanner.priority_handler import PriorityHandler
from app.core.scanner.stats_collector import StatsCollector
from app.core.scanner.zip_handler import ZipEntry, ZipHandler
from app.core.scanner.repo_handler import RepoEntry
from app.models.file_schema import FileMetadata, Priority
from app.utils.safe_utils import is_likely_binary, safe_extension

logger = logging.getLogger("ahal.scanner.streaming")


class StreamingScanner:
    """
    Stateless processor: takes a single file descriptor (ZIP entry or disk entry),
    decides whether to include it, classifies priority, loads content,
    and records metrics.
    """

    def __init__(self, cfg: ScannerConfig) -> None:
        self._cfg = cfg
        self._filter = FileFilter(cfg)
        self._priority = PriorityHandler(cfg)
        self._content = ContentLoader(cfg)

    # ── Process a ZIP entry ──────────────────────────────────────

    def process_zip_entry(
        self,
        entry: ZipEntry,
        zip_handler: ZipHandler,
        stats: StatsCollector,
    ) -> Tuple[Optional[FileMetadata], Optional[str]]:
        """
        Process a single ZIP entry.
        Returns (metadata, content_str) — either or both may be None.
        """
        try:
            if entry.is_dir:
                return None, None

            stats.record_discovered(entry.size_bytes)

            # Filter
            include, reason = self._filter.should_include(entry.path, entry.size_bytes)
            if not include:
                stats.record_skipped()
                return (
                    FileMetadata(
                        path=entry.path,
                        size_bytes=entry.size_bytes,
                        extension=safe_extension(entry.path),
                        skipped=True,
                        skip_reason=reason,
                    ),
                    None,
                )

            # Priority
            priority = self._priority.classify(entry.path)

            # Read raw bytes
            max_bytes = self._content.max_bytes_for(priority)
            raw = zip_handler.read_entry(entry.path, max_bytes)
            is_binary = False
            content: Optional[str] = None

            if raw is not None:
                is_binary = is_likely_binary(raw)
                if not is_binary:
                    content = self._content.load_from_bytes(raw, priority)

            meta = FileMetadata(
                path=entry.path,
                size_bytes=entry.size_bytes,
                extension=safe_extension(entry.path),
                priority=priority,
                is_binary=is_binary,
                skipped=is_binary,
                skip_reason="binary_file" if is_binary else None,
            )

            if is_binary:
                stats.record_skipped()
            else:
                stats.record_included(meta)

            return meta, content

        except Exception as exc:
            logger.warning("Error processing ZIP entry %s: %s", entry.path, exc)
            stats.record_error(f"zip_entry:{entry.path}:{exc}")
            return None, None

    # ── Process a disk / repo entry ──────────────────────────────

    def process_repo_entry(
        self,
        entry: RepoEntry,
        stats: StatsCollector,
    ) -> Tuple[Optional[FileMetadata], Optional[str]]:
        """
        Process a single file on disk (from repo clone or local dir).
        Returns (metadata, content_str).
        """
        try:
            stats.record_discovered(entry.size_bytes)

            # Filter
            include, reason = self._filter.should_include(entry.path, entry.size_bytes)
            if not include:
                stats.record_skipped()
                return (
                    FileMetadata(
                        path=entry.path,
                        size_bytes=entry.size_bytes,
                        extension=safe_extension(entry.path),
                        skipped=True,
                        skip_reason=reason,
                    ),
                    None,
                )

            # Priority
            priority = self._priority.classify(entry.path)

            # Load content from disk
            content = self._content.load_from_disk(entry.abs_path, priority)
            is_binary = content is None  # safe_read_file returns None for binary

            meta = FileMetadata(
                path=entry.path,
                size_bytes=entry.size_bytes,
                extension=safe_extension(entry.path),
                priority=priority,
                is_binary=is_binary,
                skipped=is_binary,
                skip_reason="binary_file" if is_binary else None,
            )

            if is_binary:
                stats.record_skipped()
            else:
                stats.record_included(meta)

            return meta, content

        except Exception as exc:
            logger.warning("Error processing repo entry %s: %s", entry.path, exc)
            stats.record_error(f"repo_entry:{entry.path}:{exc}")
            return None, None

    # ── Process a single uploaded file ───────────────────────────

    def process_single_file(
        self,
        path: str,
        abs_path: str,
        size_bytes: int,
        stats: StatsCollector,
    ) -> Tuple[Optional[FileMetadata], Optional[str]]:
        """
        Process a single uploaded file.
        """
        entry = RepoEntry(path=path, abs_path=abs_path, size_bytes=size_bytes)
        return self.process_repo_entry(entry, stats)
