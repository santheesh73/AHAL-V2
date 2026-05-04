from __future__ import annotations

from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import python_fastapi_scan


def test_empty_request_rejected(client):
    response = client.post("/analyze/change-impact", json={"source_type": "diff"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"


def test_oversized_diff_rejected(client, monkeypatch):
    from app.config import config

    original = config.scanner.change_max_diff_chars
    object.__setattr__(config.scanner, "change_max_diff_chars", 10)
    try:
        response = client.post("/analyze/change-impact", json={"source_type": "diff", "diff_text": "x" * 20})
        assert response.status_code == 400
    finally:
        object.__setattr__(config.scanner, "change_max_diff_chars", original)


def test_standalone_diff_api_works(client):
    response = client.post(
        "/analyze/change-impact",
        json={
            "source_type": "diff",
            "diff_text": """diff --git a/app/api/routes.py b/app/api/routes.py
--- a/app/api/routes.py
+++ b/app/api/routes.py
@@
+@router.get("/users")
""",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["changed_files"]
    assert data["confidence"] in {"high", "medium", "low"}


def test_with_session_id_maps_to_known_modules(client):
    sid = session_manager.create_session(session_type="folder", source_name="project.zip")
    scan = python_fastapi_scan()
    scan.session_id = sid
    session_manager.set_result(sid, scan)
    response = client.post(
        "/analyze/change-impact",
        json={
            "session_id": sid,
            "source_type": "diff",
            "diff_text": """diff --git a/app/api/routes.py b/app/api/routes.py
--- a/app/api/routes.py
+++ b/app/api/routes.py
@@
+@router.get("/users")
""",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert any("api" in " ".join(item["affected_modules"]).lower() for item in payload["changed_files"])


def test_timeline_events_append_when_session_id_exists(client):
    sid = session_manager.create_session(session_type="folder", source_name="project.zip")
    scan = python_fastapi_scan()
    scan.session_id = sid
    session_manager.set_result(sid, scan)
    response = client.post(
        "/analyze/change-impact",
        json={
            "session_id": sid,
            "source_type": "files",
            "changed_files": [{"path": "README.md", "after": "docs", "status": "modified"}],
        },
    )
    assert response.status_code == 200
    timeline = client.get(f"/analyze/timeline/{sid}").json()
    stages = [event["stage"] for event in timeline["events"]]
    assert "change_impact_started" in stages
    assert "change_impact_completed" in stages


def test_no_gemini_required(client):
    response = client.post(
        "/analyze/change-impact",
        json={
            "source_type": "files",
            "include_llm": True,
            "changed_files": [{"path": "README.md", "after": "docs", "status": "modified"}],
        },
    )
    assert response.status_code == 200
    assert "deterministic" in " ".join(response.json()["warnings"]).lower()
