from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.models.file_schema import ScanStatus
from app.mcp.server import MCPServer
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import python_fastapi_scan


def _completed_session():
    sid = session_manager.create_session(session_type="folder", source_name="project.zip")
    scan = python_fastapi_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid


def test_server_json_rpc_initialize_list_tools_call_tool_flow_works():
    server = MCPServer()
    init = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init["result"]["server"] == "AHAL MCP"

    listed = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "list_tools"})
    assert any(item["name"] == "ahal_analyze_code" for item in listed["result"]["tools"])

    called = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "call_tool",
            "params": {
                "name": "ahal_analyze_code",
                "arguments": {"code": "def run():\n    return 1\n", "filename": "demo.py"},
            },
        }
    )
    assert called["result"]["ok"] is True
    assert called["result"]["result"]["language"] == "python"


def test_python_module_entrypoint_starts_and_handles_stdio():
    repo_root = Path(__file__).resolve().parents[2]
    process = subprocess.Popen(
        [sys.executable, "-m", "app.mcp.server"],
        cwd=str(repo_root),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\n")
        process.stdin.flush()
        init = json.loads(process.stdout.readline())
        assert init["result"]["server"] == "AHAL MCP"

        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "list_tools"}) + "\n")
        process.stdin.flush()
        listed = json.loads(process.stdout.readline())
        assert any(item["name"] == "ahal_get_project_intelligence" for item in listed["result"]["tools"])

        process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 3, "method": "shutdown"}) + "\n")
        process.stdin.flush()
        shutdown = json.loads(process.stdout.readline())
        assert shutdown["result"]["shutdown"] is True
    finally:
        process.kill()
        process.wait(timeout=5)
