from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class CodeEvidence(BaseModel):
    source_id: str
    reason: str
    snippet: Optional[str] = None


class CodeSessionResult(BaseModel):
    language: str = "unknown"
    summary: str = "Insufficient evidence from codebase."
    detected_functions: list[str] = Field(default_factory=list)
    detected_classes: list[str] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    entrypoints: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    suggested_improvements: list[str] = Field(default_factory=list)
    evidence: list[CodeEvidence] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    warnings: list[str] = Field(default_factory=list)
