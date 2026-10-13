"""Sanitizes and records tool-execution attempts for the audit log.

Called from exactly one place: app/agents/graph.py's `execute_tool` node,
once per tool call attempt (success, denied, error, or timeout). Never
called with raw, unsanitized data -- sanitization happens here so there is
one place that decides what is safe to persist, rather than trusting every
call site to remember.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session as DBSession

from app.models.tool_execution_log import ToolExecutionLog

_SENSITIVE_KEY_MARKERS = ("email", "phone", "api_key", "password", "token", "secret")
_MAX_ARG_STRING_LEN = 200
_MAX_RESULT_LEN = 500


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


def sanitize_arguments(arguments: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Redact anything that looks like PII/secrets to a boolean "was this
    provided" flag; truncate long free-text fields. Keeps the audit log
    useful for debugging ("did the model pass an email at all?") without
    ever storing the email itself."""
    if not arguments:
        return {}
    out: dict[str, Any] = {}
    for key, value in arguments.items():
        lowered = key.lower()
        if any(marker in lowered for marker in _SENSITIVE_KEY_MARKERS):
            out[key] = bool(value)
            continue
        if isinstance(value, str):
            out[key] = _truncate(value, _MAX_ARG_STRING_LEN)
        elif isinstance(value, (int, float, bool)) or value is None:
            out[key] = value
        else:
            out[key] = _truncate(str(value), _MAX_ARG_STRING_LEN)
    return out


def sanitize_result(result: Any) -> Optional[str]:
    if result is None:
        return None
    return _truncate(str(result), _MAX_RESULT_LEN)


def record_execution(
    db: DBSession,
    agent_id: int,
    session_id: str,
    tool_name: str,
    status: str,
    arguments: Optional[dict[str, Any]],
    result: Any,
    started_at: datetime,
    completed_at: Optional[datetime] = None,
    error_category: Optional[str] = None,
) -> ToolExecutionLog:
    completed_at = completed_at or datetime.utcnow()
    duration_ms = (completed_at - started_at).total_seconds() * 1000

    row = ToolExecutionLog(
        agent_id=agent_id,
        session_id=session_id,
        tool_name=tool_name,
        status=status,
        error_category=error_category,
        sanitized_arguments=sanitize_arguments(arguments),
        sanitized_result=sanitize_result(result),
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
    )
    db.add(row)
    db.flush()
    return row
