"""Public agent tokens.

The token embedded in a website's widget snippet is, by definition, public
-- anyone who views page source can see it. It must therefore never be
treated like a secret credential. What it protects against is only:
casual misuse (someone copy-pasting another business's snippet) and lets us
resolve *which* agent configuration to load.

Only an HMAC-SHA256 hash of the token is ever stored, using
TOKEN_HASH_SECRET as the key. A stolen database dump cannot be used to
derive working tokens, and rotating a token is just generating a new
random value and re-hashing it.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from app.config import get_settings

TOKEN_PREFIX = "pub_"
SESSION_TOKEN_PREFIX = "usess_"


def generate_token() -> str:
    """A new, random, public agent token. Shown to the admin exactly once
    at creation/rotation time -- the plaintext is never stored."""
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def generate_session_token() -> str:
    """A new, random, self-serve user session token (app/models/user_session.py).
    Same HMAC-hash-at-rest treatment as a public agent token -- see
    `hash_token`/`tokens_match` below, which are generic over any token
    string and reused here rather than duplicated."""
    return f"{SESSION_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_token(token: str) -> str:
    settings = get_settings()
    return hmac.new(
        settings.TOKEN_HASH_SECRET.encode(), token.encode(), hashlib.sha256
    ).hexdigest()


def tokens_match(token: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), stored_hash)
