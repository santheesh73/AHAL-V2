from app.graph.analyzers.import_analyzer import ImportAnalyzer
from app.graph.builders.node_builder import NodeBuilder
from app.graph.utils.graph_ids import make_node_id
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.conftest import make_scan_result


def _edges(scan):
    intel = IntelligenceEngine().analyze(scan)
    nodes = NodeBuilder().build_nodes(scan, intel)
    return ImportAnalyzer().analyze(scan, intel, {n.id for n in nodes})


def test_python_import_to_dependency(fastapi_scan):
    edges = _edges(fastapi_scan)
    assert any(e.target.startswith("dependency:pip:fastapi") for e in edges)


def test_python_relative_import_to_file():
    scan = make_scan_result(
        files=[{"path": "pkg/a.py", "extension": ".py"}, {"path": "pkg/b.py", "extension": ".py"}],
        contents={"pkg/a.py": "from .b import thing\n", "pkg/b.py": "thing = 1\n"},
    )
    edges = _edges(scan)
    assert any(e.source == make_node_id("file", "pkg/a.py") and e.target == make_node_id("file", "pkg/b.py") for e in edges)


def test_js_import_to_dependency(js_relative_scan):
    edges = _edges(js_relative_scan)
    assert any(e.target.startswith("dependency:npm:react") for e in edges)


def test_js_relative_import_to_file(js_relative_scan):
    edges = _edges(js_relative_scan)
    assert any(e.target == make_node_id("file", "src/components/Header.tsx") for e in edges)


def test_unknown_import_ignored():
    scan = make_scan_result(files=[{"path": "a.py", "extension": ".py"}], contents={"a.py": "import unknown_package\n"})
    assert _edges(scan) == []


def test_malformed_code_does_not_crash():
    scan = make_scan_result(files=[{"path": "a.ts", "extension": ".ts"}], contents={"a.ts": "import {\n require("})
    assert isinstance(_edges(scan), list)


def test_ignored_source_file_does_not_create_import_edges():
    scan = make_scan_result(
        files=[
            {"path": "src/app.ts", "extension": ".ts"},
            {"path": "node_modules/pkg/index.js", "extension": ".js"},
        ],
        contents={
            "src/app.ts": 'import "react";\n',
            "node_modules/pkg/index.js": 'import "react";\n',
        },
    )
    edges = _edges(scan)
    assert not any("node_modules" in edge.source or "node_modules" in edge.target for edge in edges)
