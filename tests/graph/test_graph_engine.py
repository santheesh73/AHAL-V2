from app.graph.graph_engine import KnowledgeGraphEngine
from tests.intelligence.conftest import empty_scan_result


def test_fullstack_sample_produces_graph(fullstack_graph_inputs):
    scan, intel = fullstack_graph_inputs
    graph = KnowledgeGraphEngine().build(scan, intel, session_id="g1")
    assert graph.nodes
    assert graph.edges
    assert graph.session_id == "g1"


def test_empty_input_returns_empty_graph():
    graph = KnowledgeGraphEngine().build(None, None)
    assert graph.nodes == []
    assert graph.edges == []
    assert graph.warnings


def test_graph_stats_correct(fullstack_graph_inputs):
    graph = KnowledgeGraphEngine().build(*fullstack_graph_inputs)
    assert graph.stats.node_count == len(graph.nodes)
    assert graph.stats.edge_count == len(graph.edges)


def test_deterministic_output(fullstack_graph_inputs):
    engine = KnowledgeGraphEngine()
    g1 = engine.build(*fullstack_graph_inputs)
    g2 = engine.build(*fullstack_graph_inputs)
    assert g1.model_dump() == g2.model_dump()


def test_no_invalid_edges(fullstack_graph_inputs):
    graph = KnowledgeGraphEngine().build(*fullstack_graph_inputs)
    ids = {n.id for n in graph.nodes}
    assert all(e.source in ids and e.target in ids for e in graph.edges)


def test_evidence_count_correct(fullstack_graph_inputs):
    graph = KnowledgeGraphEngine().build(*fullstack_graph_inputs)
    assert graph.evidence_count == sum(len(n.evidence) for n in graph.nodes) + sum(len(e.evidence) for e in graph.edges)

