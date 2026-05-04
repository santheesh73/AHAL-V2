"""Safe path matching utilities for graph construction."""

from __future__ import annotations

import fnmatch
import posixpath


def normalize_import_path(path) -> str:
    try:
        p = str(path or "").replace("\\", "/").strip()
        while p.startswith("./") or p.startswith("/"):
            p = p[2:] if p.startswith("./") else p[1:]
        return posixpath.normpath(p).replace("\\", "/") if p else ""
    except Exception:
        return ""


def same_module(path_a, path_b) -> bool:
    try:
        a = normalize_import_path(path_a).split("/")
        b = normalize_import_path(path_b).split("/")
        return bool(a and b and a[0] == b[0])
    except Exception:
        return False


def path_matches(path, patterns) -> bool:
    try:
        p = normalize_import_path(path)
        return any(fnmatch.fnmatch(p, str(pattern).replace("\\", "/")) for pattern in (patterns or []))
    except Exception:
        return False

