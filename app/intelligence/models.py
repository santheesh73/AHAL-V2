"""
AHAL AI — Intelligence Models (Phase 2)

Pydantic models for all deterministic intelligence outputs.
Every detection carries evidence. No evidence = no detection.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ── Confidence type alias ─────────────────────────────────────────

ConfidenceLevel = Literal["high", "medium", "low"]


# ── Evidence ──────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    """A single piece of evidence backing a detection."""
    file: str
    reason: str
    snippet: Optional[str] = None
    confidence: ConfidenceLevel = "medium"


# ── Language ──────────────────────────────────────────────────────

class DetectedLanguage(BaseModel):
    """A programming language detected in the codebase."""
    name: str
    file_count: int
    percentage: float
    confidence: ConfidenceLevel
    evidence: List[EvidenceItem] = Field(default_factory=list)


# ── Dependency ────────────────────────────────────────────────────

class DetectedDependency(BaseModel):
    """A dependency detected from a manifest file."""
    name: str
    ecosystem: str
    source_file: str
    category: Literal[
        "frontend", "backend", "database", "orm",
        "tooling", "testing", "unknown",
    ] = "unknown"
    confidence: ConfidenceLevel = "medium"
    evidence: List[EvidenceItem] = Field(default_factory=list)


# ── Framework ─────────────────────────────────────────────────────

class DetectedFramework(BaseModel):
    """A framework or library detected through imports/config/deps."""
    name: str
    category: Literal[
        "frontend", "backend", "database", "orm",
        "tooling", "testing", "unknown",
    ] = "unknown"
    confidence: ConfidenceLevel = "medium"
    evidence: List[EvidenceItem] = Field(default_factory=list)


# ── Entry Point ───────────────────────────────────────────────────

class DetectedEntryPoint(BaseModel):
    """An application entry point file."""
    file: str
    type: Literal["frontend", "backend", "script", "config", "unknown"] = "unknown"
    framework: Optional[str] = None
    confidence: ConfidenceLevel = "medium"
    evidence: List[EvidenceItem] = Field(default_factory=list)


# ── API Endpoint ──────────────────────────────────────────────────

class DetectedAPIEndpoint(BaseModel):
    """A detected HTTP API route/endpoint."""
    method: str
    path: str
    framework: str
    file: str
    handler: Optional[str] = None
    confidence: ConfidenceLevel = "medium"
    evidence: List[EvidenceItem] = Field(default_factory=list)


# ── Database ──────────────────────────────────────────────────────

class DetectedDatabase(BaseModel):
    """A database or data store detected in the codebase."""
    name: str
    usage: Literal["direct", "orm", "config", "unknown"] = "unknown"
    confidence: ConfidenceLevel = "medium"
    evidence: List[EvidenceItem] = Field(default_factory=list)


# ── Module ────────────────────────────────────────────────────────

class DetectedModule(BaseModel):
    """A logical module/layer detected from directory structure."""
    name: str
    category: Literal[
        "api", "ui", "database", "config", "service", "model",
        "schema", "auth", "test", "worker", "utility", "unknown",
    ] = "unknown"
    files: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "medium"
    evidence: List[EvidenceItem] = Field(default_factory=list)


# ── Architecture ──────────────────────────────────────────────────

class ArchitectureResult(BaseModel):
    """The overall architecture classification of the project."""
    type: Literal[
        "frontend", "backend", "fullstack", "library",
        "cli", "microservices", "unknown",
    ] = "unknown"
    confidence: ConfidenceLevel = "low"
    reasoning: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)


# ── Workflow ──────────────────────────────────────────────────────

class WorkflowStep(BaseModel):
    """A single step in the inferred execution workflow."""
    order: int
    source: str
    action: str
    target: Optional[str] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)
    confidence: ConfidenceLevel = "medium"


class WorkflowResult(BaseModel):
    """The inferred execution workflow of the project."""
    completeness: Literal["complete", "partial", "minimal", "unknown"] = "unknown"
    confidence: ConfidenceLevel = "low"
    steps: List[WorkflowStep] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ── LLM Explanation ───────────────────────────────────────────────

class LLMExplanation(BaseModel):
    """Optional Gemma 26B IT explanation of intelligence results."""
    model: str = ""
    content: str = ""
    used: bool = False
    error: Optional[str] = None


# ── Top-level result ──────────────────────────────────────────────

class IntelligenceResult(BaseModel):
    """Complete intelligence analysis output for a scanned codebase."""
    session_id: Optional[str] = None
    project_type: str = "unknown"
    languages: List[DetectedLanguage] = Field(default_factory=list)
    dependencies: List[DetectedDependency] = Field(default_factory=list)
    frameworks: List[DetectedFramework] = Field(default_factory=list)
    entry_points: List[DetectedEntryPoint] = Field(default_factory=list)
    api_endpoints: List[DetectedAPIEndpoint] = Field(default_factory=list)
    databases: List[DetectedDatabase] = Field(default_factory=list)
    modules: List[DetectedModule] = Field(default_factory=list)
    architecture: ArchitectureResult = Field(default_factory=ArchitectureResult)
    workflow: WorkflowResult = Field(default_factory=WorkflowResult)
    warnings: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    confidence_score: float = 0.0
    explanation: Optional[LLMExplanation] = None
