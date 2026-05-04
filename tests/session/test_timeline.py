from __future__ import annotations

from app.models.file_schema import ScanStatus
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import python_fastapi_scan


def test_timeline_events_created():
    sid = session_manager.create_session(session_type="code", source_name="snippet.py")
    events = session_manager.get_timeline(sid)
    assert events
    assert events[0].stage == "session_created"


def test_events_append_in_order():
    sid = session_manager.create_session(session_type="folder", source_name="demo.zip")
    session_manager.append_timeline_event(sid, "upload_received", "pending", "Upload received")
    session_manager.append_timeline_event(sid, "scan_started", "scanning", "Scan started")
    events = session_manager.get_timeline(sid)
    assert [item.stage for item in events][-2:] == ["upload_received", "scan_started"]


def test_failed_event_recorded():
    sid = session_manager.create_session(session_type="repo", source_name="https://github.com/example/repo")
    session_manager.set_failed(sid, "Clone failed")
    events = session_manager.get_timeline(sid)
    assert events[-1].stage == "failed"


def test_timeline_endpoint_returns_events(client):
    sid = session_manager.create_session(session_type="folder", source_name="demo.zip")
    scan = python_fastapi_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)
    response = client.get(f"/analyze/timeline/{sid}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == sid
    assert data["events"]
