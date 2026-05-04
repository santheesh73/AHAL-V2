from app.llm_orchestration import OrchestrationRequest, OrchestrationValidator


def _request(**overrides):
    payload = {
        "text": "AHAL exposes `GET /users` [E1].",
        "warnings": ["Missing auth coverage on user routes."],
        "risks": ["Database migrations need review."],
        "evidence_ids": ["[E1]"],
        "affected_apis": ["GET /users"],
        "affected_modules": ["app/api/routes.py"],
    }
    prompt_context = {
        "fallback_text": payload["text"],
        "must_keep_warnings_in_text": True,
        "must_keep_risks_in_text": True,
    }
    kwargs = {
        "task_type": "chat",
        "deterministic_payload": payload,
        "prompt_context": prompt_context,
        "require_citations": True,
    }
    kwargs.update(overrides)
    return OrchestrationRequest(**kwargs)


def test_validator_rejects_unsupported_database():
    validator = OrchestrationValidator()
    ok, warnings = validator.validate(
        _request(),
        "AHAL uses PostgreSQL for user storage [E1]. Missing auth coverage on user routes. Database migrations need review.",
    )
    assert ok is False
    assert "database" in warnings[0].lower()


def test_validator_rejects_forbidden_claim():
    validator = OrchestrationValidator()
    ok, warnings = validator.validate(
        _request(),
        "This platform is HIPAA compliant [E1]. Missing auth coverage on user routes. Database migrations need review.",
    )
    assert ok is False
    assert "forbidden" in warnings[0].lower()


def test_validator_rejects_missing_citations_when_required():
    validator = OrchestrationValidator()
    ok, warnings = validator.validate(
        _request(),
        "AHAL exposes the user endpoint. Missing auth coverage on user routes. Database migrations need review.",
    )
    assert ok is False
    assert "citation" in warnings[0].lower()


def test_validator_rejects_dropped_warnings():
    validator = OrchestrationValidator()
    ok, warnings = validator.validate(
        _request(),
        "AHAL exposes GET /users [E1]. Database migrations need review.",
    )
    assert ok is False
    assert "warnings" in warnings[0].lower()


def test_validator_rejects_raw_repr_leakage():
    validator = OrchestrationValidator()
    ok, warnings = validator.validate(
        _request(),
        "EvidenceItem(path='app/api/routes.py') [E1]",
    )
    assert ok is False
    assert "repr" in warnings[0].lower() or "mock" in warnings[0].lower()
