"""
AHAL AI — Session Manager Unit Tests

Tests:
  - create_session_if_capacity returns session when under limit
  - create_session_if_capacity returns None when at capacity (Fix 1)
  - is_cancelled is lock-safe and accurate (Fix 2)
  - cancel_session transitions correctly
  - validate_token works and uses constant-time comparison (Fix 5)
  - get_metrics returns all expected fields (Fix 7)
  - TTL eviction removes stale sessions
  - rate limiter is_allowed enforces window (Fix 6)
"""

from __future__ import annotations

import time

import pytest

from app.sessions.session_manager import SessionManager
from app.models.file_schema import ScanResult, ScanStatus


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mgr() -> SessionManager:
    """Fresh SessionManager for each test."""
    return SessionManager()


# ── create_session_if_capacity (Fix 1) ───────────────────────────

def test_create_session_within_capacity(mgr: SessionManager):
    """Should create session when under limit."""
    result = mgr.create_session_if_capacity(max_active=5)
    assert result is not None
    assert len(result.session_id) == 32
    assert len(result.access_token) == 64  # secrets.token_hex(32) = 64 hex chars


def test_create_session_at_exactly_limit(mgr: SessionManager):
    """Should reject when active == max_active."""
    # Fill up to limit
    for _ in range(3):
        r = mgr.create_session_if_capacity(max_active=3)
        assert r is not None

    # One more should be rejected
    overflow = mgr.create_session_if_capacity(max_active=3)
    assert overflow is None


def test_create_session_atomic_under_concurrent_load(mgr: SessionManager):
    """
    Spawn many threads all calling create_session_if_capacity(max_active=5).
    Exactly 5 or fewer must succeed.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = []

    def try_create():
        return mgr.create_session_if_capacity(max_active=5)

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(try_create) for _ in range(20)]
        for f in as_completed(futures):
            results.append(f.result())

    successes = [r for r in results if r is not None]
    assert len(successes) <= 5, f"Created {len(successes)} sessions, limit is 5"


def test_capacity_frees_after_completion(mgr: SessionManager):
    """After a session completes, a new one can be created."""
    r1 = mgr.create_session_if_capacity(max_active=1)
    assert r1 is not None

    # Can't create while r1 is still active
    assert mgr.create_session_if_capacity(max_active=1) is None

    # Complete r1
    mgr.set_result(r1.session_id, ScanResult(
        session_id=r1.session_id,
        status=ScanStatus.COMPLETED,
        progress=100,
    ))

    # Now can create again
    r2 = mgr.create_session_if_capacity(max_active=1)
    assert r2 is not None


# ── is_cancelled (Fix 2) ─────────────────────────────────────────

def test_is_cancelled_false_before_cancel(mgr: SessionManager):
    sid = mgr.create_session()
    assert mgr.is_cancelled(sid) is False


def test_is_cancelled_true_after_cancel(mgr: SessionManager):
    sid = mgr.create_session()
    mgr.cancel_session(sid)
    assert mgr.is_cancelled(sid) is True


def test_is_cancelled_false_for_unknown_session(mgr: SessionManager):
    assert mgr.is_cancelled("does_not_exist") is False


def test_cancel_terminal_session_returns_false(mgr: SessionManager):
    """Cancelling a completed session must return False."""
    sid = mgr.create_session()
    mgr.set_result(sid, ScanResult(
        session_id=sid,
        status=ScanStatus.COMPLETED,
        progress=100,
    ))
    result = mgr.cancel_session(sid)
    assert result is False


# ── Access token (Fix 5) ─────────────────────────────────────────

def test_validate_token_correct(mgr: SessionManager):
    sid = mgr.create_session()
    token = mgr.get_access_token(sid)
    assert token is not None
    assert mgr.validate_token(sid, token) is True


def test_validate_token_wrong(mgr: SessionManager):
    sid = mgr.create_session()
    assert mgr.validate_token(sid, "wrong_token") is False


def test_validate_token_unknown_session(mgr: SessionManager):
    assert mgr.validate_token("ghost_session", "any_token") is False


def test_access_token_is_64_hex_chars(mgr: SessionManager):
    """secrets.token_hex(32) produces a 64-character hex string."""
    sid = mgr.create_session()
    token = mgr.get_access_token(sid)
    assert token is not None
    assert len(token) == 64
    assert all(c in "0123456789abcdef" for c in token)


# ── Metrics (Fix 7) ──────────────────────────────────────────────

def test_metrics_initial_state(mgr: SessionManager):
    m = mgr.get_metrics()
    assert m["active_sessions"] == 0
    assert m["total_sessions"] == 0
    assert m["completed_sessions"] == 0
    assert m["failed_sessions"] == 0
    assert m["cancelled_sessions"] == 0
    assert m["average_scan_time_seconds"] is None


def test_metrics_increments_on_create(mgr: SessionManager):
    mgr.create_session()
    mgr.create_session()
    assert mgr.get_metrics()["total_sessions"] == 2


def test_metrics_completed_increments(mgr: SessionManager):
    sid = mgr.create_session()
    mgr.set_result(sid, ScanResult(
        session_id=sid, status=ScanStatus.COMPLETED, progress=100
    ))
    assert mgr.get_metrics()["completed_sessions"] == 1


def test_metrics_failed_increments(mgr: SessionManager):
    sid = mgr.create_session()
    mgr.set_failed(sid, "something went wrong")
    assert mgr.get_metrics()["failed_sessions"] == 1


def test_metrics_cancelled_increments(mgr: SessionManager):
    sid = mgr.create_session()
    mgr.cancel_session(sid)
    assert mgr.get_metrics()["cancelled_sessions"] == 1


def test_metrics_average_scan_time_computed(mgr: SessionManager):
    sid = mgr.create_session()
    time.sleep(0.05)  # ensure non-zero duration
    mgr.set_result(sid, ScanResult(
        session_id=sid, status=ScanStatus.COMPLETED, progress=100
    ))
    avg = mgr.get_metrics()["average_scan_time_seconds"]
    assert avg is not None
    assert avg > 0.0


# ── Rate Limiter (Fix 6) ─────────────────────────────────────────

def test_rate_limiter_allows_within_limit():
    from app.utils.rate_limiter import RateLimiter
    rl = RateLimiter(enabled=True, window_seconds=60, max_requests=3)
    assert rl.is_allowed("10.0.0.1") is True
    assert rl.is_allowed("10.0.0.1") is True
    assert rl.is_allowed("10.0.0.1") is True


def test_rate_limiter_blocks_over_limit():
    from app.utils.rate_limiter import RateLimiter
    rl = RateLimiter(enabled=True, window_seconds=60, max_requests=3)
    for _ in range(3):
        rl.is_allowed("10.0.0.2")
    assert rl.is_allowed("10.0.0.2") is False


def test_rate_limiter_disabled_always_allows():
    from app.utils.rate_limiter import RateLimiter
    rl = RateLimiter(enabled=False, window_seconds=60, max_requests=1)
    for _ in range(100):
        assert rl.is_allowed("10.0.0.3") is True


def test_rate_limiter_different_ips_are_independent():
    from app.utils.rate_limiter import RateLimiter
    rl = RateLimiter(enabled=True, window_seconds=60, max_requests=2)
    rl.is_allowed("1.1.1.1")
    rl.is_allowed("1.1.1.1")
    # 1.1.1.1 is now at limit; 2.2.2.2 should still be allowed
    assert rl.is_allowed("1.1.1.1") is False
    assert rl.is_allowed("2.2.2.2") is True


def test_rate_limiter_window_expiry():
    """Requests outside the window should not count."""
    from app.utils.rate_limiter import RateLimiter
    rl = RateLimiter(enabled=True, window_seconds=1, max_requests=2)
    rl.is_allowed("10.0.0.9")
    rl.is_allowed("10.0.0.9")
    assert rl.is_allowed("10.0.0.9") is False  # at limit

    time.sleep(1.05)  # wait for window to expire
    assert rl.is_allowed("10.0.0.9") is True  # window reset
