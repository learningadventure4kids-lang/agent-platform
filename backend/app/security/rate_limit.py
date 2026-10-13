"""Simple in-process sliding-window rate limiter.

Good enough for a single-process prototype/small deployment. For a
multi-worker or multi-instance production deployment, replace the
in-memory store with Redis (INCR + EXPIRE, or a token-bucket library) --
the `allow()` call site in app/api/chat.py doesn't need to change, only
this module's internals.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from app.config import get_settings


class SlidingWindowLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True


_limiter = SlidingWindowLimiter()


def check_rate_limit(agent_key: str, session_id: str, client_ip: str) -> tuple[bool, str]:
    """Returns (allowed, friendly_message_if_not)."""
    settings = get_settings()

    if not _limiter.allow(f"agent:{agent_key}", settings.RATE_LIMIT_PER_MINUTE):
        return False, "You're sending messages a little too quickly. Please try again in a moment."

    if not _limiter.allow(f"session:{session_id}", settings.RATE_LIMIT_PER_MINUTE):
        return False, "You're sending messages a little too quickly. Please try again in a moment."

    if not _limiter.allow(f"ip:{client_ip}", settings.RATE_LIMIT_PER_MINUTE_PER_IP):
        return False, "Too many requests from your network right now. Please try again shortly."

    return True, ""
