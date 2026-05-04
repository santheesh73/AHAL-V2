from app.models.file_schema import ScanStatus
from app.sessions.session_manager import session_manager
from tests.intelligence.conftest import python_fastapi_scan


def test_graph_endpoint_returns_knowledge_graph(client):
    sid = session_manager.create_session()
    scan = python_fastapi_scan()
    scan.session_id = sid
    scan.status = ScanStatus.COMPLETED
    session_manager.set_result(sid, scan)

    response = client.get(f"/analyze/graph/{sid}")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == sid
    assert data["nodes"]
    assert data["edges"]
    assert data["stats"]["node_count"] == len(data["nodes"])

