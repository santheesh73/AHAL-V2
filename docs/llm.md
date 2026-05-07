# AHAL LLM Policy

AHAL only allows `gemma-4-26b-a4b-it` through the Gemini API.

The deterministic scanner and canonical presenter remain the source of truth. Gemma may only polish wording inside canonical facts. If the configured provider, key, model, endpoint, rate limit, timeout, or validator rejects a response, AHAL falls back to the deterministic answer instead of breaking chat, dashboard, or document generation.

Key settings:

```env
AHAL_LLM_PROVIDER=gemini
AHAL_LLM_ENABLED=true
AHAL_CHAT_LLM_ENABLED=true
AHAL_DOCS_LLM_ENABLED=true
AHAL_PRD_LLM_ENABLED=true
AHAL_PDF_LLM_ENABLED=true
AHAL_LLM_MODEL=gemma-4-26b-a4b-it
AHAL_CHAT_LLM_MODEL=gemma-4-26b-a4b-it
AHAL_DOCS_LLM_MODEL=gemma-4-26b-a4b-it
AHAL_LLM_REQUIRE_VALIDATION=true
AHAL_CHAT_LLM_REQUIRE_VALIDATION=true
AHAL_LLM_TIMEOUT_SECONDS=180
AHAL_LLM_MAX_RETRIES=1
AHAL_LLM_RETRY_ON_404=false
AHAL_LLM_RETRY_ON_429=true
AHAL_LLM_RATE_LIMIT_COOLDOWN_SECONDS=60
```

Observability:

- Startup logs emit provider, model, chat model, docs flag, chat flag, validation flag, and whether the API key is present.
- `GET /analyze/llm/status` returns the current flags, last error type, fallback count, and rate-limit timing.
