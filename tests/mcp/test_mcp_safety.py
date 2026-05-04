from __future__ import annotations

from app.config import config
from app.models.file_schema import ScanStatus
from app.mcp.tools import MCPToolRegistry
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import make_scan_result, python_fastapi_scan


def _completed_session(scan=None, session_type="folder", source_name="project.zip"):
    sid = session_manager.create_session(session_type=session_type, source_name=source_name)
    scan = scan or python_fastapi_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid


def test_missing_session_returns_structured_error():
    result = MCPToolRegistry().call_tool("ahal_get_project_intelligence", {"session_id": "missing"})
    assert result["ok"] is False
    assert result["error_code"] == "SESSION_NOT_FOUND"


def test_unauthorized_session_returns_structured_error(monkeypatch):
    sid = _completed_session()
    original = config.scanner.require_session_token
    object.__setattr__(config.scanner, "require_session_token", True)
    try:
        result = MCPToolRegistry().call_tool("ahal_get_project_intelligence", {"session_id": sid})
        assert result["ok"] is False
        assert result["error_code"] == "UNAUTHORIZED"
    finally:
        object.__setattr__(config.scanner, "require_session_token", original)


def test_oversized_code_input_rejected():
    result = MCPToolRegistry().call_tool("ahal_analyze_code", {"code": "\x00bad"})
    assert result["ok"] is False
    assert result["error_code"] == "INVALID_REQUEST"


def test_tool_output_excludes_env_and_secrets():
    scan = make_scan_result(
        files=[{"path": "main.py", "extension": ".py"}, {"path": ".env", "extension": ""}],
        contents={
            "main.py": 'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/health")\ndef health(): return {"ok": True}\n',
            ".env": "GEMINI_API_KEY=abc123\n",
        },
    )
    sid = _completed_session(scan=scan)
    result = MCPToolRegistry().call_tool("ahal_get_project_intelligence", {"session_id": sid})
    assert result["ok"] is True
    payload = str(result["result"]).lower()
    assert ".env" not in payload
    assert "abc123" not in payload


def test_tool_output_excludes_raw_repr_and_magicmock():
    sid = _completed_session()
    result = MCPToolRegistry().call_tool("ahal_get_project_intelligence", {"session_id": sid})
    payload = str(result["result"]).lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
