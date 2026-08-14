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
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    telegram_token: str = ""
    telegram_username: str = "haven_hunt_bot"
    simplyrets_username: str = ""
    simplyrets_password: str = ""
    web_relay_url: str = ""
    site_url: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_username=os.getenv("TELEGRAM_BOT_USERNAME", "haven_hunt_bot"),
            simplyrets_username=os.getenv("SIMPLYRETS_USERNAME", ""),
            simplyrets_password=os.getenv("SIMPLYRETS_PASSWORD", ""),
            web_relay_url=os.getenv("WEB_RELAY_URL", ""),
            site_url=os.getenv("SITE_URL", ""),
        )

    def health(self) -> dict[str, bool]:
        return {
            "openai_key": bool(self.openai_api_key),
            "telegram_token": bool(self.telegram_token),
            "simplyrets": bool(self.simplyrets_username and self.simplyrets_password),
            "web_relay": bool(self.web_relay_url),
            "site_url": bool(self.site_url),
        }


settings = Settings.from_env()
