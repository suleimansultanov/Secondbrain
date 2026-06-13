"""Unit tests for the ingestion orchestration (no DB, no network)."""

from __future__ import annotations

import asyncio

from app.rag.ingestion import ChunkRecord, build_interaction_chunks, run_ingestion


class _FakeEmbedder:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t))] * 3 for t in texts]


class _FakeStore:
    def __init__(self, content: str | None) -> None:
        self._content = content
        self.replaced: list[ChunkRecord] | None = None

    async def load_interaction_content(self, interaction_id: str) -> str | None:
        return self._content

    async def replace_chunks(self, interaction_id: str, records) -> None:
        self.replaced = records


def test_build_chunks_embeds_each_piece() -> None:
    words = " ".join(f"w{i}" for i in range(1000))
    records = asyncio.run(build_interaction_chunks(words, _FakeEmbedder()))
    assert len(records) >= 2
    assert records[0].chunk_index == 0
    assert all(len(r.embedding) == 3 for r in records)


def test_build_chunks_empty_content() -> None:
    assert asyncio.run(build_interaction_chunks("", _FakeEmbedder())) == []


def test_run_ingestion_stores_chunks() -> None:
    store = _FakeStore("hello world from the meeting")
    result = asyncio.run(run_ingestion(store, _FakeEmbedder(), "int-1"))
    assert result["status"] == "ok"
    assert result["chunks"] == len(store.replaced)
    assert store.replaced[0].chunk_index == 0


def test_run_ingestion_not_found() -> None:
    store = _FakeStore(None)
    result = asyncio.run(run_ingestion(store, _FakeEmbedder(), "missing"))
    assert result == {"status": "not-found", "interaction_id": "missing", "chunks": 0}
    assert store.replaced is None  # nothing written
