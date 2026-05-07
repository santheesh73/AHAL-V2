from __future__ import annotations

import io
import json
from urllib.error import HTTPError

import pytest

from app.llm.errors import LLMModelNotFound, LLMRateLimited, LLMTimeout
from app.llm.gemma_client import GemmaClient
from app.llm.telemetry import llm_telemetry


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_404_falls_back_deterministically(monkeypatch):
    def raise_404(*args, **kwargs):
        raise HTTPError("http://test", 404, "not found", None, io.BytesIO(b""))

    monkeypatch.setattr("app.llm.gemma_client.urllib_request.urlopen", raise_404)
    llm_telemetry.reset()
    client = GemmaClient(api_key="fake", enabled=True)
    with pytest.raises(LLMModelNotFound):
        client.generate_text("hello")
    assert llm_telemetry.snapshot().last_error_type == "MODEL_OR_ENDPOINT_NOT_FOUND"


def test_429_falls_back_after_one_retry(monkeypatch):
    calls = {"count": 0}

    def raise_429(*args, **kwargs):
        calls["count"] += 1
        raise HTTPError("http://test", 429, "rate", None, io.BytesIO(b""))

    monkeypatch.setattr("app.llm.gemma_client.urllib_request.urlopen", raise_429)
    monkeypatch.setattr("app.llm.gemma_client.time.sleep", lambda seconds: None)
    monkeypatch.setattr("app.llm.gemma_client.config", dataclasses_replace_retry())
    llm_telemetry.reset()
    client = GemmaClient(api_key="fake", enabled=True)
    with pytest.raises(LLMRateLimited):
        client.generate_text("hello")
    assert calls["count"] == 2
    assert llm_telemetry.snapshot().last_error_type == "RATE_LIMITED"


def test_timeout_falls_back(monkeypatch):
    monkeypatch.setattr("app.llm.gemma_client.urllib_request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError()))
    llm_telemetry.reset()
    client = GemmaClient(api_key="fake", enabled=True)
    with pytest.raises(LLMTimeout):
        client.generate_text("hello")
    assert llm_telemetry.snapshot().last_error_type == "TIMEOUT"


def test_generate_json_parses_payload(monkeypatch):
    monkeypatch.setattr(
        "app.llm.gemma_client.urllib_request.urlopen",
        lambda *args, **kwargs: _Response({"candidates": [{"content": {"parts": [{"text": "{\"ok\": true}"}]}}]}),
    )
    client = GemmaClient(api_key="fake", enabled=True)
    result = client.generate_json("hello", {"type": "object"})
    assert result.payload == {"ok": True}


def dataclasses_replace_retry():
    import dataclasses
    import app.config as config_module

    patched_scanner = dataclasses.replace(config_module.config.scanner, llm_max_retries=1, llm_retry_on_429=True)
    return dataclasses.replace(config_module.config, scanner=patched_scanner)
