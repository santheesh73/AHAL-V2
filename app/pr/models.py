from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.changes.models import ChangedFileInput
from app.docs.models import DocEvidence


class PullRequestAnalysisRequest(BaseModel):
    repo_url: Optional[str] = None
    session_id: Optional[str] = None
    index_id: Optional[str] = None
    pr_number: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    diff_text: Optional[str] = None
    changed_files: list[ChangedFileInput] = Field(default_factory=list)
    base_ref: Optional[str] = None
    head_ref: Optional[str] = None
    include_llm_polish: bool = False


class PullRequestFileImpact(BaseModel):
    path: str
    status: str
    summary: str
    affected_modules: list[str] = Field(default_factory=list)
    affected_apis: list[str] = Field(default_factory=list)
    affected_workflows: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    suggested_tests: list[str] = Field(default_factory=list)
    evidence: list[DocEvidence] = Field(default_factory=list)


class PullRequestAnalysisResult(BaseModel):
    summary: str
    pr_title: Optional[str] = None
    repo_url: Optional[str] = None
    session_id: Optional[str] = None
    index_id: Optional[str] = None
    changed_files: list[PullRequestFileImpact] = Field(default_factory=list)
    affected_apis: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    affected_workflows: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    breaking_change_risk: str = "low"
    suggested_tests: list[str] = Field(default_factory=list)
    reviewer_focus: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: str = "low"
    evidence_count: int = 0
