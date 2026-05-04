from __future__ import annotations

from typing import Optional

ALLOWED_EVIDENCE_SOURCE_TYPES = {
    "file",
    "graph_node",
    "graph_edge",
    "api_endpoint",
    "module",
    "framework",
    "database",
}


def normalize_evidence_source_type(
    source_type: object,
    *,
    file: Optional[str] = None,
    source_id: Optional[str] = None,
) -> tuple[str, bool]:
    raw = str(source_type or "").strip().lower()
    if raw in ALLOWED_EVIDENCE_SOURCE_TYPES:
        return raw, False
    if raw == "dependency":
        normalized = "framework"
        if file:
            lowered = file.lower()
            if any(name in lowered for name in ("requirements", "package.json", "pyproject", "poetry.lock", "package-lock", "pnpm-lock", "yarn.lock")):
                normalized = "file"
        elif source_id and str(source_id).startswith("file:"):
            normalized = "file"
        return normalized, True
    return "file", bool(raw and raw != "file")
