"""Build deterministic evidence-backed graph edges."""

from __future__ import annotations

from app.graph.analyzers.dataflow_analyzer import DataflowAnalyzer
from app.graph.analyzers.import_analyzer import ImportAnalyzer
from app.graph.analyzers.module_analyzer import ModuleAnalyzer
from app.graph.analyzers.route_analyzer import RouteAnalyzer
from app.graph.models import GraphEdge, GraphNode
from app.graph.utils.graph_evidence import dedupe_edges, from_phase2_evidence, make_graph_evidence
from app.graph.utils.graph_ids import make_edge_id, make_node_id
from app.graph.utils.path_matcher import normalize_import_path
from app.utils.ignored_paths import is_ignored_path


class EdgeBuilder:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.extra_nodes: list[GraphNode] = []

    def build_edges(self, scan_result, intelligence_result, nodes) -> list[GraphEdge]:
        self.warnings = []
        self.extra_nodes = []
        node_ids = {n.id for n in nodes or []}
        edges: list[GraphEdge] = []

        edges.extend(self._evidence_edges(intelligence_result))
        edges.extend(self._entrypoint_edges(intelligence_result))

        module_analyzer = ModuleAnalyzer()
        edges.extend(module_analyzer.containment_edges(intelligence_result))

        import_edges = ImportAnalyzer().analyze(scan_result, intelligence_result, node_ids=node_ids)
        edges.extend(import_edges)

        route_nodes, route_edges = RouteAnalyzer().analyze(intelligence_result, node_ids=node_ids)
        self.extra_nodes.extend(route_nodes)
        node_ids.update(n.id for n in route_nodes)
        edges.extend(route_edges)

        edges.extend(module_analyzer.dependency_edges(intelligence_result, import_edges))
        dataflow = DataflowAnalyzer()
        edges.extend(dataflow.database_edges(scan_result, intelligence_result, {n.id: n for n in nodes or []}))
        edges.extend(dataflow.workflow_edges(intelligence_result))

        valid = self._validate(edges, node_ids)
        return dedupe_edges(valid)

    def _evidence_edges(self, intelligence_result) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for attr, prefix, key_fn, edge_type in [
            ("frameworks", "framework", lambda x: getattr(x, "name", ""), "depends_on"),
            ("dependencies", "dependency", lambda x: f"{getattr(x, 'ecosystem', 'unknown')}:{getattr(x, 'name', '')}", "depends_on"),
            ("databases", "database", lambda x: getattr(x, "name", ""), "uses_database"),
        ]:
            for item in getattr(intelligence_result, attr, []) or []:
                target = make_node_id(prefix, key_fn(item))
                evs = from_phase2_evidence(getattr(item, "evidence", []))
                for ev in evs:
                    if not ev.file or is_ignored_path(ev.file):
                        continue
                    source = make_node_id("file", normalize_import_path(ev.file))
                    edges.append(GraphEdge(
                        id=make_edge_id(source, target, edge_type),
                        source=source,
                        target=target,
                        type=edge_type,
                        label="uses" if edge_type == "uses_database" else "depends on",
                        evidence=[ev],
                        confidence=ev.confidence,
                    ))
        return edges

    def _entrypoint_edges(self, intelligence_result) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for item in getattr(intelligence_result, "entry_points", []) or []:
            path = normalize_import_path(getattr(item, "file", ""))
            if not path or is_ignored_path(path):
                continue
            source = make_node_id("entrypoint", path)
            target = make_node_id("file", path)
            ev = from_phase2_evidence(getattr(item, "evidence", [])) or [make_graph_evidence(path, "Entrypoint detected by Phase 2", confidence=getattr(item, "confidence", "medium"))]
            edges.append(GraphEdge(
                id=make_edge_id(source, target, "entrypoint_of"),
                source=source,
                target=target,
                type="entrypoint_of",
                label="entrypoint of",
                evidence=ev,
                confidence=getattr(item, "confidence", "medium"),
            ))
        return edges

    def _validate(self, edges: list[GraphEdge], node_ids: set[str]) -> list[GraphEdge]:
        valid: list[GraphEdge] = []
        for edge in edges:
            if self._edge_has_ignored_path(edge):
                self.warnings.append(f"Dropped ignored-path edge {edge.id}")
                continue
            if edge.source not in node_ids or edge.target not in node_ids:
                self.warnings.append(f"Dropped invalid edge {edge.id}")
                continue
            if not edge.evidence:
                self.warnings.append(f"Dropped edge without evidence {edge.id}")
                continue
            valid.append(edge)
        return valid

    def _edge_has_ignored_path(self, edge: GraphEdge) -> bool:
        if any(ev.file and is_ignored_path(ev.file) for ev in edge.evidence):
            return True
        for node_id in (edge.source, edge.target):
            if ":" not in node_id:
                continue
            prefix, payload = node_id.split(":", 1)
            if prefix in ("file", "module", "entrypoint", "function"):
                path_part = payload.split(":")[0] if prefix == "function" else payload
                if is_ignored_path(path_part):
                    return True
        return False
