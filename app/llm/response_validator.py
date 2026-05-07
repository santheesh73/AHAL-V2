from __future__ import annotations

import re

from app.intelligence.output_guard import CanonicalOutputGuard
from app.intelligence.presentation_models import CanonicalProjectIntelligence
from app.llm.errors import LLMValidationRejected


class ResponseValidator:
    _SECRET_RE = re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*\S+")
    _PATH_RE = re.compile(r"[A-Za-z]:\\|/Users/|/home/")
    _HTML_RE = re.compile(r"<[^>]+>")
    _FORBIDDEN_RAW_RE = re.compile(r"(?i)\.env(?:\.example)?|mongodb://|<img|<p|src=|alt=|logo-chatgpt-transparent")
    _FINANCE_RE = re.compile(r"(?i)financial research|finance workflows|investment|market|stock|portfolio|trading")

    def validate_text(
        self,
        canonical: CanonicalProjectIntelligence,
        text: str,
        *,
        must_preserve_what: bool = False,
        must_preserve_why: bool = False,
        max_length: int = 12000,
    ) -> str:
        raw = str(text or "")
        if self._HTML_RE.search(raw):
            raise LLMValidationRejected("Polished output contains raw HTML.")
        if self._FORBIDDEN_RAW_RE.search(raw):
            raise LLMValidationRejected("Polished output contains forbidden raw content.")
        if self._SECRET_RE.search(raw):
            raise LLMValidationRejected("Polished output contains secret-like content.")
        if self._PATH_RE.search(raw):
            raise LLMValidationRejected("Polished output contains raw long paths.")
        if self._FINANCE_RE.search(raw):
            supported = " ".join([canonical.product_domain, canonical.product_summary, canonical.what, canonical.why]).lower()
            if not any(token in supported for token in ("finance", "financial", "investment", "market", "stock", "portfolio", "trading")):
                raise LLMValidationRejected("Polished output introduced an unsupported finance claim.")
        cleaned = CanonicalOutputGuard.sanitize_text(text, canonical)
        lowered = cleaned.lower()
        if must_preserve_what and canonical.what and canonical.what not in cleaned:
            raise LLMValidationRejected("Polished output changed canonical.what.")
        if must_preserve_why and canonical.why and canonical.why not in cleaned:
            raise LLMValidationRejected("Polished output changed canonical.why.")
        if len(cleaned) > max_length:
            raise LLMValidationRejected("Polished output exceeded the maximum length.")
        CanonicalOutputGuard.assert_no_forbidden_terms(cleaned, canonical)
        api_paths = {item.path.lower() for item in canonical.api_surface}
        mentioned_paths = {match.lower() for match in re.findall(r"/[a-zA-Z0-9_./{}-]+", cleaned)}
        if api_paths and not mentioned_paths.issubset(api_paths):
            raise LLMValidationRejected("Polished output introduced an unsupported API path.")
        if not api_paths and mentioned_paths:
            raise LLMValidationRejected("Polished output introduced API paths when none were detected.")
        if canonical.why.lower().startswith("the business or user-facing reason is not fully specified") and "exists to" in lowered:
            raise LLMValidationRejected("Polished output removed required uncertainty.")
        return cleaned
