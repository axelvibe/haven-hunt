"""Tests for the HavenHunt Ireland search layer (no API calls — offline)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from product.listings.models import Listing  # noqa: E402
from product.listings.ppr import PPRSnapshotProvider, normalize_county, parse_ppr_row  # noqa: E402
from product.listings.provider import StaticProvider  # noqa: E402
from product.listings.search import Filters  # noqa: E402

PROVIDER = StaticProvider()


def test_dataset_size():
    assert len(PROVIDER.all()) >= 40, "demo dataset too small"


def test_dataset_is_ireland_rentals():
    for l in PROVIDER.all():
        assert l.county in {"Dublin", "Cork", "Galway", "Limerick", "Waterford"}
        assert l.currency == "EUR"
    assert all(l.listing_type == "rent" for l in PROVIDER.all())


def test_provider_rental_budget():
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
        query="", neighborhoods=["Ranelagh"], listing_type="rent", limit=10
    )
    assert out
    assert all(l.neighborhood == "Ranelagh" for l in out)


def test_provider_pet_filter():
    out = PROVIDER.search(query="", pet_friendly=True, listing_type="rent", limit=20)
    assert out
    assert all(l.pet_friendly for l in out)


def test_provider_empty_result():
    out = PROVIDER.search(query="", listing_type="sale", max_price=50000, limit=10)
    assert out == []


def test_provider_keyword_query():
    out = PROVIDER.search(query="tramore", listing_type="rent", limit=10)
    assert out, "keyword search for tramore should match"


def test_filters_dataclass_defaults():
    f = Filters()
    assert f.listing_type is None and f.min_price is None and f.beds_min is None
    assert f.neighborhoods == [] and f.counties == []


# ---- PPR (sales) ------------------------------------------------------
def test_ppr_snapshot_is_sales_only():
    ppr = PPRSnapshotProvider()
    assert ppr.all()
    assert all(l.listing_type == "sale" for l in ppr.all())
    assert all(l.beds is None and l.baths is None for l in ppr.all())


def test_ppr_snapshot_county_filter():
    ppr = PPRSnapshotProvider()
    out = ppr.search(counties=["Cork"], limit=20)
    assert out
    assert all(l.county == "Cork" for l in out)


def test_ppr_snapshot_keyword_county():
    ppr = PPRSnapshotProvider()
    out = ppr.search(query="galway", limit=10)
    assert out
    assert all(l.county == "Galway" for l in out)


def test_normalize_county():
    assert normalize_county("Dublin") == "Dublin"
    assert normalize_county("Co. Galway") == "Galway"
    assert normalize_county("Corcaigh") == "Cork"
    assert normalize_county("Portlairge") == "Waterford"


def test_ppr_row_parse_flags():
    row = {
        "address": "1 The Quays\nDocklands, Cork",
        "price_in_euros": "275000",
        "date_of_sale": "2025-03-14T00:00:00Z",
        "county": "Cork",
        "eircode": "T12",
        "description_of_property": "Second-Hand Dwelling house /Apartment",
        "not_full_market_price": True,
        "vat_exclusive": True,
    }
    listing = parse_ppr_row(row)
    assert listing is not None
    assert listing.listing_type == "sale"
    assert listing.county == "Cork"
    assert listing.price == 275000
    assert listing.condition == "second_hand"
    assert listing.not_full_market_price is True
    assert listing.vat_exclusive is True
    assert listing.beds is None
    assert listing.id.startswith("PPR-")


# ---- Ireland presentation ---------------------------------------------
def test_size_label_not_recorded():
    l = Listing(
        id="x",
        listing_type="sale",
        property_type="house",
        title="Test",
        price=250000,
        county="Dublin",
    )
    assert l.size_label() == "Size not recorded"
    assert l.price_label() == "€250,000"
    assert "not recorded" in l.to_text()


def test_eircode_in_location():
    l = Listing(
        id="y",
        listing_type="sale",
        property_type="apartment",
        title="Test",
        price=300000,
        county="Galway",
        neighborhood="Salthill",
        city="Galway",
        eircode="H91",
    )
    assert l.eircode == "H91"
    assert "H91" in l.to_text()
