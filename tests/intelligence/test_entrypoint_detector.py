"""Tests for EntryPointDetector."""

from app.intelligence.detectors.entrypoint_detector import EntryPointDetector
from app.intelligence.detectors.framework_detector import FrameworkDetector
from app.intelligence.detectors.dependency_detector import DependencyDetector
from tests.intelligence.conftest import (
    empty_scan_result,
    make_scan_result,
    python_fastapi_scan,
    react_nextjs_scan,
)


def _detect_eps(scan):
    deps = DependencyDetector().detect(scan)
    fws = FrameworkDetector().detect(scan, dependencies=deps)
    return EntryPointDetector().detect(scan, frameworks=fws)


def test_main_py_backend_entrypoint():
    eps = _detect_eps(python_fastapi_scan())
    backend_eps = [e for e in eps if e.type == "backend"]
    files = [e.file for e in backend_eps]
    assert "main.py" in files


def test_app_py_backend_entrypoint():
    scan = make_scan_result(
        files=[{"path": "app.py", "extension": ".py"}],
        contents={"app.py": "from flask import Flask\napp = Flask(__name__)\n"},
    )
    fws = FrameworkDetector().detect(scan)
    eps = EntryPointDetector().detect(scan, frameworks=fws)
    assert any(e.file == "app.py" and e.type == "backend" for e in eps)


def test_src_main_tsx_frontend_entrypoint():
    scan = make_scan_result(
        files=[
            {"path": "src/main.tsx", "extension": ".tsx"},
            {"path": "package.json", "extension": ".json"},
        ],
        contents={
            "src/main.tsx": 'import React from "react";\n',
            "package.json": '{"dependencies":{"react":"18.0.0"}}',
        },
    )
    deps = DependencyDetector().detect(scan)
    fws = FrameworkDetector().detect(scan, dependencies=deps)
    eps = EntryPointDetector().detect(scan, frameworks=fws)
    frontend = [e for e in eps if e.type == "frontend"]
    assert any(e.file == "src/main.tsx" for e in frontend)


def test_src_index_jsx_frontend_entrypoint():
    scan = make_scan_result(
        files=[{"path": "src/index.jsx", "extension": ".jsx"}],
        contents={"src/index.jsx": "import React from 'react';\n"},
    )
    eps = EntryPointDetector().detect(scan)
    assert any(e.file == "src/index.jsx" and e.type == "frontend" for e in eps)


def test_package_json_scripts_as_config_entrypoint():
    scan = make_scan_result(
        files=[{"path": "package.json", "extension": ".json"}],
        contents={"package.json": '{"scripts":{"start":"node server.js","dev":"next dev"}}'},
    )
    eps = EntryPointDetector().detect(scan)
    config_eps = [e for e in eps if e.type == "config"]
    assert len(config_eps) >= 1


def test_dedupe_entrypoints():
    """Same file should not appear as multiple entrypoints of the same type."""
    scan = make_scan_result(
        files=[{"path": "main.py", "extension": ".py"}],
        contents={"main.py": "from fastapi import FastAPI\napp = FastAPI()\n"},
    )
    eps = _detect_eps(scan)
    main_eps = [(e.file, e.type) for e in eps if e.file == "main.py"]
    assert len(main_eps) == len(set(main_eps)), "Duplicate entrypoints found"


def test_empty_scan():
    assert EntryPointDetector().detect(empty_scan_result()) == []


def test_every_entrypoint_has_evidence():
    for ep in _detect_eps(python_fastapi_scan()):
        assert len(ep.evidence) > 0
