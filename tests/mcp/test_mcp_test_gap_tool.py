from __future__ import annotations

from app.models.file_schema import ScanStatus
from app.mcp.tools import MCPToolRegistry
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import make_scan_result


def _completed_repo_session():
    sid = session_manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    scan = make_scan_result(
        files=[{"path": "app/api/analyze.py", "extension": ".py"}],
        contents={"app/api/analyze.py": 'from fastapi import APIRouter\nrouter = APIRouter()\n@router.post("/analyze/code")\ndef analyze_code():\n    return {"ok": True}\n'},
    )
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid


def test_mcp_test_gap_tool_works():
    sid = _completed_repo_session()
    result = MCPToolRegistry().call_tool(
        "ahal_detect_test_gaps",
        {"session_id": sid, "include_low_priority": False},
    )
    assert result["ok"] is True
    assert result["result"]["session_id"] == sid
    assert "gaps" in result["result"]


def test_no_gemini_required_and_no_raw_repr_leakage():
    sid = _completed_repo_session()
    result = MCPToolRegistry().call_tool("ahal_detect_test_gaps", {"session_id": sid})
    assert result["ok"] is True
    payload = str(result["result"]).lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
