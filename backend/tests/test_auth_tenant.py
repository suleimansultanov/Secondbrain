"""Unit tests for auth verification and tenant-context construction.

These tests do NOT require a database — they cover the JWT verification logic
and the (pure) building of the session-setting parameters. The live RLS
behaviour is covered separately by tests/test_rls_isolation.py.
"""

from __future__ import annotations

import time

import pytest
from jose import jwt

from app.core.config import Settings
from app.core.db import tenant_context_params
from app.core.security import AuthContext, AuthError, verify_access_token

SECRET = "test-jwt-secret"
ORG_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "11111111-1111-1111-1111-111111111111"


def _settings() -> Settings:
    return Settings(
        supabase_jwt_secret=SECRET,
        jwt_audience="authenticated",
        database_url="",
    )


def _make_token(**overrides) -> str:
    claims = {
        "sub": USER_ID,
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        "org_id": ORG_ID,
        "app_role": "agent",
    }
    claims.update(overrides)
    return jwt.encode(claims, SECRET, algorithm="HS256")


# ---------------------------------------------------------------------------
# verify_access_token
# ---------------------------------------------------------------------------


def test_valid_token_returns_context() -> None:
    ctx = verify_access_token(_make_token(), _settings())
    assert ctx == AuthContext(user_id=USER_ID, org_id=ORG_ID, role="agent")


def test_admin_role_accepted() -> None:
    ctx = verify_access_token(_make_token(app_role="admin"), _settings())
    assert ctx.role == "admin"


def test_bad_signature_rejected() -> None:
    forged = jwt.encode(
        {
            "sub": USER_ID,
            "aud": "authenticated",
            "org_id": ORG_ID,
            "app_role": "agent",
            "exp": int(time.time()) + 3600,
        },
        "wrong-secret",
        algorithm="HS256",
    )
    with pytest.raises(AuthError):
        verify_access_token(forged, _settings())


def test_expired_token_rejected() -> None:
    with pytest.raises(AuthError):
        verify_access_token(_make_token(exp=int(time.time()) - 10), _settings())


def test_wrong_audience_rejected() -> None:
    with pytest.raises(AuthError):
        verify_access_token(_make_token(aud="some-other-audience"), _settings())


def test_missing_org_id_rejected() -> None:
    token = _make_token()
    # rebuild without org_id
    token = jwt.encode(
        {
            "sub": USER_ID,
            "aud": "authenticated",
            "app_role": "agent",
            "exp": int(time.time()) + 3600,
        },
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(AuthError):
        verify_access_token(token, _settings())


def test_invalid_role_rejected() -> None:
    with pytest.raises(AuthError):
        verify_access_token(_make_token(app_role="superuser"), _settings())


def test_empty_token_rejected() -> None:
    with pytest.raises(AuthError):
        verify_access_token("", _settings())


# ---------------------------------------------------------------------------
# tenant_context_params
# ---------------------------------------------------------------------------


def test_tenant_context_params() -> None:
    ctx = AuthContext(user_id=USER_ID, org_id=ORG_ID, role="admin")
    assert tenant_context_params(ctx) == {
        "org_id": ORG_ID,
        "user_id": USER_ID,
        "role": "admin",
    }
