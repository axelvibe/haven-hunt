"""Listing domain model."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Listing:
    """A single rental or sale property."""

    id: str
    listing_type: str  # "rent" | "sale"
    property_type: str  # "apartment" | "house" | "condo" | "townhouse" | "studio"
    title: str
    price: float  # monthly rent for rentals, purchase price for sales
    beds: float
    baths: float
    sqft: int
    neighborhood: str
    city: str = "Chicago"
    state: str = "IL"
    zipcode: str = ""
    lat: float = 0.0
    lng: float = 0.0
    description: str = ""
    amenities: list[str] = field(default_factory=list)
    pet_friendly: bool = False
    parking: bool = False
    furnished: bool = False
    image_url: str = ""
    source: str = "demo"
    external_url: str = ""
    listed_days: int = 0

    # ---- presentation helpers -----------------------------------------
    def price_label(self) -> str:
        if self.listing_type == "rent":
            return f"${self.price:,.0f}/mo"
        return f"${self.price:,.0f}"

    def type_label(self) -> str:
        return "Rental" if self.listing_type == "rent" else "For Sale"

    def address(self) -> str:
        parts = [self.neighborhood, self.city, self.state, self.zipcode]
        return ", ".join(p for p in parts if p)

    def to_text(self) -> str:
        """Compact human-readable block for Telegram / chat replies."""
        lines = [
            f"🏠 {self.title}",
            f"📍 {self.address()}",
            f"💰 {self.type_label()} — {self.price_label()}",
            f"🛏 {self.beds} bed · 🛁 {self.baths} bath · {self.sqft:,} sqft",
        ]
        tags = []
        if self.pet_friendly:
            tags.append("🐾 pet-friendly")
        if self.parking:
            tags.append("🅿️ parking")
        if self.furnished:
            tags.append("🛋 furnished")
        if tags:
            lines.append(" ".join(tags))
        if self.description:
            lines.append(f"📝 {self.description[:220]}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
