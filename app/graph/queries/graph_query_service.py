"""In-memory deterministic graph query service."""

from __future__ import annotations

from typing import Optional

from app.graph.models import GraphNode, GraphQueryResult, KnowledgeGraphResult
from app.graph.utils.graph_ids import make_node_id


class GraphQueryService:
    def __init__(self, graph: KnowledgeGraphResult):
        self.graph = graph
        self._nodes = {n.id: n for n in graph.nodes}

    def find_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)

    def neighbors(self, node_id: str, direction: str = "both") -> GraphQueryResult:
        edges = []
        for edge in self.graph.edges:
            if direction in ("both", "out") and edge.source == node_id:
                edges.append(edge)
            elif direction in ("both", "in") and edge.target == node_id:
                edges.append(edge)
        ids = {e.source for e in edges} | {e.target for e in edges}
        ids.discard(node_id)
        return GraphQueryResult(nodes=sorted([self._nodes[i] for i in ids if i in self._nodes], key=lambda n: n.id), edges=sorted(edges, key=lambda e: e.id))

    def dependencies_of(self, node_id: str) -> GraphQueryResult:
        edges = [e for e in self.graph.edges if e.source == node_id and e.type in ("depends_on", "imports", "uses_database")]
        return self._result_from_edges(edges)

    def dependents_of(self, node_id: str) -> GraphQueryResult:
        edges = [e for e in self.graph.edges if e.target == node_id and e.type in ("depends_on", "imports", "uses_database")]
        return self._result_from_edges(edges)

    def files_in_module(self, module_name: str) -> GraphQueryResult:
        module_id = make_node_id("module", module_name)
        edges = [e for e in self.graph.edges if e.source == module_id and e.type == "contains"]
        return self._result_from_edges(edges)

    def api_routes(self) -> GraphQueryResult:
        nodes = [n for n in self.graph.nodes if n.type == "api_endpoint"]
        ids = {n.id for n in nodes}
        edges = [e for e in self.graph.edges if e.source in ids or e.target in ids]
        return GraphQueryResult(nodes=sorted(nodes, key=lambda n: n.id), edges=sorted(edges, key=lambda e: e.id))

    def database_users(self) -> GraphQueryResult:
        edges = [e for e in self.graph.edges if e.type == "uses_database"]
        return self._result_from_edges(edges)

    def orphan_nodes(self) -> list[GraphNode]:
        from app.utils.ignored_paths import is_ignored_path
        connected = set()
        for edge in self.graph.edges:
            connected.add(edge.source)
            connected.add(edge.target)
        
        orphans = []
        for n in self.graph.nodes:
            if n.id in connected:
                continue
            
            # Additional safety check to drop any ignored paths that somehow became orphan nodes
            if ":" in n.id:
                prefix, payload = n.id.split(":", 1)
                if prefix in ("file", "module", "entrypoint", "function"):
                    path_part = payload.split(":")[0] if prefix == "function" else payload
                    if is_ignored_path(path_part):
                        continue
            
            orphans.append(n)
            
        return sorted(orphans, key=lambda n: n.id)

    def _result_from_edges(self, edges) -> GraphQueryResult:
        ids = {e.source for e in edges} | {e.target for e in edges}
        nodes = [self._nodes[i] for i in ids if i in self._nodes]
        return GraphQueryResult(nodes=sorted(nodes, key=lambda n: n.id), edges=sorted(edges, key=lambda e: e.id))

