"""Unit tests for the embeddings wrapper (mocked OpenAI client)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.rag.embeddings import Embedder


@dataclass
class _Item:
    embedding: list[float]


@dataclass
class _Resp:
    data: list[_Item]


class _FakeEmbeddings:
    """Stand-in for client.embeddings — records calls, returns canned vectors."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create(self, *, model: str, input: list[str]) -> _Resp:
        self.calls.append({"model": model, "input": input})
        return _Resp(data=[_Item([float(len(t))] * 3) for t in input])


def test_embed_texts_preserves_order_and_count() -> None:
    fake = _FakeEmbeddings()
    embedder = Embedder(client=fake, model="test-model")
    vectors = asyncio.run(embedder.embed_texts(["a", "bbb"]))
    assert len(vectors) == 2
    assert vectors[0] == [1.0, 1.0, 1.0]
    assert vectors[1] == [3.0, 3.0, 3.0]
    assert fake.calls[0]["model"] == "test-model"


def test_embed_texts_empty_short_circuits() -> None:
    fake = _FakeEmbeddings()
    embedder = Embedder(client=fake)
    assert asyncio.run(embedder.embed_texts([])) == []
    assert fake.calls == []  # no API call for empty input


def test_embed_query_returns_single_vector() -> None:
    fake = _FakeEmbeddings()
    embedder = Embedder(client=fake)
    vec = asyncio.run(embedder.embed_query("hello"))
    assert vec == [5.0, 5.0, 5.0]
