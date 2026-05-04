"""API route graph relationships."""

from __future__ import annotations

from app.graph.models import GraphEdge, GraphNode
from app.graph.utils.graph_evidence import from_phase2_evidence, make_graph_evidence
from app.graph.utils.graph_ids import make_edge_id, make_node_id
from app.graph.utils.path_matcher import normalize_import_path
from app.utils.ignored_paths import is_ignored_path


class RouteAnalyzer:
    def analyze(self, intelligence_result, node_ids: set[str] | None = None) -> tuple[list[GraphNode], list[GraphEdge]]:
        node_ids = node_ids or set()
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for endpoint in getattr(intelligence_result, "api_endpoints", []) or []:
            path = normalize_import_path(getattr(endpoint, "file", ""))
            if not path or is_ignored_path(path):
                continue
            file_id = make_node_id("file", path)
            api_id = make_node_id("api", f"{getattr(endpoint, 'method', '').upper()}:{getattr(endpoint, 'path', '')}")
            ev = from_phase2_evidence(getattr(endpoint, "evidence", [])) or [
                make_graph_evidence(path, "API endpoint detected by Phase 2", confidence=getattr(endpoint, "confidence", "medium"))
            ]
            edges.append(GraphEdge(
                id=make_edge_id(file_id, api_id, "defines"),
                source=file_id,
                target=api_id,
                type="defines",
                label="defines",
                evidence=ev,
                confidence=getattr(endpoint, "confidence", "medium"),
            ))
            handler = getattr(endpoint, "handler", None)
            if handler:
                func_id = make_node_id("function", f"{path}:{handler}")
                nodes.append(GraphNode(
                    id=func_id,
                    type="function",
                    name=str(handler),
                    label=f"{handler}()",
                    path=path,
                    metadata={"file": path},
                    evidence=ev,
                    confidence=getattr(endpoint, "confidence", "medium"),
                ))
                edges.append(GraphEdge(
                    id=make_edge_id(api_id, func_id, "handles"),
                    source=api_id,
                    target=func_id,
                    type="handles",
                    label="handles",
                    evidence=ev,
                    confidence=getattr(endpoint, "confidence", "medium"),
                ))
            for entry in getattr(intelligence_result, "entry_points", []) or []:
                entry_path = normalize_import_path(getattr(entry, "file", ""))
                if not entry_path or is_ignored_path(entry_path):
                    continue
                if entry_path and (entry_path == path or entry_path.split("/")[0:1] == path.split("/")[0:1]):
                    entry_id = make_node_id("entrypoint", entry_path)
                    edges.append(GraphEdge(
                        id=make_edge_id(entry_id, api_id, "routes_to"),
                        source=entry_id,
                        target=api_id,
                        type="routes_to",
                        label="routes to",
                        evidence=ev,
                        confidence="medium",
                    ))
        return nodes, edges
