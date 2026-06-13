"""Auth: verify Supabase JWTs and extract the tenant context.

Supabase access tokens carry ``aud="authenticated"`` and ``sub=<auth user id>``.
New projects sign with **asymmetric** keys (ES256/RS256); we verify those against
the project's JWKS (public keys at ``<supabase_url>/auth/v1/.well-known/jwks.json``).
Legacy projects sign with **HS256** and a shared secret — supported as a fallback.

`org_id` and the application role are added as custom claims by a Supabase
**custom access token hook**. We read the org from ``org_id`` and the application
role from ``app_role``.

> Why ``app_role`` and not ``role``: Supabase reserves the top-level ``role``
> claim for the Postgres role (``authenticated`` / ``anon``). Overwriting it
> would break the database connection role, so the application role lives under
> a separate claim name.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from jose import JWTError, jwt

from app.core.config import Settings

VALID_ROLES = {"admin", "agent"}

# Cache the JWKS in-process (keyed by URL). Supabase keys rotate rarely; on an
# unknown `kid` we refetch once to pick up a rotation.
_jwks_cache: dict[str, dict] = {}


class AuthError(Exception):
    """Raised when a token is missing, invalid, or lacks required claims."""


@dataclass(frozen=True)
class AuthContext:
    """The verified tenant context for a single request."""

    user_id: str
    org_id: str
    role: str  # 'admin' | 'agent'


def _fetch_jwks(url: str) -> dict:
    """Fetch (and cache) the JWKS document for *url*."""
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    _jwks_cache[url] = data
    return data


def _jwk_for_kid(url: str, kid: str | None) -> dict:
    """Return the JWK matching *kid*, refetching once if not cached."""
    keys = _jwks_cache.get(url, {}).get("keys")
    if keys is not None:
        for key in keys:
            if key.get("kid") == kid:
                return key
    # Not cached or key rotated — fetch fresh and look again.
    for key in _fetch_jwks(url).get("keys", []):
        if key.get("kid") == kid:
            return key
    raise AuthError("unknown signing key")


def _decode(token: str, settings: Settings) -> dict:
    """Verify the token signature and return its claims."""
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise AuthError("invalid token") from exc

    alg = header.get("alg")
    try:
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise AuthError("auth is not configured")
            key: object = settings.supabase_jwt_secret
        else:
            if not settings.supabase_url:
                raise AuthError("auth is not configured")
            key = _jwk_for_kid(settings.jwks_url, header.get("kid"))

        return jwt.decode(
            token,
            key,
            algorithms=[alg] if alg else ["ES256", "RS256", "HS256"],
            audience=settings.jwt_audience,
        )
    except JWTError as exc:  # invalid signature, expired, wrong audience, ...
        raise AuthError("invalid token") from exc


def verify_access_token(token: str, settings: Settings) -> AuthContext:
    """Verify a Supabase access token and return its :class:`AuthContext`.

    Raises :class:`AuthError` on any verification or claim problem. The error
    message is intentionally generic — never leak why a token failed.
    """
    if not token:
        raise AuthError("missing token")

    claims = _decode(token, settings)

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
