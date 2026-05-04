"""Tests for APIDetector."""

from app.intelligence.detectors.api_detector import APIDetector
from tests.intelligence.conftest import empty_scan_result, express_mongo_scan, make_scan_result, python_fastapi_scan


def test_fastapi_app_get():
    scan = python_fastapi_scan()
    detector = APIDetector()
    apis = detector.detect(scan)
    get_apis = [a for a in apis if a.method == "GET"]
    assert len(get_apis) >= 1
    assert any(a.path == "/health" for a in get_apis)


def test_fastapi_router_post():
    scan = python_fastapi_scan()
    detector = APIDetector()
    apis = detector.detect(scan)
    post_apis = [a for a in apis if a.method == "POST"]
    assert any(a.path == "/users" for a in post_apis)


def test_flask_app_route():
    scan = make_scan_result(
        files=[{"path": "app.py", "extension": ".py"}],
        contents={
            "app.py": 'from flask import Flask\napp = Flask(__name__)\n\n@app.route("/hello", methods=["GET", "POST"])\ndef hello():\n    return "hi"\n',
        },
    )
    apis = APIDetector().detect(scan)
    assert any(a.framework == "Flask" for a in apis)
    methods = [a.method for a in apis if a.path == "/hello"]
    assert "GET" in methods


def test_express_app_post():
    scan = express_mongo_scan()
    detector = APIDetector()
    apis = detector.detect(scan)
    express_apis = [a for a in apis if a.framework == "Express"]
    assert len(express_apis) >= 1


def test_django_path():
    scan = make_scan_result(
        files=[{"path": "urls.py", "extension": ".py"}],
        contents={
            "urls.py": 'from django.urls import path\n\nurlpatterns = [\n    path("api/users/", views.user_list),\n    path("api/items/", views.item_list),\n]\n',
        },
    )
    apis = APIDetector().detect(scan)
    assert len(apis) >= 2
    assert all(a.framework == "Django" for a in apis)


def test_no_fake_endpoint_from_random_text():
    scan = make_scan_result(
        files=[{"path": "readme.md"}],
        contents={"readme.md": "This project uses GET requests to fetch data.\nPOST to /submit.\n"},
    )
    apis = APIDetector().detect(scan)
    assert len(apis) == 0


def test_every_endpoint_has_evidence():
    scan = python_fastapi_scan()
    for api in APIDetector().detect(scan):
        assert len(api.evidence) > 0
        assert api.file
        assert api.method
        assert api.path


def test_empty_scan():
    assert APIDetector().detect(empty_scan_result()) == []
