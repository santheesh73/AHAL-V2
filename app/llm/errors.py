from __future__ import annotations


class LLMError(Exception):
    error_type = "LLM_ERROR"
    user_warning = "Gemma 4 26B polish unavailable — deterministic answer shown."


class LLMUnavailable(LLMError):
    error_type = "LLM_UNAVAILABLE"


class LLMModelNotFound(LLMError):
    error_type = "MODEL_OR_ENDPOINT_NOT_FOUND"


class LLMRateLimited(LLMError):
    error_type = "RATE_LIMITED"
    user_warning = "Gemma 4 26B rate limit reached — deterministic answer shown."


class LLMTimeout(LLMError):
    error_type = "TIMEOUT"
    user_warning = "Gemma 4 26B polish timed out — deterministic answer shown."


class LLMInvalidResponse(LLMError):
    error_type = "INVALID_RESPONSE"


class LLMValidationRejected(LLMError):
    error_type = "VALIDATION_REJECTED"
    user_warning = "Gemma 4 26B polish was rejected by validation — deterministic answer shown."
