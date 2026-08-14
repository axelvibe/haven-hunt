"""Lazy shared LLM for the product runtime (thread-safe singleton)."""
from __future__ import annotations

import threading

from pipeline.llm import LLM
from product.shared.config import settings

_lock = threading.Lock()
_llm: LLM | None = None


def llm() -> LLM:
    global _llm
    with _lock:
        if _llm is None:
            _llm = LLM(api_key=settings.openai_api_key, model=settings.openai_model)
        return _llm
