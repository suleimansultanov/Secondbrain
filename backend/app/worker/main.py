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

from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.worker.tasks import (
    ingest_interaction,
    ping,
    scheduled_hubspot_sync,
    sync_hubspot,
)

logger = logging.getLogger("secondbrain.worker")


async def startup(ctx: dict) -> None:
    logger.info("worker started")


async def shutdown(ctx: dict) -> None:
    logger.info("worker stopped")


def redis_settings() -> RedisSettings:
    """Build arq RedisSettings from the configured REDIS_URL.

    Falls back to localhost if REDIS_URL is unset/blank so importing the worker
    never crashes (e.g. in tests or when Redis isn't configured yet).
    """
    url = get_settings().redis_url or "redis://localhost:6379"
    return RedisSettings.from_dsn(url)


class WorkerSettings:
    """arq worker configuration (referenced by the `arq` CLI)."""

    functions = [ping, ingest_interaction, sync_hubspot]
    # Daily HubSpot sync at 03:00 UTC. No-op unless a sync target is configured
    # (HUBSPOT_SYNC_ORG_ID / HUBSPOT_SYNC_OWNER_USER_ID).
    cron_jobs = [cron(scheduled_hubspot_sync, hour=3, minute=0)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings()
