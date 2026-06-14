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

    # Connectors
    hubspot_access_token: str = ""  # HubSpot Private App token (CRM sync)

    # Supabase Auth.
    # New projects sign JWTs with asymmetric keys (ES256/RS256); the backend
    # verifies them against the project's JWKS endpoint, derived from supabase_url.
    supabase_url: str = ""
    # Legacy fallback: HS256 shared secret (only if a project still uses it).
    supabase_jwt_secret: str = ""
    # Supabase access tokens carry aud="authenticated".
    jwt_audience: str = "authenticated"

    @property
    def jwks_url(self) -> str:
        """Supabase JWKS endpoint (public keys) for verifying asymmetric JWTs."""
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    # Names of the custom claims the access-token hook must add (see
    # app/core/security.py for why we avoid the reserved `role` claim).
    org_id_claim: str = "org_id"
    role_claim: str = "app_role"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
