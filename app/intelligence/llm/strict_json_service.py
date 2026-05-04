from __future__ import annotations

import json
import logging
import re
from typing import Optional

from app.config import config
from app.context.smart_context_selector import SelectedContext
from app.utils.ignored_paths import is_ignored_path

logger = logging.getLogger("ahal.intelligence.strict_json")

_FORBIDDEN_SUMMARY_KEYS = {"contents", "source_code", "raw_code", "code", "files"}


class StrictJSONService:
    REQUIRED_KEYS = {
        "type",
        "project_goal",
        "what",
        "why",
        "built",
        "remaining",
        "issues",
        "next_steps",
        "confidence",
    }
    FORBIDDEN_CLAIMS = {
        "clinically validated",
        "guaranteed diagnosis",
        "replaces doctors",
        "hipaa compliant",
        "soc2 compliant",
        "secure by design",
        "production-ready",
        "enterprise-ready",
        "revenue-ready",
    }

    def __init__(self, client=None) -> None:
        self._client = client

    def generate(
        self,
        session_type: str,
        deterministic_summary: dict,
        selected_context: SelectedContext,
    ) -> Optional[dict]:
        if not config.scanner.strict_json_llm_enabled or not config.scanner.llm_enabled:
            return None
        if not config.scanner.gemini_api_key:
            return None

        prompt = self._build_prompt(session_type, deterministic_summary, selected_context)
        attempts = max(1, int(config.scanner.llm_retry_count) + 1)
        client = self._client or self._build_client()

        for _ in range(attempts):
            try:
                response = client.generate(prompt)
            except Exception:
                logger.warning("Strict JSON generation failed; falling back to deterministic output.")
                response = ""
            validated = self._validate_response(response, session_type, deterministic_summary)
            if validated is not None:
                return validated
        return None

    def _build_client(self):
        from app.intelligence.llm.gemini_client import GeminiClient

        return GeminiClient()

    def _build_prompt(self, session_type: str, deterministic_summary: dict, selected_context: SelectedContext) -> str:
        safe_context = [
            {
                "path": item.path,
                "reason": item.reason,
                "evidence_id": item.evidence_id,
                "excerpt": self._redact(item.excerpt),
            }
            for item in selected_context.files
            if not is_ignored_path(item.path)
        ]
        payload = {
            "type": session_type,
            "instructions": [
                "Return strict JSON only.",
                "Use only the provided deterministic summary and selected context excerpts.",
                "Do not invent APIs, frameworks, databases, modules, warnings, risks, deployment, security, or compliance claims.",
                "Do not copy raw source code beyond the provided short excerpts.",
                "Do not include secrets, tokens, API keys, or .env values.",
            ],
            "deterministic_summary": self._sanitize_summary(deterministic_summary),
            "selected_context": safe_context,
        }
        return json.dumps(payload, indent=2)

    def build_prompt_for_test(self, session_type: str, deterministic_summary: dict, selected_context: SelectedContext) -> str:
        return self._build_prompt(session_type, deterministic_summary, selected_context)

    def _validate_response(self, response_text: str, session_type: str, deterministic_summary: dict) -> Optional[dict]:
        try:
            parsed = json.loads(response_text)
        except Exception:
            return None
        if not isinstance(parsed, dict) or set(parsed.keys()) != self.REQUIRED_KEYS:
            return None
        if parsed.get("type") != session_type:
            return None
        if parsed.get("confidence") not in {"high", "medium", "low"}:
            return None
        for key in ("project_goal", "what", "why"):
            if not isinstance(parsed.get(key), str) or not str(parsed.get(key)).strip():
                return None
        for key in ("built", "remaining", "issues", "next_steps"):
            value = parsed.get(key)
            if not isinstance(value, list):
                return None
            parsed[key] = [self._clean_text(item) for item in value if self._clean_text(item)]

        combined = " ".join(
            [self._clean_text(parsed.get("project_goal", "")), self._clean_text(parsed.get("what", "")), self._clean_text(parsed.get("why", ""))]
            + parsed["built"]
            + parsed["remaining"]
            + parsed["issues"]
            + parsed["next_steps"]
        ).lower()

        if any(claim in combined for claim in self.FORBIDDEN_CLAIMS):
            return None
        if any(token in combined for token in ("magicmock", "type='", "confidence='", "__pycache__", "node_modules", ".venv")):
            return None

        allowed_apis = {str(path).lower() for path in deterministic_summary.get("api_paths", [])}
        mentioned_paths = set(re.findall(r"/[a-zA-Z0-9_./-]+", combined))
        if mentioned_paths and not mentioned_paths.issubset(allowed_apis):
            return None

        allowed_frameworks = {str(item).lower() for item in deterministic_summary.get("frameworks", [])}
        allowed_databases = {str(item).lower() for item in deterministic_summary.get("databases", [])}
        tech_candidates = ["fastapi", "django", "flask", "react", "mongodb", "postgres", "mysql", "redis"]
        for candidate in tech_candidates:
            if candidate in combined and candidate not in allowed_frameworks and candidate not in allowed_databases:
                return None

        warnings = [self._clean_text(item).lower() for item in deterministic_summary.get("warnings", []) if self._clean_text(item)]
        risks = [self._clean_text(item).lower() for item in deterministic_summary.get("risks", []) if self._clean_text(item)]
        if warnings and not any(token in combined for token in self._anchor_tokens(warnings)):
            return None
        if risks and not any(token in combined for token in self._anchor_tokens(risks)):
            return None

        return parsed

    def _anchor_tokens(self, rows: list[str]) -> list[str]:
        tokens: list[str] = []
        for row in rows:
            parts = [part for part in re.split(r"[^a-z0-9]+", row) if len(part) >= 4]
            tokens.extend(parts[:2])
        return tokens

    def _clean_text(self, value) -> str:
        text = self._redact(str(value or ""))
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _sanitize_summary(self, summary: dict) -> dict:
        sanitized = {}
        for key, value in (summary or {}).items():
            if str(key).lower() in _FORBIDDEN_SUMMARY_KEYS:
                continue
            if isinstance(value, list):
                sanitized[str(key)] = [self._clean_text(item) for item in value[:20] if self._clean_text(item)]
            elif isinstance(value, dict):
                sanitized[str(key)] = {
                    str(inner_key): self._clean_text(inner_value)
                    for inner_key, inner_value in value.items()
                    if str(inner_key).lower() not in _FORBIDDEN_SUMMARY_KEYS and self._clean_text(inner_value)
                }
            else:
                cleaned = self._clean_text(value)
                if cleaned:
                    sanitized[str(key)] = cleaned
        return sanitized

    def _redact(self, text: str) -> str:
        text = re.sub(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*\S+", r"\1=[REDACTED]", text)
        text = re.sub(r"(?i)(mongodb|postgres|mysql|redis)(\+srv)?://[^\s]+", r"\1://[REDACTED]", text)
        return text
