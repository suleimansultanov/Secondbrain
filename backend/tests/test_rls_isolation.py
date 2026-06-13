"""backend/tests/test_rls_isolation.py

Row-Level Security isolation tests.

Proves that, given two seeded organisations (Org A and Org B), a session
scoped to Org A:
  1. CAN read its own organizations, users, contacts, and interactions rows.
  2. CANNOT read or write any Org B rows — including via vector similarity
     search — even when using direct SQL with no application-layer filtering.
  3. An attempt to INSERT a row with org_id = Org B is rejected by the
     WITH CHECK policy.

The test FAILS LOUDLY (assertion error) if RLS ever allows cross-org leakage.

Running
-------
    # Prerequisites: DATABASE_URL set, migrations run, seed.py run.
    export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
    pytest backend/tests/test_rls_isolation.py -v

Dependencies (requirements.txt):
    psycopg2-binary
    pytest
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.extras
import pytest

# ---------------------------------------------------------------------------
# Deterministic UUIDs — must match backend/db/seed.py
# ---------------------------------------------------------------------------
ORG_A_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
ORG_B_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

USER_A_ADMIN_ID = uuid.UUID("00000000-0000-0000-0001-000000000001")
USER_A_AGENT_ID = uuid.UUID("00000000-0000-0000-0001-000000000002")
USER_B_ADMIN_ID = uuid.UUID("00000000-0000-0000-0002-000000000001")
USER_B_AGENT_ID = uuid.UUID("00000000-0000-0000-0002-000000000002")

CONTACT_A1_ID = uuid.UUID("00000000-0000-0001-0001-000000000001")
CONTACT_B1_ID = uuid.UUID("00000000-0000-0001-0002-000000000001")

INTERACTION_A1_ID = uuid.UUID("00000000-0000-0002-0001-000000000001")
INTERACTION_B1_ID = uuid.UUID("00000000-0000-0002-0002-000000000001")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip(
            "DATABASE_URL not set — skipping live DB tests.  "
            "Set DATABASE_URL and run migrations + seed.py first."
        )
    return url


@contextmanager
def _org_session(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
) -> Generator[psycopg2.extensions.cursor, None, None]:
    """Open a transaction scoped to *org_id* / *user_id* / *role* via
    SET LOCAL session settings, then yield a cursor.  Rolls back on exit so
    tests leave no side-effects."""
    conn = psycopg2.connect(_database_url())
    conn.autocommit = False
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL app.current_org_id  = %s;", (str(org_id),))
            cur.execute("SET LOCAL app.current_user_id = %s;", (str(user_id),))
            cur.execute("SET LOCAL app.current_user_role = %s;", (role,))
            yield cur
            conn.rollback()  # ← always roll back; tests must not persist
    finally:
        conn.close()


def _count(cur: psycopg2.extensions.cursor, table: str, org_id: uuid.UUID) -> int:
    cur.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE org_id = %s;", (str(org_id),))
    row = cur.fetchone()
    return int(row["n"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_url() -> str:
    return _database_url()


# ---------------------------------------------------------------------------
# 1. Self-access (positive tests) — must see own org's data
# ---------------------------------------------------------------------------


class TestSelfAccess:
    """Scoped to Org A; all queries against Org A data must succeed."""

    def test_org_visible(self, db_url: str) -> None:
        with _org_session(ORG_A_ID, USER_A_ADMIN_ID, "admin") as cur:
            cur.execute("SELECT id FROM organizations WHERE id = %s;", (str(ORG_A_ID),))
            rows = cur.fetchall()
        assert len(rows) == 1, "Admin must see their own organization row."

    def test_users_visible_to_admin(self, db_url: str) -> None:
        with _org_session(ORG_A_ID, USER_A_ADMIN_ID, "admin") as cur:
            n = _count(cur, "users", ORG_A_ID)
        assert n >= 2, "Admin must see all users in their org (at least admin + agent)."

    def test_users_agent_sees_only_self(self, db_url: str) -> None:
        with _org_session(ORG_A_ID, USER_A_AGENT_ID, "agent") as cur:
            cur.execute("SELECT id FROM users WHERE org_id = %s;", (str(ORG_A_ID),))
            rows = cur.fetchall()
        ids = {str(r["id"]) for r in rows}
        assert str(USER_A_AGENT_ID) in ids, "Agent must see their own user row."
        assert str(USER_A_ADMIN_ID) not in ids, "Agent must NOT see other users' rows."

    def test_contacts_visible_to_admin(self, db_url: str) -> None:
        with _org_session(ORG_A_ID, USER_A_ADMIN_ID, "admin") as cur:
            n = _count(cur, "contacts", ORG_A_ID)
        assert n >= 1, "Admin must see contacts belonging to their org."

    def test_interactions_visible_to_admin(self, db_url: str) -> None:
        with _org_session(ORG_A_ID, USER_A_ADMIN_ID, "admin") as cur:
            n = _count(cur, "interactions", ORG_A_ID)
        assert n >= 1, "Admin must see interactions belonging to their org."


# ---------------------------------------------------------------------------
# 2. Cross-org isolation (critical) — Org A session MUST NOT see Org B data
# ---------------------------------------------------------------------------


class TestCrossOrgIsolation:
    """Scoped to Org A; every assertion against Org B data must return zero rows."""

    def test_cannot_read_other_org(self, db_url: str) -> None:
        with _org_session(ORG_A_ID, USER_A_ADMIN_ID, "admin") as cur:
            cur.execute(
                "SELECT id FROM organizations WHERE id = %s;",
                (str(ORG_B_ID),),
            )
            rows = cur.fetchall()
        assert len(rows) == 0, (
            f"ISOLATION BREACH: Org A session returned {len(rows)} row(s) "
            f"from the organizations table for Org B."
        )

    def test_cannot_read_other_org_users(self, db_url: str) -> None:
        with _org_session(ORG_A_ID, USER_A_ADMIN_ID, "admin") as cur:
            n = _count(cur, "users", ORG_B_ID)
        assert n == 0, (
            f"ISOLATION BREACH: Org A session can read {n} user row(s) " f"belonging to Org B."
        )

    def test_cannot_read_other_org_contacts(self, db_url: str) -> None:
        with _org_session(ORG_A_ID, USER_A_ADMIN_ID, "admin") as cur:
            n = _count(cur, "contacts", ORG_B_ID)
        assert n == 0, (
            f"ISOLATION BREACH: Org A session can read {n} contact row(s) " f"belonging to Org B."
        )

    def test_cannot_read_other_org_interactions(self, db_url: str) -> None:
        with _org_session(ORG_A_ID, USER_A_ADMIN_ID, "admin") as cur:
            n = _count(cur, "interactions", ORG_B_ID)
        assert n == 0, (
            f"ISOLATION BREACH: Org A session can read {n} interaction row(s) "
            f"belonging to Org B."
        )

    def test_cannot_write_into_other_org_contacts(self, db_url: str) -> None:
        """WITH CHECK policy must reject an INSERT carrying org_id = Org B."""
        with _org_session(ORG_A_ID, USER_A_AGENT_ID, "agent") as cur:
            with pytest.raises(psycopg2.errors.InsufficientPrivilege) as exc_info:
                cur.execute(
                    """
                    INSERT INTO contacts (org_id, user_id, name)
                    VALUES (%s, %s, 'Evil cross-org contact');
                    """,
                    (str(ORG_B_ID), str(USER_A_AGENT_ID)),
                )
        assert (
            exc_info.value is not None
        ), "ISOLATION BREACH: INSERT into Org B from Org A session was NOT rejected."

    def test_cannot_write_into_other_org_interactions(self, db_url: str) -> None:
        """WITH CHECK policy must reject an INSERT carrying org_id = Org B."""
        with _org_session(ORG_A_ID, USER_A_AGENT_ID, "agent") as cur:
            with pytest.raises(psycopg2.errors.InsufficientPrivilege) as exc_info:
                cur.execute(
                    """
                    INSERT INTO interactions (org_id, user_id, type, content)
                    VALUES (%s, %s, 'email', 'Leaked content from org A into org B');
                    """,
                    (str(ORG_B_ID), str(USER_A_AGENT_ID)),
                )
        assert (
            exc_info.value is not None
        ), "ISOLATION BREACH: INSERT into Org B from Org A session was NOT rejected."


# ---------------------------------------------------------------------------
# 3. Vector similarity isolation — ANN search must not cross org boundaries
# ---------------------------------------------------------------------------


class TestVectorSimilarityIsolation:
    """A cosine-similarity query run in an Org A session must return zero
    rows from Org B even though both orgs have interactions with embeddings."""

    def test_vector_search_scoped_to_own_org(self, db_url: str) -> None:
        """Verify that a vector search executed inside Org A's session returns
        at least one result (own data is accessible)."""
        # The seed inserts a zero-vector embedding.  Cosine distance from
        # another zero vector is 0.  We just want to confirm rows are returned.
        zero_vec = "[" + ",".join("0" for _ in range(1536)) + "]"
        with _org_session(ORG_A_ID, USER_A_ADMIN_ID, "admin") as cur:
            cur.execute(
                """
                SELECT id, org_id
                FROM interactions
                ORDER BY embedding <=> %s::vector
                LIMIT 10;
                """,
                (zero_vec,),
            )
            rows = cur.fetchall()

        assert len(rows) > 0, "Admin should see at least one interaction via vector search."
        for row in rows:
            assert str(row["org_id"]) == str(ORG_A_ID), (
                f"ISOLATION BREACH: vector search in Org A session returned a row "
                f"with org_id={row['org_id']} (expected {ORG_A_ID})."
            )

    def test_vector_search_excludes_other_org(self, db_url: str) -> None:
        """No row from Org B must appear in a vector search scoped to Org A."""
        zero_vec = "[" + ",".join("0" for _ in range(1536)) + "]"
        with _org_session(ORG_A_ID, USER_A_ADMIN_ID, "admin") as cur:
            cur.execute(
                """
                SELECT id, org_id
                FROM interactions
                WHERE org_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT 10;
                """,
                (str(ORG_B_ID), zero_vec),
            )
            rows = cur.fetchall()

        assert len(rows) == 0, (
            f"ISOLATION BREACH: vector search filtered to Org B returned "
            f"{len(rows)} row(s) in an Org A session."
        )


# ---------------------------------------------------------------------------
# 4. Agent-level isolation (agent cannot read other agents' data within org)
# ---------------------------------------------------------------------------


class TestAgentLevelIsolation:
    """Within a single org, an agent must only see their own contacts/interactions."""

    def test_agent_cannot_see_other_agent_contacts(self, db_url: str) -> None:
        """Create a secondary agent context; it should not see the primary agent's contacts."""
        # USER_B_AGENT_ID is in ORG_B, so we run this within ORG_B.
        with _org_session(ORG_B_ID, USER_B_ADMIN_ID, "admin") as cur:
            # Confirm admin sees all contacts in Org B.
            n_admin = _count(cur, "contacts", ORG_B_ID)
        assert n_admin >= 1

        # Now scope to an agent who owns zero contacts (we give them a fresh ID).
        # They must not see USER_B_AGENT_ID's contacts.
        foreign_user_id = uuid.uuid4()  # does not exist in DB — owns nothing
        with _org_session(ORG_B_ID, foreign_user_id, "agent") as cur:
            cur.execute(
                "SELECT id FROM contacts WHERE org_id = %s;",
                (str(ORG_B_ID),),
            )
            rows = cur.fetchall()

        assert len(rows) == 0, (
            f"ISOLATION BREACH: agent with no contacts can see {len(rows)} "
            f"contact row(s) belonging to another agent."
        )
