from app.llm_orchestration.providers import MockProvider


def test_mock_provider_returns_queued_response():
    provider = MockProvider(responses=[{"ok": True, "text": "Draft [E1]", "provider": "mock"}])
    result = provider.generate("prompt")
    assert result["ok"] is True
    assert result["text"] == "Draft [E1]"
    assert result["provider"] == "mock"


def test_mock_provider_can_raise_configured_error():
    provider = MockProvider(error=RuntimeError("boom"))
    try:
        provider.generate("prompt")
    except RuntimeError as exc:
        assert "boom" in str(exc)
    else:
        raise AssertionError("Expected MockProvider to raise configured error.")
