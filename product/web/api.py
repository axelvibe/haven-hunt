"""HavenHunt web API.

Serves the chat endpoint used by the GitHub Pages chat widget, plus the
static site. Deploy alongside the Telegram bot (see deploy/).

Run locally:  uv run uvicorn product.web.api:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from product.listings.provider import build_provider
from product.listings.search import SearchEngine
from product.shared.config import settings

log = logging.getLogger("havenhunt.web")

WEB_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="HavenHunt API",
    description="AI property-search assistant for Ireland. Live sales data from the Property Price Register (PPR); demo rentals included.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_search = SearchEngine(provider=build_provider())


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "settings": settings.health()}


@app.post("/chat")
def chat(req: ChatRequest) -> dict[str, Any]:
    return _search.answer(req.query or "", limit=5)


class GeocodeRequest(BaseModel):
    q: str


@app.post("/geocode")
def geocode(req: GeocodeRequest) -> dict[str, Any]:
    from product.listings.geocode import geocode, maps_url

    point = geocode(req.q)
    if not point:
        return {"query": req.q, "point": None, "map_url": None}
    return {"query": req.q, "point": point, "map_url": maps_url(point["lat"], point["lng"])}


# Static site (also usable standalone on Render/Railway if not on Pages)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
