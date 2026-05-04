from app.graph.builders.edge_builder import EdgeBuilder
from app.graph.builders.node_builder import NodeBuilder
from app.graph.models import GraphEdge
from app.graph.utils.graph_evidence import make_graph_evidence


def test_validates_and_drops_invalid_edges(fastapi_scan, fastapi_intelligence):
    nodes = NodeBuilder().build_nodes(fastapi_scan, fastapi_intelligence)
    builder = EdgeBuilder()
    bad = GraphEdge(id="bad", source="missing:a", target="missing:b", type="related_to", label="bad", evidence=[make_graph_evidence("", "bad")], confidence="low")
    assert builder._validate([bad], {n.id for n in nodes}) == []
    assert builder.warnings


def test_dedupes_edges(fastapi_scan, fastapi_intelligence):
    nodes = NodeBuilder().build_nodes(fastapi_scan, fastapi_intelligence)
    edges = EdgeBuilder().build_edges(fastapi_scan, fastapi_intelligence, nodes)
    assert len(edges) == len({e.id for e in edges})


def test_every_edge_has_evidence(fastapi_scan, fastapi_intelligence):
    nodes = NodeBuilder().build_nodes(fastapi_scan, fastapi_intelligence)
    edges = EdgeBuilder().build_edges(fastapi_scan, fastapi_intelligence, nodes)
    assert edges
    assert all(e.evidence for e in edges)

