"""Secure handling of uploaded knowledge documents.

Two separate names matter for every document: `original_filename` (exactly
what the admin uploaded, used only for display -- never used to build a
filesystem path) and `filename`/`storage_path` (a server-generated,
UUID-based name actually written to disk). This is what makes path
traversal via a crafted filename (`../../etc/passwd`, `..\\..\\x`, absolute
paths, embedded null bytes, etc.) structurally impossible: the untrusted
string never reaches `open()`.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.config import get_settings


class FileValidationError(Exception):
    pass


_SAFE_EXT_RE = re.compile(r"^[a-z0-9]{1,10}$")


def extract_extension(original_filename: str) -> str:
    ext = Path(original_filename).suffix.lstrip(".").lower()
    if not ext or not _SAFE_EXT_RE.match(ext):
        raise FileValidationError("Could not determine a valid file extension.")
    return ext


def validate_upload(original_filename: str, file_size: int, max_size: int | None = None) -> str:
    """Returns the validated (lowercased) extension, or raises
    FileValidationError with a message safe to show the admin.

    `max_size` lets a caller enforce a tighter limit than the platform
    default (settings.MAX_FILE_SIZE) -- used by the self-serve builder to
    apply the calling user's plan limit (app/billing/plans.py) without
    changing the platform-admin upload path, which still just uses the
    default."""
    settings = get_settings()
    ext = extract_extension(original_filename)
    effective_max = settings.MAX_FILE_SIZE if max_size is None else max_size

    if ext not in settings.ALLOWED_FILE_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_FILE_EXTENSIONS)
        raise FileValidationError(f"'.{ext}' files aren't supported. Allowed types: {allowed}.")

    if file_size <= 0:
        raise FileValidationError("The uploaded file is empty.")
    if file_size > effective_max:
        max_mb = effective_max / (1024 * 1024)
        raise FileValidationError(f"File is too large. Maximum size is {max_mb:.0f} MB.")

    return ext


def build_storage_path(tenant_id: str, agent_id: int, ext: str) -> tuple[str, str]:
    """Returns (stored_filename, absolute_storage_path). tenant_id/agent_id
    are server-resolved values (never taken from user input directly as a
    path component without this function), and the filename itself is a
    fresh UUID -- nothing from the original filename is used in the path."""
    settings = get_settings()
    safe_tenant = re.sub(r"[^a-zA-Z0-9_-]", "_", tenant_id)[:80]

    directory = Path(settings.UPLOAD_DIR) / safe_tenant / str(agent_id)
    directory.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    full_path = directory / stored_filename

    # Defense in depth: confirm the resolved path is still inside UPLOAD_DIR.
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    if upload_root not in full_path.resolve().parents:
        raise FileValidationError("Invalid storage path.")

    return stored_filename, str(full_path)
