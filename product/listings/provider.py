"""Listing provider interface + factory.

The product ships with two offline sources that work with zero setup:
  * demo rentals (sample_data.py) — simulated, clearly labelled `demo`
  * a real PPR sales snapshot (data/ppr_snapshot.json) — live Irish sales data
When PPR_FETCH is enabled (default "auto"), the live PPR API provider is added
and the snapshot's record is refreshed on the next run.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from product.listings.base import ListingsProvider
from product.listings.matching import matches as _matches
from product.listings.models import Listing
from product.listings.ppr import PPRSnapshotProvider
from product.listings.sample_data import LISTINGS

log = logging.getLogger("havenhunt.listings")


class StaticProvider(ListingsProvider):
    """Serves the curated demo rental dataset. Fast, offline, deterministic."""

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
    """Offline sources first; live providers enrich the results when available."""

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
    """Build the provider: demo rentals + PPR snapshot, plus live PPR when enabled."""
    providers: list[ListingsProvider] = [StaticProvider()]
    providers.append(PPRSnapshotProvider())
    log.info("PPR snapshot provider enabled (offline real sales data).")

    if os.getenv("PPR_FETCH", "auto").lower() != "off":
        try:
            from product.listings.ppr import PPRApiProvider

            providers.append(PPRApiProvider())
            log.info("Live PPR API provider enabled.")
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not initialise live PPR provider: %s", exc)

    return CompositeProvider(providers)
