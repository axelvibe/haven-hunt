"""Live listings via the SimplyRETS API.

SimplyRETS is a real-estate data provider (free trial available per MLS market).
Docs: https://docs.simplyrets.com/

Environment:
    SIMPLYRETS_USERNAME=your_api_key
    SIMPLYRETS_PASSWORD=your_api_secret
"""
from __future__ import annotations

import logging
from typing import Any

import requests

from product.listings.models import Listing
from product.listings.provider import _matches, ListingsProvider

log = logging.getLogger("havenhunt.listings.simplyrets")

BASE_URL = "https://api.simplyrets.com/properties"


class SimplyRETSProvider(ListingsProvider):
    name = "simplyrets"

    def __init__(self, username: str, password: str, limit_per_fetch: int = 250) -> None:
        self.auth = (username, password)
        self.limit_per_fetch = limit_per_fetch
        self._cache: list[Listing] | None = None

    # ---- API ----------------------------------------------------------
    def _fetch(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        offset = 0
        while True:
            params = {"limit": self.limit_per_fetch, "offset": offset}
            resp = requests.get(
                BASE_URL,
                params=params,
                auth=self.auth,
                timeout=30,
                headers={"User-Agent": "HavenHuntBot/1.0"},
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            out.extend(batch)
            if len(batch) < self.limit_per_fetch:
                break
            offset += self.limit_per_fetch
        return out

    def all(self) -> list[Listing]:
        if self._cache is None:
            raw = self._fetch()
            self._cache = [self._convert(r) for r in raw if self._convert(r)]
            log.info("Loaded %d live listings from SimplyRETS.", len(self._cache))
        return self._cache

    @staticmethod
    def _convert(r: dict[str, Any]) -> Listing | None:
        try:
            ltype = "sale" if not r.get("listPrice") or r.get("listType") == "Sale" else "rent"
            if r.get("leaseType"):
                ltype = "rent"
            beds = r.get("beds", 0)
            return Listing(
                id=str(r.get("mlId") or r.get("listingId") or "SR-" + str(r.get("address", {}).get("city", ""))),
                listing_type=ltype,
                property_type=(r.get("property", {}) or {}).get("type", "apartment"),
                title=f"{beds}-Bedroom {ltype} in {(r.get('address', {}) or {}).get('neighborhood', 'Chicago')}",
                price=float(r.get("listPrice") or 0),
                beds=float(beds or 0),
                baths=float(r.get("bathsFull", 0) or 0) + 0.5 * float(r.get("bathsHalf", 0) or 0),
                sqft=int(r.get("sqft", 0) or 0),
                neighborhood=(r.get("address", {}) or {}).get("neighborhood", "") or "Chicago",
                city=(r.get("address", {}) or {}).get("city", "Chicago"),
                state=(r.get("address", {}) or {}).get("state", "IL"),
                zipcode=str((r.get("address", {}) or {}).get("postalCode", "") or ""),
                lat=float((r.get("geo", {}) or {}).get("lat", 0) or 0),
                lng=float((r.get("geo", {}) or {}).get("lng", 0) or 0),
                description=(r.get("publicRemarks") or "").strip(),
                amenities=(r.get("amenities", {}) or {}).get("applyToList", []) or [],
                pet_friendly=bool((r.get("animal", {}) or {}).get("catsAllowed") or (r.get("animal", {}) or {}).get("dogsAllowed")),
                parking=bool((r.get("parking", {}) or {}).get("attachedGarage")),
                image_url=((r.get("photos", []) or []) + [""])[0],
                source="simplyrets",
                external_url=(r.get("virtualTour") or ""),
            )
        except Exception as exc:  # noqa: BLE001
            log.debug("Skipping malformed SimplyRETS record: %s", exc)
            return None

    def search(self, **kw: Any) -> list[Listing]:
        query = kw.pop("query", "")
        limit = kw.pop("limit", 12)
        matches = [l for l in self.all() if _matches(l, query, kw)]
        return matches[:limit]
