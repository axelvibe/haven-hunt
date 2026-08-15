"""CSO (Central Statistics Office, Ireland) — housing statistics provider.

Live source: CSO PxStat API (JSON-stat format, no API key required).
  Dataset HPM09 = Residential Property Price Index (monthly).
  https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/HPM09/JSON-stat/1.0/en

The RPPI is the official measure of Irish house-price change (Base 2015=100),
broken down by statistic (index / % change) and region. HPM09 covers National
and Dublin (plus NUTS regions for houses); county-level detail comes from the
Property Price Register (PPR) sales data instead.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
from pathlib import Path
from typing import Any

log = logging.getLogger("havenhunt.listings.cso")

CACHE_PATH = Path(__file__).resolve().parent.parent.parent / ".cso_cache.json"
CACHE_TTL = 24 * 3600

HPM09_URL = "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/HPM09/JSON-stat/1.0/en"

# Statistic codes in HPM09
STAT_INDEX = "HPM09C01"          # Residential Property Price Index (Base 2015=100)
STAT_1M = "HPM09C02"             # % change over 1 month
STAT_12M = "HPM09C04"            # % change over 12 months

# Region codes in HPM09 (third dimension). Note: HPM09 has no per-county
# breakdown — 05/06/07 are Dublin sub-areas; county detail comes from PPR.
REGION_NATIONAL = "-"            # National - all residential properties
REGION_DUBLIN = "05"             # Dublin - all residential properties
REGION_NAT_EXCL_DUBLIN = "03"    # National excluding Dublin - all residential


def _fetch_dataset(url: str = HPM09_URL) -> dict[str, Any] | None:
    if CACHE_PATH.exists() and (time.time() - CACHE_PATH.stat().st_mtime) < CACHE_TTL:
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HavenHunt/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(data), encoding="utf-8")
        log.info("Fetched CSO HPM09 dataset (%d values).", len(data["dataset"].get("value", [])))
        return data
    except Exception as exc:  # noqa: BLE001
        log.warning("CSO fetch failed: %s", exc)
        return None


def _category_index(dim: dict[str, Any]) -> dict[str, int]:
    """Return {category_key: flat_position} honouring JSON-stat 'index' ordering."""
    idx = dim["category"]["index"]
    if isinstance(idx, dict):
        return {str(k): int(v) for k, v in idx.items()}
    return {str(k): i for i, k in enumerate(idx)}


def _category_labels(dim: dict[str, Any]) -> dict[str, str]:
    labels = dim["category"].get("label")
    return {str(k): str(v) for k, v in labels.items()} if isinstance(labels, dict) else {}


def _cell(ds: dict[str, Any], stat: str, period: str, region: str) -> float | None:
    """Read a single cell by dimension keys, using per-dimension positions."""
    dims = [(dim_id, dim) for dim_id, dim in ds["dimension"].items() if "category" in dim]
    indexes = [_category_index(dim) for _, dim in dims]
    values = ds.get("value", [])
    if not values:
        return None
    size = len(values)
    keys = [stat, period, region]
    strides: list[int] = []
    stride = 1
    for idx_map in reversed(indexes):
        strides.insert(0, stride)
        stride *= (len(idx_map) or 1)
    try:
        pos = sum(indexes[i].get(keys[i], 0) * strides[i] for i in range(len(keys)))
    except (KeyError, TypeError):
        return None
    if 0 <= pos < size:
        v = values[pos]
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    return None


def _periods(ds: dict[str, Any]) -> list[str]:
    for dim_id, dim in ds["dimension"].items():
        if isinstance(dim, dict) and dim_id.startswith("TLIST"):
            return list(_category_index(dim).keys())
    return []


def _regions(ds: dict[str, Any]) -> dict[str, str]:
    for dim_id, dim in ds["dimension"].items():
        if isinstance(dim, dict) and dim_id.startswith("C"):
            return _category_labels(dim)
    return {}


def housing_stats(data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Latest national + regional RPPI figures for the web API / bots.

    `data` may be injected (fixtures/tests); otherwise fetched live from the CSO.
    Returns a dict with a `source` marker; empty dict when the CSO is unreachable.
    """
    if data is None:
        data = _fetch_dataset()
    if not data or "dataset" not in data:
        return {}
    ds = data["dataset"]
    if not isinstance(ds, dict) or "dimension" not in ds:
        return {}
    periods = _periods(ds)
    if not periods:
        return {}
    latest = periods[-1]

    def latest_value(stat: str, region: str) -> float | None:
        return _cell(ds, stat, latest, region)

    def region(name: str, code: str) -> dict[str, Any]:
        return {
            "name": name,
            "index": latest_value(STAT_INDEX, code),
            "change_12m": latest_value(STAT_12M, code),
        }

    stats = {
        "dataset": "HPM09",
        "title": "Residential Property Price Index (CSO)",
        "base": "2015=100",
        "updated": ds.get("updated", ""),
        "latest_period": latest,
        "national": {
            "index": latest_value(STAT_INDEX, REGION_NATIONAL),
            "change_1m": latest_value(STAT_1M, REGION_NATIONAL),
            "change_12m": latest_value(STAT_12M, REGION_NATIONAL),
        },
        "regions": [
            region("National - all residential properties", REGION_NATIONAL),
            region("National - houses", "01"),
            region("National - apartments", "02"),
            region("Dublin - all residential properties", REGION_DUBLIN),
            region("Dublin - houses", "06"),
            region("Dublin - apartments", "07"),
            region("National excluding Dublin - all residential properties", REGION_NAT_EXCL_DUBLIN),
        ],
        "source": "Central Statistics Office (CSO), PxStat HPM09 — https://www.cso.ie",
    }
    return stats
