from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import make_scan_result, python_fastapi_scan

client = TestClient(app)


def _complete_session(scan=None):
    sid = session_manager.create_session(session_type="folder", source_name="project.zip")
    scan = scan or python_fastapi_scan()
    scan.session_id = sid
    session_manager.set_result(sid, scan)
    return sid


def test_missing_base_session_returns_404():
    sid = _complete_session()
    response = client.get(f"/analyze/prd/missing_base/diff/{sid}")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_NOT_FOUND"


def test_missing_target_session_returns_404():
    sid = _complete_session()
    response = client.get(f"/analyze/prd/{sid}/diff/missing_target")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_NOT_FOUND"


def test_in_progress_session_returns_202():
    base_sid = _complete_session()
    target_sid = session_manager.create_session(session_type="folder", source_name="pending.zip")
    response = client.get(f"/analyze/prd/{base_sid}/diff/{target_sid}")
    assert response.status_code == 202
    assert response.json()["detail"]["code"] == "SCAN_IN_PROGRESS"


def test_same_session_id_returns_400():
    sid = _complete_session()
    response = client.get(f"/analyze/prd/{sid}/diff/{sid}")
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"


def test_markdown_format_returns_text_markdown():
    base_sid = _complete_session()
    target_sid = _complete_session()
    response = client.get(f"/analyze/prd/{base_sid}/diff/{target_sid}?format=markdown")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "# PRD Architecture Diff" in response.text


def test_no_gemini_required():
    base_sid = _complete_session()
    target_sid = _complete_session()
    response = client.get(f"/analyze/prd/{base_sid}/diff/{target_sid}?include_llm_polish=true")
    assert response.status_code == 200
    assert "deterministic diff" in " ".join(response.json()["warnings"]).lower()


def test_timeline_appended_for_target_session():
    base_sid = _complete_session()
    target_sid = _complete_session()
    response = client.get(f"/analyze/prd/{base_sid}/diff/{target_sid}")
    assert response.status_code == 200
    timeline = client.get(f"/analyze/timeline/{target_sid}").json()
    stages = [event["stage"] for event in timeline["events"]]
    assert "prd_diff_started" in stages
    assert "prd_diff_completed" in stages


def test_added_api_endpoint_detected():
    base = make_scan_result(
        files=[{"path": "main.py", "extension": ".py"}],
        contents={"main.py": 'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/health")\ndef health(): pass\n'},
    )
    target = make_scan_result(
        files=[{"path": "main.py", "extension": ".py"}],
        contents={"main.py": 'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/health")\ndef health(): pass\n@app.post("/users")\ndef create_user(): pass\n'},
    )
    base_sid = _complete_session(base)
    target_sid = _complete_session(target)
    response = client.get(f"/analyze/prd/{base_sid}/diff/{target_sid}")
    assert response.status_code == 200
    data = response.json()
    assert any(item["path"] == "/users" and item["change_type"] == "added" for item in data["api_diff"])


def test_no_raw_repr_leakage():
    base_sid = _complete_session()
    target_sid = _complete_session()
    payload = client.get(f"/analyze/prd/{base_sid}/diff/{target_sid}").text.lower()
    assert "magicmock" not in payload
    assert "type='" not in payload
