"""Demo property listing catalog for the real-estate sample agent. Same
isolation principle as astrology_service.py / product_service.py."""
from __future__ import annotations

LISTINGS = [
    {
        "id": "re-101",
        "title": "Sunlit 2BR Condo",
        "location": "Austin, TX",
        "price": 415000,
        "bedrooms": 2,
        "type": "condo",
        "description": "Bright corner unit with a private balcony, 10 minutes from downtown.",
    },
    {
        "id": "re-102",
        "title": "Modern Family Home",
        "location": "Austin, TX",
        "price": 620000,
        "bedrooms": 4,
        "type": "house",
        "description": "Newly renovated 4-bed home with a large backyard and two-car garage.",
    },
    {
        "id": "re-103",
        "title": "Downtown Loft",
        "location": "Denver, CO",
        "price": 385000,
        "bedrooms": 1,
        "type": "loft",
        "description": "Industrial-style loft with exposed brick, walking distance to transit.",
    },
    {
        "id": "re-104",
        "title": "Suburban Starter Home",
        "location": "Denver, CO",
        "price": 340000,
        "bedrooms": 3,
        "type": "house",
        "description": "Cozy 3-bed home in a quiet, family-friendly neighborhood.",
    },
]


def search_properties(location: str | None = None, max_price: float | None = None, limit: int = 5) -> list[dict]:
    results = LISTINGS
    if location:
        loc = location.lower()
        results = [p for p in results if loc in p["location"].lower()]
    if max_price is not None:
        results = [p for p in results if p["price"] <= max_price]
    return results[:limit]


def get_property(property_id: str) -> dict | None:
    return next((p for p in LISTINGS if p["id"] == property_id), None)
