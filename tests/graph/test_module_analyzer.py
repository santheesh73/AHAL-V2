from app.graph.analyzers.import_analyzer import ImportAnalyzer
from app.graph.analyzers.module_analyzer import ModuleAnalyzer
from app.graph.builders.node_builder import NodeBuilder
from app.graph.utils.graph_ids import make_node_id
from app.intelligence.intelligence_engine import IntelligenceEngine
from tests.intelligence.conftest import make_scan_result


def test_module_contains_files(fastapi_intelligence):
    edges = ModuleAnalyzer().containment_edges(fastapi_intelligence)
    assert any(e.type == "contains" for e in edges)


def test_file_belongs_to_module(fastapi_intelligence):
    edges = ModuleAnalyzer().containment_edges(fastapi_intelligence)
    assert any(e.type == "belongs_to" for e in edges)


def test_module_dependency_inferred_from_import_edges():
    scan = make_scan_result(
        files=[{"path": "api/routes.py", "extension": ".py"}, {"path": "services/users.py", "extension": ".py"}],
        contents={"api/routes.py": "from services.users import get_users\n", "services/users.py": "def get_users(): return []\n"},
    )
    intel = IntelligenceEngine().analyze(scan)
    nodes = NodeBuilder().build_nodes(scan, intel)
    imports = ImportAnalyzer().analyze(scan, intel, {n.id for n in nodes})
    edges = ModuleAnalyzer().dependency_edges(intel, imports)
    assert any(e.type == "depends_on" for e in edges)


def test_no_import_means_no_dependency(fastapi_intelligence):
    assert ModuleAnalyzer().dependency_edges(fastapi_intelligence, []) == []

