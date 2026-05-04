from __future__ import annotations

import uuid

from app.docs.models import PRDResult
from app.docs.template_models import PRDTemplate, RenderedTemplateResult
from app.docs.utils.production_text import clean_list, clean_sentence
from app.sessions.models import utc_now_iso
from app.utils.ignored_paths import is_ignored_path


_VALID_SOURCES = {
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
}


def built_in_templates() -> dict[str, PRDTemplate]:
    now = utc_now_iso()
    return {
        "default_prd": PRDTemplate(
            template_id="default_prd",
            name="Default PRD",
            description="Balanced deterministic project brief.",
            version="1.0",
            created_at=now,
            updated_at=now,
            sections=[
                {"section_id": "overview", "title": "Overview", "source": "overview", "required": True, "render_as": "paragraph"},
                {"section_id": "architecture", "title": "Architecture", "source": "architecture", "required": True, "render_as": "paragraph"},
                {"section_id": "modules", "title": "Modules", "source": "modules", "required": True, "render_as": "bullets"},
                {"section_id": "apis", "title": "API Surface", "source": "api_surface", "required": False, "render_as": "table"},
                {"section_id": "workflow", "title": "Workflow", "source": "workflow", "required": False, "render_as": "bullets"},
                {"section_id": "risks", "title": "Risks", "source": "risks", "required": False, "render_as": "bullets"},
            ],
        ),
        "engineering_handoff": PRDTemplate(
            template_id="engineering_handoff",
            name="Engineering Handoff",
            description="Highlights architecture, APIs, risks, and test gaps.",
            version="1.0",
            created_at=now,
            updated_at=now,
            sections=[
                {"section_id": "architecture", "title": "Architecture", "source": "architecture", "required": True, "render_as": "paragraph"},
                {"section_id": "modules", "title": "Critical Modules", "source": "modules", "required": True, "render_as": "bullets", "max_items": 8},
                {"section_id": "apis", "title": "API Review", "source": "api_surface", "required": False, "render_as": "table"},
                {"section_id": "gaps", "title": "Test Gaps", "source": "test_gaps", "required": False, "render_as": "bullets"},
                {"section_id": "warnings", "title": "Warnings", "source": "warnings", "required": False, "render_as": "bullets"},
            ],
        ),
        "onboarding_brief": PRDTemplate(
            template_id="onboarding_brief",
            name="Onboarding Brief",
            description="Short handoff template for new engineers.",
            version="1.0",
            created_at=now,
            updated_at=now,
            sections=[
                {"section_id": "overview", "title": "Project Context", "source": "overview", "required": True, "render_as": "paragraph"},
                {"section_id": "onboarding", "title": "Onboarding Guide", "source": "onboarding", "required": False, "render_as": "bullets"},
                {"section_id": "apis", "title": "API Surface", "source": "api_surface", "required": False, "render_as": "bullets", "max_items": 8},
                {"section_id": "risks", "title": "Risks", "source": "risks", "required": False, "render_as": "bullets"},
            ],
        ),
        "api_review": PRDTemplate(
            template_id="api_review",
            name="API Review",
            description="Focuses on interfaces, workflow, and evidence.",
            version="1.0",
            created_at=now,
            updated_at=now,
            sections=[
                {"section_id": "overview", "title": "Summary", "source": "overview", "required": True, "render_as": "paragraph"},
                {"section_id": "apis", "title": "API Surface", "source": "api_surface", "required": True, "render_as": "table"},
                {"section_id": "workflow", "title": "Workflow", "source": "workflow", "required": False, "render_as": "bullets"},
                {"section_id": "evidence", "title": "Evidence", "source": "evidence", "required": False, "render_as": "bullets"},
            ],
        ),
    }


class PRDTemplateEngine:
    def validate_template(self, template: dict) -> PRDTemplate:
        payload = dict(template or {})
        payload.setdefault("template_id", uuid.uuid4().hex)
        payload.setdefault("name", "Custom Template")
        payload.setdefault("version", "1.0")
        payload.setdefault("created_at", utc_now_iso())
        payload.setdefault("updated_at", utc_now_iso())
        try:
            model = PRDTemplate.model_validate(payload)
        except Exception as exc:
            raise ValueError("Invalid PRD template payload or section source.") from exc
        for section in model.sections:
            if section.source not in _VALID_SOURCES:
                raise ValueError(f"Unsupported section source: {section.source}")
            if section.source == "custom_static" and not str(section.static_text or "").strip():
                raise ValueError("custom_static sections require static_text.")
        return model

    def render_markdown(self, prd_result: PRDResult, template, extra_context=None) -> RenderedTemplateResult:
        model = template if isinstance(template, PRDTemplate) else self.validate_template(template)
        context = extra_context or {}
        warnings = []
        lines = [f"# {model.name}", ""]
        for section in model.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            block, block_warnings = self._render_section(prd_result, section, context)
            warnings.extend(block_warnings)
            lines.extend(block)
            lines.append("")
        return RenderedTemplateResult(
            template_id=model.template_id,
            session_id=prd_result.session_id or "",
            title=model.name,
            markdown="\n".join(lines).strip() + "\n",
            warnings=clean_list(warnings, max_items=12),
        )

    def _render_section(self, prd_result: PRDResult, section, extra_context: dict) -> tuple[list[str], list[str]]:
        source = section.source
        warnings = []
        if source == "custom_static":
            return [self._safe_text(section.static_text)], warnings

        items = self._section_items(prd_result, source, extra_context)
        max_items = section.max_items or len(items)
        items = items[:max_items]
        if not items:
            fallback = "Insufficient evidence from codebase."
            if section.required:
                warnings.append(f"{section.title}: deterministic data was not available; rendered fallback text.")
            return [fallback], warnings

        if section.render_as == "paragraph":
            return [clean_sentence(" ".join(items))], warnings
        if section.render_as == "table":
            if not items:
                return ["Insufficient evidence from codebase."], warnings
            return self._render_table(items), warnings
        return [f"- {self._safe_text(item)}" for item in items], warnings

    def _section_items(self, prd_result: PRDResult, source: str, extra_context: dict) -> list[str]:
        if source == "overview":
            return [getattr(getattr(prd_result, "overview", None), "content", "")]
        if source == "project_brief":
            brief = getattr(prd_result, "project_brief", None)
            return [
                getattr(getattr(brief, "goal", None), "content", ""),
                getattr(getattr(brief, "what", None), "content", ""),
                getattr(getattr(brief, "why", None), "content", ""),
            ]
        if source == "architecture":
            return [getattr(getattr(prd_result, "architecture", None), "content", "")]
        if source == "tech_stack":
            return [getattr(getattr(prd_result, "tech_stack", None), "content", "")]
        if source == "modules":
            rows = []
            for item in getattr(prd_result, "modules", []) or []:
                files = [path for path in getattr(item, "files", []) or [] if path and not is_ignored_path(path)]
                rows.append(f"{getattr(item, 'name', 'unknown')} - {getattr(item, 'description', '')} {files[0] if files else ''}".strip())
            return rows
        if source == "api_surface":
            rows = []
            for item in getattr(prd_result, "api_endpoints", []) or []:
                rows.append(f"{getattr(item, 'method', '')} | {getattr(item, 'path', '')} | {getattr(item, 'description', '')}")
            return rows
        if source == "workflow":
            rows = []
            for item in getattr(prd_result, "workflow", []) or []:
                rows.append(f"{getattr(item, 'order', '')}. {getattr(item, 'source', '')} -> {getattr(item, 'action', '')} -> {getattr(item, 'target', '')}")
            return rows
        if source == "database":
            return [getattr(getattr(prd_result, "databases", None), "content", "")]
        if source == "risks":
            return [f"{getattr(item, 'severity', 'low')}: {getattr(item, 'title', '')} - {getattr(item, 'description', '')}" for item in getattr(prd_result, "risks", []) or []]
        if source == "test_gaps":
            test_gap = extra_context.get("test_gaps")
            return [f"{getattr(item, 'priority', 'low')}: {getattr(item, 'target', '')} - {getattr(item, 'reason', '')}" for item in getattr(test_gap, "gaps", []) or []]
        if source == "onboarding":
            onboarding = extra_context.get("onboarding")
            rows = []
            for item in getattr(onboarding, "reading_order", []) or []:
                rows.append(f"{getattr(item, 'title', '')} - {getattr(item, 'reason', '')}")
            return rows
        if source == "evidence":
            rows = []
            for section_obj in [
                getattr(prd_result, "overview", None),
                getattr(prd_result, "architecture", None),
                getattr(prd_result, "tech_stack", None),
                getattr(prd_result, "databases", None),
            ]:
                for evidence in getattr(section_obj, "evidence", [])[:3] if section_obj is not None else []:
                    file_path = getattr(evidence, "file", None)
                    if file_path and is_ignored_path(file_path):
                        continue
                    rows.append(f"{file_path or getattr(evidence, 'source_id', 'evidence')} - {getattr(evidence, 'reason', '')}")
            return rows
        if source == "warnings":
            return list(getattr(prd_result, "warnings", []) or [])
        return []

    def _render_table(self, items: list[str]) -> list[str]:
        lines = ["| Column 1 | Column 2 | Column 3 |", "|---|---|---|"]
        for item in items:
            parts = [self._safe_text(part.strip()) for part in str(item).split("|")]
            while len(parts) < 3:
                parts.append("")
            lines.append(f"| {parts[0]} | {parts[1]} | {parts[2]} |")
        return lines

    def _safe_text(self, value: str | None) -> str:
        text = str(value or "").replace("\r\n", "\n").strip()
        if not text:
            return "Insufficient evidence from codebase."
        return clean_sentence(text) if "\n" not in text and not text.startswith("{{") else text.replace("{{", "{ {").replace("{%", "{ %")
