from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.docs.models import DocEvidence


AudienceType = Literal["new_engineer", "frontend", "backend", "qa", "devops"]
PriorityLevel = Literal["high", "medium", "low"]
ConfidenceLevel = Literal["high", "medium", "low"]


class OnboardingRequest(BaseModel):
    session_id: str
    audience: AudienceType = "new_engineer"
    time_budget_minutes: int = 30


class OnboardingStep(BaseModel):
    title: str
    description: str
    files_to_read: list[str] = Field(default_factory=list)
    reason: str
    estimated_minutes: int
    priority: PriorityLevel
    evidence: list[DocEvidence] = Field(default_factory=list)


class OnboardingReport(BaseModel):
    session_id: str
    audience: str
    time_budget_minutes: int
    summary: str
    project_context: str
    reading_order: list[OnboardingStep] = Field(default_factory=list)
    key_entry_points: list[str] = Field(default_factory=list)
    critical_modules: list[str] = Field(default_factory=list)
    important_apis: list[str] = Field(default_factory=list)
    main_workflows: list[str] = Field(default_factory=list)
    gotchas: list[str] = Field(default_factory=list)
    safe_first_tasks: list[str] = Field(default_factory=list)
    avoid_first: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    warnings: list[str] = Field(default_factory=list)
    evidence_count: int = 0
