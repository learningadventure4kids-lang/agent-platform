"""
Astrology chart calculation, isolated from the conversational agent.

IMPORTANT: the LLM is never allowed to invent astronomical positions. It can
only call `calculate_chart`, which returns data from this service.

This ships with a DEMO implementation (`DemoAstrologyChartService`) that
derives the sun sign correctly from the date of birth (real, simple
astronomy-by-calendar-date, no external dependency needed) but produces
clearly-labeled *placeholder* moon sign / ascendant / house data, since real
ascendant/house calculation requires precise birth time, birth place
geocoding, and an ephemeris (e.g. the `flatlib` or `pyswisseph` libraries).

To plug in a real ephemeris-backed implementation later:
  1. Implement `AstrologyChartService` (same interface).
  2. Swap the instance created in `get_astrology_service()`.
No other code needs to change.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Optional, TypedDict


class ChartResult(TypedDict):
    sun_sign: str
    moon_sign: Optional[str]
    ascendant: Optional[str]
    planets: list[dict[str, Any]]
    houses: list[dict[str, Any]]
    chart_data: dict[str, Any]
    is_demo: bool
    disclaimer: str


ZODIAC_SIGNS: list[tuple[str, tuple[int, int], tuple[int, int]]] = [
    ("Capricorn", (12, 22), (1, 19)),
    ("Aquarius", (1, 20), (2, 18)),
    ("Pisces", (2, 19), (3, 20)),
    ("Aries", (3, 21), (4, 19)),
    ("Taurus", (4, 20), (5, 20)),
    ("Gemini", (5, 21), (6, 20)),
    ("Cancer", (6, 21), (7, 22)),
    ("Leo", (7, 23), (8, 22)),
    ("Virgo", (8, 23), (9, 22)),
    ("Libra", (9, 23), (10, 22)),
    ("Scorpio", (10, 23), (11, 21)),
    ("Sagittarius", (11, 22), (12, 21)),
]

DISCLAIMER = (
    "Astrology is traditionally used for personal reflection and guidance. "
    "It isn't a scientifically validated method for predicting future events."
)


def sun_sign_for_date(dob: date) -> str:
    for sign, start, end in ZODIAC_SIGNS:
        start_month, start_day = start
        end_month, end_day = end
        if start_month == 12:  # wraps across year boundary (Capricorn)
            if (dob.month == 12 and dob.day >= start_day) or (
                dob.month == 1 and dob.day <= end_day
            ):
                return sign
        else:
            if (dob.month == start_month and dob.day >= start_day) or (
                dob.month == end_month and dob.day <= end_day
            ):
                return sign
    return "Unknown"


class AstrologyChartService(ABC):
    @abstractmethod
    def calculate_chart(
        self,
        date_of_birth: str,
        birth_time: Optional[str],
        birth_place: Optional[str],
        birth_country: Optional[str],
        birth_time_known: bool = True,
    ) -> ChartResult:
        ...


class DemoAstrologyChartService(AstrologyChartService):
    """Deterministic demo implementation.

    Sun sign is calculated for real from the calendar date. Moon
    sign/ascendant/houses are seeded deterministically from the input (so the
    same birth data always yields the same demo chart) but are NOT real
    ephemeris calculations, and are clearly labeled as such.
    """

    def calculate_chart(
        self,
        date_of_birth: str,
        birth_time: Optional[str] = None,
        birth_place: Optional[str] = None,
        birth_country: Optional[str] = None,
        birth_time_known: bool = True,
    ) -> ChartResult:
        try:
            dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("date_of_birth must be in YYYY-MM-DD format")

        sun_sign = sun_sign_for_date(dob)

        seed_source = f"{date_of_birth}|{birth_time or ''}|{birth_place or ''}"
        seed = int(hashlib.sha256(seed_source.encode()).hexdigest(), 16)
        signs = [s[0] for s in ZODIAC_SIGNS]
        moon_sign = signs[seed % 12]
        ascendant = signs[(seed // 12) % 12] if birth_time_known and birth_time else None

        planets = [
            {"name": "Sun", "sign": sun_sign, "demo": False},
            {"name": "Moon", "sign": moon_sign, "demo": True},
        ]
        if ascendant:
            planets.append({"name": "Ascendant", "sign": ascendant, "demo": True})
        for i, planet_name in enumerate(
            ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"], start=1
        ):
            planets.append(
                {"name": planet_name, "sign": signs[(seed // (12 * (i + 2))) % 12], "demo": True}
            )

        houses = [
            {"house": n, "sign": signs[(seed // (n + 1)) % 12], "demo": True}
            for n in range(1, 13)
        ]

        return {
            "sun_sign": sun_sign,
            "moon_sign": moon_sign,
            "ascendant": ascendant,
            "planets": planets,
            "houses": houses,
            "chart_data": {
                "date_of_birth": date_of_birth,
                "birth_time": birth_time,
                "birth_time_known": birth_time_known,
                "birth_place": birth_place,
                "birth_country": birth_country,
                "precision_note": (
                    "Ascendant and house placements require an exact birth time "
                    "and are approximate/omitted without one."
                    if not (birth_time_known and birth_time)
                    else "Demo ascendant/house placements shown; not ephemeris-calculated."
                ),
            },
            "is_demo": True,
            "disclaimer": DISCLAIMER,
        }


_service: Optional[AstrologyChartService] = None


def get_astrology_service() -> AstrologyChartService:
    global _service
    if _service is None:
        _service = DemoAstrologyChartService()
    return _service
