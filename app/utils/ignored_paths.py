"""Shared ignored-path matching for scan, graph, and chat defenses."""

from __future__ import annotations

IGNORED_PATH_PARTS = {
    "node_modules",
    ".venv",
    "venv",
    "env",
    "site-packages",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    "dist",
    "build",
    ".next",
    ".vite",
    "coverage",
    "htmlcov",
    "vendor",
}

IGNORED_PATH_SUBSTRINGS = {
    "pip/_vendor",
    "pip\\_vendor",
    "/site-packages/",
    "\\site-packages\\",
    "/node_modules/",
    "\\node_modules\\",
}


def normalize_path_for_ignore(path: str) -> str:
    return str(path or "").replace("\\", "/").strip().lower()


def is_ignored_path(path: str) -> bool:
    normalized = normalize_path_for_ignore(path)
    if not normalized:
        return False
    for substring in IGNORED_PATH_SUBSTRINGS:
        if substring.replace("\\", "/").lower() in normalized:
            return True
    parts = [part for part in normalized.split("/") if part]
    return any(part in IGNORED_PATH_PARTS or part.endswith(".egg-info") for part in parts)
