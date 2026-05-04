"""
AHAL AI — Per-IP Rate Limiter  [Fix 6]

Sliding-window in-memory rate limiter.
Thread-safe via threading.Lock.
Disabled by default (AHAL_RATE_LIMIT_ENABLED=false).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque, Dict


class RateLimiter:
    """
    Sliding-window per-IP rate limiter.

    Each IP maintains a deque of monotonic timestamps for requests within
    the current window.  On each check:
      1. Pop entries older than the window.
      2. If len(deque) >= max_requests → denied.
      3. Otherwise append current timestamp → allowed.

    Time complexity: O(k) where k = requests per IP in window.
    Space complexity: O(IPs × max_requests).
    """

    def __init__(
        self,
        enabled: bool,
        window_seconds: int,
        max_requests: int,
    ) -> None:
        self._enabled = enabled
        self._window = window_seconds
        self._max = max_requests
        self._lock = threading.Lock()
        self._buckets: Dict[str, Deque[float]] = {}

    # ── Public API ────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    def is_allowed(self, ip: str) -> bool:
        """
        Return True if the request from *ip* is within the rate limit.
        Return False if the limit is exceeded.
        Always returns True when the limiter is disabled.
        """
        if not self._enabled:
            return True

        now = time.monotonic()
        cutoff = now - self._window

        with self._lock:
            if ip not in self._buckets:
                self._buckets[ip] = deque()

            bucket = self._buckets[ip]

            # Evict timestamps outside the current window
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= self._max:
                return False

            bucket.append(now)
            return True

    def reset(self, ip: str) -> None:
        """Clear the bucket for an IP (useful for testing)."""
        with self._lock:
            self._buckets.pop(ip, None)

    def reset_all(self) -> None:
        """Clear all buckets (useful for testing)."""
        with self._lock:
            self._buckets.clear()


# ── Module-level singleton ────────────────────────────────────────
# Lazy-initialized so tests can override config before first use.

_rate_limiter_instance: RateLimiter | None = None
_rl_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """Return the singleton RateLimiter, creating it on first call."""
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        with _rl_lock:
            if _rate_limiter_instance is None:
                from app.config import config
                _rate_limiter_instance = RateLimiter(
                    enabled=config.scanner.rate_limit_enabled,
                    window_seconds=config.scanner.rate_limit_window_seconds,
                    max_requests=config.scanner.rate_limit_max_requests,
                )
    return _rate_limiter_instance
