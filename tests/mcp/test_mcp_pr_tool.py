from __future__ import annotations

from unittest.mock import patch

from app.mcp.tools import MCPToolRegistry


def test_mcp_pr_tool_works():
    result = MCPToolRegistry().call_tool(
        "ahal_analyze_pr",
        {
            "diff_text": """diff --git a/app/api/routes.py b/app/api/routes.py
--- a/app/api/routes.py
+++ b/app/api/routes.py
@@
-@router.get("/users")
+@router.post("/users")
""",
        },
    )
    assert result["ok"] is True
    assert result["result"]["changed_files"]


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_mcp_pr_tool_no_gemini_or_repr_leakage(mock_generate):
    result = MCPToolRegistry().call_tool(
        "ahal_analyze_pr",
        {"diff_text": "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@\n-old\n+new\n"},
    )
    assert result["ok"] is True
    payload = str(result["result"]).lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
    mock_generate.assert_not_called()
