from app.graph.builders.node_builder import NodeBuilder


def test_builds_core_nodes(fastapi_scan, fastapi_intelligence):
    nodes = NodeBuilder().build_nodes(fastapi_scan, fastapi_intelligence)
    types = {n.type for n in nodes}
    assert "file" in types
    assert "module" in types
    assert "framework" in types
    assert "api_endpoint" in types


def test_dedupes_nodes(fastapi_scan, fastapi_intelligence):
    fastapi_intelligence.frameworks.append(fastapi_intelligence.frameworks[0])
    nodes = NodeBuilder().build_nodes(fastapi_scan, fastapi_intelligence)
    assert len(nodes) == len({n.id for n in nodes})


def test_every_non_synthetic_node_has_evidence(fastapi_scan, fastapi_intelligence):
    nodes = NodeBuilder().build_nodes(fastapi_scan, fastapi_intelligence)
    for node in nodes:
        if node.type != "module":
            assert node.evidence, node.id

