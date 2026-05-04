from __future__ import annotations

from pydantic import BaseModel, Field


class GitHubWebhookEvent(BaseModel):
    event_id: str
    event_type: str
    repo_url: str | None = None
    action: str | None = None
    branch: str | None = None
    pr_number: int | None = None
    status: str
    warnings: list[str] = Field(default_factory=list)
    created_at: str


class WebhookTriggeredResult(BaseModel):
    delta_scan: bool = False
    pr_analysis: bool = False


class WebhookProcessResult(BaseModel):
    ok: bool
    event_type: str
    repo_url: str | None = None
    action: str | None = None
    triggered: WebhookTriggeredResult = Field(default_factory=WebhookTriggeredResult)
    warnings: list[str] = Field(default_factory=list)
