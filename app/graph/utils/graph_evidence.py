"""Evidence and dedupe helpers for graph construction."""

from __future__ import annotations

from typing import Iterable

from app.graph.models import GraphEdge, GraphEvidence, GraphNode
from app.utils.ignored_paths import is_ignored_path


def make_graph_evidence(file, reason, snippet=None, confidence="medium") -> GraphEvidence:
    try:
        conf = confidence if confidence in ("high", "medium", "low") else "medium"
        normalized_file = str(file or "")
        if normalized_file and is_ignored_path(normalized_file):
            normalized_file = ""
        return GraphEvidence(
            file=normalized_file,
            reason=str(reason or "Graph relationship evidence"),
            snippet=str(snippet)[:500] if snippet is not None else None,
            confidence=conf,
        )
    except Exception:
        return GraphEvidence(file="", reason="Graph relationship evidence", confidence="low")


def from_phase2_evidence(items: Iterable[object] | None) -> list[GraphEvidence]:
    out: list[GraphEvidence] = []
    try:
        for item in items or []:
            file = getattr(item, "file", "")
            if file and is_ignored_path(file):
                continue
            out.append(make_graph_evidence(
                file,
                getattr(item, "reason", "Phase 2 evidence"),
                getattr(item, "snippet", None),
                getattr(item, "confidence", "medium"),
            ))
    except Exception:
        return out
    return out


def dedupe_nodes(nodes: Iterable[GraphNode]) -> list[GraphNode]:
    seen: dict[str, GraphNode] = {}
    try:
        for node in nodes or []:
            if node.id not in seen:
                seen[node.id] = node
            else:
                existing = seen[node.id]
                known = {(e.file, e.reason, e.snippet) for e in existing.evidence}
                for ev in node.evidence:
                    key = (ev.file, ev.reason, ev.snippet)
                    if key not in known:
                        existing.evidence.append(ev)
                        known.add(key)
    except Exception:
        return list(seen.values())
    return sorted(seen.values(), key=lambda n: n.id)


def dedupe_edges(edges: Iterable[GraphEdge]) -> list[GraphEdge]:
    seen: dict[str, GraphEdge] = {}
    try:
        for edge in edges or []:
            if edge.id not in seen:
                seen[edge.id] = edge
            else:
                existing = seen[edge.id]
                known = {(e.file, e.reason, e.snippet) for e in existing.evidence}
                for ev in edge.evidence:
                    key = (ev.file, ev.reason, ev.snippet)
                    if key not in known:
                        existing.evidence.append(ev)
                        known.add(key)
    except Exception:
        return list(seen.values())
    return sorted(seen.values(), key=lambda e: e.id)
