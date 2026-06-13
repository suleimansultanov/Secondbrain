"""Unit tests for RAG text chunking."""

from __future__ import annotations

import pytest

from app.rag.chunking import chunk_text


def test_empty_text_returns_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_is_one_chunk() -> None:
    text = "hello world this is short"
    assert chunk_text(text, max_tokens=500, overlap=50) == [text]


def test_long_text_splits_into_multiple_chunks() -> None:
    words = [f"w{i}" for i in range(1200)]
    text = " ".join(words)
    chunks = chunk_text(text, max_tokens=500, overlap=50)
    # step = 450 -> starts at 0, 450, 900 -> 3 chunks
    assert len(chunks) == 3
    assert chunks[0].split()[0] == "w0"
    assert chunks[0].split()[-1] == "w499"


def test_chunks_overlap() -> None:
    words = [f"w{i}" for i in range(1000)]
    chunks = chunk_text(" ".join(words), max_tokens=500, overlap=50)
    first_end = chunks[0].split()[-50:]
    second_start = chunks[1].split()[:50]
    assert first_end == second_start  # the overlap region is shared


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError):
        chunk_text("a b c", max_tokens=0)
    with pytest.raises(ValueError):
        chunk_text("a b c", max_tokens=100, overlap=100)
    with pytest.raises(ValueError):
        chunk_text("a b c", max_tokens=100, overlap=-1)
