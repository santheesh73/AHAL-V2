from app.config import config
from app.models.file_schema import ScanResult, ScanStatus
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import python_fastapi_scan


def test_post_chat_returns_chat_answer(client):
    sid = session_manager.create_session()
    scan = python_fastapi_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)

    response = client.post(
        f"/analyze/chat/{sid}",
        json={"question": "Which API endpoints exist?", "include_history": True, "max_context_items": 20},
    )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "confidence" in data
    assert "evidence" in data
    assert "insufficient_context" in data


def test_chat_token_auth_preserved(client):
    original = config.scanner.require_session_token
    object.__setattr__(config.scanner, "require_session_token", True)
    try:
        sid = session_manager.create_session()
        token = session_manager.get_access_token(sid)
        scan = python_fastapi_scan()
        scan.session_id = sid
        scan.status = ScanStatus.COMPLETED
        session_manager.set_result(sid, scan)

        unauthorized = client.post(
            f"/analyze/chat/{sid}",
            json={"question": "Which API endpoints exist?"},
        )
        assert unauthorized.status_code == 401
        assert unauthorized.json()["detail"]["code"] == "UNAUTHORIZED"

        authorized = client.post(
            f"/analyze/chat/{sid}",
            headers={"X-Session-Token": token},
            json={"question": "Which API endpoints exist?"},
        )
        assert authorized.status_code == 200
    finally:
        object.__setattr__(config.scanner, "require_session_token", original)


def test_chat_scan_in_progress_returns_structured_error(client):
    sid = session_manager.create_session()

    response = client.post(
        f"/analyze/chat/{sid}",
        json={"question": "Which API endpoints exist?"},
    )

    assert response.status_code == 202
    assert response.json()["detail"]["code"] == "SCAN_IN_PROGRESS"
