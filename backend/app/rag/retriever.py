"""Postgres + pgvector retriever.

Runs through an org-scoped cursor, so RLS guarantees only the caller's org's
chunks are ever considered — cross-tenant retrieval is impossible.
"""

from __future__ import annotations


def to_vector_literal(embedding: list[float]) -> str:
    """Format an embedding as a pgvector text literal, e.g. ``[0.1,0.2,...]``.

    pgvector's input format is bracketed; passing a raw Python list adapts to a
    Postgres array (``{...}``), which does not match ``::vector``.
    """
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


class PostgresRetriever:
    def __init__(self, cursor) -> None:
        self._cur = cursor

    async def search(self, embedding: list[float], top_k: int) -> list[tuple[str, str]]:
        """Return up to *top_k* (interaction_id, content) chunks nearest to *embedding*."""
        await self._cur.execute(
            """
            SELECT interaction_id, content
            FROM interaction_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (to_vector_literal(embedding), top_k),
        )
        rows = await self._cur.fetchall()
        results: list[tuple[str, str]] = []
        for row in rows:
            if isinstance(row, (tuple, list)):
                results.append((str(row[0]), row[1]))
            else:
                results.append((str(row["interaction_id"]), row["content"]))
        return results
