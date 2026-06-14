"""Database access with per-request tenant scoping.

The application connects with a **limited-privilege** Postgres role (one that
does NOT bypass RLS). Before any tenant-scoped query, the request's
:class:`~app.core.security.AuthContext` is pushed into the transaction as
session settings, which the RLS policies read:

    app.current_org_id, app.current_user_id, app.current_user_role

We use ``set_config(key, value, is_local => true)`` rather than a string-built
``SET LOCAL`` so the values are bound as parameters — no SQL injection surface.
``is_local => true`` scopes the settings to the current transaction, exactly
like ``SET LOCAL``.
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from typing import AsyncIterator

import psycopg
from psycopg_pool import AsyncConnectionPool

from app.core.config import Settings
from app.core.security import AuthContext

# Single statement that sets all three tenant settings, transaction-local.
_SET_TENANT_SQL = (
    "SELECT "
    "set_config('app.current_org_id',  %(org_id)s,  true), "
    "set_config('app.current_user_id', %(user_id)s, true), "
    "set_config('app.current_user_role', %(role)s,  true)"
)

# A Postgres role name we are willing to interpolate into `SET LOCAL ROLE`
# (which cannot be parameterised). Trusted config, but validated defensively.
_ROLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def set_role_sql(role: str) -> str:
    """Return a safe `SET LOCAL ROLE` statement for *role* (validated identifier)."""
    if not _ROLE_RE.match(role):
        raise ValueError(f"Invalid db_app_role {role!r}; expected a plain identifier.")
    return f'SET LOCAL ROLE "{role}"'


def tenant_context_params(ctx: AuthContext) -> dict[str, str]:
    """Build the bound parameters for :data:`_SET_TENANT_SQL` (pure; testable)."""
    return {"org_id": ctx.org_id, "user_id": ctx.user_id, "role": ctx.role}


class Database:
    """Owns the async connection pool for the app's lifetime."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pool: AsyncConnectionPool | None = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = AsyncConnectionPool(conninfo=self._settings.database_url, open=False)
            await self._pool.open()

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def tenant_transaction(self, ctx: AuthContext) -> AsyncIterator[psycopg.AsyncCursor]:
        """Yield a cursor inside a transaction scoped to *ctx*.

        The tenant settings are applied first; on exit the transaction commits
        (or rolls back on error), which also clears the LOCAL settings.
        """
        if self._pool is None:
            raise RuntimeError("Database pool is not open; call connect() first.")

        async with self._pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    # Switch to a non-BYPASSRLS role so RLS policies are enforced
                    # for the rest of this transaction (cleared on commit/rollback).
                    if self._settings.db_app_role:
                        await cur.execute(set_role_sql(self._settings.db_app_role))
                    await cur.execute(_SET_TENANT_SQL, tenant_context_params(ctx))
                    yield cur
