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

- [ ] Tables: `organizations`, `users`, `contacts`, `interactions`
- [ ] Enable `pgvector` extension
- [ ] Add `embedding vector` column to `interactions`
- [ ] `org_id` FK on every tenant-scoped table
- [ ] RLS policies scoped to `org_id` on **all** tables (incl. vector search path)
- [ ] Role separation: `admin` (sees all org data) vs `agent` (own data only)
- [ ] Seed script: 2 orgs, users in each
- [ ] **TEST: confirm RLS blocks cross-org reads/writes (automated)**

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

- _(log key decisions here as we go)_
