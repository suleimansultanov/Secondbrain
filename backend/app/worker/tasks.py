"""Background tasks run by the arq worker.

`ingest_interaction` runs the RAG pipeline for one interaction:
load (org-scoped) -> chunk (~500 tokens) -> embed (OpenAI) -> store chunks.
Every statement runs inside a transaction scoped to the interaction's `org_id`,
so ingestion can never cross tenant boundaries.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.rag.embeddings import Embedder
from app.rag.ingestion import run_ingestion
from app.rag.store import PostgresChunkStore

logger = logging.getLogger("secondbrain.worker")

# Scope the transaction to the org (admin role so the worker may ingest any
# user's interaction within that org). Parameterised — no injection.
_SET_ORG_CTX = (
    "SELECT set_config('app.current_org_id', %(org)s, true), "
    "set_config('app.current_user_id', %(org)s, true), "
    "set_config('app.current_user_role', 'admin', true)"
)


async def ping(ctx: dict | None = None) -> str:
    """Health task — enqueue it to confirm the worker is consuming jobs."""
    return "pong"


async def ingest_interaction(ctx: dict | None, interaction_id: str, org_id: str) -> dict[str, Any]:
    """Chunk + embed + store one interaction, scoped to ``org_id``."""
    if not interaction_id or not org_id:
        raise ValueError("interaction_id and org_id are required")

    import psycopg

    settings = get_settings()
    embedder = Embedder()

    logger.info("ingest_interaction: interaction=%s org=%s", interaction_id, org_id)
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(_SET_ORG_CTX, {"org": org_id})
                store = PostgresChunkStore(cur)
                return await run_ingestion(store, embedder, interaction_id)
