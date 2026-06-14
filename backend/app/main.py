"""SecondBrain API — entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_brain, routes_connectors, routes_me
from app.core.config import get_settings
from app.core.db import Database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the DB pool on startup, close it on shutdown."""
    settings = get_settings()
    db = Database(settings)
    if settings.database_url:
        await db.connect()
    app.state.db = db
    try:
        yield
    finally:
        await db.close()


app = FastAPI(title="SecondBrain API", version="0.0.1", lifespan=lifespan)

_origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_me.router)
app.include_router(routes_brain.router)
app.include_router(routes_connectors.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "secondbrain-api"}
