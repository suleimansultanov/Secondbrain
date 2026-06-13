"""Auth: verify Supabase JWTs and extract the tenant context.

Supabase issues HS256 access tokens signed with the project's JWT secret and
carrying ``aud="authenticated"`` and ``sub=<auth user id>``.

`org_id` and the application role are NOT present by default. They must be
injected as custom claims via a Supabase **custom access token hook**. We read
the org from the ``org_id`` claim and the application role from ``app_role``.

> Why ``app_role`` and not ``role``: Supabase reserves the top-level ``role``
> claim for the Postgres role (``authenticated`` / ``anon``). Overwriting it
> would break the database connection role, so the application role lives under
> a separate claim name.
"""
from __future__ import annotations

from dataclasses import dataclass

from jose import JWTError, jwt

from app.core.config import Settings

VALID_ROLES = {"admin", "agent"}


class AuthError(Exception):
    """Raised when a token is missing, invalid, or lacks required claims."""


@dataclass(frozen=True)
class AuthContext:
    """The verified tenant context for a single request."""

    user_id: str
    org_id: str
    role: str  # 'admin' | 'agent'


def verify_access_token(token: str, settings: Settings) -> AuthContext:
    """Verify a Supabase access token and return its :class:`AuthContext`.

    Raises :class:`AuthError` on any verification or claim problem. The error
    message is intentionally generic — never leak why a token failed.
    """
    if not settings.supabase_jwt_secret:
        raise AuthError("auth is not configured")
    if not token:
        raise AuthError("missing token")

    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
        )
    except JWTError as exc:  # invalid signature, expired, wrong audience, ...
        raise AuthError("invalid token") from exc

    user_id = claims.get("sub")
    org_id = claims.get(settings.org_id_claim)
    role = claims.get(settings.role_claim)

    if not user_id:
        raise AuthError("token missing subject")
    if not org_id:
        raise AuthError("token missing org_id claim")
    if role not in VALID_ROLES:
        raise AuthError("token missing or invalid app_role claim")

    return AuthContext(user_id=str(user_id), org_id=str(org_id), role=str(role))
