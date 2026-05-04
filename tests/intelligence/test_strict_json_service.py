from __future__ import annotations

import json

from app.context.smart_context_selector import SelectedContext
from app.intelligence.llm.strict_json_service import StrictJSONService


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return self._responses[min(self.calls - 1, len(self._responses) - 1)]


def _summary():
    return {
        "api_paths": ["/health"],
        "frameworks": ["fastapi"],
        "databases": ["postgres"],
        "warnings": ["Missing deployment notes"],
        "risks": ["Authentication is incomplete"],
    }


def _payload():
    return {
        "type": "folder",
        "project_goal": "Provide a backend API.",
        "what": "This is a backend API service.",
        "why": "It centralizes application logic.",
        "built": ["HTTP API routes"],
        "remaining": ["Deployment notes"],
        "issues": ["Authentication is incomplete"],
        "next_steps": ["Add deployment documentation"],
        "confidence": "medium",
    }


def test_valid_json_accepted(monkeypatch):
    from app.config import config

    old_enabled = config.scanner.strict_json_llm_enabled
    old_llm = config.scanner.llm_enabled
    old_key = config.scanner.gemini_api_key
    object.__setattr__(config.scanner, "strict_json_llm_enabled", True)
    object.__setattr__(config.scanner, "llm_enabled", True)
    object.__setattr__(config.scanner, "gemini_api_key", "x")
    try:
        service = StrictJSONService(client=_FakeClient([json.dumps(_payload())]))
        result = service.generate("folder", _summary(), SelectedContext())
        assert result is not None
        assert result["type"] == "folder"
    finally:
        object.__setattr__(config.scanner, "strict_json_llm_enabled", old_enabled)
        object.__setattr__(config.scanner, "llm_enabled", old_llm)
        object.__setattr__(config.scanner, "gemini_api_key", old_key)


def test_invalid_json_retries_once(monkeypatch):
    from app.config import config

    old_enabled = config.scanner.strict_json_llm_enabled
    old_llm = config.scanner.llm_enabled
    old_key = config.scanner.gemini_api_key
    old_retry = config.scanner.llm_retry_count
    object.__setattr__(config.scanner, "strict_json_llm_enabled", True)
    object.__setattr__(config.scanner, "llm_enabled", True)
    object.__setattr__(config.scanner, "gemini_api_key", "x")
    object.__setattr__(config.scanner, "llm_retry_count", 1)
    try:
        client = _FakeClient(["not json", json.dumps(_payload())])
        service = StrictJSONService(client=client)
        result = service.generate("folder", _summary(), SelectedContext())
        assert result is not None
        assert client.calls == 2
    finally:
        object.__setattr__(config.scanner, "strict_json_llm_enabled", old_enabled)
        object.__setattr__(config.scanner, "llm_enabled", old_llm)
        object.__setattr__(config.scanner, "gemini_api_key", old_key)
        object.__setattr__(config.scanner, "llm_retry_count", old_retry)


def test_invalid_json_fallback(monkeypatch):
    from app.config import config

    old_enabled = config.scanner.strict_json_llm_enabled
    old_llm = config.scanner.llm_enabled
    old_key = config.scanner.gemini_api_key
    object.__setattr__(config.scanner, "strict_json_llm_enabled", True)
    object.__setattr__(config.scanner, "llm_enabled", True)
    object.__setattr__(config.scanner, "gemini_api_key", "x")
    try:
        service = StrictJSONService(client=_FakeClient(["not json", "still bad"]))
        assert service.generate("folder", _summary(), SelectedContext()) is None
    finally:
        object.__setattr__(config.scanner, "strict_json_llm_enabled", old_enabled)
        object.__setattr__(config.scanner, "llm_enabled", old_llm)
        object.__setattr__(config.scanner, "gemini_api_key", old_key)


def test_hallucinated_api_rejected(monkeypatch):
    from app.config import config

    old_enabled = config.scanner.strict_json_llm_enabled
    old_llm = config.scanner.llm_enabled
    old_key = config.scanner.gemini_api_key
    object.__setattr__(config.scanner, "strict_json_llm_enabled", True)
    object.__setattr__(config.scanner, "llm_enabled", True)
    object.__setattr__(config.scanner, "gemini_api_key", "x")
    try:
        payload = _payload()
        payload["what"] = "This backend exposes /admin."
        service = StrictJSONService(client=_FakeClient([json.dumps(payload)]))
        assert service.generate("folder", _summary(), SelectedContext()) is None
    finally:
        object.__setattr__(config.scanner, "strict_json_llm_enabled", old_enabled)
        object.__setattr__(config.scanner, "llm_enabled", old_llm)
        object.__setattr__(config.scanner, "gemini_api_key", old_key)


def test_forbidden_claim_rejected(monkeypatch):
    from app.config import config

    old_enabled = config.scanner.strict_json_llm_enabled
    old_llm = config.scanner.llm_enabled
    old_key = config.scanner.gemini_api_key
    object.__setattr__(config.scanner, "strict_json_llm_enabled", True)
    object.__setattr__(config.scanner, "llm_enabled", True)
    object.__setattr__(config.scanner, "gemini_api_key", "x")
    try:
        payload = _payload()
        payload["what"] = "This service is production-ready."
        service = StrictJSONService(client=_FakeClient([json.dumps(payload)]))
        assert service.generate("folder", _summary(), SelectedContext()) is None
    finally:
        object.__setattr__(config.scanner, "strict_json_llm_enabled", old_enabled)
        object.__setattr__(config.scanner, "llm_enabled", old_llm)
        object.__setattr__(config.scanner, "gemini_api_key", old_key)


def test_disabled_returns_none_or_fallback():
    service = StrictJSONService(client=_FakeClient([json.dumps(_payload())]))
    assert service.generate("folder", _summary(), SelectedContext()) is None


def test_prompt_uses_selected_context_only():
    service = StrictJSONService(client=_FakeClient([json.dumps(_payload())]))
    prompt = service.build_prompt_for_test(
        "folder",
        {"project_goal": "API", "code": "def hidden(): pass"},
        SelectedContext(files=[]),
    )
    assert "def hidden(): pass" not in prompt
    assert '"selected_context": []' in prompt


def test_retry_count_respected(monkeypatch):
    from app.config import config

    old_enabled = config.scanner.strict_json_llm_enabled
    old_llm = config.scanner.llm_enabled
    old_key = config.scanner.gemini_api_key
    old_retry = config.scanner.llm_retry_count
    object.__setattr__(config.scanner, "strict_json_llm_enabled", True)
    object.__setattr__(config.scanner, "llm_enabled", True)
    object.__setattr__(config.scanner, "gemini_api_key", "x")
    object.__setattr__(config.scanner, "llm_retry_count", 2)
    try:
        client = _FakeClient(["bad", "bad", "bad"])
        service = StrictJSONService(client=client)
        assert service.generate("folder", _summary(), SelectedContext()) is None
        assert client.calls == 3
    finally:
        object.__setattr__(config.scanner, "strict_json_llm_enabled", old_enabled)
        object.__setattr__(config.scanner, "llm_enabled", old_llm)
        object.__setattr__(config.scanner, "gemini_api_key", old_key)
        object.__setattr__(config.scanner, "llm_retry_count", old_retry)


def test_logs_do_not_expose_prompt_or_key(caplog):
    from app.config import config

    old_enabled = config.scanner.strict_json_llm_enabled
    old_llm = config.scanner.llm_enabled
    old_key = config.scanner.gemini_api_key
    object.__setattr__(config.scanner, "strict_json_llm_enabled", True)
    object.__setattr__(config.scanner, "llm_enabled", True)
    object.__setattr__(config.scanner, "gemini_api_key", "super-secret-key")
    try:
        class RaisingClient:
            def generate(self, prompt: str) -> str:
                raise RuntimeError("boom")

        service = StrictJSONService(client=RaisingClient())
        assert service.generate("folder", _summary(), SelectedContext()) is None
        joined = " ".join(record.getMessage() for record in caplog.records)
        assert "super-secret-key" not in joined
        assert "selected_context" not in joined
    finally:
        object.__setattr__(config.scanner, "strict_json_llm_enabled", old_enabled)
        object.__setattr__(config.scanner, "llm_enabled", old_llm)
        object.__setattr__(config.scanner, "gemini_api_key", old_key)
