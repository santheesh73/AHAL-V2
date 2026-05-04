from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


SessionType = Literal["code", "folder", "repo"]


class SessionTimelineEvent(BaseModel):
    timestamp: str
    stage: str
    status: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
