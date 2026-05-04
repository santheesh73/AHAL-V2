"""
AHAL AI — Standardized Error Contract  [Fix 9]

All API failures return a consistent JSON body via HTTPException.detail.
Clients can reliably parse: status, message, code, details.
"""

from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


# ── Error Codes ───────────────────────────────────────────────────

SESSION_NOT_FOUND  = "SESSION_NOT_FOUND"
SCAN_IN_PROGRESS   = "SCAN_IN_PROGRESS"
CAPACITY_EXCEEDED  = "CAPACITY_EXCEEDED"
INVALID_FILE       = "INVALID_FILE"
FILE_TOO_LARGE     = "FILE_TOO_LARGE"
INVALID_URL        = "INVALID_URL"
INVALID_REQUEST    = "INVALID_REQUEST"
RATE_LIMITED       = "RATE_LIMITED"
UNAUTHORIZED       = "UNAUTHORIZED"
INTERNAL_ERROR     = "INTERNAL_ERROR"


# ── Error Response Model ──────────────────────────────────────────

class AHALError(BaseModel):
    """
    Standardized error payload returned in HTTPException.detail.

    Example::

        raise HTTPException(
            status_code=404,
            detail=AHALError(
                status="error",
                code=SESSION_NOT_FOUND,
                message="Session not found",
            ).model_dump(),
        )
    """

    status: Literal["error", "rejected"] = "error"
    message: str
    code: str
    details: Dict[str, Any] = Field(default_factory=dict)


# ── Convenience constructors ──────────────────────────────────────

def err(
    code: str,
    message: str,
    status: Literal["error", "rejected"] = "error",
    **details: Any,
) -> Dict[str, Any]:
    """
    Return a ready-to-use dict for ``HTTPException(detail=...)``.

    Usage::

        raise HTTPException(status_code=404, detail=err(SESSION_NOT_FOUND, "Session not found"))
    """
    return AHALError(
        status=status,
        code=code,
        message=message,
        details=dict(details),
    ).model_dump()
