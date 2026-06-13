# Backend — FastAPI

API, RAG pipeline, and ingestion workers.

## Stack
- FastAPI (Python 3.11+)
- Supabase Auth (JWT) + Row-Level Security
- PostgreSQL + pgvector
- arq + Redis (job queue)
- Claude (answers), OpenAI (embeddings), Groq Whisper (transcription)

## Dev setup
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # fill in secrets
uvicorn app.main:app --reload
```

Health check: `GET /health`

---

## Database

### Prerequisites

Set `DATABASE_URL` to a Postgres connection string with `pgvector` enabled
(Supabase projects have it by default):

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
```

### Run migrations

Migrations live in `backend/db/migrations/` as plain SQL files, numbered in
execution order.  Run them in order with `psql` or the Supabase SQL editor:

```bash
psql "$DATABASE_URL" -f backend/db/migrations/20260611000001_extensions.sql
psql "$DATABASE_URL" -f backend/db/migrations/20260611000002_tables.sql
psql "$DATABASE_URL" -f backend/db/migrations/20260611000003_rls.sql
psql "$DATABASE_URL" -f backend/db/migrations/20260611000004_indexes.sql
```

All migrations are **idempotent** (`CREATE … IF NOT EXISTS`, `DROP POLICY IF EXISTS`).

> **Supabase tip:** paste each file into the Supabase Studio SQL editor and click
> *Run*, or use `supabase db push` if you initialise a local Supabase project.

### Session-setting contract

Before any tenant-scoped query the application **must** set these three Postgres
session settings (typically in a FastAPI middleware or dependency):

```sql
SET LOCAL app.current_org_id   = '<org-uuid>';
SET LOCAL app.current_user_id  = '<user-uuid>';
SET LOCAL app.current_user_role = 'admin';   -- or 'agent'
```

`SET LOCAL` scopes the settings to the current transaction; they are cleared
automatically when the transaction ends.

### Seed the database

The seed script creates two isolated organisations with an admin + agent in each
and a couple of contacts/interactions per org:

```bash
python backend/db/seed.py
```

The script is **idempotent** (safe to run multiple times).  It uses fixed UUIDs
so that `tests/test_rls_isolation.py` can reference the same rows without a
round-trip.

---

## Tenant isolation test

`backend/tests/test_rls_isolation.py` proves that PostgreSQL Row-Level Security
blocks all cross-org reads and writes, including via vector-similarity queries.

### What the test covers

| Test class | Checks |
|---|---|
| `TestSelfAccess` | Admin and agent can read their own org's data |
| `TestCrossOrgIsolation` | Org A session returns **zero rows** for Org B on every table; INSERT with wrong `org_id` is rejected |
| `TestVectorSimilarityIsolation` | Cosine ANN search in Org A session returns only Org A rows |
| `TestAgentLevelIsolation` | Agent cannot see another agent's contacts within the same org |

### Run the isolation test

```bash
# 1. Activate venv and ensure dependencies are installed
cd backend
source .venv/bin/activate
pip install -r requirements.txt

# 2. Run migrations and seed (one-time)
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
psql "$DATABASE_URL" -f db/migrations/20260611000001_extensions.sql
psql "$DATABASE_URL" -f db/migrations/20260611000002_tables.sql
psql "$DATABASE_URL" -f db/migrations/20260611000003_rls.sql
psql "$DATABASE_URL" -f db/migrations/20260611000004_indexes.sql
python db/seed.py

# 3. Run the isolation test
pytest tests/test_rls_isolation.py -v
```

Expected output: all tests **PASSED**.  Any failure means a real isolation
breach and **must be fixed before merging**.

---

## Layout
```
app/
  main.py          # FastAPI app + health check
  core/            # settings, security, db
  middleware/      # org_id tenant scoping
  api/             # routes (brain/query, contacts, ...)
  workers/         # arq ingestion jobs
  models/          # pydantic + db models
db/
  migrations/
    20260611000001_extensions.sql   # pgvector extension
    20260611000002_tables.sql       # organizations, users, contacts, interactions
    20260611000003_rls.sql          # Row-Level Security policies
    20260611000004_indexes.sql      # org_id + ivfflat embedding indexes
  seed.py          # 2 orgs, admin+agent each, sample data
tests/
  test_rls_isolation.py   # cross-org access MUST be blocked
```
