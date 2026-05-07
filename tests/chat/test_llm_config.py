import os
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
from app.chat.chat_engine import ChatEngine
from app.chat.llm.gemini_chat_client import GeminiChatClient
from app.config import AppConfig, GEMMA_4_26B_A4B_MODEL, GEMMA_4_26B_UNAVAILABLE_WARNING, _env_bool
from app.chat.models import ProjectPurpose
from types import SimpleNamespace

def make_evidence(
    file="README.md",
    reason="Test evidence",
    snippet="FastAPI backend",
    confidence="high",
):
    return SimpleNamespace(
        file=file,
        source_file=file,
        source_id=file,
        source_type="file",
        reason=reason,
        snippet=snippet,
        confidence=confidence,
    )

def get_safe_intelligence():
    evidence = make_evidence()

    architecture = SimpleNamespace(
        type="backend",
        confidence="high",
        reasoning=["FastAPI framework detected"],
        evidence=[evidence],
    )

    framework = SimpleNamespace(
        name="FastAPI",
        category="backend",
        file="main.py",
        source_file="main.py",
        confidence="high",
        evidence=[evidence],
    )

    entrypoint = SimpleNamespace(
        file="main.py",
        path="main.py",
        type="backend",
        framework="FastAPI",
        confidence="high",
        evidence=[make_evidence(file="main.py", reason="Backend entrypoint detected")],
    )

    api_endpoint = SimpleNamespace(
        method="POST",
        path="/diagnose",
        framework="FastAPI",
        source_file="main.py",
        file="main.py",
        handler="diagnose",
        description="Diagnosis API endpoint",
        confidence="high",
        evidence=[make_evidence(file="main.py", reason="FastAPI route detected")],
    )

    workflow_step = SimpleNamespace(
        order=1,
        source="Client",
        action="HTTP POST /diagnose",
        target="main.py",
        confidence="high",
        evidence=[make_evidence(file="main.py", reason="Workflow inferred from API endpoint")],
    )

    workflow = SimpleNamespace(
        steps=[workflow_step],
        warnings=[],
        completeness="partial",
        confidence="medium",
        evidence=[evidence],
    )

    return SimpleNamespace(
        architecture=architecture,
        frameworks=[framework],
        entry_points=[entrypoint],
        api_endpoints=[api_endpoint],
        databases=[],
        modules=[],
        dependencies=[],
        workflow=workflow,
    )

def test_env_bool_parsing():
    os.environ["TEST_ENV_BOOL"] = "true"
    assert _env_bool("TEST_ENV_BOOL", False) is True
    os.environ["TEST_ENV_BOOL"] = "1"
    assert _env_bool("TEST_ENV_BOOL", False) is True
    os.environ["TEST_ENV_BOOL"] = "false"
    assert _env_bool("TEST_ENV_BOOL", True) is False
    os.environ["TEST_ENV_BOOL"] = "yes"
    assert _env_bool("TEST_ENV_BOOL", False) is True
    os.environ["TEST_ENV_BOOL"] = "no"
    assert _env_bool("TEST_ENV_BOOL", True) is False
    if "MISSING_ENV_BOOL" in os.environ:
        del os.environ["MISSING_ENV_BOOL"]
    assert _env_bool("MISSING_ENV_BOOL", True) is True

def test_llm_model_config_uses_gemma_4_26b(monkeypatch):
    monkeypatch.delenv("AHAL_LLM_MODEL", raising=False)
    monkeypatch.delenv("AHAL_CHAT_LLM_MODEL", raising=False)

    test_config = AppConfig()

    assert test_config.scanner.llm_model == GEMMA_4_26B_A4B_MODEL
    assert test_config.scanner.chat_llm_model == GEMMA_4_26B_A4B_MODEL
    assert not test_config.scanner.llm_model_warnings

def test_chat_model_falls_back_to_base_llm_model(monkeypatch):
    monkeypatch.setenv("AHAL_LLM_MODEL", GEMMA_4_26B_A4B_MODEL)
    monkeypatch.delenv("AHAL_CHAT_LLM_MODEL", raising=False)

    test_config = AppConfig()

    assert test_config.scanner.chat_llm_model == test_config.scanner.llm_model

def test_invalid_gemma_26b_triggers_warning(monkeypatch):
    monkeypatch.setenv("AHAL_LLM_MODEL", "gemma-26b-it")
    monkeypatch.delenv("AHAL_CHAT_LLM_MODEL", raising=False)

    test_config = AppConfig()

    assert test_config.scanner.llm_model == GEMMA_4_26B_A4B_MODEL
    assert any("deprecated/invalid" in warning for warning in test_config.scanner.llm_model_warnings)
    assert any(GEMMA_4_26B_A4B_MODEL in warning for warning in test_config.scanner.llm_model_warnings)

def test_llm_disabled_warning():
    client = GeminiChatClient(enabled=False, api_key="")
    engine = ChatEngine(llm_client=client)
    
    scan = SimpleNamespace(
        files=[SimpleNamespace(path="README.md", file="README.md")],
        contents={"README.md": "# Test\nFastAPI backend with POST /diagnose"}
    )
    intelligence = get_safe_intelligence()
    graph = SimpleNamespace(nodes=[], edges=[])
    engine._purpose_extractor.extract = MagicMock(return_value=ProjectPurpose())
    
    answer = engine.answer("Test", scan, intelligence, graph)
    
    assert any("LLM disabled" in w for w in answer.warnings)
    assert not any("missing" in w for w in answer.warnings)

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_missing_gemini_key_warning(mock_generate, monkeypatch):
    import dataclasses
    import app.config as config_module
    patched_scanner = dataclasses.replace(config_module.config.scanner, gemini_api_key="")
    patched_config = dataclasses.replace(config_module.config, scanner=patched_scanner)
    monkeypatch.setattr(config_module, "config", patched_config)
    
    client = GeminiChatClient(enabled=True, api_key="")
    engine = ChatEngine(llm_client=client)
    
    scan = SimpleNamespace(
        files=[SimpleNamespace(path="README.md", file="README.md")],
        contents={"README.md": "# Test\nFastAPI backend with POST /diagnose"}
    )
    intelligence = get_safe_intelligence()
    graph = SimpleNamespace(nodes=[], edges=[])
    engine._purpose_extractor.extract = MagicMock(return_value=ProjectPurpose())
    
    answer = engine.answer("Test", scan, intelligence, graph)
    
    warnings_text = " ".join(answer.warnings).lower()
    assert "api key missing" in warnings_text or "gemini api key missing" in warnings_text
    assert "llm disabled;" not in warnings_text

@patch("app.chat.llm.gemini_chat_client.urllib_request.urlopen")
def test_mocked_gemini_success_no_warning(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"candidates": [{"content": {"parts": [{"text": "LLM Answer"}]}}]}'
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp
    
    client = GeminiChatClient(enabled=True, api_key="dummy")
    engine = ChatEngine(llm_client=client)
    
    scan = SimpleNamespace(
        files=[SimpleNamespace(path="README.md", file="README.md")],
        contents={"README.md": "# Test\nFastAPI backend with POST /diagnose"}
    )
    intelligence = get_safe_intelligence()
    graph = SimpleNamespace(nodes=[], edges=[])
    engine._purpose_extractor.extract = MagicMock(return_value=ProjectPurpose())
    
    answer = engine.answer("Test", scan, intelligence, graph)
    
    assert "LLM Answer" in answer.answer
    assert not any("LLM unavailable" in w for w in answer.warnings)
    assert not any("LLM disabled" in w for w in answer.warnings)

@patch("app.chat.llm.gemini_chat_client.urllib_request.urlopen")
def test_mocked_gemini_failure_warning(mock_urlopen):
    from urllib.error import URLError
    mock_urlopen.side_effect = URLError("Mock error")
    
    client = GeminiChatClient(enabled=True, api_key="dummy")
    engine = ChatEngine(llm_client=client)
    
    scan = SimpleNamespace(
        files=[SimpleNamespace(path="README.md", file="README.md")],
        contents={"README.md": "# Test\nFastAPI backend with POST /diagnose"}
    )
    intelligence = get_safe_intelligence()
    graph = SimpleNamespace(nodes=[], edges=[])
    engine._purpose_extractor.extract = MagicMock(return_value=ProjectPurpose())
    
    answer = engine.answer("Test", scan, intelligence, graph)
    
    assert any("API call failed" in w for w in answer.warnings)

@patch("app.chat.llm.gemini_chat_client.urllib_request.urlopen")
def test_chat_returns_deterministic_answer_when_gemma_404_occurs(mock_urlopen):
    mock_urlopen.side_effect = HTTPError(
        url="https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent",
        code=404,
        msg="not found",
        hdrs=None,
        fp=None,
    )

    client = GeminiChatClient(enabled=True, api_key="dummy")
    engine = ChatEngine(llm_client=client)

    scan = SimpleNamespace(
        files=[SimpleNamespace(path="README.md", file="README.md")],
        contents={"README.md": "# Test\nFastAPI backend with POST /diagnose"}
    )
    intelligence = get_safe_intelligence()
    graph = SimpleNamespace(nodes=[], edges=[])
    engine._purpose_extractor.extract = MagicMock(return_value=ProjectPurpose())

    answer = engine.answer("What does this project do?", scan, intelligence, graph)

    assert answer.answer
    assert GEMMA_4_26B_UNAVAILABLE_WARNING in answer.warnings

def test_no_ollama_dependency_required_for_llm_clients():
    client = GeminiChatClient(enabled=False, api_key="", model=GEMMA_4_26B_A4B_MODEL)

    assert client.model_name == GEMMA_4_26B_A4B_MODEL
    assert "ollama" not in client.__class__.__module__.lower()

def test_startup_diagnostic_helper_safe():
    # Test that evaluating the diagnostic string doesn't contain the key
    from app.config import AppConfig
    import os
    os.environ["GEMINI_API_KEY"] = "super-secret-key-12345"
    test_config = AppConfig()
    
    diagnostic = f"enabled={test_config.scanner.llm_enabled} key_present={bool(test_config.scanner.gemini_api_key)} model={test_config.scanner.llm_model}"
    
    assert "super-secret-key-12345" not in diagnostic
    assert "key_present=True" in diagnostic
