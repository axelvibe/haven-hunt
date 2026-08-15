"""Shared filter/kayword matching used by listing providers (Ireland)."""
from __future__ import annotations

from typing import Any

from product.listings.counties import COUNTY_ALIASES
from product.listings.models import Listing


def matches(l: Listing, query: str, filters: dict[str, Any]) -> bool:
    q = (query or "").strip().lower()
    if q:
        haystack = " ".join(
            [
                l.title,
                l.description,
                l.neighborhood,
                l.city,
                l.county,
                l.eircode or "",
                l.property_type,
                l.listing_type,
                " ".join(l.amenities),
            ]
        ).lower()
        words = [w for w in q.split() if w]
        if not any(word in haystack for word in words):
            return False

    if filters.get("listing_type") and l.listing_type != filters["listing_type"]:
        return False
    if filters.get("min_price") is not None and l.price < filters["min_price"]:
        return False
    if filters.get("max_price") is not None and l.price > filters["max_price"]:
        return False
    if filters.get("beds_min") is not None:
        if l.beds is None:
            return False  # PPR does not record bedrooms; can't confirm
        if l.beds < filters["beds_min"]:
            return False
    if filters.get("pet_friendly") is True and not l.pet_friendly:
        return False
    if filters.get("counties"):
        aliases = {COUNTY_ALIASES.get(n.lower(), n.lower()).lower() for n in filters["counties"]}
        if l.county.lower() not in aliases:
            return False
    if filters.get("neighborhoods"):
        target = {n.lower() for n in filters["neighborhoods"]}
        if l.neighborhood.lower() not in target:
            return False
    return True
