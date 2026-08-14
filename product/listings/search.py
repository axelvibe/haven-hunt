"""Hybrid search: LLM intent parsing + keyword filters + OpenAI embeddings.

Flow:
  1. `SearchEngine.answer(query)` parses the user's natural language into structured
     filters (listing type, price range, bedrooms, pet-friendly, neighborhood) using
     the LLM (JSON mode).
  2. Filters are applied over the provider's listings (keyword/filter pass).
  3. Results are re-ranked by cosine similarity against OpenAI embeddings of the
     listings, so fuzzy descriptions like "lake views" or "near the 606" work.
  4. The LLM writes a short, human answer summarising the top matches.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from product.listings.models import Listing
from product.listings.provider import ListingsProvider
from product.shared.llm import llm as _default_llm

log = logging.getLogger("havenhunt.search")

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".embeddings_cache"


@dataclass
class Filters:
    listing_type: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    beds_min: float | None = None
    pet_friendly: bool | None = None
    neighborhoods: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "listing_type": self.listing_type,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "beds_min": self.beds_min,
            "pet_friendly": self.pet_friendly,
            "neighborhoods": self.neighborhoods,
        }


_INTENT_SYSTEM = """\
You extract structured search filters from a user's real-estate query. Respond with \
JSON only, using exactly these keys:
{
  "listing_type": "rent" | "sale" | null,
  "min_price": number | null,
  "max_price": number | null,
  "beds_min": number | null,
  "pet_friendly": true | false | null,
  "neighborhoods": [string] | []
}
Rules:
- "rent", "rental", "lease", "apartment for rent" -> listing_type "rent".
- "buy", "purchase", "for sale", "home to buy" -> listing_type "sale".
- Prices: "$1800/mo" or "under 2k" -> max_price; "over 300k" -> min_price.
- Bedrooms: "1 bed", "one bedroom", "2bd" -> beds_min (studio -> 0).
- "pet friendly", "dogs allowed", "cat ok" -> pet_friendly true.
- Neighborhood/city names go into neighborhoods as exact matches.
- Ignore greeting/filler. If nothing is extractable, emit nulls/empty arrays.
"""


class SearchEngine:
    def __init__(self, provider: ListingsProvider, llm=None) -> None:
        self.provider = provider
        self.llm = llm or _default_llm()
        if callable(self.llm):
            self.llm = self.llm()
        self._embeddings: np.ndarray | None = None
        self._embed_ids: list[str] = []

    # ---- embeddings ---------------------------------------------------
    def _load_or_build_embeddings(self, listings: list[Listing]) -> tuple[np.ndarray, list[str]]:
        ids = [l.id for l in listings]
        if self._embeddings is not None and self._embed_ids == ids:
            return self._embeddings, self._embed_ids

        cache_file = CACHE_DIR / "listing_embeddings.npy"
        cache_ids = CACHE_DIR / "listing_ids.json"
        if cache_file.exists() and cache_ids.exists():
            try:
                cached = json.loads(cache_ids.read_text())
                if cached == ids:
                    log.info("Loading cached listing embeddings.")
                    self._embeddings = np.load(cache_file)
                    self._embed_ids = ids
                    return self._embeddings, self._embed_ids
            except Exception as exc:  # noqa: BLE001
                log.warning("Embedding cache unusable: %s", exc)

        texts = [self._embed_text(l) for l in listings]
        log.info("Embedding %d listings with %s ...", len(texts), self.llm.embedding_model)
        vecs = self.llm.embed(texts)
        arr = np.asarray(vecs, dtype=np.float32)
        norm = np.linalg.norm(arr, axis=1, keepdims=True)
        arr = arr / np.maximum(norm, 1e-9)

        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.save(cache_file, arr)
        cache_ids.write_text(json.dumps(ids))
        self._embeddings, self._embed_ids = arr, ids
        return arr, ids

    @staticmethod
    def _embed_text(l: Listing) -> str:
        return " ".join(
            [
                l.title,
                l.property_type,
                l.listing_type,
                l.neighborhood,
                l.city,
                l.description,
                " ".join(l.amenities),
                "pet friendly" if l.pet_friendly else "",
                "parking" if l.parking else "",
                "furnished" if l.furnished else "",
                f"{l.price:,.0f} dollars",
                f"{l.beds} bedroom",
            ]
        ).strip()

    # ---- ranking ------------------------------------------------------
    def _semantic_scores(self, query: str, listings: list[Listing]) -> np.ndarray:
        emb, ids = self._load_or_build_embeddings(self.provider.all())
        if not query.strip():
            return np.ones(len(listings), dtype=np.float32) * 0.5
        qv = np.asarray(self.llm.embed([query])[0], dtype=np.float32)
        qv = qv / max(np.linalg.norm(qv), 1e-9)
        index = {id_: i for i, id_ in enumerate(ids)}
        return np.array(
            [float(np.dot(qv, emb[index[l.id]])) for l in listings], dtype=np.float32
        )

    # ---- intent -------------------------------------------------------
    def parse_intent(self, query: str) -> Filters:
        """Extract structured filters from a natural-language query."""
        q = (query or "").strip()
        # Fast path for very short numeric queries handled by keyword anyway.
        if not q or len(q) < 3:
            return Filters()
        try:
            raw = self.llm.chat(
                [
                    {"role": "system", "content": _INTENT_SYSTEM},
                    {"role": "user", "content": f'User query: "{q}"'},
                ],
                temperature=0.0,
                max_tokens=200,
                json_mode=True,
            )
            data = json.loads(re.sub(r"```(json)?|```", "", raw).strip())
            return Filters(
                listing_type=data.get("listing_type"),
                min_price=data.get("min_price"),
                max_price=data.get("max_price"),
                beds_min=data.get("beds_min"),
                pet_friendly=data.get("pet_friendly"),
                neighborhoods=[n.strip() for n in (data.get("neighborhoods") or []) if n.strip()],
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Intent parse failed, falling back to keyword filters: %s", exc)
            return Filters()

    # ---- public API ---------------------------------------------------
    def search(self, query: str = "", filters: Filters | None = None, limit: int = 8) -> list[Listing]:
        f = filters or Filters()
        q = (query or "").strip()

        candidates = self.provider.search(
            query=q,
            listing_type=f.listing_type,
            min_price=f.min_price,
            max_price=f.max_price,
            beds_min=f.beds_min,
            neighborhoods=f.neighborhoods or None,
            pet_friendly=f.pet_friendly,
            limit=50,
        )
        if not candidates:
            return []

        scores = self._semantic_scores(q, candidates)
        ranked = sorted(zip(candidates, scores), key=lambda t: t[1], reverse=True)
        return [l for l, _ in ranked[:limit]]

    def answer(self, query: str, limit: int = 5) -> dict:
        """Full Q&A: intent -> search -> natural-language answer."""
        filters = self.parse_intent(query)
        results = self.search(query, filters, limit=limit)
        answer_text = self._summarize(query, results)
        return {
            "query": query,
            "filters": filters.as_dict(),
            "count": len(results),
            "listings": [l.to_dict() for l in results],
            "answer": answer_text,
        }

    def _summarize(self, query: str, results: list[Listing]) -> str:
        if not results:
            return (
                "I couldn't find anything matching that just yet. Try removing a "
                "filter, widening your budget, or asking for a different neighborhood. "
                "You can also ask for “rentals under $2,500” or “2-bed condos near the lake”."
            )
        block = "\n\n".join(l.to_text() for l in results)
        system = (
            "You are HavenHunt, a warm, expert Chicago real-estate assistant. "
            "Answer the user's question in 3-6 short lines, referencing the top "
            "matches below by address/neighborhood and price. Be specific, honest, "
            "and end by offering one helpful follow-up question. Do not invent "
            "listings that are not in the provided data."
        )
        return self.llm.chat(
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f'User query: "{query}"\n\nTop matches:\n{block}',
                },
            ],
            temperature=0.4,
            max_tokens=300,
        )
