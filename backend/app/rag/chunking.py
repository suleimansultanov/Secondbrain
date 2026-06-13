"""Text chunking for RAG.

Splits an interaction's text into overlapping chunks so that semantic search can
retrieve the most relevant passage rather than a whole interaction.

This is a word-based approximation of token chunking (1 word ≈ 1 token is close
enough for English at MVP scale). Swap in a real tokenizer (e.g. tiktoken) later
if chunk sizing needs to match OpenAI's tokenizer exactly.
"""

from __future__ import annotations

DEFAULT_MAX_TOKENS = 500
DEFAULT_OVERLAP = 50


def chunk_text(
    text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Split *text* into chunks of about *max_tokens* words with *overlap* words.

    Returns an empty list for blank input. Raises ValueError on invalid sizing.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive")
    if overlap < 0 or overlap >= max_tokens:
        raise ValueError("overlap must be >= 0 and < max_tokens")

    words = text.split()
    if not words:
        return []

    step = max_tokens - overlap
    chunks: list[str] = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start : start + max_tokens]))
        if start + max_tokens >= len(words):
            break
    return chunks
