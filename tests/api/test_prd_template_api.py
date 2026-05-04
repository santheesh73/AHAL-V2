from __future__ import annotations

from app.models.file_schema import ScanStatus
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import python_fastapi_scan


def _completed_session():
    sid = session_manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    scan = python_fastapi_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid


def test_template_validation_endpoint_accepts_valid_template(client):
    response = client.post(
        "/analyze/prd/templates/validate",
        json={
            "name": "Engineering Handoff",
            "sections": [
                {"section_id": "overview", "title": "Overview", "source": "overview", "required": True, "render_as": "paragraph"},
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Engineering Handoff"


def test_template_validation_endpoint_rejects_invalid_source(client):
    response = client.post(
        "/analyze/prd/templates/validate",
        json={
            "name": "Bad",
            "sections": [
                {"section_id": "bad", "title": "Bad", "source": "filesystem", "required": True, "render_as": "paragraph"},
            ],
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"


def test_render_template_endpoint_returns_markdown(client):
    sid = _completed_session()
    response = client.post(
        f"/analyze/prd/{sid}/render-template",
        json={
            "name": "API Review",
            "sections": [
                {"section_id": "intro", "title": "Intro", "source": "custom_static", "required": True, "render_as": "paragraph", "static_text": "Team handoff only."},
                {"section_id": "apis", "title": "APIs", "source": "api_surface", "required": True, "render_as": "table"},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == sid
    assert "Team handoff only." in data["markdown"]
    assert "| Column 1 |" in data["markdown"]
