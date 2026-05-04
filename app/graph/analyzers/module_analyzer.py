"""Module containment and dependency graph relationships."""

from __future__ import annotations

from app.graph.models import GraphEdge
from app.graph.utils.graph_evidence import from_phase2_evidence, make_graph_evidence
from app.graph.utils.graph_ids import make_edge_id, make_node_id
from app.graph.utils.path_matcher import normalize_import_path
from app.utils.ignored_paths import is_ignored_path


class ModuleAnalyzer:
    def containment_edges(self, intelligence_result) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        for module in getattr(intelligence_result, "modules", []) or []:
            mod_id = make_node_id("module", getattr(module, "name", ""))
            ev = from_phase2_evidence(getattr(module, "evidence", [])) or [
                make_graph_evidence("", f"Module contains files: {getattr(module, 'name', '')}", confidence=getattr(module, "confidence", "medium"))
            ]
            for file_path in getattr(module, "files", []) or []:
                normalized = normalize_import_path(file_path)
                if not normalized or is_ignored_path(normalized):
                    continue
                file_id = make_node_id("file", normalized)
                edges.append(GraphEdge(
                    id=make_edge_id(mod_id, file_id, "contains"),
                    source=mod_id,
                    target=file_id,
                    type="contains",
                    label="contains",
                    evidence=ev,
                    confidence=getattr(module, "confidence", "medium"),
                ))
                edges.append(GraphEdge(
                    id=make_edge_id(file_id, mod_id, "belongs_to"),
                    source=file_id,
                    target=mod_id,
                    type="belongs_to",
                    label="belongs to",
                    evidence=ev,
                    confidence=getattr(module, "confidence", "medium"),
                ))
        return edges

    def dependency_edges(self, intelligence_result, import_edges: list[GraphEdge]) -> list[GraphEdge]:
        file_to_module: dict[str, str] = {}
        for module in getattr(intelligence_result, "modules", []) or []:
            mod_id = make_node_id("module", getattr(module, "name", ""))
            for file_path in getattr(module, "files", []) or []:
                normalized = normalize_import_path(file_path)
                if not normalized or is_ignored_path(normalized):
                    continue
                file_to_module[make_node_id("file", normalized)] = mod_id

        edges: list[GraphEdge] = []
        for edge in import_edges or []:
            src_mod = file_to_module.get(edge.source)
            dst_mod = file_to_module.get(edge.target)
            if src_mod and dst_mod and src_mod != dst_mod:
                edges.append(GraphEdge(
                    id=make_edge_id(src_mod, dst_mod, "depends_on"),
                    source=src_mod,
                    target=dst_mod,
                    type="depends_on",
                    label="depends on",
                    metadata={"via": edge.id},
                    evidence=edge.evidence,
                    confidence=edge.confidence,
                ))
        return edges
