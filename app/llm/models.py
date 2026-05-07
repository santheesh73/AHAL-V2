from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResult:
    text: str = ""
    raw_text: str = ""
    payload: dict[str, Any] | None = None
    model: str = ""
    provider: str = "gemini"
    warnings: list[str] = field(default_factory=list)
    latency_ms: int = 0
    prompt_tokens_estimate: int = 0
    output_tokens_estimate: int = 0
    fallback_used: bool = False
    error_type: str | None = None


@dataclass
class TelemetrySnapshot:
    provider: str
    model: str
    llm_enabled: bool
    chat_llm_enabled: bool
    docs_llm_enabled: bool
    key_present: bool
    last_error_type: str | None
    fallback_count: int
    rate_limited_until: float | None
    not_found_count: int
    rate_limit_count: int
    timeout_count: int
