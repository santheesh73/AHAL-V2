"""
AHAL AI — Repo Handler
Handles GitHub repository cloning (shallow) and local directory scanning.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Generator, Optional, Tuple

from app.config import ScannerConfig
from app.utils.ignored_paths import is_ignored_path
from app.utils.logger import log_error, log_info
from app.utils.safe_utils import normalize_path

logger = logging.getLogger("ahal.scanner.repo")


class RepoEntry:
    """Lightweight descriptor for a file discovered on disk."""

    __slots__ = ("path", "abs_path", "size_bytes")

    def __init__(self, path: str, abs_path: str, size_bytes: int) -> None:
        self.path = path          # relative to repo root
        self.abs_path = abs_path  # absolute on disk
        self.size_bytes = size_bytes


class RepoHandler:
    """
    Clone a GitHub repo (shallow, depth=1) into a temp directory
    and yield its file entries.
    """

    def __init__(self, cfg: ScannerConfig) -> None:
        self._cfg = cfg
        self._clone_dir: Optional[str] = None
        self._owns_dir: bool = False  # True if we created the temp dir

    # ── Public API ───────────────────────────────────────────────

    def clone(self, github_url: str) -> str:
        """
        Shallow‑clone the repo and return the local directory path.
        Raises on failure.
        """
        base = self._cfg.temp_base_dir or tempfile.gettempdir()
        self._clone_dir = tempfile.mkdtemp(prefix="ahal_repo_", dir=base)
        self._owns_dir = True

        log_info(f"Cloning repo: {github_url}", session_id=None)
        logger.info("Cloning %s → %s", github_url, self._clone_dir)

        try:
            subprocess.run(
                [
                    "git", "clone",
                    "--depth", "1",
                    "--single-branch",
                    github_url,
                    self._clone_dir,
                ],
                capture_output=True,
                text=True,
                timeout=self._cfg.github_clone_timeout_seconds,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            log_error(f"git clone failed: {exc.stderr}")
            logger.error("git clone failed: %s", exc.stderr)
            self.cleanup()
            raise RuntimeError(f"git clone failed: {exc.stderr}") from exc
        except subprocess.TimeoutExpired:
            log_error(f"git clone timed out after {self._cfg.github_clone_timeout_seconds}s")
            logger.error("git clone timed out after %ds", self._cfg.github_clone_timeout_seconds)
            self.cleanup()
            raise RuntimeError("git clone timed out")

        log_info(f"Clone complete: {self._clone_dir}")
        return self._clone_dir

    def set_directory(self, path: str) -> None:
        """Use an existing local directory (e.g. from an uploaded folder)."""
        self._clone_dir = path
        self._owns_dir = False

    @property
    def clone_dir(self) -> Optional[str]:
        """The current clone / working directory, or None if not set."""
        return self._clone_dir

    def iter_files(self) -> Generator[RepoEntry, None, None]:
        """
        Walk the cloned / set directory and yield RepoEntry for each file.
        """
        if self._clone_dir is None:
            return

        for root, dirs, files in os.walk(self._clone_dir):
            # Prune ignored directories in‑place for efficiency
            dirs[:] = [
                d for d in dirs
                if d not in self._cfg.ignored_directories
                and not d.endswith(".egg-info")
                and not is_ignored_path(d)
            ]

            for fname in files:
                abs_path = os.path.join(root, fname)
                try:
                    size = os.path.getsize(abs_path)
                except OSError:
                    continue

                rel = os.path.relpath(abs_path, self._clone_dir)
                rel = normalize_path(rel)
                if is_ignored_path(rel):
                    continue
                yield RepoEntry(path=rel, abs_path=abs_path, size_bytes=size)

    def cleanup(self) -> None:
        """Remove the temp directory if we created it."""
        if self._clone_dir and self._owns_dir:
            try:
                shutil.rmtree(self._clone_dir, ignore_errors=True)
                log_info(f"Cleaned up repo dir: {self._clone_dir}")
                logger.info("Cleaned up temp dir: %s", self._clone_dir)
            except Exception:
                pass
            self._clone_dir = None
