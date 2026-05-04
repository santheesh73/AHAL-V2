import pytest
from unittest.mock import MagicMock, patch
from app.docs.llm.prd_polish_service import PRDPolishService
from app.docs.models import PRDResult, PRDSection, APISectionItem
from app.config import config
import dataclasses
import app.config as config_module
import app.docs.llm.prd_polish_service as polish_module

def patch_scanner_config(monkeypatch, **overrides):
    patched_scanner = dataclasses.replace(config_module.config.scanner, **overrides)
    patched_config = dataclasses.replace(config_module.config, scanner=patched_scanner)
    monkeypatch.setattr(config_module, "config", patched_config)
    monkeypatch.setattr(polish_module, "config", patched_config)

@pytest.fixture
def sample_prd():
    return PRDResult(
        title="Project Requirements Document",
        project_type="backend",
        overview=PRDSection(title="Project Overview", content="Overview content", confidence="high"),
        architecture=PRDSection(title="Architecture", content="Arch content", confidence="high"),
        tech_stack=PRDSection(title="Tech Stack", content="Tech stack content", confidence="high"),
        api_endpoints=[APISectionItem(method="POST", path="/diagnose", framework="FastAPI", description="Diagnose endpoint", confidence="high")],
        modules=[],
        workflow=[],
        databases=PRDSection(title="Database / Storage", content="DB content", confidence="high"),
        setup_notes=PRDSection(title="Setup and Run Notes", content="Setup content", confidence="high"),
        risks=[],
        confidence="high",
        evidence_count=1,
        warnings=[]
    )

def test_polish_returns_warning_when_llm_disabled(sample_prd, monkeypatch):
    patch_scanner_config(monkeypatch, llm_enabled=False)
    service = PRDPolishService()
    md, warnings = service.polish(sample_prd, "Original MD")
    assert md == "Original MD"
    assert "LLM disabled" in warnings[0]

def test_polish_returns_warning_when_missing_key(sample_prd, monkeypatch):
    patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="")
    service = PRDPolishService()
    md, warnings = service.polish(sample_prd, "Original MD")
    assert md == "Original MD"
    assert "missing" in warnings[0]

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_polish_returns_warning_when_api_fails(mock_generate, sample_prd, monkeypatch):
    patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    mock_generate.side_effect = Exception("API error")
    
    service = PRDPolishService()
    md, warnings = service.polish(sample_prd, "Original MD")
    assert md == "Original MD"
    assert "failed" in warnings[0]

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_polish_validates_sections(mock_generate, sample_prd, monkeypatch):
    patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    
    # Missing required section like 'architecture'
    mock_generate.return_value = "project overview\ntech stack\ncore modules\napi surface\nworkflow\ndatabase\nsetup\nrisks\nevidence summary\nPOST /diagnose\ninsufficient evidence"
    
    service = PRDPolishService()
    md, warnings = service.polish(sample_prd, "Original MD")
    
    assert md == "Original MD"
    assert "failed validation" in warnings[0]
    assert any("architecture" in w.lower() for w in warnings)

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_polish_rejects_ignored_paths(mock_generate, sample_prd, monkeypatch):
    patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    
    valid_sections = "project overview\narchitecture\ntech stack\ncore modules\napi surface\nworkflow\ndatabase\nsetup\nrisks\nevidence summary\nPOST /diagnose\ninsufficient evidence"
    mock_generate.return_value = valid_sections + "\nnode_modules"
    
    service = PRDPolishService()
    md, warnings = service.polish(sample_prd, "Original MD")
    
    assert md == "Original MD"
    assert any("node_modules" in w for w in warnings)

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_polish_rejects_hallucinations(mock_generate, sample_prd, monkeypatch):
    patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    
    valid_sections = "project overview\narchitecture\ntech stack\ncore modules\napi surface\nworkflow\ndatabase\nsetup\nrisks\nevidence summary\nPOST /diagnose\ninsufficient evidence"
    mock_generate.return_value = valid_sections + "\nFuture Roadmap"
    
    service = PRDPolishService()
    md, warnings = service.polish(sample_prd, "Original MD")
    
    assert md == "Original MD"
    assert any("invented unsupported section" in w.lower() for w in warnings)

@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_polish_accepts_valid_markdown(mock_generate, sample_prd, monkeypatch):
    patch_scanner_config(monkeypatch, llm_enabled=True, gemini_api_key="fake-key")
    
    valid_sections = "project overview\narchitecture\ntech stack\ncore modules\napi surface\nworkflow\ndatabase\nsetup\nrisks\nevidence summary\nPOST /diagnose\ninsufficient evidence"
    mock_generate.return_value = valid_sections
    
    service = PRDPolishService()
    md, warnings = service.polish(sample_prd, "Original MD")
    
    assert md == valid_sections
    assert not warnings
