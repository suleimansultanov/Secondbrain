"""Postgres-backed chunk store.

Operates through a cursor whose transaction is already scoped to the tenant
(``app.current_org_id`` etc. set), so every statement is constrained by RLS.
"""

from __future__ import annotations

from app.rag.ingestion import ChunkRecord


class PostgresChunkStore:
    """Reads interaction text and writes its chunks, within an org-scoped txn."""

    def __init__(self, cursor) -> None:
        self._cur = cursor

    async def load_interaction_content(self, interaction_id: str) -> str | None:
        await self._cur.execute(
            "SELECT content FROM interactions WHERE id = %s",
            (interaction_id,),
        )
        row = await self._cur.fetchone()
        if row is None:
            return None
        # Support both tuple and dict-row cursors.
        return row[0] if isinstance(row, (tuple, list)) else row["content"]

    async def replace_chunks(self, interaction_id: str, records: list[ChunkRecord]) -> None:
        # Remove any previous chunks for this interaction (idempotent re-ingest).
        await self._cur.execute(
            "DELETE FROM interaction_chunks WHERE interaction_id = %s",
            (interaction_id,),
        )
        if not records:
            return
        # org_id and user_id are copied from the parent interaction so chunks
        # inherit the same tenant + owner scoping the RLS policy enforces.
        for rec in records:
            await self._cur.execute(
                """
                INSERT INTO interaction_chunks
                    (org_id, interaction_id, user_id, chunk_index, content, embedding)
                SELECT i.org_id, i.id, i.user_id, %s, %s, %s
                FROM interactions i
                WHERE i.id = %s
                """,
                (rec.chunk_index, rec.content, rec.embedding, interaction_id),
            )
