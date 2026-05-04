from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.docs.models import DocEvidence


class TestGapRequest(BaseModel):
    session_id: str
    include_low_priority: bool = False


class TestGapItem(BaseModel):
    target: str
    target_type: Literal["api", "module", "workflow", "function", "class", "service", "database", "auth", "config"]
    path: str
    reason: str
    suggested_test: str
    priority: Literal["low", "medium", "high"]
    confidence: Literal["low", "medium", "high"]
    evidence: list[DocEvidence] = Field(default_factory=list)


class TestGapResult(BaseModel):
    session_id: str
    summary: str
    total_targets: int = 0
    tested_targets: int = 0
    gap_count: int = 0
    gaps: list[TestGapItem] = Field(default_factory=list)
    tested_evidence: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "low"
