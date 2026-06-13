"""Unit tests for the arq worker skeleton (no live Redis required)."""

from __future__ import annotations

import asyncio

import pytest

from app.worker.main import WorkerSettings
from app.worker.tasks import ingest_interaction, ping


def test_ping_returns_pong() -> None:
    assert asyncio.run(ping(None)) == "pong"


def test_ingest_interaction_stub() -> None:
    result = asyncio.run(ingest_interaction(None, "interaction-1", "org-1"))
    assert result == {
        "status": "stub-ok",
        "interaction_id": "interaction-1",
        "org_id": "org-1",
    }


def test_ingest_interaction_requires_ids() -> None:
    with pytest.raises(ValueError):
        asyncio.run(ingest_interaction(None, "", "org-1"))
    with pytest.raises(ValueError):
        asyncio.run(ingest_interaction(None, "interaction-1", ""))


def test_worker_registers_functions() -> None:
    names = {getattr(f, "__name__", "") for f in WorkerSettings.functions}
    assert {"ping", "ingest_interaction"} <= names


def test_worker_has_redis_settings() -> None:
    assert WorkerSettings.redis_settings is not None
