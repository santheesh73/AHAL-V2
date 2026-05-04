"""Build deterministic graph nodes from scan and intelligence results."""

from __future__ import annotations

from app.graph.models import GraphNode
from app.graph.utils.graph_evidence import dedupe_nodes, from_phase2_evidence, make_graph_evidence
from app.graph.utils.graph_ids import make_node_id
from app.graph.utils.path_matcher import normalize_import_path
from app.utils.ignored_paths import is_ignored_path


class NodeBuilder:
    def __init__(self) -> None:
        self.warnings: list[str] = []

    def build_nodes(self, scan_result, intelligence_result) -> list[GraphNode]:
        self.warnings = []
        nodes: list[GraphNode] = []

        try:
            for file_meta in getattr(scan_result, "files", []) or []:
                path = normalize_import_path(getattr(file_meta, "path", ""))
                if not path or is_ignored_path(path):
                    self.warnings.append("Skipped malformed file node")
                    continue
                nodes.append(GraphNode(
                    id=make_node_id("file", path),
                    type="file",
                    name=path.split("/")[-1],
                    label=path,
                    path=path,
                    metadata={
                        "extension": getattr(file_meta, "extension", ""),
                        "size_bytes": getattr(file_meta, "size_bytes", 0),
                        "priority": str(getattr(file_meta, "priority", "")),
                    },
                    evidence=[make_graph_evidence(path, "File included in Phase 1 scan", confidence="high")],
                    confidence="high",
                ))
        except Exception as exc:
            self.warnings.append(f"File node build failed: {exc}")

        items = [
            ("modules", "module", lambda m: getattr(m, "name", ""), "module"),
            ("frameworks", "framework", lambda f: getattr(f, "name", ""), "framework"),
            ("dependencies", "dependency", lambda d: f"{getattr(d, 'ecosystem', 'unknown')}:{getattr(d, 'name', '')}", "dependency"),
            ("api_endpoints", "api_endpoint", lambda a: f"{getattr(a, 'method', '').upper()}:{getattr(a, 'path', '')}", "api"),
            ("databases", "database", lambda d: getattr(d, "name", ""), "database"),
            ("entry_points", "entrypoint", lambda e: getattr(e, "file", ""), "entrypoint"),
        ]
        for attr, node_type, key_fn, prefix in items:
            for item in getattr(intelligence_result, attr, []) or []:
                try:
                    key = key_fn(item)
                    if not key:
                        self.warnings.append(f"Skipped malformed {node_type} node")
                        continue
                    ev = from_phase2_evidence(getattr(item, "evidence", []))
                    if node_type == "module" and not ev:
                        ev = [make_graph_evidence("", f"Synthetic module grouping: {key}", confidence=getattr(item, "confidence", "medium"))]
                    node_id = make_node_id(prefix, key)
                    path = normalize_import_path(getattr(item, "file", "") or getattr(item, "source_file", ""))
                    if path and is_ignored_path(path):
                        continue
                    if prefix in ("file", "module", "entrypoint", "function"):
                        path_part = key.split(":")[0] if prefix == "function" else key
                        if is_ignored_path(path_part):
                            continue
                    if node_type != "module" and node_type != "workflow_step" and not ev and node_type in {"entrypoint", "api_endpoint", "dependency", "database", "framework"}:
                        continue
                    label = key if node_type != "api_endpoint" else f"{getattr(item, 'method', '').upper()} {getattr(item, 'path', '')}"
                    nodes.append(GraphNode(
                        id=node_id,
                        type=node_type,
                        name=str(getattr(item, "name", "") or getattr(item, "path", "") or key),
                        label=label,
                        path=path or None,
                        metadata=_metadata(item),
                        evidence=ev,
                        confidence=getattr(item, "confidence", "medium"),
                    ))
                except Exception as exc:
                    self.warnings.append(f"Skipped malformed {node_type} node: {exc}")

        try:
            for step in getattr(getattr(intelligence_result, "workflow", None), "steps", []) or []:
                src = getattr(step, "source", "")
                tgt = getattr(step, "target", "")
                if (src and is_ignored_path(src)) or (tgt and is_ignored_path(tgt)):
                    continue
                key = f"{getattr(step, 'order', 0)}:{src}:{tgt}"
                ev = from_phase2_evidence(getattr(step, "evidence", []))
                nodes.append(GraphNode(
                    id=make_node_id("workflow", key),
                    type="workflow_step",
                    name=f"Step {getattr(step, 'order', 0)}",
                    label=str(getattr(step, "action", "") or key),
                    metadata={"order": getattr(step, "order", 0), "source": src, "target": tgt},
                    evidence=ev or [make_graph_evidence("", "Workflow step inferred by Phase 2", confidence=getattr(step, "confidence", "medium"))],
                    confidence=getattr(step, "confidence", "medium"),
                ))
        except Exception as exc:
            self.warnings.append(f"Workflow node build failed: {exc}")

        return dedupe_nodes(nodes)


def _metadata(item) -> dict:
    data = {}
    for key in ("category", "ecosystem", "source_file", "framework", "handler", "usage", "files", "type", "method"):
        if hasattr(item, key):
            data[key] = getattr(item, key)
    return data
