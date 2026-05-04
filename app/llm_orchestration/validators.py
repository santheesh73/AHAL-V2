from __future__ import annotations

import json
import re

from app.docs.utils.production_text import clean_sentence
from app.storage.serialization import sanitize_for_storage
from app.utils.ignored_paths import is_ignored_path


class OrchestrationValidator:
    FORBIDDEN_CLAIMS = {
        "clinically validated",
        "guaranteed diagnosis",
        "replaces doctors",
        "hipaa compliant",
        "soc2 compliant",
        "secure by design",
        "production-ready",
        "enterprise-ready",
    }
    FORBIDDEN_REPR_TOKENS = {"magicmock", "type='", "evidenceitem(", "architectureresult(", "object at 0x"}
    KNOWN_DATABASES = {"mongodb", "postgresql", "postgres", "mysql", "sqlite", "redis", "oracle"}
    KNOWN_FRAMEWORKS = {"fastapi", "django", "flask", "react", "next.js", "nextjs", "vue", "angular", "express", "spring"}
    LENGTH_LIMIT = 4000

    def validate(self, request, candidate_text: str, critic_output: dict | None = None) -> tuple[bool, list[str]]:
        warnings: list[str] = []
        text = str(candidate_text or "").strip()
        payload = sanitize_for_storage(dict(getattr(request, "deterministic_payload", {}) or {}))
        prompt_context = dict(getattr(request, "prompt_context", {}) or {})
        snapshot = json.dumps(payload, sort_keys=True).lower()
        lowered = text.lower()

        if not text:
            return False, ["LLM output was empty."]
        if len(text) > self.LENGTH_LIMIT:
            return False, ["LLM output exceeded the safe length limit."]
        if any(token in lowered for token in self.FORBIDDEN_REPR_TOKENS):
            return False, ["LLM output contained raw repr or mock leakage."]
        if any(claim in lowered for claim in self.FORBIDDEN_CLAIMS):
            return False, ["LLM output contained forbidden medical, security, or readiness claims."]
        if any(token in lowered for token in ("node_modules", ".venv", "site-packages", "__pycache__")):
            return False, ["LLM output referenced ignored paths."]

        mentioned_paths = set(re.findall(r"/[a-zA-Z0-9_./-]+", text))
        allowed_paths = self._allowed_paths(payload)
        if mentioned_paths and not mentioned_paths.issubset(allowed_paths):
            return False, ["LLM output invented API paths or file paths not present in deterministic evidence."]

        if self._invented_database(lowered, snapshot):
            return False, ["LLM output introduced an unsupported database claim."]
        if self._invented_framework(lowered, snapshot):
            return False, ["LLM output introduced an unsupported framework claim."]

        evidence_ids = self._evidence_ids(payload)
        require_citations = bool(getattr(request, "require_citations", True))
        if require_citations and evidence_ids and not re.findall(r"\[E\d+\]", text):
            return False, ["LLM output dropped required citations."]

        if prompt_context.get("must_keep_warnings_in_text", True):
            if not self._contains_required_items(text, payload.get("warnings", [])):
                return False, ["LLM output dropped deterministic warnings."]

        if prompt_context.get("must_keep_risks_in_text", True):
            if not self._contains_required_items(text, payload.get("risks", [])):
                return False, ["LLM output dropped deterministic risks."]

        if critic_output:
            critic_passed = bool((critic_output.get("structured_output") or {}).get("passed", critic_output.get("passed", True)))
            if not critic_passed:
                return False, ["Critic rejected the draft output."]

        return True, warnings

    def _allowed_paths(self, payload: dict) -> set[str]:
        snapshot = json.dumps(payload, sort_keys=True)
        paths = set(re.findall(r"/[a-zA-Z0-9_./-]+", snapshot))
        for key in ("related_files", "files", "key_entry_points", "important_apis", "affected_apis"):
            for item in payload.get(key, []) or []:
                item_text = str(item or "")
                paths.update(re.findall(r"/[a-zA-Z0-9_./-]+", item_text))
        return paths

    def _evidence_ids(self, payload: dict) -> set[str]:
        ids = set(payload.get("evidence_ids", []) or [])
        for item in payload.get("evidence", []) or []:
            if isinstance(item, dict) and item.get("source_id"):
                ids.add(str(item["source_id"]))
        return ids

    def _invented_database(self, lowered_text: str, snapshot: str) -> bool:
        for candidate in self.KNOWN_DATABASES:
            if candidate in lowered_text and candidate not in snapshot:
                return True
        return False

    def _invented_framework(self, lowered_text: str, snapshot: str) -> bool:
        for candidate in self.KNOWN_FRAMEWORKS:
            if candidate in lowered_text and candidate not in snapshot:
                return True
        return False

    def _contains_required_items(self, text: str, items) -> bool:
        normalized = text.lower()
        required = [str(item or "") for item in items or [] if str(item or "").strip()]
        if not required:
            return True
        for item in required:
            lowered = item.lower()
            tokens = [token for token in re.split(r"[^a-z0-9]+", lowered) if len(token) >= 4 and not is_ignored_path(token)]
            if not tokens:
                continue
            leading_tokens = tokens[:4]
            matched = [token for token in leading_tokens if token in normalized]
            if lowered not in normalized and len(matched) < min(2, len(leading_tokens)):
                return False
        return True
