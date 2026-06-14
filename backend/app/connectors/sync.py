"""Sync orchestration: pull from a connector, store, enqueue ingestion.

Storage-agnostic and unit-testable: depends only on a `connector`, a `store`
(upserts), and an `enqueue` callback. The real Postgres store lives in
`store_crm.py`; the worker wires them together with an org-scoped DB connection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

from app.connectors.base import CrmConnector, RawContact, RawInteraction


@dataclass
class SyncResult:
    contacts: int
    interactions_new: int


class SyncStore(Protocol):
    async def upsert_contact(
        self, raw: RawContact
    ) -> str: ...  # noqa: E704  -> internal contact id
    async def upsert_interaction(
        self, raw: RawInteraction, contact_id: str | None
    ) -> tuple[str, bool]: ...  # noqa: E704  -> (interaction_id, created_new)


# enqueue(interaction_id, org_id) -> schedules ingestion
EnqueueFn = Callable[[str, str], Awaitable[None]]


async def sync_crm(
    connector: CrmConnector,
    store: SyncStore,
    enqueue: EnqueueFn,
    org_id: str,
) -> SyncResult:
    """Fetch contacts + interactions, upsert them, and enqueue ingestion of new ones.

    Idempotent: re-running only enqueues interactions that were newly created
    (dedup is the store's job, via (org, source, external_id)).
    """
    contacts = await connector.fetch_contacts()
    by_external: dict[str, str] = {}
    for c in contacts:
        by_external[c.external_id] = await store.upsert_contact(c)

    new_count = 0
    for it in await connector.fetch_interactions():
        contact_id = by_external.get(it.contact_external_id) if it.contact_external_id else None
        interaction_id, created = await store.upsert_interaction(it, contact_id)
        if created:
            await enqueue(interaction_id, org_id)
            new_count += 1

    return SyncResult(contacts=len(contacts), interactions_new=new_count)
