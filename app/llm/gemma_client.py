from __future__ import annotations

import json
import time
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from app.config import config
from app.llm.errors import (
    LLMInvalidResponse,
    LLMModelNotFound,
    LLMRateLimited,
    LLMTimeout,
    LLMUnavailable,
)
from app.llm.models import LLMResult
from app.llm.telemetry import llm_telemetry

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/{model}:generateContent?key={api_key}"
)


class GemmaClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        self.api_key = config.scanner.gemini_api_key if api_key is None else api_key
        self.model = model or config.scanner.llm_model
        self.timeout = timeout or config.scanner.llm_timeout_seconds
        self.enabled = config.scanner.llm_enabled if enabled is None else enabled

    def is_available(self) -> bool:
        return bool(self.enabled and self.api_key and config.scanner.llm_provider == "gemini")

    def generate_text(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResult:
        if not self.is_available():
            raise LLMUnavailable("Gemma 4 26B is not enabled or configured.")
        payload = {
            "contents": [{"parts": [{"text": self._build_prompt(prompt, system)}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        return self._post_json(payload)

    def generate_json(
        self,
        prompt: str,
        schema,
        system: str | None = None,
        temperature: float = 0.1,
    ) -> LLMResult:
        schema_text = json.dumps(schema, ensure_ascii=True) if not isinstance(schema, str) else schema
        combined = f"{prompt}\n\nReturn JSON matching this schema exactly:\n{schema_text}"
        result = self.generate_text(combined, system=system, temperature=temperature)
        try:
            result.payload = json.loads(result.text)
        except json.JSONDecodeError as exc:
            llm_telemetry.record_failure("INVALID_RESPONSE")
            raise LLMInvalidResponse("Gemma returned invalid JSON.") from exc
        return result

    def classify_error(self, error: Exception) -> str:
        if isinstance(error, LLMModelNotFound):
            return error.error_type
        if isinstance(error, LLMRateLimited):
            return error.error_type
        if isinstance(error, LLMTimeout):
            return error.error_type
        if isinstance(error, LLMInvalidResponse):
            return error.error_type
        if isinstance(error, LLMUnavailable):
            return error.error_type
        return "LLM_ERROR"

    def _build_prompt(self, prompt: str, system: str | None) -> str:
        if system:
            return f"{system.strip()}\n\n{prompt.strip()}"
        return prompt.strip()

    def _post_json(self, payload: dict) -> LLMResult:
        request_url = _GEMINI_URL.format(model=self.model, api_key=self.api_key)
        encoded = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            request_url,
            data=encoded,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        retries = max(0, config.scanner.llm_max_retries)
        attempt = 0
        while True:
            started = time.time()
            try:
                with urllib_request.urlopen(req, timeout=self.timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                text = self._extract_text(body)
                if not text:
                    raise LLMInvalidResponse("Gemma returned an empty response.")
                latency_ms = int((time.time() - started) * 1000)
                llm_telemetry.record_success()
                return LLMResult(
                    text=text,
                    raw_text=text,
                    model=self.model,
                    provider=config.scanner.llm_provider,
                    latency_ms=latency_ms,
                    prompt_tokens_estimate=max(1, len(json.dumps(payload)) // 4),
                    output_tokens_estimate=max(1, len(text) // 4),
                )
            except HTTPError as exc:
                if exc.code == 404:
                    llm_telemetry.record_failure("MODEL_OR_ENDPOINT_NOT_FOUND")
                    raise LLMModelNotFound("Gemma 4 26B model or endpoint was not found.") from exc
                if exc.code == 429:
                    if config.scanner.llm_retry_on_429 and attempt < retries:
                        attempt += 1
                        time.sleep(1)
                        continue
                    llm_telemetry.record_failure("RATE_LIMITED")
                    raise LLMRateLimited("Gemma 4 26B rate limit was reached.") from exc
                llm_telemetry.record_failure("LLM_ERROR")
                raise LLMUnavailable(f"Gemma request failed with HTTP {exc.code}.") from exc
            except TimeoutError as exc:
                llm_telemetry.record_failure("TIMEOUT")
                raise LLMTimeout("Gemma 4 26B timed out.") from exc
            except URLError as exc:
                llm_telemetry.record_failure("LLM_UNAVAILABLE")
                raise LLMUnavailable("Gemma 4 26B is unavailable.") from exc

    def _extract_text(self, body: dict) -> str:
        candidates = body.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return ""
        return str(parts[0].get("text", "") or "").strip()
