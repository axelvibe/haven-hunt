"""Geocoding for Ireland — Google Maps API with OpenStreetMap fallback.

Google Maps Geocoding API is used when GOOGLE_MAPS_API_KEY is set (production).
Without a key we fall back to the free OpenStreetMap Nominatim service so the
product keeps working. Results are cached to `.embeddings_cache/geocode.json`.

Also emits Google Maps link/embed URLs for the web chat and Telegram cards.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import urllib.parse
from pathlib import Path

log = logging.getLogger("havenhunt.geocode")

CACHE_PATH = Path(__file__).resolve().parent.parent.parent / ".embeddings_cache" / "geocode.json"
_lock = threading.Lock()


def _load_cache() -> dict[str, dict]:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {}


def _save_cache(cache: dict[str, dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")


def _geocode_google(place: str, api_key: str) -> dict | None:
    import urllib.request

    url = (
        "https://maps.googleapis.com/maps/api/geocode/json?"
        + urllib.parse.urlencode({"address": place, "key": api_key})
    )
    req = urllib.request.Request(url, headers={"User-Agent": "HavenHunt/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    if data.get("status") == "OK" and data.get("results"):
        loc = data["results"][0]["geometry"]["location"]
        return {"lat": loc["lat"], "lng": loc["lng"]}
    return None


def _geocode_nominatim(place: str) -> dict | None:
    import urllib.request

    url = (
        "https://nominatim.openstreetmap.org/search?"
        + urllib.parse.urlencode(
            {"q": place, "format": "json", "limit": 1, "countrycodes": "ie"}
        )
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "HavenHuntBot/1.0 (contact: info@havenhunt.local)"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    if data:
        return {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"])}
    return None


def geocode(place: str) -> dict | None:
    """Return {'lat': float, 'lng': float} for an Irish place name/address."""
    place = (place or "").strip()
    if not place:
        return None
    with _lock:
        cache = _load_cache()
        if place in cache:
            return cache[place]
    result = None
    key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    try:
        result = _geocode_google(place, key) if key else _geocode_nominatim(place)
    except Exception as exc:  # noqa: BLE001
        log.warning("Google geocode failed (%s); trying Nominatim", exc)
        try:
            result = _geocode_nominatim(place)
        except Exception as exc2:  # noqa: BLE001
            log.warning("Nominatim geocode failed: %s", exc2)
    if result:
        with _lock:
            cache = _load_cache()
            cache[place] = result
            _save_cache(cache)
    return result


def maps_url(lat: float, lng: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"


def maps_embed(lat: float, lng: float) -> str:
    return f"https://maps.google.com/maps?q={lat},{lng}&z=14&output=embed"
