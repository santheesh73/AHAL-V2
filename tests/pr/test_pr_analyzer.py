from __future__ import annotations

from unittest.mock import patch

from app.models.file_schema import ScanStatus
from app.pr import PullRequestAnalysisRequest, PullRequestAnalyzer
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import make_scan_result


def _session_scan():
    return make_scan_result(
        files=[
            {"path": "app/main.py", "extension": ".py"},
            {"path": "app/api/routes.py", "extension": ".py"},
            {"path": "app/services/auth.py", "extension": ".py"},
            {"path": "app/models/user.py", "extension": ".py"},
            {"path": "tests/test_routes.py", "extension": ".py"},
        ],
        contents={
            "app/main.py": 'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/health")\ndef health():\n    return {"ok": True}\n',
            "app/api/routes.py": 'from fastapi import APIRouter\nrouter = APIRouter()\n@router.get("/users")\ndef list_users():\n    return []\n@router.post("/users")\ndef create_user():\n    return {}\n',
            "app/services/auth.py": "def validate_session(token):\n    return bool(token)\n",
            "app/models/user.py": "class User: pass\n",
            "tests/test_routes.py": "def test_users():\n    assert True\n",
        },
    )


def _completed_session():
    sid = session_manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    scan = _session_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid, scan


def test_standalone_pr_diff_works():
    diff_text = """diff --git a/app/services/order_service.py b/app/services/order_service.py
--- a/app/services/order_service.py
+++ b/app/services/order_service.py
@@
-def total():
+def total_with_tax():
"""
    result = PullRequestAnalyzer().analyze(PullRequestAnalysisRequest(diff_text=diff_text, title="Service change"))
    assert result.pr_title == "Service change"
    assert result.changed_files
    assert result.summary


def test_api_removal_becomes_high_risk():
    diff_text = """diff --git a/app/api/routes.py b/app/api/routes.py
deleted file mode 100644
--- a/app/api/routes.py
+++ /dev/null
@@
-@router.get("/users")
-def list_users():
-    return []
"""
    result = PullRequestAnalyzer().analyze(PullRequestAnalysisRequest(diff_text=diff_text))
    assert result.risk_level == "high"
    assert result.breaking_change_risk == "high"


def test_database_change_becomes_high_risk():
    diff_text = """diff --git a/app/models/user.py b/app/models/user.py
--- a/app/models/user.py
+++ b/app/models/user.py
@@
-class User:
+class User:
+    email = None
"""
    result = PullRequestAnalyzer().analyze(PullRequestAnalysisRequest(diff_text=diff_text))
    assert result.risk_level == "high"


def test_docs_only_change_is_low_risk():
    diff_text = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@
-Old text
+New documentation text
"""
    result = PullRequestAnalyzer().analyze(PullRequestAnalysisRequest(diff_text=diff_text))
    assert result.risk_level == "low"


def test_suggested_tests_and_reviewer_focus_are_generated():
    sid, scan = _completed_session()
    diff_text = """diff --git a/app/api/routes.py b/app/api/routes.py
--- a/app/api/routes.py
+++ b/app/api/routes.py
@@
-@router.get("/users")
+@router.post("/users")
"""
    result = PullRequestAnalyzer().analyze(
        PullRequestAnalysisRequest(session_id=sid, diff_text=diff_text),
        scan_result=scan,
    )
    assert result.suggested_tests
    assert result.reviewer_focus


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_no_gemini_required_and_no_raw_repr_leakage(mock_generate):
    diff_text = """diff --git a/docs/README.md b/docs/README.md
--- a/docs/README.md
+++ b/docs/README.md
@@
-A
+B
"""
    result = PullRequestAnalyzer().analyze(PullRequestAnalysisRequest(diff_text=diff_text))
    payload = str(result.model_dump()).lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
    mock_generate.assert_not_called()
