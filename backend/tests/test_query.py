"""Unit tests for the RAG query orchestration (no DB, no network)."""

from __future__ import annotations

import asyncio

import pytest

from app.rag.query import answer_question


class _FakeEmbedder:
    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class _FakeRetriever:
    def __init__(self, hits):
        self._hits = hits
        self.called_with = None

    async def search(self, embedding, top_k):
        self.called_with = (embedding, top_k)
        return self._hits


class _FakeClaude:
    def __init__(self):
        self.seen = None

    async def generate(self, system, question, context):
        self.seen = {"system": system, "question": question, "context": context}
        return "Grounded answer [1]."


def test_empty_question_raises() -> None:
    with pytest.raises(ValueError):
        asyncio.run(answer_question("  ", _FakeEmbedder(), _FakeRetriever([]), _FakeClaude()))


def test_no_hits_returns_no_info_and_no_sources() -> None:
    claude = _FakeClaude()
    result = asyncio.run(answer_question("anything", _FakeEmbedder(), _FakeRetriever([]), claude))
    assert result.sources == []
    assert "don't have" in result.answer.lower()
    assert claude.seen is None  # Claude not called when there is no context


def test_answer_uses_context_and_builds_sources() -> None:
    hits = [("int-1", "we agreed to ship in Q3"), ("int-2", "budget is 50k")]
    claude = _FakeClaude()
    retriever = _FakeRetriever(hits)
    result = asyncio.run(
        answer_question("when do we ship?", _FakeEmbedder(), retriever, claude, top_k=3)
    )
    assert result.answer == "Grounded answer [1]."
    assert [s.interaction_id for s in result.sources] == ["int-1", "int-2"]
    assert retriever.called_with[1] == 3  # top_k passed through
    # context handed to Claude contains the retrieved passages, numbered
    assert "[1] we agreed to ship in Q3" in claude.seen["context"]
