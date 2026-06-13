"""arq worker entrypoint.

Run the worker with:

    cd backend
    arq app.worker.main.WorkerSettings

It needs a reachable Redis (set ``REDIS_URL``; defaults to localhost). The worker
process is separate from the FastAPI app: the API enqueues jobs (see
``app/worker/queue.py``) and this process consumes them.
"""

from __future__ import annotations

import logging

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.worker.tasks import ingest_interaction, ping

logger = logging.getLogger("secondbrain.worker")


async def startup(ctx: dict) -> None:
    logger.info("worker started")


async def shutdown(ctx: dict) -> None:
    logger.info("worker stopped")


def redis_settings() -> RedisSettings:
    """Build arq RedisSettings from the configured REDIS_URL."""
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    """arq worker configuration (referenced by the `arq` CLI)."""

    functions = [ping, ingest_interaction]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings()
