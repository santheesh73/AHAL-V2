from __future__ import annotations

from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import python_fastapi_scan


def test_code_session_response_contract(client):
    response = client.post("/analyze/code", json={"filename": "demo.py", "code": "def run():\n    return 1\n"})
    assert response.status_code == 200
    data = response.json()
    assert set(["session_id", "session_type", "status", "progress", "message", "created_at", "updated_at"]).issubset(data.keys())
    assert data["session_type"] == "code"


def test_intelligence_schema_has_no_missing_keys(client):
    sid = session_manager.create_session(session_type="folder", source_name="project.zip")
    scan = python_fastapi_scan()
    scan.session_id = sid
    session_manager.set_result(sid, scan)
    data = client.get(f"/analyze/intelligence/{sid}").json()
    assert set(["session_id", "session_type", "status", "project_name", "project_goal", "architecture_style", "key_modules", "core_features", "risks", "summary", "technical", "evidence", "warnings", "confidence"]).issubset(data.keys())


def test_intelligence_schema_scan_in_progress_returns_202(client):
    sid = session_manager.create_session(session_type="folder", source_name="project.zip")
    response = client.get(f"/analyze/intelligence/{sid}")
    assert response.status_code == 202
    assert response.json()["detail"]["code"] == "SCAN_IN_PROGRESS"


def test_timeline_schema_contract(client):
    response = client.post("/analyze/code", json={"filename": "demo.py", "code": "def run():\n    return 1\n"})
    sid = response.json()["session_id"]
    timeline = client.get(f"/analyze/timeline/{sid}")
    assert timeline.status_code == 200
    data = timeline.json()
    assert data["session_id"] == sid
    assert isinstance(data["events"], list)
    assert {"timestamp", "stage", "status", "message", "metadata"}.issubset(data["events"][0].keys())


def test_missing_session_returns_404(client):
    response = client.get("/analyze/timeline/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_NOT_FOUND"


def test_invalid_code_returns_400(client):
    response = client.post("/analyze/code", json={"code": "\x00\x00bad"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"


def test_oversized_code_returns_400(client, monkeypatch):
    from app.config import config

    original = config.scanner.code_max_chars
    object.__setattr__(config.scanner, "code_max_chars", 10)
    try:
        response = client.post("/analyze/code", json={"code": "a" * 20})
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_REQUEST"
    finally:
        object.__setattr__(config.scanner, "code_max_chars", original)


def test_code_filename_sanitized(client):
    response = client.post("/analyze/code", json={"filename": "nested/path/demo.py", "code": "def run():\n    return 1\n"})
    assert response.status_code == 200
    sid = response.json()["session_id"]
    status = client.get(f"/analyze/status/{sid}")
    assert status.status_code == 200
    assert status.json()["source_name"] == "demo.py"


def test_no_none_values_in_intelligence_schema(client):
    response = client.post("/analyze/code", json={"code": "def run():\n    return 1\n"})
    data = client.get(f"/analyze/intelligence/{response.json()['session_id']}").json()

    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        else:
            assert value is not None

    walk(data)


def test_no_raw_repr_in_intelligence_schema(client):
    response = client.post("/analyze/code", json={"code": "def run():\n    return 1\n"})
    payload = client.get(f"/analyze/intelligence/{response.json()['session_id']}").text.lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
