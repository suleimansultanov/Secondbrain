"""Connector abstractions — normalize any source into contacts + interactions.

A CRM (or email/messaging) connector fetches raw records and maps them to the
neutral shapes below. The sync layer (`app/connectors/sync.py`) then stores them
as tenant-scoped rows and enqueues ingestion — connectors never touch the DB,
so adding a new source is cheap and isolated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

# Interaction types accepted by the schema (matches the CHECK constraint).
VALID_TYPES = {"call", "email", "message", "crm_note"}


@dataclass
class RawContact:
    external_id: str
    name: str
    email: str | None = None
    phone: str | None = None


@dataclass
class RawInteraction:
    external_id: str
    type: str  # one of VALID_TYPES
    content: str
    contact_external_id: str | None = None
    occurred_at: datetime | None = None


class CrmConnector(Protocol):
    """Source-specific adapter. Implementations live in e.g. `hubspot.py`."""

    async def fetch_contacts(self) -> list[RawContact]: ...  # noqa: E704

    async def fetch_interactions(
        self, since: datetime | None = None
    ) -> list[RawInteraction]: ...  # noqa: E704
