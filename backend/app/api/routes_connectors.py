"""`POST /connectors/sync` — trigger a CRM sync for the caller's org.

Admin-only. The endpoint does no heavy work itself: it enqueues the
`sync_hubspot` background job (consumed by the arq worker) and returns
immediately, so the dashboard can offer a "Sync now" button without blocking.
"""

from __future__ import annotations

from typing import Annotated, AsyncIterator

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import AuthContextDep
from app.worker.queue import get_arq_pool

router = APIRouter(prefix="/connectors", tags=["connectors"])


async def get_arq_pool_dep() -> AsyncIterator[ArqRedis]:
    """Yield an arq Redis pool for the request, closing it afterwards.

    Kept as a separate dependency (rather than calling get_arq_pool inline) so
    tests can override it with a fake pool — no Redis needed.
    """
    pool = await get_arq_pool()
    try:
        yield pool
    finally:
        await pool.close()


ArqPoolDep = Annotated[ArqRedis, Depends(get_arq_pool_dep)]


class SyncResponse(BaseModel):
    status: str
    job_id: str | None = None


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(ctx: AuthContextDep, pool: ArqPoolDep) -> SyncResponse:
    """Enqueue a HubSpot sync for the caller's org. Admins only."""
    if ctx.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only org admins can trigger a sync",
        )
    job = await pool.enqueue_job("sync_hubspot", ctx.org_id, ctx.user_id)
    return SyncResponse(status="queued", job_id=job.job_id if job else None)
