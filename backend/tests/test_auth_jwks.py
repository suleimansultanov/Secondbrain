"""Test the asymmetric (JWKS) verification path with a locally generated key.

No network: we pre-populate the in-process JWKS cache with a public key we
control, sign a token with the matching private key, and verify it.
"""

from __future__ import annotations

import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

from app.core import security
from app.core.config import Settings
from app.core.security import AuthContext, verify_access_token

ORG_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "11111111-1111-1111-1111-111111111111"
KID = "test-kid"


def _settings() -> Settings:
    return Settings(
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret="",
        jwt_audience="authenticated",
        database_url="",
    )


def _rsa_keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv_pem, pub_pem


def test_rs256_token_verified_via_jwks() -> None:
    settings = _settings()
    priv_pem, pub_pem = _rsa_keypair()

    jwk_dict = jwk.construct(pub_pem, "RS256").to_dict()
    jwk_dict["kid"] = KID
    # Seed the cache so no network call is made.
    security._jwks_cache[settings.jwks_url] = {"keys": [jwk_dict]}

    token = jwt.encode(
        {
            "sub": USER_ID,
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
            "org_id": ORG_ID,
            "app_role": "admin",
        },
        priv_pem,
        algorithm="RS256",
        headers={"kid": KID},
    )

    ctx = verify_access_token(token, settings)
    assert ctx == AuthContext(user_id=USER_ID, org_id=ORG_ID, role="admin")
