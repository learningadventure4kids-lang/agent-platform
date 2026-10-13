"""Reversible encryption for provider API keys.

Unlike `app/security/tokens.py` (one-way HMAC hashing -- correct for
public agent tokens, which only ever need to be *verified*, never
retrieved), provider API keys must be decrypted again to actually call the
provider's API. Fernet (AES-128-CBC + HMAC, from the already-installed
`cryptography` package) gives authenticated, reversible encryption keyed
by a single secret (`ENCRYPTION_KEY`) that never leaves the backend.

Nothing outside this module and `app/ai/factory.py` should ever see a
decrypted API key.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def _fernet() -> Fernet:
    settings = get_settings()
    # ENCRYPTION_KEY can be any string (not necessarily a valid Fernet key);
    # derive a proper 32-byte urlsafe-base64 key from it via SHA-256 so
    # operators can set a plain passphrase in .env rather than having to
    # generate a Fernet key themselves.
    digest = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Could not decrypt stored credential -- ENCRYPTION_KEY may have changed."
        ) from exc
