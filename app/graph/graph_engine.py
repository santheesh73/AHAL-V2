"""Knowledge graph engine orchestrator."""

from __future__ import annotations

from typing import Optional

from app.graph.builders.edge_builder import EdgeBuilder
from app.graph.builders.node_builder import NodeBuilder
from app.graph.models import GraphStats, KnowledgeGraphResult
from app.graph.queries.graph_query_service import GraphQueryService
from app.graph.utils.graph_evidence import dedupe_nodes


class KnowledgeGraphEngine:
    def build(self, scan_result, intelligence_result, session_id: Optional[str] = None) -> KnowledgeGraphResult:
        warnings: list[str] = []
        if scan_result is None or intelligence_result is None:
            warnings.append("Empty input: scan_result or intelligence_result missing")
            return KnowledgeGraphResult(session_id=session_id, warnings=warnings)

        try:
            node_builder = NodeBuilder()
            nodes = node_builder.build_nodes(scan_result, intelligence_result)
            warnings.extend(node_builder.warnings)

            edge_builder = EdgeBuilder()
            edges = edge_builder.build_edges(scan_result, intelligence_result, nodes)
            nodes = dedupe_nodes([*nodes, *edge_builder.extra_nodes])
            edges = edge_builder._validate(edges, {n.id for n in nodes})
            warnings.extend(edge_builder.warnings)

            nodes = sorted(nodes, key=lambda n: n.id)
            edges = sorted(edges, key=lambda e: e.id)
            stats = self._stats(nodes, edges)
            evidence_count = sum(len(n.evidence) for n in nodes) + sum(len(e.evidence) for e in edges)
            return KnowledgeGraphResult(
                session_id=session_id,
                nodes=nodes,
                edges=edges,
                stats=stats,
                warnings=warnings,
                evidence_count=evidence_count,
            )
        except Exception as exc:
            warnings.append(f"Knowledge graph build failed: {exc}")
            return KnowledgeGraphResult(session_id=session_id, warnings=warnings)

    def _stats(self, nodes, edges) -> GraphStats:
        service_graph = KnowledgeGraphResult(nodes=nodes, edges=edges)
        orphan_count = len(GraphQueryService(service_graph).orphan_nodes())
        confidence = self._confidence_score(nodes, edges)
        return GraphStats(
            node_count=len(nodes),
            edge_count=len(edges),
            files=len([n for n in nodes if n.type == "file"]),
            modules=len([n for n in nodes if n.type == "module"]),
            api_endpoints=len([n for n in nodes if n.type == "api_endpoint"]),
            databases=len([n for n in nodes if n.type == "database"]),
            dependencies=len([n for n in nodes if n.type == "dependency"]),
            orphan_nodes=orphan_count,
            confidence_score=confidence,
        )

    def _confidence_score(self, nodes, edges) -> float:
        weights = {"high": 1.0, "medium": 0.66, "low": 0.33}
        items = [*nodes, *edges]
        if not items:
            return 0.0
        score = sum(weights.get(getattr(item, "confidence", "low"), 0.33) for item in items) / len(items)
        return round(max(0.0, min(1.0, score)), 3)

