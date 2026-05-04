from __future__ import annotations

from unittest.mock import patch

from app.models.file_schema import ScanStatus
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import make_scan_result


def _completed_session():
    sid = session_manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    scan = make_scan_result(
        files=[{"path": "app/api/routes.py", "extension": ".py"}],
        contents={"app/api/routes.py": 'from fastapi import APIRouter\nrouter = APIRouter()\n@router.get("/users")\ndef users():\n    return []\n'},
    )
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid


def test_missing_input_returns_400(client):
    response = client.post("/analyze/pr", json={})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_pr_analysis_endpoint_works_and_timeline_updates(mock_generate, client):
    sid = _completed_session()
    payload = {
        "session_id": sid,
        "diff_text": """diff --git a/app/api/routes.py b/app/api/routes.py
--- a/app/api/routes.py
+++ b/app/api/routes.py
@@
-@router.get("/users")
+@router.post("/users")
""",
    }
    response = client.post("/analyze/pr", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == sid
    assert data["reviewer_focus"]
    timeline = client.get(f"/analyze/timeline/{sid}").json()
    stages = [event["stage"] for event in timeline["events"]]
    assert "pr_analysis_started" in stages
    assert "pr_analysis_completed" in stages
    mock_generate.assert_not_called()
