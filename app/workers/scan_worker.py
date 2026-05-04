"""
AHAL AI — Scan Worker  [HARDENED v4]

Fix 3: Config-driven background pool via AHAL_BG_WORKERS.
       Pool is lazy-initialized on first use (after env is fully loaded).

Existing capabilities preserved:
  - Cancellation checks before every stage transition
  - Structured logging throughout
  - cancel_cb wired into Scanner for mid-loop cancellation
  - Guaranteed temp file cleanup in finally block
"""

from __future__ import annotations

import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from app.core.scanner.scanner import Scanner
from app.models.file_schema import InputType, ScanStage
from app.sessions.session_manager import session_manager
from app.utils.logger import log_error, log_info, log_stage

logger = logging.getLogger("ahal.workers.scan")

# ── Lazy background pool (Fix 3) ─────────────────────────────────
# Pool is NOT created at import time — config must be fully loaded first.

_bg_pool: Optional[ThreadPoolExecutor] = None
_pool_lock = __import__("threading").Lock()


def _get_bg_pool() -> ThreadPoolExecutor:
    """Return the singleton background pool, creating it on first call."""
    global _bg_pool
    if _bg_pool is None:
        with _pool_lock:
            if _bg_pool is None:
                from app.config import config
                n = config.scanner.bg_worker_count
                logger.info("Initializing background pool: max_workers=%d", n)
                _bg_pool = ThreadPoolExecutor(
                    max_workers=n,
                    thread_name_prefix="scan-bg",
                )
    return _bg_pool


def submit_scan(
    session_id: str,
    input_type: InputType,
    file_path: Optional[str] = None,
    display_name: Optional[str] = None,
    github_url: Optional[str] = None,
) -> None:
    """
    Submit a scan job to the background pool.
    Returns immediately — non-blocking.
    """
    _get_bg_pool().submit(
        _run_scan,
        session_id,
        input_type,
        file_path,
        display_name,
        github_url,
    )
    log_info(f"Scan job submitted: type={input_type.value}", session_id=session_id)


def _run_scan(
    session_id: str,
    input_type: InputType,
    file_path: Optional[str],
    display_name: Optional[str],
    github_url: Optional[str],
) -> None:
    """
    Execute the scan synchronously inside a background thread.
    NEVER raises — all errors captured and stored in the session.
    """
    scanner = Scanner()

    # ── Cancellation callback — O(1) lock-protected set lookup ───
    def _is_cancelled() -> bool:
        return session_manager.is_cancelled(session_id)

    # ── Progress callback ─────────────────────────────────────────
    def _progress(pct: int, processed: int = 0, total: int = 0) -> None:
        session_manager.update_progress(
            session_id,
            pct,
            message=(
                f"Scanning… {pct}% ({processed}/{total} files)"
                if total else f"Scanning… {pct}%"
            ),
            processed_files=processed,
            total_files=total,
        )

    try:
        # ── Stage: initializing ───────────────────────────────────
        if _is_cancelled():
            log_info("Scan cancelled before start", session_id=session_id)
            session_manager.set_failed(session_id, "Cancelled by user")
            return

        session_manager.set_stage(session_id, ScanStage.INITIALIZING, "Preparing scan…")
        session_manager.update_progress(session_id, 0)
        log_info(f"Scan starting: type={input_type.value}", session_id=session_id)

        # ── Dispatch by input type ────────────────────────────────
        if input_type == InputType.ZIP:
            if not file_path:
                raise ValueError("file_path required for ZIP scan")

            if _is_cancelled():
                session_manager.set_failed(session_id, "Cancelled by user")
                return

            session_manager.set_stage(
                session_id, ScanStage.EXTRACTING_ZIP, "Streaming ZIP archive…"
            )
            result = scanner.scan_zip(
                zip_path=file_path,
                session_id=session_id,
                progress_cb=_progress,
                cancel_cb=_is_cancelled,
            )

        elif input_type == InputType.GITHUB_REPO:
            if not github_url:
                raise ValueError("github_url required for repo scan")

            if _is_cancelled():
                session_manager.set_failed(session_id, "Cancelled by user")
                return

            session_manager.set_stage(
                session_id, ScanStage.CLONING_REPO, f"Cloning {github_url}…"
            )
            result = scanner.scan_repo(
                github_url=github_url,
                session_id=session_id,
                progress_cb=_progress,
                cancel_cb=_is_cancelled,
            )

        elif input_type == InputType.SINGLE_FILE:
            if not file_path or not display_name:
                raise ValueError("file_path and display_name required for single file scan")

            if _is_cancelled():
                session_manager.set_failed(session_id, "Cancelled by user")
                return

            session_manager.set_stage(
                session_id, ScanStage.SCANNING_FILES, f"Scanning {display_name}…"
            )
            result = scanner.scan_file(
                abs_path=file_path,
                display_name=display_name,
                session_id=session_id,
                progress_cb=_progress,
                cancel_cb=_is_cancelled,
            )

        else:
            raise ValueError(f"Unknown input type: {input_type}")

        # ── Final cancellation check before storing result ────────
        if _is_cancelled():
            log_info("Scan cancelled post-processing", session_id=session_id)
            # Result already stored by cancel_session; don't overwrite
            return

        session_manager.set_result(session_id, result)
        log_info(
            f"Scan completed: status={result.status.value} "
            f"files={result.stats.files_included}",
            session_id=session_id,
        )

    except Exception as exc:
        log_error(f"Scan worker exception: {exc}", session_id=session_id)
        logger.exception("Scan worker failed for session %s", session_id)
        session_manager.set_failed(session_id, str(exc))

    finally:
        # ── Guaranteed resource cleanup ───────────────────────────
        _cleanup(session_id, input_type, file_path)


def _cleanup(
    session_id: str,
    input_type: InputType,
    file_path: Optional[str],
) -> None:
    """
    Delete temp files/directories.
    shutil.rmtree for dirs, os.unlink for files.
    Always runs — never raises.
    """
    if not file_path:
        return

    try:
        if os.path.isdir(file_path):
            shutil.rmtree(file_path, ignore_errors=True)
            log_info(f"Cleaned up temp dir: {file_path}", session_id=session_id)
        elif os.path.isfile(file_path):
            os.unlink(file_path)
            log_info(f"Removed temp file: {file_path}", session_id=session_id)
    except Exception as exc:
        log_error(f"Cleanup failed for {file_path}: {exc}", session_id=session_id)
