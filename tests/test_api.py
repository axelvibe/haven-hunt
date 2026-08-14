"""API smoke tests using FastAPI TestClient (offline, no network)."""
from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

import product.web.api as api_module  # noqa: E402

client = TestClient(api_module.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "HavenHunt" in r.text


def test_chat_contract(monkeypatch):
    def fake_answer(query, limit=5):
        return {
            "query": query,
            "filters": {},
            "count": 1,
            "listings": [{"id": "CHI-0001", "title": "Test", "price": 100}],
            "answer": "Found a match for you.",
        }

    monkeypatch.setattr(api_module, "_search", types.SimpleNamespace(answer=fake_answer))
    r = client.post("/chat", json={"query": "1 bed"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1 and "answer" in body and "listings" in body
