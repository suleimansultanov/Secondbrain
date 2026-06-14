"""Unit tests for POST /connectors/sync (admin gating + enqueue), no Redis.

We override the auth context and the arq pool dependency so the route can be
exercised without a real token or a running Redis.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import get_auth_context
from app.api.routes_connectors import get_arq_pool_dep
from app.core.security import AuthContext
from app.main import app


class _FakeJob:
    job_id = "job-123"


class _FakePool:
    def __init__(self) -> None:
        self.jobs: list[tuple] = []

    async def enqueue_job(self, name: str, *args):
        self.jobs.append((name, args))
        return _FakeJob()


def _client_with(role: str, pool: _FakePool) -> TestClient:
    app.dependency_overrides[get_auth_context] = lambda: AuthContext(
        user_id="user-1", org_id="org-1", role=role
    )
    app.dependency_overrides[get_arq_pool_dep] = lambda: pool
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_admin_can_trigger_sync_and_job_is_enqueued() -> None:
    pool = _FakePool()
    client = _client_with("admin", pool)
    resp = client.post("/connectors/sync")
    assert resp.status_code == 200
    assert resp.json() == {"status": "queued", "job_id": "job-123"}
    assert pool.jobs == [("sync_hubspot", ("org-1", "user-1"))]


def test_agent_is_forbidden_and_nothing_enqueued() -> None:
    pool = _FakePool()
    client = _client_with("agent", pool)
    resp = client.post("/connectors/sync")
    assert resp.status_code == 403
    assert pool.jobs == []
