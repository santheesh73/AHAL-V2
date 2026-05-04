import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.sessions.session_manager import session_manager
from app.models.file_schema import SessionInfo, ScanStatus, ScanResult
from app.config import config

client = TestClient(app)

@pytest.fixture
def mock_session():
    session_id = session_manager.create_session()
    session_manager.update_progress(session_id, 100, processed_files=2, total_files=2)
    
    from tests.intelligence.conftest import python_fastapi_scan
    result = python_fastapi_scan()
    result.session_id = session_id
    session_manager.set_result(session_id, result)
    
    yield session_id
    
    # cleanup safely
    with session_manager._lock:
        session_manager._sessions.pop(session_id, None)

@pytest.fixture
def mock_in_progress_session():
    session_id = session_manager.create_session()
    session_manager.update_progress(session_id, 50, processed_files=1, total_files=2)
    # The stage is managed via set_stage if needed, but we can just set it internally or via progress
    with session_manager._lock:
        if session_id in session_manager._sessions:
            session_manager._sessions[session_id].stage = "extracting"
            
    yield session_id
    
    with session_manager._lock:
        session_manager._sessions.pop(session_id, None)


def test_missing_session_returns_404():
    response = client.get("/analyze/prd/invalid_session")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_NOT_FOUND"

def test_scan_in_progress_returns_202(mock_in_progress_session):
    response = client.get(f"/analyze/prd/{mock_in_progress_session}")
    assert response.status_code == 202
    assert response.json()["detail"]["code"] == "SCAN_IN_PROGRESS"

def test_unsupported_format_returns_400(mock_session):
    response = client.get(f"/analyze/prd/{mock_session}?format=docx")
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"
    assert "Unsupported format" in response.json()["detail"]["message"]

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_json_format_returns_prd_result(mock_generate, mock_session):
    response = client.get(f"/analyze/prd/{mock_session}?format=json")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Project Requirements Document"
    assert "overview" in data
    assert "architecture" in data
    assert "tech_stack" in data
    assert "api_endpoints" in data
    assert "risks" in data
    
    # Check no LLM call made
    mock_generate.assert_not_called()

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_prd_json_overview_product_level(mock_generate, mock_session, monkeypatch):
    from tests.intelligence.conftest import make_scan_result
    from app.intelligence.intelligence_engine import IntelligenceEngine
    
    scan = make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "main.py", "extension": ".py"},
        ],
        contents={
            "README.md": "# Kannadi Med\n\nAI-assisted diagnosis engine.\n",
            "main.py": 'from fastapi import FastAPI\napp = FastAPI()\n\n@app.post("/diagnose")\ndef diagnose(): pass\n\n@app.post("/search")\ndef search(): pass\n',
        },
    )
    intel = IntelligenceEngine().analyze(scan)
    scan.session_id = mock_session
    session_manager.set_result(mock_session, scan)
    
    # Needs to bypass the cache in real implementation, but tests run clean
    # Also need to provide intelligence result in the endpoint logic or the PRD endpoint recomputes it
    
    response = client.get(f"/analyze/prd/{mock_session}?format=json")
    assert response.status_code == 200
    data = response.json()
    overview_text = data["overview"]["content"].lower()
    
    assert "kannadi med" in overview_text
    assert "fastapi" in overview_text
    assert "diagnosis" in overview_text
    
    mock_generate.assert_not_called()

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_prd_json_overview_startup_level_for_ahal_ai(mock_generate, mock_session, monkeypatch):
    from tests.intelligence.conftest import make_scan_result
    from app.intelligence.intelligence_engine import IntelligenceEngine

    scan = make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "main.py", "extension": ".py"},
            {"path": "app/chat/chat_service.py", "extension": ".py"},
            {"path": "frontend/dashboard/page.tsx", "extension": ".tsx"},
        ],
        contents={
            "README.md": "# AHAL AI\n\nAI-Powered Developer Intelligence System.\n",
            "main.py": 'from fastapi import FastAPI\napp = FastAPI()\n\n@app.post("/analyze")\ndef analyze(): pass\n\n@app.post("/ask")\ndef ask(): pass\n\n@app.post("/summarize")\ndef summarize(): pass\n\n@app.get("/report")\ndef report(): pass\n',
            "app/chat/chat_service.py": "class ChatService: pass\n",
            "frontend/dashboard/page.tsx": "export default function Dashboard() {}\n",
        },
    )
    intel = IntelligenceEngine().analyze(scan)
    scan.session_id = mock_session
    session_manager.set_result(mock_session, scan)

    response = client.get(f"/analyze/prd/{mock_session}?format=json")
    assert response.status_code == 200
    data = response.json()
    overview_text = data["overview"]["content"].lower()

    assert "ahal ai" in overview_text
    assert "repository intelligence" in overview_text or "code intelligence" in overview_text
    assert "fastapi" in overview_text

    # No unsupported business claims
    for bad in ["funding", "revenue", "enterprise-grade security", "guarantees"]:
        assert bad not in overview_text

    mock_generate.assert_not_called()

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_markdown_format_returns_md(mock_generate, mock_session):
    response = client.get(f"/analyze/prd/{mock_session}?format=markdown")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "ahal_prd" in response.headers["content-disposition"]
    text = response.text
    assert "# Project Requirement Document" in text
    assert "POST" in text
    assert "/users" in text
    assert "node_modules" not in text
    
    mock_generate.assert_not_called()

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_latex_format_returns_tex(mock_generate, mock_session):
    response = client.get(f"/analyze/prd/{mock_session}?format=latex")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/x-tex; charset=utf-8"
    assert "ahal_prd" in response.headers["content-disposition"]
    text = response.text
    assert r"\documentclass" in text
    assert "POST" in text
    assert "/users" in text
    assert "node_modules" not in text
    
    mock_generate.assert_not_called()

def test_token_auth_preserved(mock_session, monkeypatch):
    import dataclasses
    import app.config as config_module
    import app.api.analyze as analyze_module
    patched_scanner = dataclasses.replace(config_module.config.scanner, require_session_token=True)
    patched_config = dataclasses.replace(config_module.config, scanner=patched_scanner)
    monkeypatch.setattr(config_module, "config", patched_config)
    monkeypatch.setattr(analyze_module, "config", patched_config)
    
    # Without token -> 401
    response = client.get(f"/analyze/prd/{mock_session}")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "UNAUTHORIZED"
    
    # With valid token -> 200
    token = session_manager.get_access_token(mock_session)
    response = client.get(f"/analyze/prd/{mock_session}", headers={"X-Session-Token": token})
    assert response.status_code == 200

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_include_llm_polish_json_does_not_call_llm(mock_generate, mock_session):
    response = client.get(f"/analyze/prd/{mock_session}?format=json&include_llm_polish=true")
    assert response.status_code == 200
    data = response.json()
    assert "LLM polish is only applied to markdown output" in str(data["warnings"])
    mock_generate.assert_not_called()

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_include_llm_polish_latex_does_not_call_llm(mock_generate, mock_session):
    response = client.get(f"/analyze/prd/{mock_session}?format=latex&include_llm_polish=true")
    assert response.status_code == 200
    assert "LLM polish is only applied to markdown output" in response.text
    mock_generate.assert_not_called()

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_include_llm_polish_markdown_calls_llm(mock_generate, mock_session, monkeypatch):
    import dataclasses
    import app.config as config_module
    import app.docs.llm.prd_polish_service as polish_module
    patched_scanner = dataclasses.replace(config_module.config.scanner, llm_enabled=True, gemini_api_key="fake-key")
    patched_config = dataclasses.replace(config_module.config, scanner=patched_scanner)
    monkeypatch.setattr(config_module, "config", patched_config)
    monkeypatch.setattr(polish_module, "config", patched_config)
    
    valid_sections = """
# Project Requirement Document

## 1. Project Overview
Polished overview.

## 2. Architecture
Polished architecture.

## 3. Tech Stack
Polished tech stack.

## 4. Core Modules
Polished modules.

## 5. API Surface
GET /health
GET /users
POST /users

## 6. Workflow
Polished workflow.

## 7. Database / Storage
Insufficient evidence from codebase.

## 8. Setup and Run Notes
Polished setup.

## 9. Risks and Gaps
Polished risks.

## 10. Evidence Summary
Evidence preserved.
"""
    mock_generate.return_value = valid_sections
    
    response = client.get(f"/analyze/prd/{mock_session}?format=markdown&include_llm_polish=true")
    assert response.status_code == 200
    mock_generate.assert_called_once()
    assert "Polished overview" in response.text
    assert "GET /health" in response.text
    assert "POST /users" in response.text

def test_pdf_format_returns_pdf(mock_session):
    response = client.get(f"/analyze/prd/{mock_session}?format=pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "ahal_prd" in response.headers["content-disposition"]
    assert ".pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")

@patch("app.docs.llm.pdf_polish_service.PDFPolishService.polish_for_pdf")
def test_pdf_format_no_gemini_call(mock_polish, mock_session):
    response = client.get(f"/analyze/prd/{mock_session}?format=pdf&include_llm_polish=false")
    assert response.status_code == 200
    mock_polish.assert_not_called()

@patch("app.docs.llm.pdf_polish_service.PDFPolishService.polish_for_pdf")
def test_pdf_with_llm_polish_calls_service_when_enabled(mock_polish, mock_session):
    mock_polish.return_value = {
        "executive_summary": "Polished PDF summary.",
        "project_goal": "Polished goal.",
        "what": "Polished what.",
        "why": "Polished why.",
        "built_summary": "Polished built summary.",
        "remaining_summary": "Polished remaining summary.",
        "risk_summary": "Polished risk summary.",
        "next_steps": ["Polished next step."],
        "section_intros": {
            "architecture": "Architecture intro.",
            "tech_stack": "Tech stack intro.",
            "core_modules": "Core modules intro.",
            "api_surface": "API surface intro.",
            "workflow": "Workflow intro.",
            "database_storage": "Database intro.",
            "setup_notes": "Setup intro.",
            "evidence_summary": "Evidence intro.",
            "warnings": "Warnings intro.",
        },
    }
    response = client.get(f"/analyze/prd/{mock_session}?format=pdf&include_llm_polish=true")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    mock_polish.assert_called_once()

@patch("app.docs.llm.pdf_polish_service.PDFPolishService.polish_for_pdf")
def test_pdf_with_llm_polish_fallback_when_service_fails(mock_polish, mock_session):
    mock_polish.side_effect = Exception("Gemini failure")
    response = client.get(f"/analyze/prd/{mock_session}?format=pdf&include_llm_polish=true")
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")

@patch("app.docs.llm.pdf_polish_service.PDFPolishService.polish_for_pdf")
def test_pdf_with_llm_polish_does_not_call_for_json_markdown_latex(mock_polish, mock_session):
    json_response = client.get(f"/analyze/prd/{mock_session}?format=json&include_llm_polish=true")
    markdown_response = client.get(f"/analyze/prd/{mock_session}?format=markdown&include_llm_polish=false")
    latex_response = client.get(f"/analyze/prd/{mock_session}?format=latex&include_llm_polish=true")
    assert json_response.status_code == 200
    assert markdown_response.status_code == 200
    assert latex_response.status_code == 200
    mock_polish.assert_not_called()
