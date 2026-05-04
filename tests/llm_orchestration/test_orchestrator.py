from app.config import config
from app.llm_orchestration import LLMOrchestrator, MockProvider, OrchestrationRequest


def _request():
    return OrchestrationRequest(
        task_type="chat",
        deterministic_payload={
            "text": "AHAL exposes GET /users [E1].",
            "warnings": ["Missing auth coverage on user routes."],
            "risks": ["Database migrations need review."],
            "evidence_ids": ["[E1]"],
            "affected_apis": ["GET /users"],
        },
        prompt_context={
            "fallback_text": "AHAL exposes GET /users [E1].",
            "must_keep_warnings_in_text": True,
            "must_keep_risks_in_text": True,
        },
        require_citations=True,
    )


def test_disabled_returns_fallback():
    old = config.scanner.llm_orchestration_enabled
    object.__setattr__(config.scanner, "llm_orchestration_enabled", False)
    try:
        result = LLMOrchestrator(
            primary_provider=MockProvider(responses=[{"ok": True, "text": "ignored", "provider": "mock"}]),
            critic_provider=MockProvider(responses=[{"ok": True, "structured_output": {"passed": True, "issues": []}, "provider": "mock"}]),
        ).orchestrate(_request())
    finally:
        object.__setattr__(config.scanner, "llm_orchestration_enabled", old)
    assert result.fallback_used is True
    assert result.text == "AHAL exposes GET /users [E1]."
    assert any("disabled" in warning.lower() for warning in result.warnings)


def test_primary_success_and_critic_pass_accepted():
    old = config.scanner.llm_orchestration_enabled
    object.__setattr__(config.scanner, "llm_orchestration_enabled", True)
    try:
        result = LLMOrchestrator(
            primary_provider=MockProvider(
                responses=[{"ok": True, "text": "AHAL exposes GET /users [E1]. Missing auth coverage on user routes. Database migrations need review.", "provider": "mock"}]
            ),
            critic_provider=MockProvider(
                responses=[{"ok": True, "structured_output": {"passed": True, "issues": []}, "provider": "mock"}]
            ),
        ).orchestrate(_request())
    finally:
        object.__setattr__(config.scanner, "llm_orchestration_enabled", old)
    assert result.ok is True
    assert result.fallback_used is False
    assert result.critic_passed is True
    assert result.validation_passed is True


def test_critic_rejects_hallucinated_api():
    old = config.scanner.llm_orchestration_enabled
    object.__setattr__(config.scanner, "llm_orchestration_enabled", True)
    try:
        result = LLMOrchestrator(
            primary_provider=MockProvider(
                responses=[{"ok": True, "text": "AHAL exposes GET /admin [E1]. Missing auth coverage on user routes. Database migrations need review.", "provider": "mock"}]
            ),
            critic_provider=MockProvider(
                responses=[{"ok": True, "structured_output": {"passed": False, "issues": ["Invented API path `/admin`."]}, "provider": "mock"}]
            ),
        ).orchestrate(_request())
    finally:
        object.__setattr__(config.scanner, "llm_orchestration_enabled", old)
    assert result.fallback_used is True
    assert any("critic" in warning.lower() or "invented api" in warning.lower() for warning in result.warnings)


def test_provider_error_falls_back():
    old = config.scanner.llm_orchestration_enabled
    object.__setattr__(config.scanner, "llm_orchestration_enabled", True)
    try:
        result = LLMOrchestrator(
            primary_provider=MockProvider(error=RuntimeError("provider failed")),
            critic_provider=MockProvider(),
        ).orchestrate(_request())
    finally:
        object.__setattr__(config.scanner, "llm_orchestration_enabled", old)
    assert result.fallback_used is True
    assert any("failed" in warning.lower() for warning in result.warnings)


def test_timeout_falls_back():
    old = config.scanner.llm_orchestration_enabled
    object.__setattr__(config.scanner, "llm_orchestration_enabled", True)
    try:
        result = LLMOrchestrator(
            primary_provider=MockProvider(error=TimeoutError("timeout")),
            critic_provider=MockProvider(),
        ).orchestrate(_request())
    finally:
        object.__setattr__(config.scanner, "llm_orchestration_enabled", old)
    assert result.fallback_used is True
    assert any("timed out" in warning.lower() for warning in result.warnings)
