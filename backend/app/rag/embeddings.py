"""Embeddings via OpenAI `text-embedding-3-small` (1536-dim).

The OpenAI client is injectable so the pipeline can be unit-tested without a key
or network. In production the client is created lazily from `OPENAI_API_KEY`.
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import get_settings

EMBED_DIM = 1536


class _AsyncEmbeddingsClient(Protocol):
    async def create(self, *, model: str, input: list[str]): ...  # noqa: E704


class Embedder:
    """Turns text into embedding vectors."""

    def __init__(self, client=None, model: str | None = None) -> None:
        self._client = client
        self._model = model or get_settings().embedding_model

    def _embeddings(self):
        if self._client is None:
            # Imported lazily so the module loads without the openai package
            # installed (e.g. in environments that only need chunking).
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=get_settings().openai_api_key).embeddings
        return self._client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts; returns one vector per input (order preserved)."""
        if not texts:
            return []
        resp = await self._embeddings().create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        vectors = await self.embed_texts([text])
        return vectors[0]
