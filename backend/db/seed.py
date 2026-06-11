#!/usr/bin/env python3
"""backend/db/seed.py

Seed the database with two isolated organisations, an admin + agent in each,
and a couple of contacts / interactions per org.

Usage
-----
    export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
    python backend/db/seed.py

The script is idempotent: it uses INSERT ... ON CONFLICT DO NOTHING so it is
safe to run multiple times.  It reads DATABASE_URL from the environment and
never hard-codes credentials.

Dependencies (already in requirements.txt):
    psycopg2-binary  (or psycopg[binary] for psycopg3)
"""

from __future__ import annotations

import os
import sys
import uuid

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:  # pragma: no cover
    sys.exit(
        "psycopg2 is not installed.  Run: pip install psycopg2-binary"
    )

# ---------------------------------------------------------------------------
# Fixed UUIDs so the seed is deterministic and the isolation test can use the
# same IDs without a round-trip.  These are NOT secrets.
# ---------------------------------------------------------------------------
ORG_A_ID  = uuid.UUID("00000000-0000-0000-0000-000000000001")
ORG_B_ID  = uuid.UUID("00000000-0000-0000-0000-000000000002")

USER_A_ADMIN_ID = uuid.UUID("00000000-0000-0000-0001-000000000001")
USER_A_AGENT_ID = uuid.UUID("00000000-0000-0000-0001-000000000002")
USER_B_ADMIN_ID = uuid.UUID("00000000-0000-0000-0002-000000000001")
USER_B_AGENT_ID = uuid.UUID("00000000-0000-0000-0002-000000000002")

CONTACT_A1_ID = uuid.UUID("00000000-0000-0001-0001-000000000001")
CONTACT_A2_ID = uuid.UUID("00000000-0000-0001-0001-000000000002")
CONTACT_B1_ID = uuid.UUID("00000000-0000-0001-0002-000000000001")
CONTACT_B2_ID = uuid.UUID("00000000-0000-0001-0002-000000000002")

INTERACTION_A1_ID = uuid.UUID("00000000-0000-0002-0001-000000000001")
INTERACTION_A2_ID = uuid.UUID("00000000-0000-0002-0001-000000000002")
INTERACTION_B1_ID = uuid.UUID("00000000-0000-0002-0002-000000000001")
INTERACTION_B2_ID = uuid.UUID("00000000-0000-0002-0002-000000000002")

# Minimal placeholder embeddings (all zeros).  Replace with real OpenAI
# text-embedding-3-small vectors in production.
ZERO_EMBEDDING = [0.0] * 1536


def get_connection() -> "psycopg2.connection":
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit(
            "DATABASE_URL environment variable is not set.\n"
            "Example: export DATABASE_URL=postgresql://user:pass@host:5432/dbname"
        )
    return psycopg2.connect(database_url)


def seed(conn: "psycopg2.connection") -> None:
    with conn:
        with conn.cursor() as cur:
            # -- organisations --------------------------------------------------
            cur.execute(
                """
                INSERT INTO organizations (id, name)
                VALUES
                    (%s, 'Acme Corp'),
                    (%s, 'Globex Inc')
                ON CONFLICT (id) DO NOTHING;
                """,
                (str(ORG_A_ID), str(ORG_B_ID)),
            )

            # -- users ----------------------------------------------------------
            execute_values(
                cur,
                """
                INSERT INTO users (id, org_id, email, full_name, role)
                VALUES %s
                ON CONFLICT (id) DO NOTHING;
                """,
                [
                    (str(USER_A_ADMIN_ID), str(ORG_A_ID), "admin@acme.example",   "Alice Admin",  "admin"),
                    (str(USER_A_AGENT_ID), str(ORG_A_ID), "agent@acme.example",   "Bob Agent",    "agent"),
                    (str(USER_B_ADMIN_ID), str(ORG_B_ID), "admin@globex.example", "Carol Admin",  "admin"),
                    (str(USER_B_AGENT_ID), str(ORG_B_ID), "agent@globex.example", "Dave Agent",   "agent"),
                ],
            )

            # -- contacts -------------------------------------------------------
            execute_values(
                cur,
                """
                INSERT INTO contacts (id, org_id, user_id, name, email, phone)
                VALUES %s
                ON CONFLICT (id) DO NOTHING;
                """,
                [
                    (str(CONTACT_A1_ID), str(ORG_A_ID), str(USER_A_AGENT_ID), "Acme Contact One",   "c1@acme.example",   "+1-555-0001"),
                    (str(CONTACT_A2_ID), str(ORG_A_ID), str(USER_A_AGENT_ID), "Acme Contact Two",   "c2@acme.example",   "+1-555-0002"),
                    (str(CONTACT_B1_ID), str(ORG_B_ID), str(USER_B_AGENT_ID), "Globex Contact One", "c1@globex.example", "+1-555-0003"),
                    (str(CONTACT_B2_ID), str(ORG_B_ID), str(USER_B_AGENT_ID), "Globex Contact Two", "c2@globex.example", "+1-555-0004"),
                ],
            )

            # -- interactions (with placeholder embeddings) ---------------------
            # psycopg2 needs the vector as a string literal that Postgres casts.
            embedding_literal = "[" + ",".join("0" for _ in range(1536)) + "]"

            execute_values(
                cur,
                """
                INSERT INTO interactions
                    (id, org_id, user_id, contact_id, type, content, raw_file_url, embedding)
                VALUES %s
                ON CONFLICT (id) DO NOTHING;
                """,
                [
                    (
                        str(INTERACTION_A1_ID), str(ORG_A_ID), str(USER_A_AGENT_ID),
                        str(CONTACT_A1_ID), "call",
                        "Discussed Q3 renewal with Acme Contact One.",
                        None,
                        embedding_literal,
                    ),
                    (
                        str(INTERACTION_A2_ID), str(ORG_A_ID), str(USER_A_AGENT_ID),
                        str(CONTACT_A2_ID), "email",
                        "Sent proposal to Acme Contact Two.",
                        None,
                        embedding_literal,
                    ),
                    (
                        str(INTERACTION_B1_ID), str(ORG_B_ID), str(USER_B_AGENT_ID),
                        str(CONTACT_B1_ID), "message",
                        "Followed up with Globex Contact One via Slack.",
                        None,
                        embedding_literal,
                    ),
                    (
                        str(INTERACTION_B2_ID), str(ORG_B_ID), str(USER_B_AGENT_ID),
                        str(CONTACT_B2_ID), "crm_note",
                        "Logged call notes for Globex Contact Two.",
                        None,
                        embedding_literal,
                    ),
                ],
            )

    print("Seed complete.")
    print(f"  Org A (Acme Corp):   {ORG_A_ID}")
    print(f"    admin:  {USER_A_ADMIN_ID}")
    print(f"    agent:  {USER_A_AGENT_ID}")
    print(f"  Org B (Globex Inc):  {ORG_B_ID}")
    print(f"    admin:  {USER_B_ADMIN_ID}")
    print(f"    agent:  {USER_B_AGENT_ID}")


if __name__ == "__main__":
    conn = get_connection()
    try:
        seed(conn)
    finally:
        conn.close()
