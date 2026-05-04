from __future__ import annotations

import pytest

from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.conftest import fullstack_scan, make_scan_result, python_fastapi_scan, react_nextjs_scan


@pytest.fixture
def fastapi_scan():
    return python_fastapi_scan()


@pytest.fixture
def fastapi_intelligence(fastapi_scan):
    return IntelligenceEngine().analyze(fastapi_scan)


@pytest.fixture
def fullstack_graph_inputs():
    scan = fullstack_scan()
    return scan, IntelligenceEngine().analyze(scan)


@pytest.fixture
def js_relative_scan():
    return make_scan_result(
        files=[
            {"path": "src/App.tsx", "extension": ".tsx"},
            {"path": "src/components/Header.tsx", "extension": ".tsx"},
            {"path": "package.json", "extension": ".json"},
        ],
        contents={
            "src/App.tsx": 'import React from "react";\nimport { Header } from "./components/Header";\n',
            "src/components/Header.tsx": "export function Header() { return null; }\n",
            "package.json": '{"dependencies":{"react":"18.0.0"}}',
        },
    )

