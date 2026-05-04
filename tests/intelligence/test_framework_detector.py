"""Tests for FrameworkDetector."""

from app.intelligence.detectors.dependency_detector import DependencyDetector
from app.intelligence.detectors.framework_detector import FrameworkDetector
from tests.intelligence.conftest import (
    empty_scan_result,
    express_mongo_scan,
    make_scan_result,
    python_fastapi_scan,
    react_nextjs_scan,
)


def _detect_with_deps(scan):
    """Run dependency detection first, then framework detection."""
    deps = DependencyDetector().detect(scan)
    return FrameworkDetector().detect(scan, dependencies=deps)


def test_react_from_package_json():
    fws = _detect_with_deps(react_nextjs_scan())
    names = [f.name for f in fws]
    assert "React" in names


def test_nextjs_from_dependency_and_config():
    fws = _detect_with_deps(react_nextjs_scan())
    names = [f.name for f in fws]
    assert "Next.js" in names


def test_fastapi_from_import():
    fws = _detect_with_deps(python_fastapi_scan())
    names = [f.name for f in fws]
    assert "FastAPI" in names


def test_flask_from_import():
    scan = make_scan_result(
        files=[{"path": "app.py", "extension": ".py"}],
        contents={"app.py": "from flask import Flask\napp = Flask(__name__)\n"},
    )
    fws = FrameworkDetector().detect(scan)
    names = [f.name for f in fws]
    assert "Flask" in names


def test_express_from_dependency_and_import():
    fws = _detect_with_deps(express_mongo_scan())
    names = [f.name for f in fws]
    assert "Express" in names


def test_mongodb_from_mongoose():
    fws = _detect_with_deps(express_mongo_scan())
    names = [f.name for f in fws]
    assert "MongoDB" in names or "Mongoose" in names


def test_sqlalchemy_from_import():
    scan = make_scan_result(
        files=[{"path": "db.py", "extension": ".py"}],
        contents={"db.py": "from sqlalchemy import create_engine\nengine = create_engine('sqlite:///test.db')\n"},
    )
    fws = FrameworkDetector().detect(scan)
    names = [f.name for f in fws]
    assert "SQLAlchemy" in names


def test_no_framework_returns_empty():
    scan = make_scan_result(
        files=[{"path": "readme.md"}],
        contents={"readme.md": "# My Project\nJust a readme.\n"},
    )
    fws = FrameworkDetector().detect(scan)
    assert fws == []


def test_every_framework_has_evidence():
    fws = _detect_with_deps(python_fastapi_scan())
    for fw in fws:
        assert len(fw.evidence) > 0, f"Framework {fw.name} has no evidence"
        for e in fw.evidence:
            assert e.reason


def test_duplicate_signals_merge_into_one():
    """Multiple FastAPI imports should not produce duplicate frameworks."""
    scan = make_scan_result(
        files=[
            {"path": "app.py", "extension": ".py"},
            {"path": "routes.py", "extension": ".py"},
        ],
        contents={
            "app.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "routes.py": "from fastapi import APIRouter\nrouter = APIRouter()\n",
        },
    )
    fws = FrameworkDetector().detect(scan)
    fastapi_fws = [f for f in fws if f.name == "FastAPI"]
    assert len(fastapi_fws) == 1
    # But should have merged evidence from both files
    assert len(fastapi_fws[0].evidence) >= 2


def test_empty_scan():
    assert FrameworkDetector().detect(empty_scan_result()) == []
