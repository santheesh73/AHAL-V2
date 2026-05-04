"""
AHAL AI - Test Fixtures and Shared Configuration

Provides:
  - FastAPI TestClient (sync)
  - Repo-local tmp_path fixture
  - ZIP file factory
  - Monkeypatch helpers for config-driven limits
"""

from __future__ import annotations

import io
import shutil
import tempfile
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Shared TestClient for the full FastAPI app."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def fresh_client() -> TestClient:
    """Per-test client - useful when state must be isolated."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def tmp_path() -> Path:
    """
    Repo-local tmp_path override for Windows environments where pytest's
    default temp-root cleanup can hit permission issues.
    """
    root = Path(__file__).resolve().parents[1] / "tmp-pytest-run2"
    root.mkdir(exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="case-", dir=root))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def make_zip_bytes(files: dict[str, str]) -> bytes:
    """
    Build a valid ZIP file in memory.

    Args:
        files: mapping of {filename: content_string}

    Returns:
        Raw ZIP bytes suitable for multipart upload.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def make_minimal_zip() -> bytes:
    """ZIP with a single Python file."""
    return make_zip_bytes({"main.py": "print('hello')\n"})


def make_empty_zip() -> bytes:
    """ZIP with no files."""
    return make_zip_bytes({})


def make_corrupted_zip() -> bytes:
    """Random bytes that look like a zip by extension but are not."""
    return b"PK\x00\x00GARBAGE_NOT_A_REAL_ZIP"


def upload_zip(client: TestClient, zip_bytes: bytes, filename: str = "test.zip") -> dict:
    """POST a zip file to /analyze/upload and return the JSON response."""
    response = client.post(
        "/analyze/upload",
        files={"file": (filename, zip_bytes, "application/zip")},
    )
    return response


def upload_and_get_session(client: TestClient, zip_bytes: bytes) -> str:
    """Upload a ZIP and return the session_id (asserts accepted)."""
    r = upload_zip(client, zip_bytes)
    assert r.status_code == 200, f"Upload failed: {r.text}"
    data = r.json()
    assert data["status"] == "accepted", f"Expected accepted, got: {data}"
    return data["session_id"]
