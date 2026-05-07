from __future__ import annotations

import dataclasses
from urllib.error import HTTPError

from app.config import AppConfig, GEMMA_4_26B_A4B_MODEL
from app.llm.telemetry import llm_telemetry


def test_chat_llm_defaults_to_global_enabled(monkeypatch):
    monkeypatch.setenv("AHAL_LLM_ENABLED", "true")
    monkeypatch.delenv("AHAL_CHAT_LLM_ENABLED", raising=False)
    cfg = AppConfig()
    assert cfg.scanner.llm_enabled is True
    assert cfg.scanner.chat_llm_enabled is True


def test_chat_llm_can_be_explicitly_disabled(monkeypatch, fresh_client):
    monkeypatch.setenv("AHAL_LLM_ENABLED", "true")
    monkeypatch.setenv("AHAL_CHAT_LLM_ENABLED", "false")
    cfg = AppConfig()
    assert cfg.scanner.chat_llm_enabled is False
    assert "Global LLM is enabled but chat LLM is disabled. Chat will use deterministic fallback." in cfg.scanner.llm_health_warnings()

    import app.api.analyze as analyze_module

    monkeypatch.setattr(analyze_module, "config", cfg)
    llm_telemetry.reset()
    response = fresh_client.get("/analyze/llm/status")
    assert response.status_code == 200
    data = response.json()
    assert data["llm_enabled"] is True
    assert data["chat_llm_enabled"] is False
    assert any("chat LLM is disabled" in warning for warning in data["warnings"])


def test_only_gemma_4_26b_allowed(monkeypatch):
    monkeypatch.setenv("AHAL_LLM_MODEL", GEMMA_4_26B_A4B_MODEL)
    cfg = AppConfig()
    assert cfg.scanner.llm_model == GEMMA_4_26B_A4B_MODEL

    monkeypatch.setenv("AHAL_LLM_MODEL", "gemma-26b-it")
    cfg = AppConfig()
    assert cfg.scanner.llm_model == GEMMA_4_26B_A4B_MODEL
    assert any("deprecated/invalid" in warning for warning in cfg.scanner.llm_model_warnings)

    monkeypatch.setenv("AHAL_LLM_MODEL", "gemini-1.5-flash")
    cfg = AppConfig()
    assert cfg.scanner.llm_model == GEMMA_4_26B_A4B_MODEL
    assert any("not allowed" in warning for warning in cfg.scanner.llm_model_warnings)

    monkeypatch.setenv("AHAL_LLM_MODEL", "ollama")
    cfg = AppConfig()
    assert cfg.scanner.llm_model == GEMMA_4_26B_A4B_MODEL
    assert any("ollama is not allowed" in warning.lower() for warning in cfg.scanner.llm_model_warnings)


def test_chat_model_falls_back_to_base_model(monkeypatch):
    monkeypatch.setenv("AHAL_LLM_MODEL", GEMMA_4_26B_A4B_MODEL)
    monkeypatch.delenv("AHAL_CHAT_LLM_MODEL", raising=False)
    cfg = AppConfig()
    assert cfg.scanner.chat_llm_model == cfg.scanner.llm_model


def test_llm_status_endpoint_shape(monkeypatch, fresh_client):
    cfg = AppConfig()
    import app.api.analyze as analyze_module

    monkeypatch.setattr(analyze_module, "config", cfg)
    llm_telemetry.reset()
    llm_telemetry.record_failure("RATE_LIMITED")
    response = fresh_client.get("/analyze/llm/status")
    assert response.status_code == 200
    data = response.json()
    assert {"llm_enabled", "chat_llm_enabled", "docs_llm_enabled", "model", "key_present", "last_error_type", "fallback_count"}.issubset(data.keys())
