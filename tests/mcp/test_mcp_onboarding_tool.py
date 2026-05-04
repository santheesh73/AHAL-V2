from __future__ import annotations

from unittest.mock import patch

from app.models.file_schema import ScanStatus
from app.mcp.tools import MCPToolRegistry
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import make_scan_result


def _completed_repo_session():
    sid = session_manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    scan = make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "app/main.py", "extension": ".py"},
            {"path": "app/api/routes.py", "extension": ".py"},
            {"path": "docker-compose.yml", "extension": ".yml"},
            {"path": "node_modules/ignored.js", "extension": ".js"},
        ],
        contents={
            "README.md": "# Demo\n\nRepository intelligence backend.\n",
            "app/main.py": 'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/health")\ndef health():\n    return {"ok": True}\n',
            "app/api/routes.py": 'from fastapi import APIRouter\nrouter = APIRouter()\n@router.get("/users")\ndef users():\n    return []\n',
            "docker-compose.yml": "services:\n  api:\n    build: .\n",
            "node_modules/ignored.js": "console.log('ignore');\n",
        },
    )
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid


def test_mcp_onboarding_tool_works():
    sid = _completed_repo_session()
    result = MCPToolRegistry().call_tool(
        "ahal_generate_onboarding_report",
        {"session_id": sid, "audience": "new_engineer", "time_budget_minutes": 30, "format": "json"},
    )
    assert result["ok"] is True
    assert result["result"]["session_id"] == sid
    assert result["result"]["reading_order"][0]["files_to_read"][0] == "README.md"


def test_mcp_onboarding_tool_markdown_works():
    sid = _completed_repo_session()
    result = MCPToolRegistry().call_tool(
        "ahal_generate_onboarding_report",
        {"session_id": sid, "audience": "devops", "time_budget_minutes": 30, "format": "markdown"},
    )
    assert result["ok"] is True
    assert "# New Engineer Onboarding Guide" in result["result"]
    assert "## Important APIs" in result["result"]


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_no_gemini_required_and_no_raw_repr_leakage(mock_generate):
    sid = _completed_repo_session()
    result = MCPToolRegistry().call_tool("ahal_generate_onboarding_report", {"session_id": sid})
    assert result["ok"] is True
    payload = str(result["result"]).lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
    assert "node_modules" not in payload
    mock_generate.assert_not_called()
