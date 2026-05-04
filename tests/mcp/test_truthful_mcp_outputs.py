from app.mcp.tools import MCPToolRegistry
from app.sessions.session_manager import session_manager
from app.models.file_schema import ScanStatus
from tests.intelligence.conftest import make_scan_result


def _completed_session(scan):
    sid = session_manager.create_session(session_type="folder", source_name="frontend")
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid


def test_mcp_outputs_are_sanitized_and_do_not_return_env_paths():
    scan = make_scan_result(
        files=[{"path": "README.md", "extension": ".md"}, {"path": ".env", "extension": ""}],
        contents={
            "README.md": "# FactShield\n\nAI hallucination detection backend.\n",
            ".env": "OPENAI_API_KEY=secret",
        },
    )
    sid = _completed_session(scan)
    result = MCPToolRegistry().call_tool("ahal_get_project_intelligence", {"session_id": sid})
    assert result["ok"] is True
    text = str(result["result"]).lower()
    assert ".env" not in text
    assert "secret" not in text


def test_mcp_does_not_return_wrong_high_confidence_domain():
    scan = make_scan_result(
        files=[{"path": "main.py", "extension": ".py"}],
        contents={"main.py": 'from fastapi import FastAPI\napp = FastAPI()\n@app.post("/analyze")\ndef analyze(): pass\n'},
    )
    sid = _completed_session(scan)
    result = MCPToolRegistry().call_tool("ahal_get_project_intelligence", {"session_id": sid})
    assert result["ok"] is True
    payload = str(result["result"]).lower()
    assert "repository intelligence platform" not in payload


def test_mcp_frontend_project_not_repo_intelligence():
    scan = make_scan_result(
        files=[
            {"path": "package.json", "extension": ".json"},
            {"path": "src/pages/DashboardPage.tsx", "extension": ".tsx"},
        ],
        contents={
            "package.json": '{"name":"nisf-frontend","dependencies":{"react":"18.2.0","vite":"5.0.0"}}',
            "src/pages/DashboardPage.tsx": "export default function DashboardPage() { return null }",
        },
    )
    sid = _completed_session(scan)
    result = MCPToolRegistry().call_tool("ahal_get_project_intelligence", {"session_id": sid})
    assert result["ok"] is True
    payload = str(result["result"]).lower()
    assert "repository intelligence" not in payload
    assert "frontend application" in payload or "frontend" in payload
