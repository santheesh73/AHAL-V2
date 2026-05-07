from __future__ import annotations

from app.config import (
    GEMMA_4_26B_TIMEOUT_WARNING,
    GEMMA_4_26B_UNAVAILABLE_WARNING,
    GEMMA_4_26B_VALIDATION_WARNING,
)
from app.intelligence.output_guard import CanonicalOutputGuard
from app.intelligence.presentation_models import CanonicalProjectIntelligence
from app.llm.errors import LLMError, LLMValidationRejected
from app.llm.gemma_client import GemmaClient
from app.llm.response_validator import ResponseValidator


class PolishOrchestrator:
    def __init__(
        self,
        client: GemmaClient | None = None,
        validator: ResponseValidator | None = None,
    ) -> None:
        self._client = client or GemmaClient()
        self._validator = validator or ResponseValidator()

    def polish_chat_answer(self, canonical: CanonicalProjectIntelligence, question: str, deterministic_answer: str) -> tuple[str, list[str]]:
        must_preserve_why = "why does this project exist" in question.lower()
        must_preserve_what = "what does this project do" in question.lower()
        return self._polish_text(
            canonical,
            deterministic_answer,
            must_preserve_what=must_preserve_what,
            must_preserve_why=must_preserve_why,
        )

    def polish_pdf_section(self, canonical: CanonicalProjectIntelligence, section_name: str, deterministic_text: str) -> tuple[str, list[str]]:
        return self._polish_text(
            canonical,
            deterministic_text,
            must_preserve_what=section_name.lower() == "what",
            must_preserve_why=section_name.lower() == "why",
        )

    def polish_project_summary(self, canonical: CanonicalProjectIntelligence) -> tuple[str, list[str]]:
        return self._polish_text(canonical, canonical.product_summary, must_preserve_what=False, must_preserve_why=False)

    def polish_markdown(self, canonical: CanonicalProjectIntelligence, markdown_text: str) -> tuple[str, list[str]]:
        return self._polish_text(canonical, markdown_text)

    def polish_onboarding(self, canonical: CanonicalProjectIntelligence, deterministic_report: str) -> tuple[str, list[str]]:
        return self._polish_text(canonical, deterministic_report)

    def _polish_text(
        self,
        canonical: CanonicalProjectIntelligence,
        deterministic_text: str,
        *,
        must_preserve_what: bool = False,
        must_preserve_why: bool = False,
    ) -> tuple[str, list[str]]:
        if not self._client.is_available():
            return deterministic_text, [GEMMA_4_26B_UNAVAILABLE_WARNING]
        prompt = self._build_prompt(canonical, deterministic_text)
        try:
            result = self._client.generate_text(prompt, temperature=0.2, max_tokens=2048)
            polished = self._validator.validate_text(
                canonical,
                result.text,
                must_preserve_what=must_preserve_what,
                must_preserve_why=must_preserve_why,
            )
            return CanonicalOutputGuard.sanitize_text(polished, canonical), []
        except LLMValidationRejected:
            return deterministic_text, [GEMMA_4_26B_VALIDATION_WARNING]
        except LLMError as exc:
            if exc.error_type == "TIMEOUT":
                return deterministic_text, [GEMMA_4_26B_TIMEOUT_WARNING]
            return deterministic_text, [getattr(exc, "user_warning", GEMMA_4_26B_UNAVAILABLE_WARNING)]

    def _build_prompt(self, canonical: CanonicalProjectIntelligence, deterministic_text: str) -> str:
        allowed_facts = {
            "product_summary": canonical.product_summary,
            "project_goal": canonical.project_goal,
            "what": canonical.what,
            "why": canonical.why,
            "repo_type": canonical.repo_type,
            "completed": [item.title for item in canonical.completed],
            "remaining": [item.title for item in canonical.remaining],
            "api_surface": [f"{item.method} {item.path}" for item in canonical.api_surface],
            "workflow": [item.description for item in canonical.workflow],
            "warnings": canonical.warnings,
        }
        return (
            "You may improve wording only.\n"
            "You may not introduce new facts.\n"
            "You may not add unsupported domains.\n"
            "You may not invent APIs/files/modules/commands.\n"
            "You must preserve uncertainty.\n"
            "You must preserve canonical What and Why exactly when asked.\n"
            f"Allowed facts: {allowed_facts}\n"
            f"Deterministic draft: {deterministic_text}"
        )
