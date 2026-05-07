from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CanonicalConfidenceValue = Literal["High", "Medium", "Low", "Unknown"]


class CanonicalStatusItem(BaseModel):
    title: str
    description: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: CanonicalConfidenceValue = "Unknown"


class CanonicalIssue(BaseModel):
    severity: str
    title: str
    recommendation: str
    evidence_ids: list[str] = Field(default_factory=list)


class CanonicalTechStack(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


class CanonicalAPI(BaseModel):
    method: str
    path: str
    purpose: str
    source: str
    evidence_ids: list[str] = Field(default_factory=list)


class CanonicalWorkflowStep(BaseModel):
    step: int
    title: str
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


class CanonicalEvidence(BaseModel):
    id: str
    label: str
    source_type: str
    reason: str
    confidence: CanonicalConfidenceValue = "Unknown"


class CanonicalConfidence(BaseModel):
    architecture: CanonicalConfidenceValue = "Unknown"
    product_purpose: CanonicalConfidenceValue = "Unknown"
    overall: CanonicalConfidenceValue = "Unknown"


class CanonicalDataQuality(BaseModel):
    normalized: bool = False
    notes: list[str] = Field(default_factory=list)


class CanonicalProjectIntelligence(BaseModel):
    session_id: str
    project_name: str
    project_type: str
    repo_type: str = "unknown"
    product_summary: str
    project_goal: str = ""
    product_domain: str
    architecture_summary: str
    what: str
    why: str
    completed: list[CanonicalStatusItem] = Field(default_factory=list)
    remaining: list[CanonicalStatusItem] = Field(default_factory=list)
    issues: list[CanonicalIssue] = Field(default_factory=list)
    tech_stack: CanonicalTechStack = Field(default_factory=CanonicalTechStack)
    api_surface: list[CanonicalAPI] = Field(default_factory=list)
    workflow: list[CanonicalWorkflowStep] = Field(default_factory=list)
    evidence: list[CanonicalEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: CanonicalConfidence = Field(default_factory=CanonicalConfidence)
    data_quality: CanonicalDataQuality = Field(default_factory=CanonicalDataQuality)
