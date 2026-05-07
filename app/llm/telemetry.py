from __future__ import annotations

import time
from dataclasses import dataclass

from app.config import config
from app.llm.models import TelemetrySnapshot


@dataclass
class _TelemetryState:
    last_error_type: str | None = None
    fallback_count: int = 0
    rate_limited_until: float | None = None
    not_found_count: int = 0
    rate_limit_count: int = 0
    timeout_count: int = 0


class LLMTelemetry:
    def __init__(self) -> None:
        self._state = _TelemetryState()

    def reset(self) -> None:
        self._state = _TelemetryState()

    def record_success(self) -> None:
        self._state.last_error_type = None

    def record_failure(self, error_type: str, *, used_fallback: bool = True) -> None:
        self._state.last_error_type = error_type
        if used_fallback:
            self._state.fallback_count += 1
        if error_type == "MODEL_OR_ENDPOINT_NOT_FOUND":
            self._state.not_found_count += 1
        elif error_type == "RATE_LIMITED":
            self._state.rate_limit_count += 1
            self._state.rate_limited_until = time.time() + config.scanner.llm_rate_limit_cooldown_seconds
        elif error_type == "TIMEOUT":
            self._state.timeout_count += 1

    def snapshot(self) -> TelemetrySnapshot:
        return TelemetrySnapshot(
            provider=config.scanner.llm_provider,
            model=config.scanner.llm_model,
            llm_enabled=config.scanner.llm_enabled,
            chat_llm_enabled=config.scanner.chat_llm_enabled,
            docs_llm_enabled=config.scanner.docs_llm_enabled,
            key_present=bool(config.scanner.gemini_api_key),
            last_error_type=self._state.last_error_type,
            fallback_count=self._state.fallback_count,
            rate_limited_until=self._state.rate_limited_until,
            not_found_count=self._state.not_found_count,
            rate_limit_count=self._state.rate_limit_count,
            timeout_count=self._state.timeout_count,
        )


llm_telemetry = LLMTelemetry()
