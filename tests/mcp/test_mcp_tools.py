from __future__ import annotations

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


def test_tool_registry_lists_all_tools():
    registry = MCPToolRegistry()
    names = {item["name"] for item in registry.list_tools()}
    assert {
        "ahal_analyze_code",
        "ahal_get_project_intelligence",
        "ahal_ask_repo",
        "ahal_generate_prd",
        "ahal_diff_prd",
        "ahal_create_repo_index",
        "ahal_delta_scan",
    }.issubset(names)


def test_analyze_code_tool_works_without_gemini():
    result = MCPToolRegistry().call_tool(
        "ahal_analyze_code",
        {"code": "def run():\n    return 1\n", "filename": "demo.py"},
    )
    assert result["ok"] is True
    assert result["result"]["language"] == "python"
    assert "summary" in result["result"]


def test_get_project_intelligence_returns_stable_schema():
    sid = _completed_session()
    result = MCPToolRegistry().call_tool("ahal_get_project_intelligence", {"session_id": sid})
    assert result["ok"] is True
    data = result["result"]
    assert data["session_id"] == sid
    assert {"project_goal", "architecture_style", "summary", "technical", "warnings", "confidence"}.issubset(data.keys())


def test_ask_repo_returns_answer_with_evidence():
    sid = _completed_session()
    result = MCPToolRegistry().call_tool(
        "ahal_ask_repo",
        {"session_id": sid, "question": "What does this project do?"},
    )
    assert result["ok"] is True
    data = result["result"]
    assert data["answer"]
    assert isinstance(data["evidence"], list)


def test_generate_prd_json_works():
    sid = _completed_session()
    result = MCPToolRegistry().call_tool("ahal_generate_prd", {"session_id": sid, "format": "json"})
    assert result["ok"] is True
    assert result["result"]["title"]
    assert "overview" in result["result"]


def test_generate_prd_markdown_works():
    sid = _completed_session()
    result = MCPToolRegistry().call_tool("ahal_generate_prd", {"session_id": sid, "format": "markdown"})
    assert result["ok"] is True
    assert "# " in result["result"] or "## " in result["result"]


def test_diff_prd_works():
    base = _completed_session()
    target_scan = make_scan_result(
        files=[{"path": "main.py", "extension": ".py"}],
        contents={"main.py": 'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/health")\ndef health(): pass\n@app.post("/users")\ndef create_user(): pass\n'},
    )
    target = _completed_session(scan=target_scan)
    result = MCPToolRegistry().call_tool(
        "ahal_diff_prd",
        {"base_session_id": base, "target_session_id": target, "format": "json"},
    )
    assert result["ok"] is True
    assert any(item["path"] == "/users" for item in result["result"]["api_diff"])


def test_create_repo_index_works():
    sid = _completed_session(session_type="repo", source_name="https://github.com/example/repo")
    result = MCPToolRegistry().call_tool("ahal_create_repo_index", {"session_id": sid})
    assert result["ok"] is True
    assert result["result"]["session_id"] == sid
    assert result["result"]["source_type"] == "repo"


def test_delta_scan_works():
    sid = _completed_session(session_type="repo", source_name="https://github.com/example/repo")
    index = MCPToolRegistry().call_tool("ahal_create_repo_index", {"session_id": sid})
    result = MCPToolRegistry().call_tool(
        "ahal_delta_scan",
        {
            "index_id": index["result"]["index_id"],
            "changed_files": [{"path": "app/new_service.py", "content": "def run(): pass", "status": "added"}],
        },
    )
    assert result["ok"] is True
    assert "app/new_service.py" in result["result"]["added_files"]
