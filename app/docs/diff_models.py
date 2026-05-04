from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PRDDiffRequest(BaseModel):
    base_session_id: str
    target_session_id: str
    include_llm_polish: bool = False


class SectionDiff(BaseModel):
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    changed: list[str] = Field(default_factory=list)
    unchanged_count: int = 0
    summary: str
    confidence: Literal["high", "medium", "low"] = "low"


class APIDiffItem(BaseModel):
    method: str
    path: str
    change_type: Literal["added", "removed", "modified"]
    summary: str
    risk_level: Literal["low", "medium", "high"] = "low"


class ModuleDiffItem(BaseModel):
    name: str
    change_type: Literal["added", "removed", "modified"]
    category: str
    summary: str
    risk_level: Literal["low", "medium", "high"] = "low"


class PRDDiffResult(BaseModel):
    base_session_id: str
    target_session_id: str
    summary: str
    project_goal_diff: SectionDiff
    architecture_diff: SectionDiff
    tech_stack_diff: SectionDiff
    module_diff: list[ModuleDiffItem] = Field(default_factory=list)
    api_diff: list[APIDiffItem] = Field(default_factory=list)
    workflow_diff: SectionDiff
    database_diff: SectionDiff
    risk_diff: SectionDiff
    remaining_diff: SectionDiff
    suggested_review_focus: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    evidence_count: int = 0
