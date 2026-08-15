"""Listing domain model (Ireland market).

Ireland notes:
- Prices are in EUR.
- Sales come from the Property Price Register (PPR), which records sale price,
  date, address, county and (often) eircode — but NO bedrooms/bathrooms/floor area.
  Those fields are therefore optional and displayed as "not recorded" when absent.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Listing:
    """A single rental or sale property."""

    id: str
    listing_type: str  # "rent" | "sale"
    property_type: str  # "apartment" | "house" | "townhouse" | "studio"
    title: str
    price: float  # monthly rent (EUR) for rentals, purchase price for sales
    county: str  # e.g. Dublin, Cork, Galway...
    beds: float | None = None
    baths: float | None = None
    sqft: int | None = None
    neighborhood: str = ""
    city: str = ""
    eircode: str = ""
    address_line: str = ""
    lat: float = 0.0
    lng: float = 0.0
    description: str = ""
    amenities: list[str] = field(default_factory=list)
    pet_friendly: bool = False
    parking: bool = False
    furnished: bool = False
    image_url: str = ""
    source: str = "demo"  # demo | ppr | ppr_live
    external_url: str = ""
    sale_date: str = ""
    condition: str = ""  # "new" | "second_hand" (PPR)
    not_full_market_price: bool = False  # PPR ** marker
    vat_exclusive: bool = False  # PPR: new builds exclude VAT
    listed_days: int = 0
    currency: str = "EUR"

    # ---- presentation helpers -----------------------------------------
    def price_label(self) -> str:
        if self.listing_type == "rent":
            return f"€{self.price:,.0f}/mo"
        return f"€{self.price:,.0f}"

    def type_label(self) -> str:
        return "Rental" if self.listing_type == "rent" else "For Sale"

    def size_label(self) -> str:
        parts: list[str] = []
        if self.beds is not None:
            parts.append(f"🛏 {self.beds} bed")
        if self.baths is not None:
            parts.append(f"🛁 {self.baths} bath")
        if self.sqft is not None:
            parts.append(f"{self.sqft:,} sqft")
        return " · ".join(parts) or "Size not recorded"

    def location_label(self) -> str:
        bits = [p for p in (self.neighborhood, self.city, self.county) if p]
        return ", ".join(bits) if bits else self.county

    def to_text(self) -> str:
        """Compact human-readable block for Telegram / chat replies."""
        lines = [f"🏠 {self.title}", f"📍 {self.location_label()}"]
        if self.eircode:
            lines[1] += f" ({self.eircode})"
        lines.append(f"💰 {self.type_label()} — {self.price_label()}")
        lines.append(self.size_label())
        tags = []
        if self.pet_friendly:
            tags.append("🐾 pet-friendly")
        if self.parking:
            tags.append("🅿️ parking")
        if self.furnished:
            tags.append("🛋 furnished")
        if self.condition == "new":
            tags.append("🆕 new build")
        if tags:
            lines.append(" ".join(tags))
        if self.description:
            lines.append(f"📝 {self.description[:220]}")
        if self.not_full_market_price:
            lines.append("⚠️ PPR notes this price may not reflect full market value (**).")
        if self.vat_exclusive:
            lines.append("ℹ️ New build price shown exclusive of VAT (PPR).")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
