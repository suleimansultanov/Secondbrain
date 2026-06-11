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

## Layout (planned)
```
app/
  main.py          # FastAPI app + health check
  core/            # settings, security, db
  middleware/      # org_id tenant scoping
  api/             # routes (brain/query, contacts, ...)
  workers/         # arq ingestion jobs
  models/          # pydantic + db models
db/
  migrations/      # SQL (tables, pgvector, RLS)
  seed.py          # 2 orgs for isolation testing
tests/
  test_rls_isolation.py   # cross-org access MUST be blocked
```
