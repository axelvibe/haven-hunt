"""Property Price Register (PPR) Ireland — sales data providers.

Source of truth: https://www.propertypriceregister.ie/ (PSRA). The register has no
official API; we use two real routes:

1. A community JSON API mirroring the full register:
   https://priceregister.civictech.ie/api/v1/residential/sales  (~798k records)
2. An offline snapshot of real records shipped in this repo
   (product/listings/data/ppr_snapshot.json) so the product works with no network.

PPR data caveats (engineered into the parsing below):
- Sales ONLY — there is no rental data on the register.
- No bedrooms/bathrooms/floor area — those Listing fields stay None.
- Addresses are often townland + street + county, sometimes without eircode.
- Some prices are flagged (**) as not reflecting full market value; some new-build
  prices are shown exclusive of VAT. Both flags are preserved and surfaced to users.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from product.listings.base import ListingsProvider
from product.listings.counties import COUNTY_ALIASES, normalize_county
from product.listings.matching import matches as _matches
from product.listings.models import Listing

log = logging.getLogger("havenhunt.listings.ppr")

SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "ppr_snapshot.json"
CACHE_PATH = Path(__file__).resolve().parent.parent.parent / ".ppr_cache.json"
CACHE_TTL = 12 * 3600  # refresh live data at most every 12h

LIVE_API = "https://priceregister.civictech.ie/api/v1/residential/sales"
_DEFAULT_FETCH = 1500


def parse_ppr_row(row: dict[str, Any]) -> Listing | None:
    """Convert a raw PPR record to a Listing. Returns None if unusable."""
    try:
        price = float(str(row.get("price_in_euros") or 0))
    except (TypeError, ValueError):
        price = 0.0
    if price <= 0:
        return None

    county = normalize_county(row.get("county")) or ""
    desc = (row.get("description_of_property") or "").strip()
    low = desc.lower()
    if "apartment" in low:
        ptype = "apartment"
    elif "house" in low or "dwelling" in low:
        ptype = "house"
    elif "site" in low or "land" in low:
        ptype = "house"
    else:
        ptype = "house"
    condition = "new" if "new" in low else ("second_hand" if "second" in low else "")

    address = (row.get("address") or "").strip()
    eircode = (row.get("eircode") or "").strip()
    sale_date = (row.get("date_of_sale") or "")[:10]

    # neighbourhood = last two comma segments of the address (townland, town)
    segs = [s.strip() for s in re.split(r"[,\n]+", address) if s.strip()]
    hood = segs[-1] if segs else county
    town = segs[-2] if len(segs) > 1 else ""

    return Listing(
        id=f"PPR-{sale_date}-{county}-{len(address):d}-{int(price):d}",
        listing_type="sale",
        property_type=ptype,
        title=f"{ptype.capitalize()} sold in {town or hood or county} ({county})",
        price=price,
        county=county,
        neighborhood=hood,
        city=town,
        eircode=eircode,
        address_line=address,
        description=(desc + (" · " + address if address and desc else address)).strip(),
        source="ppr",
        external_url="https://www.propertypriceregister.ie/",
        sale_date=sale_date,
        condition=condition,
        not_full_market_price=bool(row.get("not_full_market_price")),
        vat_exclusive=bool(row.get("vat_exclusive")),
        image_url="",
    )


class PPRApiProvider(ListingsProvider):
    """Live PPR data via the community JSON API, with a disk cache."""

    name = "ppr_live"

    def __init__(self, api_url: str | None = None, fetch: int = _DEFAULT_FETCH) -> None:
        self.api_url = api_url or os.getenv("PPR_API_URL", LIVE_API)
        self.fetch = int(os.getenv("PPR_FETCH_COUNT", str(fetch)))
        self._cache: list[Listing] | None = None

    def _fetch_raw(self) -> list[dict[str, Any]]:
        if CACHE_PATH.exists() and (time.time() - CACHE_PATH.stat().st_mtime) < CACHE_TTL:
            try:
                return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass
        import urllib.request

        rows: list[dict[str, Any]] = []
        url = f"{self.api_url}?limit=1000"
        for _ in range(4):
            req = urllib.request.Request(url, headers={"User-Agent": "HavenHunt/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
            rows.extend(data.get("data", []))
            cursor = (data.get("metadata") or {}).get("after_cursor")
            if not cursor or len(rows) >= self.fetch:
                break
            url = f"{self.api_url}?limit=1000&after_cursor={cursor}"
        rows = rows[: self.fetch]
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(rows), encoding="utf-8")
        log.info("Fetched %d live PPR records.", len(rows))
        return rows

    def all(self) -> list[Listing]:
        if self._cache is None:
            self._cache = [l for l in (parse_ppr_row(r) for r in self._fetch_raw()) if l]
        return self._cache

    def search(self, **kw: Any) -> list[Listing]:
        query = kw.pop("query", "")
        limit = kw.pop("limit", 12)
        matches = [l for l in self.all() if _matches(l, query, kw)]
        matches.sort(key=lambda l: l.sale_date, reverse=True)
        return matches[:limit]


class PPRSnapshotProvider(ListingsProvider):
    """Offline snapshot of real PPR records shipped in the repo."""

    name = "ppr"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SNAPSHOT_PATH
        self._listings: list[Listing] | None = None

    def all(self) -> list[Listing]:
        if self._listings is None:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._listings = [l for l in (parse_ppr_row(r) for r in raw["rows"]) if l]
        return self._listings

    def search(self, **kw: Any) -> list[Listing]:
        query = kw.pop("query", "")
        limit = kw.pop("limit", 12)
        matches = [l for l in self.all() if _matches(l, query, kw)]
        matches.sort(key=lambda l: l.sale_date, reverse=True)
        return matches[:limit]
