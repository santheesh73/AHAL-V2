"""
AHAL AI — Path helpers (Phase 2)

Deterministic path utilities for intelligence detectors.
Never raise on bad input.
"""

from __future__ import annotations

import os
from typing import Generator, List, Optional, Tuple

from app.models.file_schema import FileMetadata, ScanResult


def safe_lower(value: object) -> str:
    """Lowercase a value safely. Returns '' on failure."""
    try:
        return str(value).lower()
    except Exception:
        return ""


def normalize_repo_path(path: str) -> str:
    """Forward-slash, strip leading ./ and /."""
    try:
        p = path.replace("\\", "/")
        while p.startswith("./") or p.startswith("/"):
            p = p[1:] if p.startswith("/") else p[2:]
        return p
    except Exception:
        return ""


def path_parts(path: str) -> List[str]:
    """Split a normalized path into segments."""
    try:
        return normalize_repo_path(path).split("/")
    except Exception:
        return []


def filename(path: str) -> str:
    """Return the basename of a path."""
    try:
        return os.path.basename(normalize_repo_path(path))
    except Exception:
        return ""


def extension(path: str) -> str:
    """Return the lowercase file extension including dot."""
    try:
        _, ext = os.path.splitext(path)
        return ext.lower()
    except Exception:
        return ""


def is_config_file(path: str) -> bool:
    """Check if a file is a known config/manifest file."""
    known = {
        "package.json", "requirements.txt", "pyproject.toml",
        "pipfile", "poetry.lock", "pom.xml", "build.gradle",
        "go.mod", "cargo.toml", "composer.json", "gemfile",
        "dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "makefile", "tsconfig.json", "vite.config.js", "vite.config.ts",
        "next.config.js", "next.config.ts", "next.config.mjs",
        "angular.json", "webpack.config.js", "rollup.config.js",
        ".eslintrc", ".eslintrc.js", ".eslintrc.json",
        ".prettierrc", ".babelrc", "jest.config.js", "jest.config.ts",
        "setup.py", "setup.cfg", "manage.py",
    }
    return filename(path).lower() in known


def content_for(scan_result: ScanResult, path: str) -> Optional[str]:
    """
    Retrieve content for a file from the ScanResult.
    Returns None if not available. Never raises.
    """
    try:
        return scan_result.contents.get(path) or scan_result.contents.get(normalize_repo_path(path))
    except Exception:
        return None


def iter_files(scan_result: ScanResult) -> Generator[FileMetadata, None, None]:
    """Yield all non-skipped FileMetadata from the scan result."""
    try:
        for f in scan_result.files:
            if not f.skipped:
                yield f
    except Exception:
        return


def iter_contents(scan_result: ScanResult) -> Generator[Tuple[str, str], None, None]:
    """Yield (path, content) pairs from the scan result."""
    try:
        for path, content in scan_result.contents.items():
            if content:
                yield path, content
    except Exception:
        return
