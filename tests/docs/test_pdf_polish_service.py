import dataclasses
from unittest.mock import patch

from app.docs.llm.pdf_polish_service import PDFPolishService
from app.docs.models import PRDResult, PRDSection, ProjectBrief, RiskItem, ProjectStatusItem
import app.config as config_module
import app.docs.llm.pdf_polish_service as pdf_polish_module


def _patch_scanner_config(monkeypatch, **overrides):
    patched_scanner = dataclasses.replace(config_module.config.scanner, **overrides)
    patched_config = dataclasses.replace(config_module.config, scanner=patched_scanner)
    monkeypatch.setattr(config_module, "config", patched_config)
    monkeypatch.setattr(pdf_polish_module, "config", patched_config)


def _sample_prd():
    risk = RiskItem(
        title="No auth detected",
        severity="medium",
        description="No explicit auth module detected.",
        recommendation="Add authentication if required.",
        evidence=[],
    )
    brief = ProjectBrief(
        goal=PRDSection(title="Goal", content="The primary goal is to support medical query workflows.", confidence="high"),
        what=PRDSection(title="What", content="Kannadi Med is an offline-first AI-assisted medical diagnosis and knowledge retrieval backend built with FastAPI.", confidence="high"),
        why=PRDSection(title="Why", content="It exists to support medical query workflows using AI-assisted diagnosis and retrieval components.", confidence="high"),
        completed=[
            ProjectStatusItem(title="API Layer", status="built", description="Backend API layer built with 2 endpoints.", confidence="high", evidence=[]),
        ],
        remaining=[
            ProjectStatusItem(title="Authentication", status="missing", description="No auth detected.", confidence="high", evidence=[]),
        ],
        issues=[risk],
        next_steps=["Add authentication if required."],
        confidence="high",
        warnings=[],
    )
    return PRDResult(
        session_id="test-session",
        title="Project Requirements Document",
        project_type="backend",
        overview=PRDSection(title="Overview", content="Kannadi Med is an offline-first AI-assisted medical diagnosis and knowledge retrieval backend built with FastAPI.", confidence="high"),
        project_brief=brief,
        architecture=PRDSection(title="Architecture", content="Backend architecture centered on FastAPI request handling.", confidence="high"),
        tech_stack=PRDSection(title="Tech Stack", content="FastAPI, Python, and SQLite", confidence="high"),
        modules=[],
        api_endpoints=[],
        databases=PRDSection(title="Database / Storage", content="SQLite storage is configured for local persistence.", confidence="high"),
        workflow=[],
        setup_notes=PRDSection(title="Setup Notes", content="Run uvicorn main:app --reload", confidence="high"),
        risks=[risk],
        confidence="high",
        evidence_count=5,
        warnings=["Ignored paths were detected during deterministic analysis."],
    )


def _valid_polished_json():
    return """{
      "executive_summary": "Kannadi Med is an AI-assisted medical backend for diagnosis workflows and knowledge retrieval.",
      "project_goal": "Support medical query workflows through deterministic backend APIs.",
      "what": "Kannadi Med is an offline-first AI-assisted medical diagnosis and knowledge retrieval backend built with FastAPI.",
      "why": "It exists to support safe medical query workflows with AI-assisted diagnosis and knowledge retrieval.",
      "built_summary": "Built components include the API layer for diagnosis workflows.",
      "remaining_summary": "Remaining work includes authentication coverage for protected workflows.",
      "risk_summary": "Detected issues include no auth detected and the need for stronger access control.",
      "next_steps": ["Add authentication if required."],
      "section_intros": {
        "architecture": "The architecture section below remains deterministic.",
        "tech_stack": "The tech stack below remains deterministic.",
        "core_modules": "The module details below remain deterministic.",
        "api_surface": "The API details below remain deterministic.",
        "workflow": "The workflow details below remain deterministic.",
        "database_storage": "The database notes below remain deterministic.",
        "setup_notes": "The setup notes below remain deterministic.",
        "evidence_summary": "The evidence summary below remains deterministic.",
        "warnings": "Warnings below remain deterministic, including the ignored paths warning."
      }
    }"""


def test_pdf_polish_disabled_returns_none(monkeypatch):
    _patch_scanner_config(monkeypatch, llm_enabled=False, gemini_api_key="fake-key")
    assert PDFPolishService().polish_for_pdf(_sample_prd()) is None


def test_pdf_polish_missing_key_returns_none(monkeypatch):
    _patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="")
    assert PDFPolishService().polish_for_pdf(_sample_prd()) is None


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_pdf_polish_valid_json_accepted(mock_generate, monkeypatch):
    _patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    mock_generate.return_value = _valid_polished_json()
    polished = PDFPolishService().polish_for_pdf(_sample_prd())
    assert polished is not None
    assert polished["executive_summary"].startswith("Kannadi Med")


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_pdf_polish_rejects_hallucinated_api(mock_generate, monkeypatch):
    _patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    mock_generate.return_value = _valid_polished_json().replace(
        '"executive_summary": "Kannadi Med is an AI-assisted medical backend for diagnosis workflows and knowledge retrieval."',
        '"executive_summary": "Kannadi Med is an AI-assisted medical backend for diagnosis workflows, knowledge retrieval, and POST /not-real support."',
    )
    assert PDFPolishService().polish_for_pdf(_sample_prd()) is None


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_pdf_polish_rejects_forbidden_medical_claim(mock_generate, monkeypatch):
    _patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    mock_generate.return_value = _valid_polished_json().replace("AI-assisted medical backend", "clinically validated medical backend")
    assert PDFPolishService().polish_for_pdf(_sample_prd()) is None


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_pdf_polish_rejects_ignored_paths(mock_generate, monkeypatch):
    _patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    mock_generate.return_value = _valid_polished_json().replace("The module details below remain deterministic.", "The module details below remain deterministic and exclude node_modules.")
    assert PDFPolishService().polish_for_pdf(_sample_prd()) is None


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_pdf_polish_rejects_raw_repr(mock_generate, monkeypatch):
    _patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    mock_generate.return_value = _valid_polished_json().replace("The tech stack below remains deterministic.", "The tech stack below remains deterministic with type='backend'.")
    assert PDFPolishService().polish_for_pdf(_sample_prd()) is None


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_pdf_polish_limits_next_steps(mock_generate, monkeypatch):
    _patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    mock_generate.return_value = _valid_polished_json().replace(
        '"next_steps": ["Add authentication if required."]',
        '"next_steps": ["one", "two", "three", "four", "five", "six", "seven"]',
    )
    assert PDFPolishService().polish_for_pdf(_sample_prd()) is None


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_pdf_polish_preserves_warnings_and_risks(mock_generate, monkeypatch):
    _patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    mock_generate.return_value = _valid_polished_json().replace(
        '"risk_summary": "Detected issues include no auth detected and the need for stronger access control."',
        '"risk_summary": "Detected issues include stronger access control needs."',
    ).replace(
        '"warnings": "Warnings below remain deterministic, including the ignored paths warning."',
        '"warnings": "Warnings below remain deterministic."',
    )
    assert PDFPolishService().polish_for_pdf(_sample_prd()) is None
