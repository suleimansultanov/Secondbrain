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

    # Comma-separated list of allowed browser origins (the web dashboard).
    cors_origins: str = "http://localhost:3000"

    # Database (Postgres + pgvector, EU region)
    database_url: str = ""

    # Redis (arq job queue for background ingestion)
    redis_url: str = "redis://localhost:6379"

    # AI providers
    openai_api_key: str = ""  # embeddings (text-embedding-3-small)
    anthropic_api_key: str = ""  # answers (Claude)
    embedding_model: str = "text-embedding-3-small"
    answer_model: str = "claude-haiku-4-5-20251001"

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
