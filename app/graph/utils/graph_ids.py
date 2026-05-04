"""Deterministic graph ID helpers."""

from __future__ import annotations

import re


def _clean(value: object) -> str:
    try:
        text = str(value or "").strip().replace("\\", "/")
        text = re.sub(r"\s+", " ", text)
        return text
    except Exception:
        return ""


def make_node_id(type: object, key: object) -> str:
    try:
        return f"{_clean(type).lower()}:{_clean(key)}"
    except Exception:
        return "unknown:"


def make_edge_id(source: object, target: object, type: object) -> str:
    try:
        return f"{_clean(type).lower()}:{_clean(source)}->{_clean(target)}"
    except Exception:
        return "related_to:->"

