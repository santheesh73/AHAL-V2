"""Pydantic models for chat and conversational repo analysis."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.utils.evidence_types import normalize_evidence_source_type

ConfidenceLevel = Literal["high", "medium", "low"]
SourceType = Literal[
    "file", "graph_node", "graph_edge", "api_endpoint", "module", "framework", "database",
]
QuestionCategory = Literal[
    "architecture", "workflow", "api", "database", "module", "file",
    "dependency", "security", "testing", "general",
]
ChatIntentName = Literal[
    "project_overview",
    "project_goal",
    "what_is_built",
    "what_remaining",
    "api_explanation",
    "architecture_explanation",
    "workflow_explanation",
    "file_explanation",
    "module_explanation",
    "risk_analysis",
    "test_gap_question",
    "onboarding_question",
    "change_impact_question",
    "how_to_run",
    "how_to_modify",
    "debugging_help",
    "general_repo_question",
    "unsupported",
]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: Optional[str] = None
    summary: Optional[str] = None
    intent: Optional[ChatIntentName] = None
    referenced_files: list[str] = Field(default_factory=list)
    referenced_apis: list[str] = Field(default_factory=list)
    referenced_modules: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    question: str
    include_history: bool = True
    max_context_items: int = 20


class EvidenceReference(BaseModel):
    source_type: SourceType
    source_id: str
    file: Optional[str] = None
    reason: str
    snippet: Optional[str] = None
    confidence: ConfidenceLevel = "medium"

    @field_validator("source_type", mode="before")
    @classmethod
    def _normalize_source_type(cls, value):
        normalized, _ = normalize_evidence_source_type(value)
        return normalized


class ChatAnswerSection(BaseModel):
    title: str
    content: str = ""
    bullets: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ChatIntentEntities(BaseModel):
    file: Optional[str] = None
    api_path: Optional[str] = None
    module: Optional[str] = None
    topic: Optional[str] = None


class ChatIntentResult(BaseModel):
    intent: ChatIntentName = "general_repo_question"
    confidence: ConfidenceLevel = "low"
    entities: ChatIntentEntities = Field(default_factory=ChatIntentEntities)


class ChatContextPack(BaseModel):
    session_id: str
    question: str
    intent: ChatIntentName
    project_identity: dict[str, Any] = Field(default_factory=dict)
    architecture_summary: dict[str, Any] = Field(default_factory=dict)
    relevant_apis: list[dict[str, Any]] = Field(default_factory=list)
    relevant_modules: list[dict[str, Any]] = Field(default_factory=list)
    relevant_workflow: list[dict[str, Any]] = Field(default_factory=list)
    relevant_risks: list[dict[str, Any]] = Field(default_factory=list)
    relevant_test_gaps: list[dict[str, Any]] = Field(default_factory=list)
    relevant_onboarding_steps: list[dict[str, Any]] = Field(default_factory=list)
    selected_evidence: list[EvidenceReference] = Field(default_factory=list)
    conversation_memory: list[ChatMessage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"
    evidence_map: dict[str, EvidenceReference] = Field(default_factory=dict)
    max_context_chars: int = 0


class RetrievedContext(BaseModel):
    context_id: str
    title: str
    content: str
    source_type: SourceType
    source_id: str
    file: Optional[str] = None
    confidence: ConfidenceLevel = "medium"
    category: QuestionCategory = "general"
    keywords: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    score: float = 0.0

    @field_validator("source_type", mode="before")
    @classmethod
    def _normalize_source_type(cls, value):
        normalized, _ = normalize_evidence_source_type(value)
        return normalized


class ChatAnswer(BaseModel):
    answer: str
    short_answer: str = ""
    sections: list[ChatAnswerSection] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"
    evidence: list[EvidenceReference] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    related_nodes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    insufficient_context: bool = False
    suggested_followups: list[str] = Field(default_factory=list)
    intent: ChatIntentName = "general_repo_question"
    used_llm: bool = False
    fallback_used: bool = True


class QuestionClassification(BaseModel):
    category: QuestionCategory = "general"
    entities: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"


class ProjectPurpose(BaseModel):
    title: Optional[str] = None
    domain: Optional[str] = None
    summary: Optional[str] = None
    capabilities: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"
