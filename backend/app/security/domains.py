"""Server-side check that a chat request is coming from a domain the agent
has allow-listed. This is separate from (and in addition to) browser CORS:
CORS only affects what a *browser* will let JS read, it does nothing to
stop a direct server-to-server request, so the real enforcement has to
happen here by reading Origin/Referer.

An empty allowed_domains list means "no restriction" (useful in local
development, or for agents happy to be embedded anywhere).
"""
from __future__ import annotations

from urllib.parse import urlparse

from fastapi import Request


def _hostname_from(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlparse(value)
        return (parsed.hostname or value).lower()
    except Exception:
        return None


def is_origin_allowed(allowed_domains: list[str], request: Request) -> bool:
    if not allowed_domains:
        return True

    allowed = {d.lower().lstrip("www.") for d in allowed_domains}
    allowed |= {f"www.{d}" for d in allowed}

    candidate = _hostname_from(request.headers.get("origin")) or _hostname_from(
        request.headers.get("referer")
    )
    if candidate is None:
        # No browser Origin/Referer at all (e.g. server-to-server or a
        # tool like curl) -- allow it through; this check exists to stop
        # unauthorized *browser embeds*, not to replace the token check.
        return True

    return candidate in allowed
