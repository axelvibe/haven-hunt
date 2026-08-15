"""Environment configuration for the product."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    market: str = "ireland"  # only Ireland is supported in this build
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    telegram_token: str = ""
    telegram_username: str = "haven_hunt_bot"
    ppr_api_url: str = "https://priceregister.civictech.ie/api/v1/residential/sales"
    ppr_fetch: str = "auto"  # "auto" | "on" | "off"
    google_maps_api_key: str = ""
    web_relay_url: str = ""
    site_url: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            market=os.getenv("MARKET", "ireland"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_username=os.getenv("TELEGRAM_BOT_USERNAME", "haven_hunt_bot"),
            ppr_api_url=os.getenv("PPR_API_URL", "https://priceregister.civictech.ie/api/v1/residential/sales"),
            ppr_fetch=os.getenv("PPR_FETCH", "auto"),
            google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
            web_relay_url=os.getenv("WEB_RELAY_URL", ""),
            site_url=os.getenv("SITE_URL", ""),
        )

    def health(self) -> dict[str, bool]:
        return {
            "openai_key": bool(self.openai_api_key),
            "telegram_token": bool(self.telegram_token),
            "ppr": bool(self.ppr_api_url),
            "ppr_live_fetch": self.ppr_fetch.lower() != "off",
            "google_maps": bool(self.google_maps_api_key),
            "web_relay": bool(self.web_relay_url),
            "site_url": bool(self.site_url),
        }


settings = Settings.from_env()
