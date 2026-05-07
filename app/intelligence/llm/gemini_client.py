"""Backward-compatible Gemini client wrapper.

Compatibility wrapper. New code should use app.llm.polish_orchestrator.
Use app.llm.gemma_client.GemmaClient for new code.
"""

from __future__ import annotations

from app.config import config
from app.llm.errors import LLMError
from app.llm.gemma_client import GemmaClient as _GemmaClient
from app.llm.gemma_client import urllib_request


class GeminiClient:
    def __init__(self, api_key=None, model=None, timeout=None) -> None:
        self._client = _GemmaClient(api_key=api_key, model=model, timeout=timeout)
        self._last_error = ""

    def generate(self, prompt: str, model=None, timeout=None) -> str:
        try:
            result = _GemmaClient(
                api_key=self._client.api_key,
                model=model or self._client.model,
                timeout=timeout or self._client.timeout,
                enabled=self._client.enabled,
            ).generate_text(prompt)
            self._last_error = ""
            return result.text
        except LLMError as exc:
            self._last_error = getattr(exc, "user_warning", str(exc))
            return ""

    @property
    def model_name(self) -> str:
        return self._client.model

    @property
    def enabled(self) -> bool:
        return self._client.is_available()

    @property
    def last_error(self) -> str:
        return self._last_error
