from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


LLMRole = Literal["primary", "critic"]
TaskType = Literal["chat", "pdf", "prd", "onboarding", "pr_review", "test_gap", "diff"]


class OrchestrationRequest(BaseModel):
    task_type: TaskType
    deterministic_payload: dict = Field(default_factory=dict)
    prompt_context: dict = Field(default_factory=dict)
    max_rounds: int = 1
    require_citations: bool = True


class OrchestrationResult(BaseModel):
    ok: bool
    text: str
    structured_output: Optional[dict] = None
    provider_used: str
    critic_passed: bool
    validation_passed: bool
    fallback_used: bool
    warnings: list[str] = Field(default_factory=list)
