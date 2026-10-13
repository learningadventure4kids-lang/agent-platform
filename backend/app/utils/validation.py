"""Lightweight validation helpers shared by services and the agent tools.

Kept dependency-free (no external phone-number library) so the prototype has
no extra install requirements, while still accepting common international
formats (US, Canada, India, UK, etc.) and rejecting obvious junk.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Accepts optional leading +, optional spaces/dashes/parentheses, 7-15 digits.
PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,20}$")


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value.strip()))


def is_valid_phone(value: str) -> bool:
    value = value.strip()
    if not PHONE_RE.match(value):
        return False
    digits = re.sub(r"\D", "", value)
    return 7 <= len(digits) <= 15


def normalize_date_of_birth(value: str) -> Optional[str]:
    """Best-effort parse of a date string into YYYY-MM-DD. Returns None if it
    can't confidently parse (the LLM is expected to normalize most of the
    time; this is a safety net for direct API/tool calls)."""
    value = value.strip()
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def is_plausible_dob(value: str) -> bool:
    try:
        dob = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return False
    today = date.today()
    if dob > today:
        return False
    age_years = (today - dob).days / 365.25
    return 0 <= age_years <= 130


def normalize_birth_time(value: str) -> Optional[str]:
    """Best-effort parse into 24h HH:MM."""
    value = value.strip().upper().replace(".", "")
    formats = ["%H:%M", "%I:%M %p", "%I %p", "%I:%M%p", "%I%p"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


def is_valid_birth_time(value: str) -> bool:
    try:
        datetime.strptime(value, "%H:%M")
        return True
    except ValueError:
        return False
