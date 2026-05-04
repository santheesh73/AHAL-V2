"""
AHAL AI — Explanation Service (Phase 2)

Orchestrates prompt building and Gemini API client to produce LLMExplanation.
Safe — returns used=False on any failure, never crashes.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.config import config
from app.intelligence.llm.gemini_client import GeminiClient
from app.intelligence.llm.prompt_builder import build_prompt
from app.intelligence.models import IntelligenceResult, LLMExplanation

logger = logging.getLogger("ahal.llm.explanation")


class ExplanationService:
    """Produce an LLMExplanation from an IntelligenceResult via Gemini API."""

    def __init__(self, client: Optional[GeminiClient] = None) -> None:
        self._client = client or GeminiClient()

    def explain(self, result: IntelligenceResult) -> Optional[LLMExplanation]:
        """
        Generate an LLM explanation of the intelligence results.

        Only calls Gemini API when:
            - AHAL_LLM_ENABLED=true
            - GEMINI_API_KEY is set

        Returns LLMExplanation with used=True on success.
        Returns LLMExplanation with used=False and error on failure.
        Returns LLMExplanation with used=False if LLM is disabled.
        """
        if not config.scanner.llm_enabled:
            return LLMExplanation(
                model=self._client.model_name,
                content="",
                used=False,
                error="LLM is disabled (AHAL_LLM_ENABLED=false)",
            )

        if not config.scanner.gemini_api_key:
            return LLMExplanation(
                model=self._client.model_name,
                content="",
                used=False,
                error="GEMINI_API_KEY is not set",
            )

        try:
            prompt = build_prompt(result)
            response = self._client.generate(prompt)

            return LLMExplanation(
                model=self._client.model_name,
                content=response,
                used=True,
                error=None,
            )
        except Exception as e:
            logger.error("LLM explanation failed: %s", e)
            return LLMExplanation(
                model=self._client.model_name,
                content="",
                used=False,
                error=str(e),
            )
