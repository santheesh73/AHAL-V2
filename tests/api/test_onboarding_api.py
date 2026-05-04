from __future__ import annotations

from unittest.mock import patch

from app.models.file_schema import ScanStatus
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import make_scan_result


def _completed_session(session_type="repo"):
    sid = session_manager.create_session(session_type=session_type, source_name="demo")
    scan = make_scan_result(
        files=[
            {"path": "README.md", "extension": ".md"},
            {"path": "app/main.py", "extension": ".py"},
            {"path": "app/api/routes.py", "extension": ".py"},
            {"path": "app/services/auth_service.py", "extension": ".py"},
            {"path": "app/models/user.py", "extension": ".py"},
            {"path": "docker-compose.yml", "extension": ".yml"},
            {"path": "tests/test_routes.py", "extension": ".py"},
            {"path": "node_modules/ignored.js", "extension": ".js"},
        ],
        contents={
            "README.md": "# AHAL Demo\n\nRepository intelligence backend.\n",
            "app/main.py": 'from fastapi import FastAPI\napp = FastAPI()\n@app.get("/health")\ndef health():\n    return {"ok": True}\n',
            "app/api/routes.py": 'from fastapi import APIRouter\nrouter = APIRouter()\n@router.get("/users")\ndef list_users():\n    return []\n',
            "app/services/auth_service.py": 'def validate_session(token: str) -> bool:\n    return bool(token)\n',
            "app/models/user.py": 'from pydantic import BaseModel\nclass User(BaseModel):\n    id: str\n',
            "docker-compose.yml": "services:\n  api:\n    build: .\n",
            "tests/test_routes.py": "def test_users():\n    assert True\n",
            "node_modules/ignored.js": "console.log('ignore');\n",
        },
    )
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    return sid


def test_invalid_audience_returns_400(client):
    sid = _completed_session()
    response = client.get(f"/analyze/onboard/{sid}?audience=mobile")
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"


def test_missing_session_returns_404(client):
    response = client.get("/analyze/onboard/missing")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "SESSION_NOT_FOUND"


def test_in_progress_session_returns_202(client):
    sid = session_manager.create_session(session_type="repo", source_name="demo")
    response = client.get(f"/analyze/onboard/{sid}")
    assert response.status_code == 202
    assert response.json()["detail"]["code"] == "SCAN_IN_PROGRESS"


def test_markdown_format_returns_text_markdown(client):
    sid = _completed_session()
    response = client.get(f"/analyze/onboard/{sid}?format=markdown")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert "# New Engineer Onboarding Guide" in response.text


@patch("app.intelligence.llm.gemini_client.GeminiClient.generate")
def test_onboarding_endpoint_returns_report_and_timeline(mock_generate, client):
    sid = _completed_session()
    response = client.get(f"/analyze/onboard/{sid}?audience=backend&time_budget_minutes=30")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == sid
    assert data["audience"] == "backend"
    assert data["reading_order"][0]["files_to_read"][0] == "README.md"
    assert any("/users" in item for item in data["important_apis"])
    assert "node_modules" not in response.text.lower()
    timeline = client.get(f"/analyze/timeline/{sid}").json()
    stages = [event["stage"] for event in timeline["events"]]
    assert "onboarding_started" in stages
    assert "onboarding_completed" in stages
    mock_generate.assert_not_called()


def test_unsupported_code_session_returns_400(client):
    response = client.post("/analyze/code", json={"code": "def run():\n    return 1\n"})
    sid = response.json()["session_id"]
    onboarding = client.get(f"/analyze/onboard/{sid}")
    assert onboarding.status_code == 400
    assert onboarding.json()["detail"]["code"] == "INVALID_REQUEST"
