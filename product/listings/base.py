"""Provider interface shared by all listing sources."""
from __future__ import annotations

from typing import Any

from product.listings.models import Listing


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
        counties: list[str] | None = None,
        neighborhoods: list[str] | None = None,
        pet_friendly: bool | None = None,
        limit: int = 12,
    ) -> list[Listing]:
        raise NotImplementedError
