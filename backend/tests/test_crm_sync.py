"""Unit tests for CRM sync orchestration (fake connector + store, no DB)."""

from __future__ import annotations

import asyncio

from app.connectors.base import RawContact, RawInteraction
from app.connectors.sync import sync_crm


class _FakeConnector:
    def __init__(self, contacts, interactions):
        self._contacts = contacts
        self._interactions = interactions

    async def fetch_contacts(self):
        return self._contacts

    async def fetch_interactions(self, since=None):
        return self._interactions


class _FakeStore:
    def __init__(self):
        self.seen_external: set[str] = set()
        self.contacts: list[RawContact] = []
        self.interactions: list[tuple[RawInteraction, str | None]] = []

    async def upsert_contact(self, raw):
        self.contacts.append(raw)
        return f"cid-{raw.external_id}"

    async def upsert_interaction(self, raw, contact_id):
        created = raw.external_id not in self.seen_external
        self.seen_external.add(raw.external_id)
        self.interactions.append((raw, contact_id))
        return f"iid-{raw.external_id}", created


def _data():
    contacts = [RawContact(external_id="501", name="Jane")]
    interactions = [
        RawInteraction(external_id="1", type="crm_note", content="a", contact_external_id="501"),
        RawInteraction(external_id="2", type="email", content="b", contact_external_id="501"),
    ]
    return contacts, interactions


def test_sync_creates_and_enqueues_new() -> None:
    contacts, interactions = _data()
    store = _FakeStore()
    enq: list[tuple[str, str]] = []

    async def enqueue(iid, org):
        enq.append((iid, org))

    result = asyncio.run(sync_crm(_FakeConnector(contacts, interactions), store, enqueue, "org-1"))
    assert result.contacts == 1
    assert result.interactions_new == 2
    assert enq == [("iid-1", "org-1"), ("iid-2", "org-1")]
    # interaction linked to the contact's internal id
    assert store.interactions[0][1] == "cid-501"


def test_sync_idempotent_second_run_enqueues_nothing() -> None:
    contacts, interactions = _data()
    store = _FakeStore()
    enq: list[tuple[str, str]] = []

    async def enqueue(iid, org):
        enq.append((iid, org))

    conn = _FakeConnector(contacts, interactions)
    asyncio.run(sync_crm(conn, store, enqueue, "org-1"))
    enq.clear()
    result = asyncio.run(sync_crm(conn, store, enqueue, "org-1"))  # same records again
    assert result.interactions_new == 0
    assert enq == []  # nothing re-enqueued
