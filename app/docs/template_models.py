from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


TemplateSource = Literal[
    "overview",
    "project_brief",
    "architecture",
    "tech_stack",
    "modules",
    "api_surface",
    "workflow",
    "database",
    "risks",
    "test_gaps",
    "onboarding",
    "evidence",
    "warnings",
    "custom_static",
]


class PRDTemplateSection(BaseModel):
    section_id: str
    title: str
    source: TemplateSource
    required: bool
    max_items: Optional[int] = None
    render_as: Literal["paragraph", "bullets", "table"]
    static_text: Optional[str] = None


class PRDTemplate(BaseModel):
    template_id: str
    name: str
    description: Optional[str] = None
    version: str
    sections: list[PRDTemplateSection] = Field(default_factory=list)
    created_at: str
    updated_at: str


class RenderedTemplateResult(BaseModel):
    template_id: str
    session_id: str
    title: str
    markdown: str
    warnings: list[str] = Field(default_factory=list)
