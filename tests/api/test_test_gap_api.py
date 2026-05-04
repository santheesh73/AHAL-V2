from __future__ import annotations

from app.models.file_schema import ScanStatus
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


def test_in_progress_session_returns_202(client):
    sid = session_manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    response = client.get(f"/analyze/testgap/{sid}")
    assert response.status_code == 202
    assert response.json()["detail"]["code"] == "SCAN_IN_PROGRESS"


def test_missing_session_returns_404(client):
    response = client.get("/analyze/testgap/missing")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_NOT_FOUND"


def test_test_gap_endpoint_returns_report_and_timeline(client):
    sid = _completed_repo_session()
    response = client.get(f"/analyze/testgap/{sid}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == sid
    assert "gaps" in data
    timeline = client.get(f"/analyze/timeline/{sid}").json()
    stages = [event["stage"] for event in timeline["events"]]
    assert "test_gap_started" in stages
    assert "test_gap_completed" in stages


def test_unsupported_code_session_returns_400(client):
    response = client.post("/analyze/code", json={"code": "def run():\n    return 1\n"})
    sid = response.json()["session_id"]
    gap = client.get(f"/analyze/testgap/{sid}")
    assert gap.status_code == 400
    assert gap.json()["detail"]["code"] == "INVALID_REQUEST"
