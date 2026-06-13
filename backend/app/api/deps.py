"""FastAPI dependencies for authentication and tenant-scoped DB access."""
from __future__ import annotations

from typing import Annotated, AsyncIterator

import psycopg
from fastapi import Depends, Header, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.db import Database
from app.core.security import AuthContext, AuthError, verify_access_token

SettingsDep = Annotated[Settings, Depends(get_settings)]


def _bearer_token(authorization: str | None) -> str:
    """Extract the bearer token from an Authorization header."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization[7:].strip()


async def get_auth_context(
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
) -> AuthContext:
    """Verify the request's bearer token and return the tenant context."""
    token = _bearer_token(authorization)
    try:
        return verify_access_token(token, settings)
    except AuthError:
        # Generic message — never leak why verification failed.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


AuthContextDep = Annotated[AuthContext, Depends(get_auth_context)]


def get_database(request: Request) -> Database:
    """Return the app-wide Database held on app.state (set on startup)."""
    db: Database | None = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available",
        )
    return db


async def get_tenant_cursor(
    ctx: AuthContextDep,
    db: Annotated[Database, Depends(get_database)],
) -> AsyncIterator[psycopg.AsyncCursor]:
    """Yield a DB cursor inside a transaction scoped to the caller's org/user/role.

    Every query made through this cursor is automatically constrained by RLS to
    the caller's tenant — there is no way to read across `org_id` boundaries.
    """
    async with db.tenant_transaction(ctx) as cur:
        yield cur
