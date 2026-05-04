from app.graph.analyzers.route_analyzer import RouteAnalyzer


def test_fastapi_endpoint_connected_to_file(fastapi_intelligence):
    _, edges = RouteAnalyzer().analyze(fastapi_intelligence)
    assert any(e.type == "defines" and e.target.startswith("api:") for e in edges)


def test_endpoint_connected_to_handler_if_known(fastapi_intelligence):
    nodes, edges = RouteAnalyzer().analyze(fastapi_intelligence)
    assert any(n.type == "function" for n in nodes)
    assert any(e.type == "handles" for e in edges)


def test_unknown_handler_does_not_invent_function(fastapi_intelligence):
    for endpoint in fastapi_intelligence.api_endpoints:
        endpoint.handler = None
    nodes, edges = RouteAnalyzer().analyze(fastapi_intelligence)
    assert not any(n.type == "function" for n in nodes)
    assert not any(e.type == "handles" for e in edges)


def test_every_route_edge_has_evidence(fastapi_intelligence):
    _, edges = RouteAnalyzer().analyze(fastapi_intelligence)
    assert all(e.evidence for e in edges)

