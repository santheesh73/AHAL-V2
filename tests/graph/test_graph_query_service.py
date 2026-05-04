from app.graph.graph_engine import KnowledgeGraphEngine
from app.graph.queries.graph_query_service import GraphQueryService


def _service(inputs):
    graph = KnowledgeGraphEngine().build(*inputs)
    return graph, GraphQueryService(graph)


def test_find_node(fullstack_graph_inputs):
    graph, svc = _service(fullstack_graph_inputs)
    assert svc.find_node(graph.nodes[0].id) == graph.nodes[0]


def test_neighbors(fullstack_graph_inputs):
    graph, svc = _service(fullstack_graph_inputs)
    node_id = graph.edges[0].source
    assert svc.neighbors(node_id).edges


def test_dependencies_and_dependents(fullstack_graph_inputs):
    graph, svc = _service(fullstack_graph_inputs)
    edge = next(e for e in graph.edges if e.type in ("depends_on", "imports", "uses_database"))
    assert svc.dependencies_of(edge.source).edges
    assert svc.dependents_of(edge.target).edges


def test_files_in_module(fullstack_graph_inputs):
    graph, svc = _service(fullstack_graph_inputs)
    module = next(n for n in graph.nodes if n.type == "module")
    assert svc.files_in_module(module.name).nodes


def test_api_routes(fullstack_graph_inputs):
    _, svc = _service(fullstack_graph_inputs)
    assert svc.api_routes().nodes


def test_database_users(fullstack_graph_inputs):
    _, svc = _service(fullstack_graph_inputs)
    assert svc.database_users().edges


def test_orphan_nodes(fullstack_graph_inputs):
    graph, svc = _service(fullstack_graph_inputs)
    assert isinstance(svc.orphan_nodes(), list)

