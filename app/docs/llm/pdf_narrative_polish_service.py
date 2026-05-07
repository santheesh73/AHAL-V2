import json
import logging
import re

from app.config import config
from app.docs.models import PRDResult

logger = logging.getLogger("ahal.docs.pdf_polish")


class PDFNarrativePolishService:
    SECTION_KEYS = [
        "overview",
        "project_goal",
        "what_this_project_is",
        "why_this_project_exists",
        "architecture",
        "tech_stack",
        "database_storage",
        "setup_notes",
    ]

    def polish(self, prd_result: PRDResult) -> tuple[dict[str, str], list[str]]:
        warnings = []
        if not config.scanner.llm_enabled:
            warnings.append("LLM disabled; returned deterministic PDF narrative.")
            return {}, warnings

        if not config.scanner.gemini_api_key:
            warnings.append("LLM unavailable: Gemini API key missing; returned deterministic PDF narrative.")
            return {}, warnings

        sections = self._extract_sections(prd_result)
        prompt = self._build_prompt(prd_result, sections)

        from app.intelligence.llm.gemini_client import GeminiClient

        client = GeminiClient()
        try:
            response_text = client.generate(prompt)
        except Exception as exc:
            logger.error("PDF narrative polish failed: %s", exc)
            warnings.append(getattr(client, "last_error", "") or "LLM unavailable: Gemini API call failed; returned deterministic PDF narrative.")
            return {}, warnings

        if not response_text:
            warnings.append(getattr(client, "last_error", "") or "LLM unavailable: Gemini API call failed; returned deterministic PDF narrative.")
            return {}, warnings

        overrides, validation_warnings = self._validate_response(prd_result, sections, response_text)
        if not overrides:
            warnings.append("LLM polished PDF narrative failed validation; returned deterministic PDF narrative.")
            warnings.extend(validation_warnings)
            return {}, warnings

        return overrides, []

    def _extract_sections(self, prd_result: PRDResult) -> dict[str, str]:
        pb = getattr(prd_result, "project_brief", None)
        sections = {
            "overview": self._section_text(getattr(prd_result, "overview", None)),
            "project_goal": self._section_text(getattr(pb, "goal", None)) if pb else "",
            "what_this_project_is": self._section_text(getattr(pb, "what", None)) if pb else "",
            "why_this_project_exists": self._section_text(getattr(pb, "why", None)) if pb else "",
            "architecture": self._section_text(getattr(prd_result, "architecture", None)),
            "tech_stack": self._section_text(getattr(prd_result, "tech_stack", None)),
            "database_storage": self._section_text(getattr(prd_result, "databases", None)),
            "setup_notes": self._section_text(getattr(prd_result, "setup_notes", None)),
        }
        return {key: value for key, value in sections.items() if value}

    def _section_text(self, section) -> str:
        if not section:
            return ""
        content = getattr(section, "content", "") or ""
        return self._sanitize_prompt_text(str(content))

    def _sanitize_prompt_text(self, text: str) -> str:
        text = re.sub(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*\S+", r"\1=[REDACTED]", text)
        text = re.sub(r"(?i)(mongodb|postgres|mysql|redis)(\+srv)?://[^\s]+", r"\1://[REDACTED]", text)
        return text.strip()

    def _build_prompt(self, prd_result: PRDResult, sections: dict[str, str]) -> str:
        payload = json.dumps(sections, indent=2)
        known_paths = sorted({
            f"{getattr(api, 'method', '')} {getattr(api, 'path', '')}".strip()
            for api in getattr(prd_result, "api_endpoints", []) or []
            if getattr(api, "path", None)
        })
        return f"""You are polishing PDF narrative paragraphs for a code-analysis PRD.

Rules:
1. Rewrite only for clarity and readability.
2. Do not invent APIs, modules, databases, frameworks, risks, evidence, workflows, or claims.
3. Do not add markdown headings, bullet lists, or code blocks.
4. Do not include secrets, tokens, passwords, or raw source code.
5. Preserve uncertainty and insufficient-evidence wording when present.
6. Keep medical wording safe: allowed phrases include AI-assisted, diagnosis workflows, medical query workflows, knowledge retrieval.
7. Forbidden claims include guarantees, clinically validated, certified, replaces doctors, enterprise-grade security, funding, revenue, compliance.
8. Return JSON only with the exact same keys you were given. Each value must be a short paragraph.

Known API signatures:
{json.dumps(known_paths, indent=2)}

Narrative sections:
{payload}
"""

    def _validate_response(
        self,
        prd_result: PRDResult,
        original_sections: dict[str, str],
        response_text: str,
    ) -> tuple[dict[str, str], list[str]]:
        warnings = []
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            return {}, ["LLM response was not valid JSON."]

        if not isinstance(parsed, dict):
            return {}, ["LLM response was not a JSON object."]

        if set(parsed.keys()) != set(original_sections.keys()):
            return {}, ["LLM response changed the narrative section keys."]

        ignored = ["node_modules", ".venv", "site-packages", "__pycache__", "pip/_vendor", "type='", "confidence='", "reasoning=[", "evidence=[", "EvidenceItem(", "ArchitectureResult("]
        forbidden = [
            "guarantees", "clinically validated", "certified", "replaces doctors",
            "enterprise-grade security", "funding", "revenue", "compliance", "regulatory",
        ]
        known_paths = {
            getattr(api, "path", "")
            for api in getattr(prd_result, "api_endpoints", []) or []
            if getattr(api, "path", None)
        }

        cleaned = {}
        for key, value in parsed.items():
            if not isinstance(value, str):
                return {}, [f"Narrative section '{key}' was not text."]

            text = value.strip()
            if not text:
                return {}, [f"Narrative section '{key}' was empty."]

            lower_text = text.lower()
            for token in ignored:
                if token.lower() in lower_text:
                    return {}, [f"Narrative section '{key}' contained disallowed content."]
            for token in forbidden:
                if token in lower_text:
                    return {}, [f"Narrative section '{key}' introduced an unsupported claim."]
            if re.search(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*\S+", text):
                return {}, [f"Narrative section '{key}' exposed secret-like material."]

            found_paths = set(re.findall(r"/[a-zA-Z0-9_./-]+", text))
            if not found_paths.issubset(known_paths):
                return {}, [f"Narrative section '{key}' introduced unknown API paths."]

            cleaned[key] = text

        return cleaned, warnings
