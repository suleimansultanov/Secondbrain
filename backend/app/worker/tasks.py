"""Background tasks run by the arq worker.

Phase 0 ships only skeleton tasks that prove the queue plumbing end to end.
Phase 1 fills `ingest_interaction` with the real pipeline:
normalize -> identify contact -> chunk (~500 tokens) -> embed (OpenAI) ->
store the vector on the interaction row (always scoped to its `org_id`).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("secondbrain.worker")


async def ping(ctx: dict | None = None) -> str:
    """Health task — enqueue it to confirm the worker is consuming jobs."""
    return "pong"


async def ingest_interaction(ctx: dict | None, interaction_id: str, org_id: str) -> dict[str, Any]:
    """Skeleton ingestion task.

    Validates its inputs and returns a status payload. The real implementation
    (Phase 1) MUST keep every read/write scoped to ``org_id`` so ingestion can
    never cross tenant boundaries.
    """
    if not interaction_id or not org_id:
        raise ValueError("interaction_id and org_id are required")

    logger.info("ingest_interaction (stub): interaction=%s org=%s", interaction_id, org_id)
    return {
        "status": "stub-ok",
        "interaction_id": interaction_id,
        "org_id": org_id,
    }
