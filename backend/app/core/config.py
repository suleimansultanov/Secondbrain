"""Application settings, loaded from environment via pydantic-settings.

Never hard-code secrets. Document every new variable in `.env.example`.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"

    # Database (Postgres + pgvector, EU region)
    database_url: str = ""

    # Supabase Auth — JWTs are HS256-signed with this secret.
    supabase_jwt_secret: str = ""
    # Supabase access tokens carry aud="authenticated".
    jwt_audience: str = "authenticated"

    # Names of the custom claims the access-token hook must add (see
    # app/core/security.py for why we avoid the reserved `role` claim).
    org_id_claim: str = "org_id"
    role_claim: str = "app_role"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
