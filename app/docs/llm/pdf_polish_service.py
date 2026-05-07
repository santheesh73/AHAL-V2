import json
import logging
import re
from typing import Optional

from app.config import config
from app.docs.llm.prd_prompt_builder import PRDPromptBuilder
from app.docs.models import PRDResult
from app.docs.utils.production_text import safe_remaining_summary, safe_risk_summary
from app.llm.response_validator import ResponseValidator
logger = logging.getLogger("ahal.docs.pdf_polish")


class PDFPolishService:
    """Compatibility wrapper. New code should use app.llm.polish_orchestrator."""

    REQUIRED_FIELDS = {
        "executive_summary",
        "project_goal",
        "what",
        "why",
        "built_summary",
        "remaining_summary",
        "risk_summary",
        "next_steps",
        "section_intros",
    }
    REQUIRED_SECTION_INTROS = {
        "architecture",
        "tech_stack",
        "core_modules",
        "api_surface",
        "workflow",
        "database_storage",
        "setup_notes",
        "evidence_summary",
        "warnings",
    }
    FORBIDDEN_CLAIMS = [
        "clinically validated",
        "guaranteed diagnosis",
        "replaces doctors",
        "hipaa compliant",
        "soc2 compliant",
        "secure by design",
        "production-ready",
        "enterprise-ready",
        "revenue-ready",
    ]
    IGNORED_TOKENS = [
        "node_modules",
        ".venv",
        "site-packages",
        "__pycache__",
        "pip/_vendor",
        "magicmock",
        "type='",
        "confidence='",
        "reasoning=[",
        "evidence=[",
        "evidenceitem(",
        "architectureresult(",
    ]
    TECH_CANDIDATES = [
        "fastapi",
        "django",
        "flask",
        "react",
        "next.js",
        "vue",
        "angular",
        "mongodb",
        "postgresql",
        "postgres",
        "mysql",
        "sqlite",
        "redis",
        "supabase",
        "oracle",
    ]
    LENGTH_LIMITS = {
        "executive_summary": 900,
        "project_goal": 300,
        "what": 400,
        "why": 500,
        "built_summary": 600,
        "remaining_summary": 600,
        "risk_summary": 600,
    }

    def __init__(self):
        self.prompt_builder = PRDPromptBuilder()
        self.response_validator = ResponseValidator()

    def polish_for_pdf(self, prd_result: PRDResult) -> Optional[dict]:
        if not config.scanner.llm_enabled or not config.scanner.docs_llm_enabled or not config.scanner.pdf_llm_enabled:
            return None
        if not config.scanner.gemini_api_key:
            return None

        payload = self._build_payload(prd_result)
        prompt = self.prompt_builder.build_pdf_polish_prompt(payload)

        from app.intelligence.llm.gemini_client import GeminiClient

        client = GeminiClient()
        try:
            response_text = client.generate(prompt)
        except Exception:
            logger.info("%s", getattr(client, "last_error", "") or "PDF LLM polish unavailable; using deterministic PDF.")
            return None

        if not response_text:
            logger.info("%s", getattr(client, "last_error", "") or "PDF LLM polish unavailable; using deterministic PDF.")
            return None

        validated = self._validate_polished(prd_result, response_text)
        if validated is None:
            logger.info("PDF LLM polish rejected; using deterministic PDF.")
        return validated

    def _build_payload(self, prd_result: PRDResult) -> dict:
        pb = getattr(prd_result, "project_brief", None)
        executive_summary = self._clean_text(getattr(getattr(prd_result, "overview", None), "content", ""))
        project_goal = self._clean_text(getattr(getattr(pb, "goal", None), "content", ""))
        what = self._clean_text(getattr(getattr(pb, "what", None), "content", executive_summary))
        why = self._clean_text(getattr(getattr(pb, "why", None), "content", ""))
        built_summary = self._clean_text(self._status_summary(getattr(pb, "completed", []), "Built components include"))
        remaining_summary = self._clean_text(self._status_summary(getattr(pb, "remaining", []), "Remaining work includes"))
        risk_summary = self._clean_text(self._risk_summary(prd_result))
        next_steps = [self._clean_text(step) for step in (getattr(pb, "next_steps", []) or []) if self._clean_text(step)]

        deterministic_json = {
            "title": self._clean_text(getattr(prd_result, "title", "")),
            "project_type": self._clean_text(getattr(prd_result, "project_type", "")),
            "overview": executive_summary,
            "project_goal": project_goal,
            "what": what,
            "why": why,
            "architecture": self._clean_text(getattr(getattr(prd_result, "architecture", None), "content", "")),
            "tech_stack": self._clean_text(getattr(getattr(prd_result, "tech_stack", None), "content", "")),
            "database_storage": self._clean_text(getattr(getattr(prd_result, "databases", None), "content", "")),
            "setup_notes": self._clean_text(getattr(getattr(prd_result, "setup_notes", None), "content", "")),
            "api_endpoints": [
                {
                    "method": self._clean_text(getattr(api, "method", "")),
                    "path": self._clean_text(getattr(api, "path", "")),
                    "framework": self._clean_text(getattr(api, "framework", "")),
                }
                for api in (getattr(prd_result, "api_endpoints", []) or [])
            ],
            "modules": [
                {
                    "name": self._clean_text(getattr(mod, "name", "")),
                    "category": self._clean_text(getattr(mod, "category", "")),
                    "description": self._clean_text(getattr(mod, "description", "")),
                }
                for mod in (getattr(prd_result, "modules", []) or [])
            ],
            "workflow": [
                {
                    "order": getattr(step, "order", 0),
                    "source": self._clean_text(getattr(step, "source", "")),
                    "action": self._clean_text(getattr(step, "action", "")),
                    "target": self._clean_text(getattr(step, "target", "")),
                }
                for step in (getattr(prd_result, "workflow", []) or [])
            ],
            "risks": [
                {
                    "title": self._clean_text(getattr(risk, "title", "")),
                    "severity": self._clean_text(getattr(risk, "severity", "")),
                    "description": self._clean_text(getattr(risk, "description", "")),
                    "recommendation": self._clean_text(getattr(risk, "recommendation", "")),
                }
                for risk in (getattr(prd_result, "risks", []) or [])
            ],
            "warnings": [self._clean_text(w) for w in (getattr(prd_result, "warnings", []) or []) if self._clean_text(w)],
        }

        return {
            "instructions": {
                "required_fields": sorted(self.REQUIRED_FIELDS),
                "required_section_intros": sorted(self.REQUIRED_SECTION_INTROS),
            },
            "deterministic_prd_json": deterministic_json,
            "narrative_seed": {
                "executive_summary": executive_summary,
                "project_goal": project_goal,
                "what": what,
                "why": why,
                "built_summary": built_summary,
                "remaining_summary": remaining_summary,
                "risk_summary": risk_summary,
                "next_steps": next_steps[:6],
                "section_intros": {
                    "architecture": "The following architecture section is rendered from deterministic analysis.",
                    "tech_stack": "The detected technologies below come directly from deterministic evidence.",
                    "core_modules": "The module list below reflects deterministic structure extracted from the repository.",
                    "api_surface": "The API endpoints below are preserved exactly from deterministic detection.",
                    "workflow": "The workflow below is preserved exactly from deterministic evidence.",
                    "database_storage": "The database and storage notes below come from deterministic evidence.",
                    "setup_notes": "The setup notes below come from deterministic evidence.",
                    "evidence_summary": "The evidence summary below is preserved directly from deterministic PRD evidence.",
                    "warnings": "Warnings below are preserved directly from the deterministic PRD output.",
                },
            },
        }

    def _validate_polished(self, prd_result: PRDResult, response_text: str) -> Optional[dict]:
        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, dict) or set(parsed.keys()) != self.REQUIRED_FIELDS:
            return None

        for field in self.REQUIRED_FIELDS - {"next_steps", "section_intros"}:
            value = parsed.get(field)
            if not isinstance(value, str):
                return None
            cleaned = self._clean_text(value)
            if not cleaned or len(cleaned) > self.LENGTH_LIMITS[field]:
                return None
            parsed[field] = cleaned

        next_steps = parsed.get("next_steps")
        if not isinstance(next_steps, list) or len(next_steps) > 6:
            return None
        cleaned_steps = []
        for step in next_steps:
            if not isinstance(step, str):
                return None
            cleaned = self._clean_text(step)
            if not cleaned or len(cleaned) > 180:
                return None
            cleaned_steps.append(cleaned)
        parsed["next_steps"] = cleaned_steps

        section_intros = parsed.get("section_intros")
        if not isinstance(section_intros, dict):
            return None
        if not self.REQUIRED_SECTION_INTROS.issubset(set(section_intros.keys())):
            return None
        cleaned_intros = {}
        for key, value in section_intros.items():
            if not isinstance(key, str) or not isinstance(value, str):
                return None
            cleaned = self._clean_text(value)
            if not cleaned or len(cleaned) > 300:
                return None
            cleaned_intros[str(key)] = cleaned
        parsed["section_intros"] = cleaned_intros

        combined = " ".join(
            [parsed[field] for field in self.REQUIRED_FIELDS - {"next_steps", "section_intros"}]
            + parsed["next_steps"]
            + list(parsed["section_intros"].values())
        ).lower()

        if any(token in combined for token in self.IGNORED_TOKENS):
            return None
        if any(token in combined for token in self.FORBIDDEN_CLAIMS):
            return None
        if self._contains_secret_like_value(combined):
            return None

        allowed_paths = {
            self._clean_text(getattr(api, "path", "")).lower()
            for api in (getattr(prd_result, "api_endpoints", []) or [])
            if self._clean_text(getattr(api, "path", ""))
        }
        mentioned_paths = set(re.findall(r"/[a-zA-Z0-9_./-]+", combined))
        if not mentioned_paths.issubset(allowed_paths):
            return None

        snapshot = self._deterministic_snapshot(prd_result)
        for tech in self.TECH_CANDIDATES:
            if tech in combined and tech not in snapshot:
                return None

        if not self._warnings_preserved(prd_result, parsed["section_intros"].get("warnings", "")):
            return None
        if not self._risks_preserved(prd_result, parsed["risk_summary"]):
            return None

        if self._is_healthcare_prd(prd_result):
            health_text = f"{parsed['executive_summary']} {parsed['what']} {parsed['why']} {parsed['risk_summary']}".lower()
            if "ai-assisted" not in health_text:
                return None
            if "diagnos" not in health_text and "medical query workflows" not in health_text and "knowledge retrieval" not in health_text:
                return None

        canonical = getattr(prd_result, "canonical_intelligence", None)
        if canonical is not None:
            try:
                parsed["executive_summary"] = self.response_validator.validate_text(canonical, parsed["executive_summary"])
                parsed["project_goal"] = self.response_validator.validate_text(canonical, parsed["project_goal"])
                parsed["what"] = self.response_validator.validate_text(canonical, parsed["what"], must_preserve_what=True)
                parsed["why"] = self.response_validator.validate_text(canonical, parsed["why"], must_preserve_why=True)
                parsed["built_summary"] = self.response_validator.validate_text(canonical, parsed["built_summary"])
                parsed["remaining_summary"] = self.response_validator.validate_text(canonical, parsed["remaining_summary"])
                parsed["risk_summary"] = self.response_validator.validate_text(canonical, parsed["risk_summary"])
            except Exception:
                return None

        return parsed

    def _status_summary(self, items, prefix: str) -> str:
        rows = []
        for item in items or []:
            title = self._clean_text(getattr(item, "title", ""))
            desc = self._clean_text(getattr(item, "description", ""))
            if title and desc:
                rows.append(f"{title}: {desc}")
            elif title:
                rows.append(title)
        if not rows:
            return "Insufficient evidence from codebase."
        return f"{prefix}: " + "; ".join(rows[:6]) + "."

    def _risk_summary(self, prd_result: PRDResult) -> str:
        pb = getattr(prd_result, "project_brief", None)
        risks = getattr(pb, "issues", None) if pb and getattr(pb, "issues", None) else getattr(prd_result, "risks", [])
        summary = safe_risk_summary(risks or [])
        if summary == "No critical issues detected." and risks:
            return self._status_summary(risks, "Detected issues include")
        return summary

    def _warnings_preserved(self, prd_result: PRDResult, warnings_text: str) -> bool:
        warnings = [self._clean_text(w).lower() for w in (getattr(prd_result, "warnings", []) or []) if self._clean_text(w)]
        if not warnings:
            return True
        lowered = warnings_text.lower()
        for warning in warnings:
            tokens = [token for token in re.split(r"[^a-z0-9]+", warning) if len(token) >= 4 and token != "redacted"]
            if tokens and not any(token in lowered for token in tokens[:3]):
                return False
        return True

    def _risks_preserved(self, prd_result: PRDResult, risk_summary: str) -> bool:
        pb = getattr(prd_result, "project_brief", None)
        risks = getattr(pb, "issues", None) if pb and getattr(pb, "issues", None) else getattr(prd_result, "risks", [])
        if not risks:
            return True
        lowered = risk_summary.lower()
        for risk in risks:
            title = self._clean_text(getattr(risk, "title", "")).lower()
            tokens = [token for token in re.split(r"[^a-z0-9]+", title) if len(token) >= 4]
            if tokens and not any(token in lowered for token in tokens[:3]):
                return False
        return True

    def _deterministic_snapshot(self, prd_result: PRDResult) -> str:
        try:
            snapshot = prd_result.model_dump_json().lower()
        except AttributeError:
            snapshot = prd_result.json().lower()
        return snapshot

    def _is_healthcare_prd(self, prd_result: PRDResult) -> bool:
        snapshot = self._deterministic_snapshot(prd_result)
        return any(token in snapshot for token in ["medical", "healthcare", "diagnos", "clinical", "patient"])

    def _contains_secret_like_value(self, text: str) -> bool:
        return bool(re.search(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*\S+", text))

    def _clean_text(self, text) -> str:
        value = str(text or "")
        value = re.sub(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*\S+", r"\1=[REDACTED]", value)
        value = re.sub(r"(?i)(mongodb|postgres|mysql|redis)(\+srv)?://[^\s]+", r"\1://[REDACTED]", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value
