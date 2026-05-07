"""Gemini-backed answer client for Phase 4 chat.

Compatibility wrapper. New code should use app.llm.polish_orchestrator.
"""

from __future__ import annotations

from app.config import GEMMA_4_26B_UNAVAILABLE_WARNING, config
from app.llm.gemma_client import urllib_request
from app.llm.errors import LLMError
from app.llm.gemma_client import GemmaClient


class GeminiChatClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._client = GemmaClient(
            api_key=api_key,
            model=model or config.scanner.chat_llm_model,
            timeout=timeout,
            enabled=config.scanner.chat_llm_enabled if enabled is None else enabled,
        )

    @property
    def enabled(self) -> bool:
        return self._client.enabled

    @property
    def model_name(self) -> str:
        return self._client.model

    def generate(self, prompt: str) -> dict:
        if self._client.enabled and not self._client.api_key:
            return {"ok": False, "text": "", "error": "Gemini API key missing"}
        try:
            result = self._client.generate_text(prompt, temperature=0.1, max_tokens=2048)
            return {"ok": True, "text": result.text, "error": None}
        except LLMError as exc:
            error_type = getattr(exc, "error_type", None)
            if error_type in {"MODEL_OR_ENDPOINT_NOT_FOUND", "RATE_LIMITED", "TIMEOUT"}:
                error = getattr(exc, "user_warning", GEMMA_4_26B_UNAVAILABLE_WARNING)
            else:
                error = f"Gemini API call failed: {type(exc).__name__}"
            return {"ok": False, "text": "", "error": error, "status": error_type}
