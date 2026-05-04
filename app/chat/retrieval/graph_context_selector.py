"""Select graph-aware context deterministically from Phase 3 results."""

from __future__ import annotations

from app.chat.models import EvidenceReference, RetrievedContext
from app.graph.queries.graph_query_service import GraphQueryService
from app.utils.ignored_paths import is_ignored_path


class GraphContextSelector:
    def select(self, question: str, classification, graph_result, max_items: int = 20) -> list[RetrievedContext]:
        service = GraphQueryService(graph_result)
        category = classification.category
        entities = [entity.lower() for entity in classification.entities]
        selected_nodes = self._pick_nodes(graph_result, category, entities)

        items: list[RetrievedContext] = []
        seen: set[str] = set()
        for node in selected_nodes:
            if self._node_ignored(node):
                continue
            if node.id in seen:
                continue
            seen.add(node.id)
            items.append(self._node_context(node, category))
            neighbors = service.neighbors(node.id)
            for edge in neighbors.edges:
                if self._edge_ignored(edge):
                    continue
                items.append(self._edge_context(edge, category))
            for neighbor in neighbors.nodes[:3]:
                if self._node_ignored(neighbor):
                    continue
                if neighbor.id not in seen:
                    seen.add(neighbor.id)
                    items.append(self._node_context(neighbor, category))

        if category == "database":
            for edge in service.database_users().edges:
                if self._edge_ignored(edge):
                    continue
                items.append(self._edge_context(edge, category))
        if category == "api":
            for edge in service.api_routes().edges:
                if self._edge_ignored(edge):
                    continue
                items.append(self._edge_context(edge, category))

        deduped: list[RetrievedContext] = []
        ids: set[str] = set()
        for item in items:
            if item.context_id in ids:
                continue
            ids.add(item.context_id)
            deduped.append(item)
        return deduped[:max_items]

    def _pick_nodes(self, graph_result, category: str, entities: list[str]):
        preferred_order = {
            "api": ("api_endpoint", "function", "file", "module"),
            "workflow": ("workflow_step", "module", "file"),
            "module": ("module", "file"),
            "database": ("database", "file", "module"),
        }.get(category, tuple())
        preferred = set(preferred_order)

        scored_nodes = []
        for node in graph_result.nodes:
            node_blob = " ".join([node.id.lower(), node.name.lower(), node.label.lower(), str(node.metadata).lower()])
            score = None
            if preferred and node.type in preferred:
                score = 100 - preferred_order.index(node.type)
            elif any(entity in node_blob for entity in entities):
                score = 50
            if score is not None:
                scored_nodes.append((score, node.id, node))
        scored_nodes.sort(key=lambda item: (-item[0], item[1]))
        return [node for _score, _node_id, node in scored_nodes]

    def _node_context(self, node, category: str) -> RetrievedContext:
        evidence = [
            EvidenceReference(
                source_type="graph_node",
                source_id=node.id,
                file=getattr(ev, "file", None),
                reason=getattr(ev, "reason", ""),
                snippet=getattr(ev, "snippet", None),
                confidence=getattr(ev, "confidence", "medium"),
            )
            for ev in node.evidence
        ]
        prefix = "workflow-node" if node.type == "workflow_step" else "graph-node"
        return RetrievedContext(
            context_id=f"{prefix}-{node.id}",
            title=f"Graph node {node.label}",
            content=f"Node {node.type}: {node.label}",
            source_type="graph_node",
            source_id=node.id,
            file=node.path,
            confidence=node.confidence,
            category=category if category != "general" else "general",
            keywords=[node.type, node.name.lower(), node.label.lower()],
            evidence=evidence,
        )

    def _edge_context(self, edge, category: str) -> RetrievedContext:
        evidence = [
            EvidenceReference(
                source_type="graph_edge",
                source_id=edge.id,
                file=getattr(ev, "file", None),
                reason=getattr(ev, "reason", ""),
                snippet=getattr(ev, "snippet", None),
                confidence=getattr(ev, "confidence", "medium"),
            )
            for ev in edge.evidence
        ]
        return RetrievedContext(
            context_id=f"graph-edge-{edge.id}",
            title=f"Graph edge {edge.label}",
            content=f"{edge.source} -[{edge.type}]-> {edge.target}",
            source_type="graph_edge",
            source_id=edge.id,
            confidence=edge.confidence,
            category=category if category != "general" else "general",
            keywords=[edge.type, edge.label.lower()],
            evidence=evidence,
        )

    def _node_ignored(self, node) -> bool:
        return bool(getattr(node, "path", None) and is_ignored_path(node.path))

    def _edge_ignored(self, edge) -> bool:
        if any(ev.file and is_ignored_path(ev.file) for ev in edge.evidence):
            return True
        for value in (edge.source, edge.target):
            if ":" not in value:
                continue
            payload = value.split(":", 1)[1]
            if "/" in payload and is_ignored_path(payload):
                return True
        return False
