from typing import Literal, Optional, List
from pydantic import BaseModel, Field
from app.intelligence.presentation_models import CanonicalProjectIntelligence

class DocEvidence(BaseModel):
    source_type: str
    source_id: str
    file: Optional[str] = None
    reason: str
    snippet: Optional[str] = None
    confidence: Literal["high", "medium", "low"]

class PRDSection(BaseModel):
    title: str
    content: str
    evidence: List[DocEvidence] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    warnings: List[str] = Field(default_factory=list)

class APISectionItem(BaseModel):
    method: str
    path: str
    framework: str
    source_file: Optional[str] = None
    handler: Optional[str] = None
    description: str
    evidence: List[DocEvidence] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]

class ModuleSectionItem(BaseModel):
    name: str
    category: str
    files: List[str] = Field(default_factory=list)
    description: str
    evidence: List[DocEvidence] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]

class WorkflowSectionItem(BaseModel):
    order: int
    source: str
    action: str
    target: Optional[str] = None
    evidence: List[DocEvidence] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]

class RiskItem(BaseModel):
    title: str
    severity: Literal["high", "medium", "low"]
    description: str
    evidence: List[DocEvidence] = Field(default_factory=list)
    recommendation: str

class ProjectStatusItem(BaseModel):
    title: str
    status: Literal["built", "partial", "missing", "unknown"]
    description: str
    evidence: List[DocEvidence] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]

class ProjectBrief(BaseModel):
    goal: PRDSection
    what: PRDSection
    why: PRDSection
    completed: List[ProjectStatusItem] = Field(default_factory=list)
    remaining: List[ProjectStatusItem] = Field(default_factory=list)
    issues: List[RiskItem] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    warnings: List[str] = Field(default_factory=list)

class PRDResult(BaseModel):
    session_id: Optional[str] = None
    title: str
    project_type: str
    architecture_label: Optional[str] = None
    repo_intelligence_score: int = 0
    architecture_confidence: Literal["high", "medium", "low"] = "low"
    product_purpose_confidence: Literal["high", "medium", "low"] = "low"
    overview: PRDSection
    project_brief: Optional[ProjectBrief] = None
    architecture: PRDSection
    tech_stack: PRDSection
    modules: List[ModuleSectionItem] = Field(default_factory=list)
    api_endpoints: List[APISectionItem] = Field(default_factory=list)
    databases: PRDSection
    workflow: List[WorkflowSectionItem] = Field(default_factory=list)
    setup_notes: PRDSection
    risks: List[RiskItem] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    evidence_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    canonical_intelligence: Optional[CanonicalProjectIntelligence] = None
