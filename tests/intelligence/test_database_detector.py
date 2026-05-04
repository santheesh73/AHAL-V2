"""Tests for DatabaseDetector."""

from app.intelligence.detectors.database_detector import DatabaseDetector
from app.intelligence.detectors.dependency_detector import DependencyDetector
from app.intelligence.detectors.framework_detector import FrameworkDetector
from tests.intelligence.conftest import empty_scan_result, express_mongo_scan, make_scan_result, python_fastapi_scan


def _detect_dbs(scan):
    deps = DependencyDetector().detect(scan)
    fws = FrameworkDetector().detect(scan, dependencies=deps)
    return DatabaseDetector().detect(scan, dependencies=deps, frameworks=fws)


def test_mongodb_connection_string():
    scan = make_scan_result(
        files=[{"path": "db.py", "extension": ".py"}],
        contents={"db.py": 'MONGO_URL = "mongodb://localhost:27017/mydb"\n'},
    )
    dbs = DatabaseDetector().detect(scan)
    assert any(d.name == "MongoDB" for d in dbs)


def test_postgresql_dependency():
    dbs = _detect_dbs(python_fastapi_scan())
    assert any(d.name == "PostgreSQL" for d in dbs)


def test_sqlite_import():
    scan = make_scan_result(
        files=[{"path": "db.py", "extension": ".py"}],
        contents={"db.py": "import sqlite3\nconn = sqlite3.connect('app.db')\n"},
    )
    dbs = DatabaseDetector().detect(scan)
    assert any(d.name == "SQLite" for d in dbs)


def test_redis_connection_string():
    scan = make_scan_result(
        files=[{"path": "cache.py", "extension": ".py"}],
        contents={"cache.py": 'REDIS_URL = "redis://localhost:6379/0"\n'},
    )
    dbs = DatabaseDetector().detect(scan)
    assert any(d.name == "Redis" for d in dbs)


def test_no_db_returns_empty():
    scan = make_scan_result(
        files=[{"path": "readme.md"}],
        contents={"readme.md": "No database here.\n"},
    )
    dbs = DatabaseDetector().detect(scan)
    assert dbs == []


def test_mongodb_from_mongoose():
    dbs = _detect_dbs(express_mongo_scan())
    assert any(d.name == "MongoDB" for d in dbs)


def test_empty_scan():
    assert DatabaseDetector().detect(empty_scan_result()) == []


def test_every_db_has_evidence():
    for db in _detect_dbs(python_fastapi_scan()):
        assert len(db.evidence) > 0
