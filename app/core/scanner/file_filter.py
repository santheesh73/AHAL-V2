"""
AHAL AI — File Filter
Determines whether a file should be included or excluded from scanning.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

from app.config import ScannerConfig
from app.utils.ignored_paths import is_ignored_path
from app.utils.safe_utils import normalize_path, safe_extension

logger = logging.getLogger("ahal.scanner.filter")


class FileFilter:
    """Stateless filter: given a path and size, decide include / exclude."""

    def __init__(self, cfg: ScannerConfig) -> None:
        self._cfg = cfg

    # ── Public API ───────────────────────────────────────────────

    def should_include(self, path: str, size_bytes: int = 0) -> Tuple[bool, Optional[str]]:
        """
        Returns (include: bool, skip_reason: str | None).
        *skip_reason* is human‑readable when include is False.
        """
        norm = normalize_path(path)

        if is_ignored_path(norm):
            reason = self._ignored_path_reason(norm)
            return False, reason or "ignored_directory"

        # 1. Check ignored directories
        reason = self._check_ignored_directory(norm)
        if reason:
            return False, reason

        # 2. Check ignored extensions
        ext = safe_extension(norm)
        if ext in self._cfg.ignored_extensions:
            return False, f"ignored_extension:{ext}"

        # 3. Check hidden files / directories (dot‑prefixed beyond .git)
        basename = os.path.basename(norm)
        if basename.startswith(".") and basename not in {
            ".env", ".env.example", ".editorconfig", ".eslintrc",
            ".prettierrc", ".gitignore", ".dockerignore",
            ".eslintrc.js", ".eslintrc.json", ".babelrc",
        }:
            # Allow common dotfiles, skip the rest
            if not any(ext == e for e in (".js", ".json", ".yml", ".yaml", ".toml")):
                return False, "hidden_file"

        return True, None

    # ── Internal ─────────────────────────────────────────────────

    def _check_ignored_directory(self, norm_path: str) -> Optional[str]:
        """Return skip reason if any path segment is an ignored directory."""
        parts = norm_path.split("/")
        for part in parts[:-1]:  # skip the filename itself
            if part in self._cfg.ignored_directories:
                return f"ignored_directory:{part}"
            # Catch patterns like `*.egg-info`
            if part.endswith(".egg-info"):
                return f"ignored_directory:{part}"
        return None

    def _ignored_path_reason(self, norm_path: str) -> Optional[str]:
        parts = [part for part in norm_path.split("/") if part]
        for part in parts[:-1]:
            if part in self._cfg.ignored_directories or part in {
                ".venv", "venv", "env", "ENV", "site-packages",
                "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                ".cache", "dist", "build", ".next", ".vite", "coverage",
                "htmlcov", "vendor",
            }:
                return f"ignored_directory:{part}"
            if part.endswith(".egg-info"):
                return f"ignored_directory:{part}"
        return None
