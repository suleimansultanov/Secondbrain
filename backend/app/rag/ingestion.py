"""Ingestion pipeline: turn an interaction's text into stored, embedded chunks.

The orchestration here is storage-agnostic and fully unit-testable: it depends
only on an `embedder` (embed_texts) and a `store` (load/replace). The real
Postgres store lives in `app/rag/store.py`; the worker wires them together.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.rag.chunking import chunk_text


@dataclass
class ChunkRecord:
    chunk_index: int
    content: str
    embedding: list[float]


class Embedderlike(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...  # noqa: E704


class ChunkStore(Protocol):
    async def load_interaction_content(self, interaction_id: str) -> str | None: ...  # noqa: E704
    async def replace_chunks(
        self, interaction_id: str, records: list[ChunkRecord]
    ) -> None: ...  # noqa: E704


async def build_interaction_chunks(content: str, embedder: Embedderlike) -> list[ChunkRecord]:
    """Chunk *content* and embed each chunk; return ordered ChunkRecords."""
    pieces = chunk_text(content)
    if not pieces:
        return []
    vectors = await embedder.embed_texts(pieces)
    return [
        ChunkRecord(chunk_index=i, content=c, embedding=v)
        for i, (c, v) in enumerate(zip(pieces, vectors))
    ]


async def run_ingestion(store: ChunkStore, embedder: Embedderlike, interaction_id: str) -> dict:
    """Load an interaction, (re)build its chunks, and store them.

    Idempotent: `replace_chunks` removes any prior chunks for the interaction.
    """
    content = await store.load_interaction_content(interaction_id)
    if content is None:
        return {"status": "not-found", "interaction_id": interaction_id, "chunks": 0}

    records = await build_interaction_chunks(content, embedder)
    await store.replace_chunks(interaction_id, records)
    return {"status": "ok", "interaction_id": interaction_id, "chunks": len(records)}
