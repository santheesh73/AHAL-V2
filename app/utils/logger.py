"""
AHAL AI — Structured Logger
Lightweight, zero-dependency structured logging utility.

Outputs consistent, grep-friendly log lines:
    [INFO]  [session_id] message
    [ERROR] [session_id] message
    [STAGE] [session_id] stage_name
    [SCAN]  [session_id] batch_info

No external frameworks — wraps stdlib logging only.
Performance: log calls are no-ops if level is disabled.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

# Root AHAL logger — configured by main.py at startup
_root = logging.getLogger("ahal")

# Module-level sub-loggers (lazy, zero cost if unused)
_info_log  = logging.getLogger("ahal.structured.info")
_error_log = logging.getLogger("ahal.structured.error")
_stage_log = logging.getLogger("ahal.structured.stage")
_scan_log  = logging.getLogger("ahal.structured.scan")


# ── Public helpers ────────────────────────────────────────────────

def log_info(message: str, session_id: Optional[str] = None) -> None:
    """
    Emit an INFO-level structured log line.

    Format: [INFO]  [<session_id>] <message>
    """
    try:
        sid = f"[{session_id}]" if session_id else "[-]"
        _info_log.info("[INFO]  %s %s", sid, message)
    except Exception:
        pass  # logging must never crash the caller


def log_error(message: str, session_id: Optional[str] = None) -> None:
    """
    Emit an ERROR-level structured log line.

    Format: [ERROR] [<session_id>] <message>
    """
    try:
        sid = f"[{session_id}]" if session_id else "[-]"
        _error_log.error("[ERROR] %s %s", sid, message)
    except Exception:
        pass


def log_stage(session_id: str, stage: str) -> None:
    """
    Emit a STAGE transition log line.

    Format: [STAGE] [<session_id>] <stage>
    """
    try:
        _stage_log.info("[STAGE] [%s] %s", session_id, stage)
    except Exception:
        pass


def log_scan(session_id: str, processed: int, total: int, skipped: int = 0) -> None:
    """
    Emit a scan batch progress log line.

    Format: [SCAN]  [<session_id>] processed=<n> total=<n> skipped=<n>
    """
    try:
        _scan_log.info(
            "[SCAN]  [%s] processed=%d total=%d skipped=%d",
            session_id, processed, total, skipped,
        )
    except Exception:
        pass


def log_timeout(session_id: str, elapsed: float, limit: float) -> None:
    """Log a watchdog timeout event."""
    try:
        _error_log.warning(
            "[TIMEOUT] [%s] scan exceeded %.1fs limit (%.1fs elapsed)",
            session_id, limit, elapsed,
        )
    except Exception:
        pass
