from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.changes.models import ChangedFileInput
from app.indexing.models import DeltaChangedFile


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)


class AnalyzeCodeToolInput(BaseModel):
    code: str
    filename: Optional[str] = None
    language: Optional[str] = None


class SessionToolInput(BaseModel):
    session_id: str
    session_token: Optional[str] = None


class AskRepoToolInput(SessionToolInput):
    question: str


class GeneratePRDToolInput(SessionToolInput):
    format: Literal["json", "markdown"] = "json"


class DiffPRDToolInput(BaseModel):
    base_session_id: str
    target_session_id: str
    format: Literal["json", "markdown"] = "json"
    session_token: Optional[str] = None


class CreateRepoIndexToolInput(SessionToolInput):
    pass


class DeltaScanToolInput(BaseModel):
    index_id: str
    changed_files: list[DeltaChangedFile] = Field(default_factory=list)
    session_token: Optional[str] = None


class TestGapToolInput(SessionToolInput):
    include_low_priority: bool = False


class OnboardingToolInput(SessionToolInput):
    audience: str = "new_engineer"
    time_budget_minutes: int = 30
    format: Literal["json", "markdown"] = "json"


class AnalyzePRToolInput(BaseModel):
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
    session_token: Optional[str] = None


class MCPErrorResponse(BaseModel):
    ok: bool = False
    error_code: str
    message: str
