from __future__ import annotations

from typing import Protocol

from app.intelligence.llm.gemini_client import GeminiClient


class LLMProvider(Protocol):
    provider_name: str

    def generate(self, prompt: str, schema: dict | None = None) -> dict: ...


class GeminiProvider:
    provider_name = "gemini"

    def __init__(self, client: GeminiClient | None = None) -> None:
        self._client = client or GeminiClient()

    def generate(self, prompt: str, schema: dict | None = None) -> dict:
        text = self._client.generate(prompt)
        return {"ok": bool(text), "text": text or "", "provider": self.provider_name}


class MockProvider:
    provider_name = "mock"

    def __init__(self, responses: list[dict] | None = None, error: Exception | None = None) -> None:
        self._responses = list(responses or [])
        self._error = error

    def generate(self, prompt: str, schema: dict | None = None) -> dict:
        if self._error is not None:
            raise self._error
        if self._responses:
            return dict(self._responses.pop(0))
        return {"ok": True, "text": "", "provider": self.provider_name}


class LocalFallbackProvider:
    provider_name = "local_fallback"

    def generate(self, prompt: str, schema: dict | None = None) -> dict:
        return {"ok": False, "text": "", "provider": self.provider_name, "error": "Local fallback provider is a stub only."}
