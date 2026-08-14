"""Thin OpenAI client wrapper with retries, timeouts and usage logging."""
from __future__ import annotations

import logging
import os
import time
from typing import Any

from openai import OpenAI

log = logging.getLogger("havenhunt.llm")


class LLMError(RuntimeError):
    pass


class LLM:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 90.0,
        max_retries: int = 3,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not set")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.client = OpenAI(api_key=self.api_key, timeout=timeout, max_retries=max_retries)
        self.usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}

    # ---- chat ----------------------------------------------------------
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """Run a chat completion with retry and return the assistant text."""
        kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                usage = resp.usage
                if usage:
                    self.usage["prompt_tokens"] += usage.prompt_tokens or 0
                    self.usage["completion_tokens"] += usage.completion_tokens or 0
                return resp.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                log.warning("LLM call failed (attempt %d): %s", attempt + 1, exc)
                time.sleep(1.5 * (attempt + 1))
        raise LLMError(f"LLM call failed after retries: {last_err}")

    # ---- embeddings ----------------------------------------------------
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for a list of texts."""
        resp = self.client.embeddings.create(model=self.embedding_model, input=texts)
        return [d.embedding for d in resp.data]

    # ---- helpers -------------------------------------------------------
    def token_budget(self) -> str:
        return (
            f"tokens: {self.usage['prompt_tokens']:,} in / "
            f"{self.usage['completion_tokens']:,} out"
        )
