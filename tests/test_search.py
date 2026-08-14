"""Tests for the HavenHunt search layer (no API calls — offline)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.listings.provider import StaticProvider  # noqa: E402
from product.listings.search import Filters  # noqa: E402

PROVIDER = StaticProvider()


def test_dataset_size():
    assert len(PROVIDER.all()) >= 40, "demo dataset too small"


def test_dataset_has_rent_and_sale():
    types = {l.listing_type for l in PROVIDER.all()}
    assert types == {"rent", "sale"}


def test_provider_filter_rental_budget():
    out = PROVIDER.search(
        query="2 bed rental",
        listing_type="rent",
        min_price=2000,
        max_price=2600,
        beds_min=2,
        limit=10,
    )
    assert out, "no results for valid filter"
    for l in out:
        assert l.listing_type == "rent"
        assert l.beds >= 2
        assert 2000 <= l.price <= 2600


def test_provider_neighborhood_filter():
    out = PROVIDER.search(
        query="", neighborhoods=["Lincoln Park"], listing_type="sale", limit=10
    )
    assert out
    assert all(l.neighborhood == "Lincoln Park" for l in out)


def test_provider_pet_filter():
    out = PROVIDER.search(query="", pet_friendly=True, listing_type="rent", limit=20)
    assert out
    assert all(l.pet_friendly for l in out)


def test_provider_empty_result():
    out = PROVIDER.search(
        query="", listing_type="sale", max_price=50000, limit=10
    )
    assert out == []


def test_provider_keyword_query():
    out = PROVIDER.search(query="wrigley", listing_type="rent", limit=10)
    assert out, "keyword search for wrigley should match"


def test_filters_dataclass_defaults():
    f = Filters()
    assert f.listing_type is None and f.min_price is None and f.beds_min is None
    assert f.neighborhoods == []
