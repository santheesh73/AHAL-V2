from __future__ import annotations

import json
import sys
from typing import Any

from app.mcp.tools import MCPToolRegistry


class MCPServer:
    def __init__(self, registry: MCPToolRegistry | None = None) -> None:
        self._registry = registry or MCPToolRegistry()

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {}) or {}
        if method == "initialize":
            return self._response(request_id, {"server": "AHAL MCP", "version": "1.0", "capabilities": {"tools": True}})
        if method in {"list_tools", "tools/list"}:
            return self._response(request_id, {"tools": self._registry.list_tools()})
        if method in {"call_tool", "tools/call"}:
            name = params.get("name") or params.get("tool")
            arguments = params.get("arguments") or {}
            return self._response(request_id, self._registry.call_tool(str(name or ""), arguments))
        if method == "shutdown":
            return self._response(request_id, {"ok": True, "shutdown": True})
        return self._response(request_id, {"ok": False, "error_code": "INVALID_REQUEST", "message": f"Unsupported MCP method: {method}"})

    def serve_stdio(self) -> int:
        for line in sys.stdin:
            text = line.strip()
            if not text:
                continue
            try:
                request = json.loads(text)
            except json.JSONDecodeError:
                response = self._response(None, {"ok": False, "error_code": "INVALID_REQUEST", "message": "Invalid JSON request."})
            else:
                response = self.handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            if response.get("result", {}).get("shutdown") is True:
                return 0
        return 0

    def _response(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> int:
    return MCPServer().serve_stdio()


if __name__ == "__main__":
    raise SystemExit(main())
