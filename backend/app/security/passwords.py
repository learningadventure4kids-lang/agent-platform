"""Password hashing for self-serve user accounts. Uses PBKDF2-HMAC-SHA256
(stdlib `hashlib`, no extra dependency) with a random per-user salt and a
high iteration count -- deliberately not a fast hash like plain SHA-256.
Stored format: "pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>", so the
iteration count can be raised later without invalidating existing hashes
(older rows just keep verifying at their original count)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 390_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations_str, salt, hash_hex = stored.split("$")
        if algorithm != _ALGORITHM:
            return False
        iterations = int(iterations_str)
    except (ValueError, AttributeError):
        return False

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return hmac.compare_digest(digest.hex(), hash_hex)
