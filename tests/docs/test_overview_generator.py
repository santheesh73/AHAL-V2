from app.docs.generators.overview_generator import OverviewGenerator
from unittest.mock import MagicMock


def test_kannadi_med_overview_is_product_level():
    gen = OverviewGenerator()
    mock_scan = MagicMock()
    mock_scan.contents = {
        "readme.md": b"# Kannadi Med\n\nAI-assisted diagnosis engine.\n",
    }

    mock_api_1 = MagicMock()
    mock_api_1.path = "/diagnose"
    mock_api_2 = MagicMock()
    mock_api_2.path = "/search"

    mock_mod = MagicMock()
    mock_mod.name = "rag_engine"

    mock_fw = MagicMock()
    mock_fw.name = "FastAPI"

    mock_intel = MagicMock()
    mock_intel.api_endpoints = [mock_api_1, mock_api_2]
    mock_intel.modules = [mock_mod]
    mock_intel.frameworks = [mock_fw]
    mock_intel.architecture = "Backend"
    mock_intel.dependencies = []
    mock_intel.databases = []

    res = gen.generate(mock_scan, mock_intel)

    assert "Kannadi Med" in res.content
    assert "AI-assisted" in res.content
    assert "diagnosis" in res.content
    assert "FastAPI" in res.content
    assert "search" in res.content
    assert res.confidence == "high"
    assert "guarantees" not in res.content
    assert "replaces doctors" not in res.content


def test_ahal_ai_overview_is_startup_level():
    gen = OverviewGenerator()
    mock_scan = MagicMock()
    mock_scan.contents = {
        "README.md": b"# AHAL AI\n\nAI-Powered Developer Intelligence System.\n",
        "app/api/analyze.py": b"@app.post('/analyze')\ndef analyze(): pass\n",
        "app/chat/chat_service.py": b"class ChatService: pass\n",
        "app/docs/report.py": b"class ReportGenerator: pass\n",
        "frontend/dashboard/page.tsx": b"export default function Dashboard() {}\n",
        "frontend/lib/api.ts": b"export const api = {};\n",
        "frontend/store.ts": b"export const store = {};\n",
    }

    mock_api_1 = MagicMock(); mock_api_1.path = "/analyze"
    mock_api_2 = MagicMock(); mock_api_2.path = "/ask"
    mock_api_3 = MagicMock(); mock_api_3.path = "/summarize"
    mock_api_4 = MagicMock(); mock_api_4.path = "/report"
    mock_api_5 = MagicMock(); mock_api_5.path = "/session/status"

    mock_mod_1 = MagicMock(); mock_mod_1.name = "analysis_service"
    mock_mod_2 = MagicMock(); mock_mod_2.name = "chat_service"
    mock_mod_3 = MagicMock(); mock_mod_3.name = "session_manager"

    mock_fw_1 = MagicMock(); mock_fw_1.name = "FastAPI"
    mock_fw_2 = MagicMock(); mock_fw_2.name = "Next.js"
    mock_fw_3 = MagicMock(); mock_fw_3.name = "React"

    mock_db = MagicMock(); mock_db.name = "MongoDB"

    mock_intel = MagicMock()
    mock_intel.api_endpoints = [mock_api_1, mock_api_2, mock_api_3, mock_api_4, mock_api_5]
    mock_intel.modules = [mock_mod_1, mock_mod_2, mock_mod_3]
    mock_intel.frameworks = [mock_fw_1, mock_fw_2, mock_fw_3]
    mock_intel.architecture = "Fullstack"
    mock_intel.dependencies = []
    mock_intel.databases = [mock_db]

    res = gen.generate(mock_scan, mock_intel)

    content = res.content
    content_lower = content.lower()

    # Must include project name
    assert "AHAL AI" in content

    # Must include product-level language
    assert "ai-powered" in content_lower or "ai-assisted" in content_lower

    # Must include repo-intel domain
    assert "repository intelligence" in content_lower or "code intelligence" in content_lower

    # Must include stack
    assert "fastapi" in content_lower
    assert "next.js" in content_lower or "react" in content_lower
    assert "mongodb" in content_lower

    # Must include at least two capabilities
    cap_keywords = ["repository analysis", "chat", "summarization", "session", "report"]
    found_caps = [k for k in cap_keywords if k in content_lower]
    assert len(found_caps) >= 2, f"Only found capabilities: {found_caps}"

    # Must NOT be the old generic fallback
    assert content != "A fullstack project built with FastAPI, MongoDB, Next.js, React."

    # Must NOT include unsupported business claims
    for bad in ["funding", "revenue", "enterprise-grade security", "guarantees"]:
        assert bad not in content_lower

    # Confidence
    assert res.confidence in ("high", "medium")


def test_dependency_evidence_is_sanitized_without_crashing_overview():
    gen = OverviewGenerator()
    mock_scan = MagicMock()
    mock_scan.contents = {
        "README.md": b"# AHAL AI\n\nAI-Powered Developer Intelligence System.\n",
    }

    mock_api = MagicMock()
    mock_api.path = "/analyze"

    mock_fw = MagicMock()
    mock_fw.name = "FastAPI"

    dep = MagicMock()
    dep.name = "openai"

    mock_intel = MagicMock()
    mock_intel.api_endpoints = [mock_api]
    mock_intel.modules = []
    mock_intel.frameworks = [mock_fw]
    mock_intel.architecture = "Fullstack"
    mock_intel.dependencies = [dep]
    mock_intel.databases = []

    res = gen.generate(mock_scan, mock_intel)

    assert res.content
    assert "Generation failed" not in res.content
    assert any(ev.source_id == "dep:openai" for ev in res.evidence)
    assert all(ev.source_type != "dependency" for ev in res.evidence)
    assert any("normalized" in warning.lower() or "dependency" in warning.lower() for warning in res.warnings) or res.evidence
