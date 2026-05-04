from __future__ import annotations

from app.config import config
from app.models.file_schema import ScanStatus
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import python_fastapi_scan


def _completed_session(session_type="repo", source_name="https://github.com/example/repo", scan=None):
    sid = session_manager.create_session(session_type=session_type, source_name=source_name)
    scan = scan or python_fastapi_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid


def test_create_index_from_completed_repo_session(client):
    sid = _completed_session()
    response = client.post(f"/analyze/index/{sid}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == sid
    assert data["source_type"] == "repo"


def test_missing_session_returns_404(client):
    response = client.post("/analyze/index/missing-session")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_NOT_FOUND"


def test_in_progress_session_returns_202(client):
    sid = session_manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    response = client.post(f"/analyze/index/{sid}")
    assert response.status_code == 202
    assert response.json()["detail"]["code"] == "SCAN_IN_PROGRESS"


def test_code_session_cannot_create_repo_index(client):
    response = client.post("/analyze/code", json={"code": "def run():\n    return 1\n"})
    sid = response.json()["session_id"]
    index_response = client.post(f"/analyze/index/{sid}")
    assert index_response.status_code == 400
    assert index_response.json()["detail"]["code"] == "INVALID_REQUEST"


def test_delta_scan_appends_timeline_events(client):
    sid = _completed_session()
    index_id = client.post(f"/analyze/index/{sid}").json()["index_id"]
    response = client.post(
        f"/analyze/index/{index_id}/delta",
        json={"index_id": index_id, "changed_files": [{"path": "app/new_service.py", "content": "def run(): pass", "status": "added"}]},
    )
    assert response.status_code == 200
    timeline = client.get(f"/analyze/timeline/{sid}").json()
    stages = [event["stage"] for event in timeline["events"]]
    assert "delta_scan_started" in stages
    assert "delta_scan_completed" in stages


def test_index_history_returns_previous_scans(client):
    sid = _completed_session()
    index_id = client.post(f"/analyze/index/{sid}").json()["index_id"]
    client.post(
        f"/analyze/index/{index_id}/delta",
        json={"index_id": index_id, "changed_files": [{"path": "app/new_service.py", "content": "def run(): pass", "status": "added"}]},
    )
    history = client.get(f"/analyze/index/{index_id}/history")
    assert history.status_code == 200
    payload = history.json()
    assert payload["history"]
    assert any(item["type"] == "delta_scan" for item in payload["history"])


def test_no_mongodb_required(client):
    sid = _completed_session(session_type="folder", source_name="project.zip")
    response = client.post(f"/analyze/index/{sid}")
    assert config.scanner.storage_backend == "memory"
    assert response.status_code == 200
