"""
AHAL AI — ZIP Handler
Streaming extraction of ZIP archives without loading the entire archive into memory.
Uses ZipFile.infolist() to iterate entries and reads each file individually.
"""

from __future__ import annotations

import logging
import os
import threading
import zipfile
from typing import Callable, Generator, Optional, Tuple

from app.config import ScannerConfig
from app.utils.safe_utils import normalize_path

logger = logging.getLogger("ahal.scanner.zip")


class ZipEntry:
    """Lightweight descriptor for a single ZIP entry."""

    __slots__ = ("path", "size_bytes", "is_dir")

    def __init__(self, path: str, size_bytes: int, is_dir: bool) -> None:
        self.path = path
        self.size_bytes = size_bytes
        self.is_dir = is_dir


class ZipHandler:
    """
    Handles ZIP archive scanning via streaming.

    The archive is opened ONCE and entries are yielded lazily via
    ``iter_entries``.  Content for individual files is read on‑demand
    via ``read_entry``.
    """

    def __init__(self, zip_path: str, cfg: ScannerConfig) -> None:
        self._zip_path = zip_path
        self._cfg = cfg
        self._zf: Optional[zipfile.ZipFile] = None
        # Fix 4: serialize concurrent ZipFile reads from inner thread pool
        self._read_lock = threading.Lock()

    # ── Context manager ──────────────────────────────────────────

    def open(self) -> None:
        """Open the ZIP file for reading."""
        try:
            self._zf = zipfile.ZipFile(self._zip_path, "r")
            logger.info("Opened ZIP: %s", self._zip_path)
        except (zipfile.BadZipFile, Exception) as exc:
            logger.error("Failed to open ZIP %s: %s", self._zip_path, exc)
            raise

    def close(self) -> None:
        """Close the ZIP file handle."""
        if self._zf is not None:
            try:
                self._zf.close()
            except Exception:
                pass
            self._zf = None

    def __enter__(self) -> "ZipHandler":
        self.open()
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # ── Iteration ────────────────────────────────────────────────

    def iter_entries(self) -> Generator[ZipEntry, None, None]:
        """
        Yield ZipEntry objects for every member in the archive.
        Directories are yielded with is_dir=True so callers can skip them.
        """
        if self._zf is None:
            raise RuntimeError("ZipHandler is not open")

        for info in self._zf.infolist():
            path = normalize_path(info.filename)
            is_dir = info.is_dir()
            size = info.file_size if not is_dir else 0
            yield ZipEntry(path=path, size_bytes=size, is_dir=is_dir)

    # ── Reading ──────────────────────────────────────────────────

    def read_entry(self, entry_path: str, max_bytes: int) -> Optional[bytes]:
        """
        Read up to *max_bytes* of the specified entry.
        Returns None on any error.

        The ZipFile handle is not thread-safe, so reads are serialized
        via _read_lock (Fix 4). The lock is released before decoding.
        """
        if self._zf is None:
            return None
        try:
            with self._read_lock:
                with self._zf.open(entry_path) as fh:
                    raw = fh.read(max_bytes)
            # Lock released — decoding happens here without holding it
            return raw
        except Exception as exc:
            logger.warning("Failed to read ZIP entry %s: %s", entry_path, exc)
            return None

    @property
    def entry_count(self) -> int:
        """Total entries in the archive (files + dirs)."""
        if self._zf is None:
            return 0
        return len(self._zf.infolist())
