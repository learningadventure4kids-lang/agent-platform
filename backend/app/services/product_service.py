"""Demo jewellery product catalog. Same idea as astrology_service.py: an
isolated service the `search_jewellery` / `get_product_details` tools call,
so the LLM never invents product data. Swap for a real catalog/DB or
e-commerce API integration later behind the same two functions."""
from __future__ import annotations

CATALOG = [
    {
        "id": "kj-001",
        "name": "Aurora Diamond Necklace",
        "category": "necklace",
        "occasion": ["wedding", "anniversary"],
        "price": 2450.0,
        "currency": "USD",
        "description": "18k white gold necklace with a 1.2ct diamond pendant.",
    },
    {
        "id": "kj-002",
        "name": "Meadow Gold Bangle",
        "category": "bracelet",
        "occasion": ["everyday", "gift"],
        "price": 680.0,
        "currency": "USD",
        "description": "22k gold bangle with a hand-engraved floral pattern.",
    },
    {
        "id": "kj-003",
        "name": "Celeste Sapphire Ring",
        "category": "ring",
        "occasion": ["engagement", "anniversary"],
        "price": 3200.0,
        "currency": "USD",
        "description": "Blue sapphire halo ring set in platinum.",
    },
    {
        "id": "kj-004",
        "name": "Ember Pearl Earrings",
        "category": "earrings",
        "occasion": ["wedding", "gift", "everyday"],
        "price": 340.0,
        "currency": "USD",
        "description": "Freshwater pearl drop earrings in rose gold.",
    },
    {
        "id": "kj-005",
        "name": "Solstice Statement Necklace",
        "category": "necklace",
        "occasion": ["party", "gift"],
        "price": 890.0,
        "currency": "USD",
        "description": "Bold gold-plated statement piece with citrine accents.",
    },
]


def search_products(query: str, limit: int = 5) -> list[dict]:
    q = query.lower()
    scored = []
    for item in CATALOG:
        haystack = " ".join(
            [item["name"], item["category"], item["description"], " ".join(item["occasion"])]
        ).lower()
        score = sum(1 for word in q.split() if word in haystack)
        if score > 0 or not q.strip():
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]] or CATALOG[:limit]


def get_product(product_id: str) -> dict | None:
    return next((item for item in CATALOG if item["id"] == product_id), None)
