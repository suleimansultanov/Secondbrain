"""`/me` — a minimal protected route that echoes the verified tenant context.

Serves as the first end-to-end check that auth + tenant scoping are wired up.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import AuthContextDep

router = APIRouter(tags=["auth"])


class MeResponse(BaseModel):
    user_id: str
    org_id: str
    role: str


@router.get("/me", response_model=MeResponse)
async def read_me(ctx: AuthContextDep) -> MeResponse:
    """Return the authenticated user's tenant context."""
    return MeResponse(user_id=ctx.user_id, org_id=ctx.org_id, role=ctx.role)
