"""Unit tests for HubSpot field mapping (pure functions, no network)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.connectors.hubspot import (
    map_call,
    map_contact,
    map_email,
    map_note,
    parse_timestamp,
    strip_html,
)


def test_strip_html() -> None:
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert strip_html(None) == ""
    assert strip_html("  spaced\n\ntext ") == "spaced text"


def test_parse_timestamp_iso_and_epoch() -> None:
    assert parse_timestamp("2026-06-13T10:00:00Z") == datetime(
        2026, 6, 13, 10, 0, tzinfo=timezone.utc
    )
    # epoch millis as string
    assert parse_timestamp("1700000000000").tzinfo is not None
    assert parse_timestamp(None) is None
    assert parse_timestamp("not-a-date") is None


def test_map_contact() -> None:
    obj = {
        "id": "501",
        "properties": {
            "firstname": "Jane",
            "lastname": "Doe",
            "email": "jane@acme.example",
            "phone": "+1-555",
        },
    }
    c = map_contact(obj)
    assert c.external_id == "501"
    assert c.name == "Jane Doe"
    assert c.email == "jane@acme.example"


def test_map_note() -> None:
    obj = {"id": "1", "properties": {"hs_note_body": "<p>Met client</p>", "hs_timestamp": None}}
    n = map_note(obj)
    assert n.type == "crm_note"
    assert n.content == "Met client"
    assert n.external_id == "1"


def test_map_call_and_email_combine_title_subject() -> None:
    call = map_call(
        {"id": "2", "properties": {"hs_call_title": "Intro call", "hs_call_body": "<i>notes</i>"}}
    )
    assert call.type == "call"
    assert "Intro call" in call.content and "notes" in call.content

    email = map_email(
        {"id": "3", "properties": {"hs_email_subject": "Quote", "hs_email_text": "Pricing details"}}
    )
    assert email.type == "email"
    assert "Quote" in email.content and "Pricing details" in email.content
