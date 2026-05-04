from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.docs.models import DocEvidence, RiskItem


class ChangedFileInput(BaseModel):
    path: str
    before: Optional[str] = None
    after: Optional[str] = None
    status: Literal["added", "modified", "deleted", "renamed", "unknown"] = "unknown"


class ChangeAnalysisRequest(BaseModel):
    session_id: Optional[str] = None
    diff_text: Optional[str] = None
    changed_files: list[ChangedFileInput] = Field(default_factory=list)
    base_ref: Optional[str] = None
    head_ref: Optional[str] = None
    source_type: Literal["diff", "files", "github_pr"] = "diff"
    include_llm: bool = False


class ChangedFileImpact(BaseModel):
    path: str
    status: str
    change_type: str
    summary: str
    affected_symbols: list[str] = Field(default_factory=list)
    affected_apis: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    suggested_tests: list[str] = Field(default_factory=list)
    evidence: list[DocEvidence] = Field(default_factory=list)


class ChangeImpactResult(BaseModel):
    session_id: Optional[str] = None
    source_type: str
    summary: str
    changed_files: list[ChangedFileImpact] = Field(default_factory=list)
    affected_apis: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    affected_workflows: list[str] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    suggested_tests: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    warnings: list[str] = Field(default_factory=list)
    evidence_count: int = 0
