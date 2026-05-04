"""Shared relationship helpers for graph builders."""

from __future__ import annotations

from app.graph.models import GraphEdge
from app.graph.utils.graph_evidence import make_graph_evidence
from app.graph.utils.graph_ids import make_edge_id


def make_relationship(source: str, target: str, edge_type: str, label: str, file: str, reason: str, confidence: str = "medium") -> GraphEdge:
    return GraphEdge(
        id=make_edge_id(source, target, edge_type),
        source=source,
        target=target,
        type=edge_type,
        label=label,
        evidence=[make_graph_evidence(file, reason, confidence=confidence)],
        confidence=confidence,
    )

