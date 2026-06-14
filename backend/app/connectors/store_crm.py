"""Postgres sync store: upsert connector records within an org-scoped txn.

The cursor's transaction is already scoped to the tenant (admin role), so every
statement is constrained by RLS. Imported rows are owned by *owner_user_id*
(the org admin) and tagged with (source, external_id) for idempotent re-sync.
"""

from __future__ import annotations

from app.connectors.base import RawContact, RawInteraction


def _scalar(row):
    if row is None:
        return None
    return row[0] if isinstance(row, (tuple, list)) else next(iter(row.values()))


class PostgresSyncStore:
    def __init__(self, cursor, org_id: str, owner_user_id: str, source: str = "hubspot") -> None:
        self._cur = cursor
        self._org = org_id
        self._owner = owner_user_id
        self._source = source

    async def upsert_contact(self, raw: RawContact) -> str:
        await self._cur.execute(
            """
            INSERT INTO contacts (org_id, user_id, name, email, phone, source, external_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (org_id, source, external_id) WHERE external_id IS NOT NULL
            DO UPDATE SET name = EXCLUDED.name, email = EXCLUDED.email, phone = EXCLUDED.phone
            RETURNING id
            """,
            (self._org, self._owner, raw.name, raw.email, raw.phone, self._source, raw.external_id),
        )
        return str(_scalar(await self._cur.fetchone()))

    async def upsert_interaction(
        self, raw: RawInteraction, contact_id: str | None
    ) -> tuple[str, bool]:
        # (xmax = 0) is true only for a freshly INSERTed row (not an UPDATE).
        await self._cur.execute(
            """
            INSERT INTO interactions
                (org_id, user_id, contact_id, type, content, source, external_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (org_id, source, external_id) WHERE external_id IS NOT NULL
            DO UPDATE SET content = EXCLUDED.content
            RETURNING id, (xmax = 0) AS created
            """,
            (
                self._org,
                self._owner,
                contact_id,
                raw.type,
                raw.content,
                self._source,
                raw.external_id,
            ),
        )
        row = await self._cur.fetchone()
        if isinstance(row, (tuple, list)):
            return str(row[0]), bool(row[1])
        return str(row["id"]), bool(row["created"])
