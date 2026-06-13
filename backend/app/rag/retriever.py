"""Postgres + pgvector retriever.

Runs through an org-scoped cursor, so RLS guarantees only the caller's org's
chunks are ever considered — cross-tenant retrieval is impossible.
"""

from __future__ import annotations


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
            (embedding, top_k),
        )
        rows = await self._cur.fetchall()
        results: list[tuple[str, str]] = []
        for row in rows:
            if isinstance(row, (tuple, list)):
                results.append((str(row[0]), row[1]))
            else:
                results.append((str(row["interaction_id"]), row["content"]))
        return results
