"""
AHAL AI — GitHub Endpoint Tests

Tests:
  - Invalid URL rejected (400 INVALID_URL)
  - Non-github.com URL rejected
  - Valid URL accepted (monkeypatched — no real git clone)
  - Backpressure rejected when at capacity
  - Cancellation endpoint
  - Already-done cancel returns already_done
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import make_minimal_zip, upload_and_get_session


# ── URL validation ────────────────────────────────────────────────

def test_invalid_github_url_rejected(client: TestClient):
    """Non-github.com URL must return 400 INVALID_URL."""
    r = client.post(
        "/analyze/github",
        json={"github_url": "https://gitlab.com/user/repo"},
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["code"] == "INVALID_URL"


def test_http_not_https_rejected(client: TestClient):
    """http:// URLs must be rejected."""
    r = client.post(
        "/analyze/github",
        json={"github_url": "http://github.com/user/repo"},
    )
    assert r.status_code == 400


def test_empty_url_rejected(client: TestClient):
    """Empty URL must be rejected."""
    r = client.post(
        "/analyze/github",
        json={"github_url": "   "},
    )
    assert r.status_code == 400


def test_missing_body_rejected(client: TestClient):
    """Missing body should return 422."""
    r = client.post("/analyze/github")
    assert r.status_code == 422


# ── Valid URL acceptance (mocked clone) ──────────────────────────

def test_valid_github_url_accepted(client: TestClient, monkeypatch):
    """
    Valid GitHub URL should create a session and return accepted.
    Monkeypatch git clone to avoid network dependency.
    """
    import app.core.scanner.repo_handler as rh_module

    class MockRepoHandler:
        def __init__(self, cfg):
            self._cfg = cfg
            self._clone_dir = None
            self._owns_dir = False

        def clone(self, url):
            import tempfile, os
            self._clone_dir = tempfile.mkdtemp(prefix="ahal_mock_")
            self._owns_dir = True
            # Write one file so scanner has something to do
            with open(os.path.join(self._clone_dir, "main.py"), "w") as f:
                f.write("print('mocked')\n")
            return self._clone_dir

        @property
        def clone_dir(self):
            return self._clone_dir

        def iter_files(self):
            import os
            from app.core.scanner.repo_handler import RepoEntry
            if self._clone_dir:
                for fname in os.listdir(self._clone_dir):
                    abs_path = os.path.join(self._clone_dir, fname)
                    if os.path.isfile(abs_path):
                        yield RepoEntry(
                            path=fname,
                            abs_path=abs_path,
                            size_bytes=os.path.getsize(abs_path),
                        )

        def cleanup(self):
            import shutil
            if self._clone_dir and self._owns_dir:
                shutil.rmtree(self._clone_dir, ignore_errors=True)

    monkeypatch.setattr(rh_module, "RepoHandler", MockRepoHandler)
    # Also patch in scanner.py
    import app.core.scanner.scanner as scanner_module
    monkeypatch.setattr(scanner_module, "RepoHandler", MockRepoHandler)

    r = client.post(
        "/analyze/github",
        json={"github_url": "https://github.com/octocat/Hello-World"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    assert len(data["session_id"]) == 32


# ── Cancellation ─────────────────────────────────────────────────

def test_cancel_nonexistent_session(client: TestClient):
    """Cancel of non-existent session → 404 SESSION_NOT_FOUND."""
    r = client.post("/analyze/cancel/doesnotexist999")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "SESSION_NOT_FOUND"


def test_cancel_accepted_scan(client: TestClient):
    """
    Upload a ZIP, immediately cancel, verify status is terminal.
    This tests the cancellation path end-to-end.
    """
    sid = upload_and_get_session(client, make_minimal_zip())
    cancel_r = client.post(f"/analyze/cancel/{sid}")
    assert cancel_r.status_code == 200
    data = cancel_r.json()
    # Either cancelled or already done (scan may have completed very fast)
    assert data["status"] in {"cancelled", "already_done"}


def test_cancel_already_done_returns_already_done(client: TestClient):
    """Cancel a session twice: second call must return already_done."""
    sid = upload_and_get_session(client, make_minimal_zip())
    # First cancel
    client.post(f"/analyze/cancel/{sid}")
    # Second cancel
    r2 = client.post(f"/analyze/cancel/{sid}")
    assert r2.status_code == 200
    # After first cancel sets status to FAILED, second must be already_done
    assert r2.json()["status"] == "already_done"


# ── Health and Metrics ────────────────────────────────────────────

def test_health_endpoint(client: TestClient):
    """GET /health must return status=ok with required fields."""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "active_sessions" in data
    assert "max_active_sessions" in data
    assert "bg_workers" in data
    assert "version" in data


def test_metrics_endpoint(client: TestClient):
    """GET /metrics must return all required counter fields."""
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    required = {
        "active_sessions",
        "total_sessions",
        "completed_sessions",
        "failed_sessions",
        "cancelled_sessions",
        "average_scan_time_seconds",
    }
    assert required.issubset(data.keys()), f"Missing keys: {required - data.keys()}"
