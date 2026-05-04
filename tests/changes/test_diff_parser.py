from __future__ import annotations

from app.changes.change_impact_analyzer import ChangeImpactAnalyzer


def test_unified_diff_parses_changed_files():
    diff_text = """diff --git a/app/api/routes.py b/app/api/routes.py
--- a/app/api/routes.py
+++ b/app/api/routes.py
@@
-@router.get("/health")
+@router.get("/status")
"""
    parsed = ChangeImpactAnalyzer().parse_unified_diff(diff_text)
    assert len(parsed) == 1
    assert parsed[0].path == "app/api/routes.py"
    assert parsed[0].status == "modified"
