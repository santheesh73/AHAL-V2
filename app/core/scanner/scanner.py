"""
AHAL AI — Scanner Orchestrator  [HARDENED v3]

Capabilities added:
  - Cancellation hook: cancel_cb checked in every processing loop
  - Structured logging: batch progress, skip events, timeout events
  - All existing hardening (dynamic pool, watchdog, content cap) preserved
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional

from app.config import ScannerConfig, config
from app.core.scanner.repo_handler import RepoHandler
from app.core.scanner.stats_collector import StatsCollector
from app.core.scanner.streaming_scanner import StreamingScanner
from app.core.scanner.zip_handler import ZipHandler
from app.models.file_schema import (
    FileMetadata,
    ScanResult,
    ScanStatus,
)
from app.utils.logger import log_info, log_scan, log_timeout
from app.utils.safe_utils import clamp

logger = logging.getLogger("ahal.scanner")

# Dynamic pool size: cpu_count capped at 8, env-overridable
_MAX_WORKERS = int(
    os.getenv("AHAL_MAX_WORKERS", str(min(8, os.cpu_count() or 4)))
)

# Log a [SCAN] line every N files to avoid flooding
_LOG_INTERVAL = 100


class Scanner:
    """
    High‑level orchestrator.

    All scan methods accept an optional `cancel_cb: Callable[[], bool]`.
    When cancel_cb() returns True, the scan stops immediately and returns
    a partial result — no exception is raised.
    """

    def __init__(self, cfg: ScannerConfig | None = None) -> None:
        self._cfg = cfg or config.scanner
        self._streaming = StreamingScanner(self._cfg)
        self._max_content_bytes = self._cfg.max_total_content_mb * 1024 * 1024
        self._timeout = self._cfg.max_scan_time_seconds

    # ── ZIP scanning ─────────────────────────────────────────────

    def scan_zip(
        self,
        zip_path: str,
        session_id: str = "",
        progress_cb: Optional[Callable[[int, int, int], None]] = None,
        cancel_cb: Optional[Callable[[], bool]] = None,
    ) -> ScanResult:
        """
        Stream‑scan a ZIP archive.
        progress_cb(pct, processed, total) — never raises.
        cancel_cb() → True stops the scan and returns partial result.
        """
        stats = StatsCollector()
        files: List[FileMetadata] = []
        contents: Dict[str, str] = {}
        errors: List[str] = []
        timed_out = False
        cancelled = False
        deadline = time.monotonic() + self._timeout
        start_time = time.monotonic()

        log_info("ZIP scan started", session_id=session_id)

        try:
            with ZipHandler(zip_path, self._cfg) as zh:
                entries = [e for e in zh.iter_entries() if not e.is_dir]
                total = len(entries)
                content_bytes_used = 0

                log_info(f"ZIP has {total} files to scan", session_id=session_id)

                with ThreadPoolExecutor(
                    max_workers=_MAX_WORKERS,
                    thread_name_prefix="zip-scan",
                ) as pool:
                    futures: Dict[Future, object] = {}
                    for entry in entries:
                        fut = pool.submit(
                            self._streaming.process_zip_entry,
                            entry, zh, stats,
                        )
                        futures[fut] = entry

                    processed = 0
                    skipped = 0

                    for fut in as_completed(futures):
                        # ── Cancellation check ────────────────────
                        if cancel_cb and cancel_cb():
                            cancelled = True
                            errors.append(f"scan_cancelled at {processed}/{total} files")
                            log_info(
                                f"ZIP scan cancelled at {processed}/{total} files",
                                session_id=session_id,
                            )
                            for pending in futures:
                                pending.cancel()
                            break

                        # ── Watchdog check ────────────────────────
                        if time.monotonic() > deadline:
                            timed_out = True
                            elapsed = time.monotonic() - start_time
                            errors.append(
                                f"scan_timeout: exceeded {self._timeout}s — "
                                f"processed {processed}/{total} files"
                            )
                            log_timeout(session_id, elapsed, self._timeout)
                            for pending in futures:
                                pending.cancel()
                            break

                        processed += 1
                        try:
                            meta, content = fut.result()
                            if meta is not None:
                                files.append(meta)
                                if meta.skipped:
                                    skipped += 1
                            # ── Content budget check ───────────────
                            if (
                                content is not None
                                and meta is not None
                                and not meta.skipped
                            ):
                                content_len = len(content.encode("utf-8", errors="replace"))
                                if content_bytes_used + content_len <= self._max_content_bytes:
                                    contents[meta.path] = content
                                    content_bytes_used += content_len
                                else:
                                    logger.debug(
                                        "Content cap reached (%dMB) — skipping %s",
                                        self._cfg.max_total_content_mb, meta.path,
                                    )
                        except Exception as exc:
                            errors.append(f"worker_error:{exc}")

                        # ── Real progress ──────────────────────────
                        if progress_cb and total > 0:
                            pct = clamp(int((processed / total) * 100), 0, 99)
                            progress_cb(pct, processed, total)

                        # ── Periodic structured log ────────────────
                        if processed % _LOG_INTERVAL == 0:
                            log_scan(session_id, processed, total, skipped)

        except Exception as exc:
            logger.error("ZIP scan failed: %s", exc)
            errors.append(f"zip_scan_error:{exc}")

        scan_stats = stats.snapshot()
        scan_stats.errors.extend(errors)
        status = (
            ScanStatus.PARTIAL
            if (errors or timed_out or cancelled)
            else ScanStatus.COMPLETED
        )

        if progress_cb:
            progress_cb(100, len(files), len(files))

        log_info(
            f"ZIP scan finished → {status.value} "
            f"({len(files)} files, {len(contents)} contents loaded)",
            session_id=session_id,
        )

        return ScanResult(
            session_id=session_id,
            status=status,
            progress=100,
            stats=scan_stats,
            files=self._sort_files(files),
            contents=contents,
            errors=errors,
        )

    # ── GitHub repo scanning ─────────────────────────────────────

    def scan_repo(
        self,
        github_url: str,
        session_id: str = "",
        progress_cb: Optional[Callable[[int, int, int], None]] = None,
        cancel_cb: Optional[Callable[[], bool]] = None,
    ) -> ScanResult:
        """
        Clone and scan a GitHub repository.
        Never raises — always returns a (possibly partial) ScanResult.
        """
        stats = StatsCollector()
        files: List[FileMetadata] = []
        contents: Dict[str, str] = {}
        errors: List[str] = []
        handler = RepoHandler(self._cfg)
        timed_out = False
        cancelled = False
        deadline = time.monotonic() + self._timeout
        start_time = time.monotonic()

        log_info(f"Repo scan started: {github_url}", session_id=session_id)

        try:
            # ── Pre-clone cancellation check ──────────────────────
            if cancel_cb and cancel_cb():
                return ScanResult(
                    session_id=session_id,
                    status=ScanStatus.FAILED,
                    progress=0,
                    errors=["Cancelled by user"],
                )

            handler.clone(github_url)

            # ── Post-clone cancellation check ─────────────────────
            if cancel_cb and cancel_cb():
                cancelled = True
                errors.append("scan_cancelled after clone")
            else:
                # ── Repo size guard ───────────────────────────────
                clone_dir = handler.clone_dir
                if clone_dir:
                    repo_size_mb = self._dir_size_mb(clone_dir)
                    log_info(
                        f"Repo size: {repo_size_mb:.1f}MB",
                        session_id=session_id,
                    )
                    if repo_size_mb > self._cfg.github_max_repo_size_mb:
                        errors.append(
                            f"repo_too_large: {repo_size_mb:.1f}MB > "
                            f"{self._cfg.github_max_repo_size_mb}MB limit"
                        )
                        logger.warning(
                            "Repo %s is %.1fMB — exceeds limit, aborting",
                            github_url, repo_size_mb,
                        )
                        return ScanResult(
                            session_id=session_id,
                            status=ScanStatus.PARTIAL,
                            progress=0,
                            errors=errors,
                        )

                entries = list(handler.iter_files())
                total = len(entries)
                content_bytes_used = 0
                skipped = 0

                log_info(f"Repo has {total} files to scan", session_id=session_id)

                with ThreadPoolExecutor(
                    max_workers=_MAX_WORKERS,
                    thread_name_prefix="repo-scan",
                ) as pool:
                    futures: Dict[Future, object] = {}
                    for entry in entries:
                        fut = pool.submit(
                            self._streaming.process_repo_entry,
                            entry, stats,
                        )
                        futures[fut] = entry

                    processed = 0
                    for fut in as_completed(futures):
                        # ── Cancellation check ────────────────────
                        if cancel_cb and cancel_cb():
                            cancelled = True
                            errors.append(f"scan_cancelled at {processed}/{total} files")
                            log_info(
                                f"Repo scan cancelled at {processed}/{total} files",
                                session_id=session_id,
                            )
                            for pending in futures:
                                pending.cancel()
                            break

                        # ── Watchdog ──────────────────────────────
                        if time.monotonic() > deadline:
                            timed_out = True
                            elapsed = time.monotonic() - start_time
                            errors.append(
                                f"scan_timeout: exceeded {self._timeout}s — "
                                f"processed {processed}/{total} files"
                            )
                            log_timeout(session_id, elapsed, self._timeout)
                            for pending in futures:
                                pending.cancel()
                            break

                        processed += 1
                        try:
                            meta, content = fut.result()
                            if meta is not None:
                                files.append(meta)
                                if meta.skipped:
                                    skipped += 1
                            if (
                                content is not None
                                and meta is not None
                                and not meta.skipped
                            ):
                                content_len = len(content.encode("utf-8", errors="replace"))
                                if content_bytes_used + content_len <= self._max_content_bytes:
                                    contents[meta.path] = content
                                    content_bytes_used += content_len
                                else:
                                    logger.debug(
                                        "Content cap reached — skipping %s", meta.path
                                    )
                        except Exception as exc:
                            errors.append(f"worker_error:{exc}")

                        if progress_cb and total > 0:
                            pct = clamp(int((processed / total) * 100), 0, 99)
                            progress_cb(pct, processed, total)

                        if processed % _LOG_INTERVAL == 0:
                            log_scan(session_id, processed, total, skipped)

        except Exception as exc:
            logger.error("Repo scan failed: %s", exc)
            errors.append(f"repo_scan_error:{exc}")
        finally:
            handler.cleanup()

        scan_stats = stats.snapshot()
        scan_stats.errors.extend(errors)
        status = (
            ScanStatus.PARTIAL
            if (errors or timed_out or cancelled)
            else ScanStatus.COMPLETED
        )

        if progress_cb:
            progress_cb(100, len(files), len(files))

        log_info(
            f"Repo scan finished → {status.value} "
            f"({len(files)} files, {len(contents)} contents loaded)",
            session_id=session_id,
        )

        return ScanResult(
            session_id=session_id,
            status=status,
            progress=100,
            stats=scan_stats,
            files=self._sort_files(files),
            contents=contents,
            errors=errors,
        )

    # ── Single file scanning ─────────────────────────────────────

    def scan_file(
        self,
        abs_path: str,
        display_name: str,
        session_id: str = "",
        progress_cb: Optional[Callable[[int, int, int], None]] = None,
        cancel_cb: Optional[Callable[[], bool]] = None,
    ) -> ScanResult:
        """Scan a single uploaded file."""
        stats = StatsCollector()
        files: List[FileMetadata] = []
        contents: Dict[str, str] = {}
        errors: List[str] = []

        log_info(f"Single file scan: {display_name}", session_id=session_id)

        # Cancellation check before work
        if cancel_cb and cancel_cb():
            return ScanResult(
                session_id=session_id,
                status=ScanStatus.FAILED,
                progress=0,
                errors=["Cancelled by user"],
            )

        try:
            size = os.path.getsize(abs_path)
            meta, content = self._streaming.process_single_file(
                path=display_name,
                abs_path=abs_path,
                size_bytes=size,
                stats=stats,
            )
            if meta is not None:
                files.append(meta)
            if content is not None and meta is not None and not meta.skipped:
                content_len = len(content.encode("utf-8", errors="replace"))
                if content_len <= self._max_content_bytes:
                    contents[meta.path] = content

        except Exception as exc:
            logger.error("Single file scan failed: %s", exc)
            errors.append(f"file_scan_error:{exc}")

        if progress_cb:
            progress_cb(100, 1, 1)

        scan_stats = stats.snapshot()
        scan_stats.errors.extend(errors)
        status = ScanStatus.COMPLETED if not errors else ScanStatus.PARTIAL

        log_info(f"Single file scan → {status.value}", session_id=session_id)

        return ScanResult(
            session_id=session_id,
            status=status,
            progress=100,
            stats=scan_stats,
            files=files,
            contents=contents,
            errors=errors,
        )

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _sort_files(files: List[FileMetadata]) -> List[FileMetadata]:
        """Sort: HIGH first, MEDIUM, LOW. Non‑skipped before skipped."""
        priority_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            files,
            key=lambda f: (
                f.skipped,
                priority_order.get(f.priority.value, 3),
                f.path,
            ),
        )

    @staticmethod
    def _dir_size_mb(path: str) -> float:
        """Calculate total directory size in MB. Returns 0.0 on error."""
        try:
            total = 0
            for dirpath, _, filenames in os.walk(path):
                for fname in filenames:
                    try:
                        total += os.path.getsize(os.path.join(dirpath, fname))
                    except OSError:
                        pass
            return total / (1024 * 1024)
        except Exception:
            return 0.0
