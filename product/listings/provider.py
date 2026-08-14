"""Listing provider interface + factory.

The product ships with a built-in demo dataset so it works with zero setup.
When SIMPLYRETS_USERNAME/PASSWORD are provided, live listings are fetched
through the SimplyRETS API and merged with (or replace) the demo set.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from product.listings.models import Listing
from product.listings.sample_data import LISTINGS

log = logging.getLogger("havenhunt.listings")


class ListingsProvider:
    """Interface all providers implement."""

    name = "base"

    def all(self) -> list[Listing]:
        raise NotImplementedError

    def search(
        self,
        query: str = "",
        listing_type: str | None = None,  # "rent" | "sale"
        min_price: float | None = None,
        max_price: float | None = None,
        beds_min: float | None = None,
        neighborhoods: list[str] | None = None,
        pet_friendly: bool | None = None,
        limit: int = 12,
    ) -> list[Listing]:
        raise NotImplementedError


def _matches(l: Listing, query: str, filters: dict[str, Any]) -> bool:
    q = query.lower()
    if q:
        haystack = " ".join(
            [
                l.title,
                l.description,
                l.neighborhood,
                l.property_type,
                l.listing_type,
                " ".join(l.amenities),
            ]
        ).lower()
        if all(word in haystack for word in q.split()):
            pass
        elif not any(word in haystack for word in q.split()):
            return False

    if filters.get("listing_type") and l.listing_type != filters["listing_type"]:
        return False
    if filters.get("min_price") is not None and l.price < filters["min_price"]:
        return False
    if filters.get("max_price") is not None and l.price > filters["max_price"]:
        return False
    if filters.get("beds_min") is not None and l.beds < filters["beds_min"]:
        return False
    if filters.get("pet_friendly") is True and not l.pet_friendly:
        return False
    if filters.get("neighborhoods"):
        if l.neighborhood.lower() not in {n.lower() for n in filters["neighborhoods"]}:
            return False
    return True


class StaticProvider(ListingsProvider):
    """Serves the curated demo dataset. Fast, offline, deterministic."""

    name = "demo"

    def __init__(self, listings: list[Listing] | None = None) -> None:
        self._listings = listings if listings is not None else LISTINGS

    def all(self) -> list[Listing]:
        return self._listings

    def search(self, **kw: Any) -> list[Listing]:
        query = kw.pop("query", "")
        limit = kw.pop("limit", 12)
        matches = [l for l in self._listings if _matches(l, query, kw)]
        return matches[:limit]


class CompositeProvider(ListingsProvider):
    """Demo data first; live listings enrich the results when available."""

    name = "composite"

    def __init__(self, providers: list[ListingsProvider]) -> None:
        self.providers = providers

    def all(self) -> list[Listing]:
        out: list[Listing] = []
        seen: set[str] = set()
        for p in self.providers:
            for l in p.all():
                if l.id not in seen:
                    seen.add(l.id)
                    out.append(l)
        return out

    def search(self, **kw: Any) -> list[Listing]:
        out: list[Listing] = []
        seen: set[str] = set()
        for p in self.providers:
            try:
                for l in p.search(**kw):
                    if l.id not in seen:
                        seen.add(l.id)
                        out.append(l)
            except Exception as exc:  # noqa: BLE001
                log.warning("Provider %s failed: %s", p.name, exc)
        return out[: kw.get("limit", 12)]


def build_provider() -> ListingsProvider:
    """Build the provider from environment configuration."""
    username = os.getenv("SIMPLYRETS_USERNAME", "").strip()
    password = os.getenv("SIMPLYRETS_PASSWORD", "").strip()

    providers: list[ListingsProvider] = [StaticProvider()]
    if username and password:
        try:
            from product.listings.simplyrets import SimplyRETSProvider

            providers.append(SimplyRETSProvider(username=username, password=password))
            log.info("Live SimplyRETS provider enabled.")
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not initialise SimplyRETS provider: %s", exc)
    if len(providers) > 1:
        return CompositeProvider(providers)
    return providers[0]
