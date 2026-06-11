---
title: "Phase 0 — Foundation"
tags: [secondbrain, phase-0, foundation, checklist]
status: in-progress
parent: "[[SecondBrain]]"
created: 2026-06-11
---

# Phase 0 — Foundation (~1 week)

> Goal: stand up a secure, multi-tenant foundation and **prove cross-tenant isolation before writing any feature code**.
> Definition of done: 2 organizations exist, and an automated test confirms RLS blocks all cross-org access.

---

## A. Repo & environment

- [ ] Create monorepo with `/backend`, `/web`, `/mobile`
- [ ] Root tooling: `.gitignore`, `.editorconfig`, `README.md`, `.env.example`
- [ ] Pre-commit hooks (ruff/black for Python, prettier/eslint for JS)
- [ ] Initialize git + first commit + push to GitHub

## B. Cloud accounts (free / pay-as-you-go)

- [ ] GitHub repo
- [ ] Supabase project — **Frankfurt (eu-central)** region
- [ ] Vercel project (web)
- [ ] Hetzner server (backend + workers) — German DC
- [ ] Cloudflare R2 **or** S3 `eu-central-1` (audio — can defer to Phase 2)
- [ ] Redis (Upstash free or self-hosted on Hetzner)

## C. Database & multi-tenancy 🔒 (critical)

- [x] Tables: `organizations`, `users`, `contacts`, `interactions`
      → `backend/db/migrations/20260611000002_tables.sql`
- [x] Enable `pgvector` extension
      → `backend/db/migrations/20260611000001_extensions.sql`
- [x] Add `embedding vector(1536)` column to `interactions`
      → `backend/db/migrations/20260611000002_tables.sql`
- [x] `org_id` FK on every tenant-scoped table (`users`, `contacts`, `interactions`)
      → `backend/db/migrations/20260611000002_tables.sql`
- [x] RLS policies scoped to `org_id` on **all** tables (incl. vector search path)
      → `backend/db/migrations/20260611000003_rls.sql`
- [x] Role separation: `admin` (sees all org data) vs `agent` (own data only)
      → `backend/db/migrations/20260611000003_rls.sql`
- [x] Seed script: 2 orgs, admin + agent in each, sample contacts/interactions
      → `backend/db/seed.py`
- [x] **TEST: confirm RLS blocks cross-org reads/writes (automated)**
      → `backend/tests/test_rls_isolation.py`

## D. Backend skeleton

- [ ] FastAPI app + health check
- [ ] Supabase Auth + JWT verification
- [ ] `org_id` middleware (inject tenant scope into every request)
- [ ] Redis + arq worker skeleton (empty job that runs)
- [ ] Settings/secrets loader (pydantic-settings)

## E. Secrets & config

- [ ] Anthropic (Claude) key
- [ ] OpenAI (embeddings) key
- [ ] Groq (Whisper) key — can defer to Phase 2
- [ ] Supabase URL + keys
- [ ] Storage credentials (R2/S3) — defer to Phase 2
- [ ] All secrets in `.env` (never committed) + documented in `.env.example`

## F. CI/CD

- [ ] GitHub Actions: lint + test on PR
- [ ] Deploy backend → Hetzner
- [ ] Deploy web → Vercel

---

## ✅ Phase 0 exit criteria

1. Repo builds and deploys (web + backend) from CI.
2. Two orgs in the DB.
3. Automated test proves **no cross-org data leakage** via RLS.

Once green → move to **Phase 1 (MVP Core)**: first data source → index → `POST /brain/query` → sourced answer.

---

## Notes / decisions

- **Block C (2026-06-11):** All DB schema and RLS work implemented in
  `agent/phase0-block-c-rls` branch. Session settings `app.current_org_id`,
  `app.current_user_id`, and `app.current_user_role` are used as the tenant
  context signal. `FORCE ROW LEVEL SECURITY` is set on all tables so even
  table-owner connections are subject to policies. Chose `AS RESTRICTIVE`
  policies (most restrictive option) to ensure deny-by-default when session
  settings are not initialised. ivfflat index used for ANN search; HNSW
  alternative is commented in the index migration for future upgrade.
