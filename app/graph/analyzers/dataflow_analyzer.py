"""Conservative dataflow graph relationships."""

from __future__ import annotations

from app.graph.models import GraphEdge
from app.graph.utils.graph_evidence import from_phase2_evidence, make_graph_evidence
from app.graph.utils.graph_ids import make_edge_id, make_node_id
from app.graph.utils.path_matcher import normalize_import_path
from app.utils.ignored_paths import is_ignored_path

_DB_IMPORTS = {
    "postgresql": ("asyncpg", "psycopg", "sqlalchemy"),
    "postgres": ("asyncpg", "psycopg", "sqlalchemy"),
    "mongodb": ("pymongo", "motor", "mongoose"),
    "mongo": ("pymongo", "motor", "mongoose"),
    "sqlite": ("sqlite3", "sqlalchemy"),
    "mysql": ("pymysql", "mysql", "sqlalchemy"),
    "prisma": ("prisma",),
}


class DataflowAnalyzer:
    def database_edges(self, scan_result, intelligence_result, nodes_by_id: dict) -> list[GraphEdge]:
        edges: list[GraphEdge] = []
        contents = getattr(scan_result, "contents", {}) or {}
        for db in getattr(intelligence_result, "databases", []) or []:
            db_name = str(getattr(db, "name", ""))
            db_id = make_node_id("database", db_name)
            signals = _DB_IMPORTS.get(db_name.lower(), (db_name.lower(),))
            evidence = from_phase2_evidence(getattr(db, "evidence", []))
            evidence_files = {normalize_import_path(ev.file) for ev in evidence if ev.file and not is_ignored_path(ev.file)}
            for path, content in contents.items():
                norm = normalize_import_path(path)
                if not norm or is_ignored_path(norm):
                    continue
                text = (content or "").lower()
                has_signal = norm in evidence_files or any(sig and sig in text for sig in signals) or "://" in text and db_name.lower() in text
                if not has_signal:
                    continue
                file_id = make_node_id("file", norm)
                ev = [make_graph_evidence(norm, f"File has database evidence for {db_name}", confidence=getattr(db, "confidence", "medium"))]
                edges.append(GraphEdge(
                    id=make_edge_id(file_id, db_id, "uses_database"),
                    source=file_id,
                    target=db_id,
                    type="uses_database",
                    label="uses database",
                    evidence=ev,
                    confidence=getattr(db, "confidence", "medium"),
                ))
                for api in getattr(intelligence_result, "api_endpoints", []) or []:
                    api_file = normalize_import_path(getattr(api, "file", ""))
                    if api_file and not is_ignored_path(api_file) and api_file == norm:
                        api_id = make_node_id("api", f"{getattr(api, 'method', '').upper()}:{getattr(api, 'path', '')}")
                        edges.append(GraphEdge(
                            id=make_edge_id(api_id, db_id, "uses_database"),
                            source=api_id,
                            target=db_id,
                            type="uses_database",
                            label="uses database",
                            evidence=ev,
                            confidence="medium",
                        ))
        return edges

    def workflow_edges(self, intelligence_result) -> list[GraphEdge]:
        steps = sorted(getattr(getattr(intelligence_result, "workflow", None), "steps", []) or [], key=lambda s: getattr(s, "order", 0))
        edges: list[GraphEdge] = []
        for left, right in zip(steps, steps[1:]):
            left_id = make_node_id("workflow", f"{getattr(left, 'order', 0)}:{getattr(left, 'source', '')}:{getattr(left, 'target', '')}")
            right_id = make_node_id("workflow", f"{getattr(right, 'order', 0)}:{getattr(right, 'source', '')}:{getattr(right, 'target', '')}")
            ev = from_phase2_evidence(getattr(right, "evidence", [])) or [make_graph_evidence("", "Workflow steps follow Phase 2 order", confidence=getattr(right, "confidence", "medium"))]
            edges.append(GraphEdge(
                id=make_edge_id(left_id, right_id, "part_of_workflow"),
                source=left_id,
                target=right_id,
                type="part_of_workflow",
                label="next workflow step",
                evidence=ev,
                confidence=getattr(right, "confidence", "medium"),
            ))
        return edges
