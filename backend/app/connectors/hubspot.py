"""HubSpot CRM connector (CRM API v3).

Auth: a HubSpot **Private App** access token (simplest for a single account;
swap for OAuth per-org later). The HTTP client is injectable so the mapping and
pagination are unit-testable without network.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from app.connectors.base import RawContact, RawInteraction
from app.core.config import get_settings

HUBSPOT_BASE = "https://api.hubapi.com"
PAGE_LIMIT = 100

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str | None) -> str:
    """Crudely strip HTML tags and collapse whitespace (HubSpot bodies are HTML)."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", text)).strip()


def parse_timestamp(value: str | None) -> datetime | None:
    """Parse a HubSpot timestamp (ISO 8601 or epoch-millis string)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (ValueError, TypeError):
        return None


# --- pure mappers (HubSpot object dict -> neutral shape) -------------------


def map_contact(obj: dict) -> RawContact:
    p = obj.get("properties", {})
    name = " ".join(x for x in [p.get("firstname"), p.get("lastname")] if x).strip()
    return RawContact(
        external_id=str(obj["id"]),
        name=name or (p.get("email") or "Unknown"),
        email=p.get("email"),
        phone=p.get("phone"),
    )


def map_note(obj: dict) -> RawInteraction:
    p = obj.get("properties", {})
    return RawInteraction(
        external_id=str(obj["id"]),
        type="crm_note",
        content=strip_html(p.get("hs_note_body")),
        occurred_at=parse_timestamp(p.get("hs_timestamp")),
    )


def map_call(obj: dict) -> RawInteraction:
    p = obj.get("properties", {})
    title = p.get("hs_call_title") or ""
    body = strip_html(p.get("hs_call_body"))
    return RawInteraction(
        external_id=str(obj["id"]),
        type="call",
        content=(f"{title}\n{body}".strip() if title else body),
        occurred_at=parse_timestamp(p.get("hs_timestamp")),
    )


def map_email(obj: dict) -> RawInteraction:
    p = obj.get("properties", {})
    subject = p.get("hs_email_subject") or ""
    text = strip_html(p.get("hs_email_text"))
    return RawInteraction(
        external_id=str(obj["id"]),
        type="email",
        content=(f"{subject}\n{text}".strip() if subject else text),
        occurred_at=parse_timestamp(p.get("hs_timestamp")),
    )


# Object type -> (properties to request, mapper)
_OBJECTS = {
    "notes": (["hs_note_body", "hs_timestamp"], map_note),
    "calls": (["hs_call_title", "hs_call_body", "hs_timestamp"], map_call),
    "emails": (["hs_email_subject", "hs_email_text", "hs_timestamp"], map_email),
}


class HubSpotConnector:
    def __init__(self, token: str | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._token = token or get_settings().hubspot_access_token
        self._client = client

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=HUBSPOT_BASE,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=30,
            )
        return self._client

    async def _list(self, path: str, properties: list[str]) -> list[dict]:
        """Page through a CRM object list endpoint, returning all result objects."""
        results: list[dict] = []
        after: str | None = None
        while True:
            params: dict = {"limit": PAGE_LIMIT, "properties": ",".join(properties)}
            if after:
                params["after"] = after
            resp = await self._http().get(path, params=params)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("results", []))
            after = data.get("paging", {}).get("next", {}).get("after")
            if not after:
                return results

    async def fetch_contacts(self) -> list[RawContact]:
        objs = await self._list(
            "/crm/v3/objects/contacts", ["firstname", "lastname", "email", "phone"]
        )
        return [map_contact(o) for o in objs]

    async def fetch_interactions(self, since: datetime | None = None) -> list[RawInteraction]:
        out: list[RawInteraction] = []
        for object_type, (props, mapper) in _OBJECTS.items():
            objs = await self._list(f"/crm/v3/objects/{object_type}", props)
            for o in objs:
                rec = mapper(o)
                if rec.content and (
                    since is None or rec.occurred_at is None or rec.occurred_at >= since
                ):
                    out.append(rec)
        return out
