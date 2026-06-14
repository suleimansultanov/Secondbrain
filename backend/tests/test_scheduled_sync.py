"""Unit tests for the daily scheduled HubSpot sync cron task (no DB, no Redis)."""

from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.worker import tasks


class _FakeRedis:
    def __init__(self) -> None:
        self.jobs: list[tuple] = []

    async def enqueue_job(self, name: str, *args):
        self.jobs.append((name, args))


def _patch_settings(monkeypatch, **overrides) -> None:
    base = dict(hubspot_sync_org_id="", hubspot_sync_owner_user_id="")
    base.update(overrides)
    monkeypatch.setattr(tasks, "get_settings", lambda: Settings(**base))


def test_skips_when_no_target_configured(monkeypatch) -> None:
    _patch_settings(monkeypatch)
    redis = _FakeRedis()
    result = asyncio.run(tasks.scheduled_hubspot_sync({"redis": redis}))
    assert result == {"status": "skipped"}
    assert redis.jobs == []


def test_enqueues_when_target_configured(monkeypatch) -> None:
    _patch_settings(
        monkeypatch,
        hubspot_sync_org_id="org-1",
        hubspot_sync_owner_user_id="user-1",
    )
    redis = _FakeRedis()
    result = asyncio.run(tasks.scheduled_hubspot_sync({"redis": redis}))
    assert result == {"status": "enqueued", "org_id": "org-1"}
    assert redis.jobs == [("sync_hubspot", ("org-1", "user-1"))]
