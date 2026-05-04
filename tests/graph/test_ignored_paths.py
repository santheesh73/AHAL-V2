from app.graph.graph_engine import KnowledgeGraphEngine
from app.graph.queries.graph_query_service import GraphQueryService
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.conftest import make_scan_result


def _polluted_scan():
    return make_scan_result(
        files=[
            {"path": "src/main.tsx", "extension": ".tsx"},
            {"path": "package.json", "extension": ".json"},
            {"path": "node_modules/@swc/helpers/index.js", "extension": ".js"},
            {"path": ".venv/Lib/site-packages/pkg/mod.py", "extension": ".py"},
        ],
        contents={
            "src/main.tsx": 'import React from "react";\nexport const app = 1;\n',
            "package.json": '{"dependencies":{"react":"18.0.0","vite":"5.0.0"}}',
            "node_modules/@swc/helpers/index.js": 'export function helper() {}',
            ".venv/Lib/site-packages/pkg/mod.py": "import requests\n",
        },
    )


def test_graph_excludes_ignored_file_nodes_and_edges():
    scan = _polluted_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)

    assert not any("node_modules" in node.id or "site-packages" in node.id for node in graph.nodes)
    assert not any("node_modules" in edge.id or "site-packages" in edge.id for edge in graph.edges)
    assert not any(ev.file and ("node_modules" in ev.file or "site-packages" in ev.file) for node in graph.nodes for ev in node.evidence)
    assert not any(ev.file and ("node_modules" in ev.file or "site-packages" in ev.file) for edge in graph.edges for ev in edge.evidence)


def test_orphan_nodes_do_not_return_ignored_paths():
    scan = _polluted_scan()
    intelligence = IntelligenceEngine().analyze(scan)
    graph = KnowledgeGraphEngine().build(scan, intelligence)
    orphans = GraphQueryService(graph).orphan_nodes()

    assert not any("node_modules" in node.id or "site-packages" in node.id for node in orphans)
