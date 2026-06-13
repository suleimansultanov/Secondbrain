"""Helpers for enqueuing background jobs from the API process."""

from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings


async def get_arq_pool() -> ArqRedis:
    """Open an arq Redis pool for enqueuing jobs.

    Usage (e.g. from a FastAPI route):

        pool = await get_arq_pool()
        await pool.enqueue_job("ingest_interaction", interaction_id, org_id)
    """
    return await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
