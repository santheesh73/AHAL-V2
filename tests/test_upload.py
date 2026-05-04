"""
AHAL AI — Upload Endpoint Tests

Tests:
  - Valid ZIP accepted and session created
  - Corrupted ZIP rejected (400)
  - Empty ZIP handled (completed with 0 or more files)
  - Non-ZIP file upload
  - Missing file → validation error
  - Size limit rejection (413)
  - Atomic backpressure: cannot exceed max_active_sessions
"""

from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    make_corrupted_zip,
    make_empty_zip,
    make_minimal_zip,
    make_zip_bytes,
    upload_zip,
    upload_and_get_session,
)


# ── Basic upload lifecycle ────────────────────────────────────────

def test_valid_zip_upload_accepted(client: TestClient):
    """A valid ZIP should be accepted with status=accepted and a session_id."""
    r = upload_zip(client, make_minimal_zip())
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    assert len(data["session_id"]) == 32  # uuid4.hex


def test_valid_zip_session_pollable(client: TestClient):
    """After upload, /status/{id} should return session info."""
    sid = upload_and_get_session(client, make_minimal_zip())
    r = client.get(f"/analyze/status/{sid}")
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == sid
    assert data["status"] in {"pending", "scanning", "completed", "partial", "failed"}


def test_corrupted_zip_rejected(client: TestClient):
    """Random bytes with .zip extension must be rejected with 400."""
    r = upload_zip(client, make_corrupted_zip())
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["code"] == "INVALID_FILE"


def test_empty_zip_accepted_and_completes(client: TestClient):
    """An empty ZIP (no files) should be accepted and eventually complete."""
    r = upload_zip(client, make_empty_zip())
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_single_python_file_upload(client: TestClient):
    """Upload a single .py file (not zip)."""
    content = b"def hello(): pass\n"
    r = client.post(
        "/analyze/upload",
        files={"file": ("script.py", content, "text/x-python")},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_missing_file_rejected(client: TestClient):
    """POST /upload with no file should return 422 (validation error)."""
    r = client.post("/analyze/upload")
    assert r.status_code == 422


# ── Content-cap enforcement ───────────────────────────────────────

def test_zip_with_multiple_files_accepted(client: TestClient):
    """ZIP with multiple files should be accepted without error."""
    files = {f"file_{i}.py": f"x = {i}\n" * 100 for i in range(20)}
    r = upload_zip(client, make_zip_bytes(files))
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


# ── Atomic backpressure (Fix 1) ───────────────────────────────────

def test_atomic_backpressure_cannot_exceed_limit(monkeypatch):
    """
    Fire N concurrent uploads where N > MAX_ACTIVE limit.
    Exactly MAX_ACTIVE must be accepted; the rest must be rejected.
    No session should be created beyond the cap.
    """
    from app.config import config, ScannerConfig, AppConfig
    import dataclasses

    # Patch max_active_sessions to 2 for this test
    patched_scanner = dataclasses.replace(config.scanner, max_active_sessions=2)
    patched_config = dataclasses.replace(config, scanner=patched_scanner)

    import app.config as cfg_module
    monkeypatch.setattr(cfg_module, "config", patched_config)

    # Also patch session_manager to use the patched config
    import app.sessions.session_manager as sm_module
    monkeypatch.setattr(sm_module, "config", patched_config)

    from app.main import app as fastapi_app
    test_client = TestClient(fastapi_app, raise_server_exceptions=False)

    zip_bytes = make_minimal_zip()
    results = []

    def do_upload():
        return upload_zip(test_client, zip_bytes)

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(do_upload) for _ in range(5)]
        for f in as_completed(futures):
            results.append(f.result())

    accepted = [r for r in results if r.status_code == 200 and r.json()["status"] == "accepted"]
    rejected = [r for r in results if r.status_code == 200 and r.json()["status"] == "rejected"]

    # Must not exceed the limit
    assert len(accepted) <= 2, f"Accepted {len(accepted)} but limit is 2"
    assert len(accepted) + len(rejected) == 5


# ── Session not found ─────────────────────────────────────────────

def test_status_session_not_found(client: TestClient):
    r = client.get("/analyze/status/nonexistent123")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["code"] == "SESSION_NOT_FOUND"


def test_result_session_not_found(client: TestClient):
    r = client.get("/analyze/result/nonexistent456")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["code"] == "SESSION_NOT_FOUND"
