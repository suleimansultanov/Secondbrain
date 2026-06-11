# SecondBrain — AI Company Brain

Multi-tenant SaaS that unifies calls, emails, messaging, and CRM into one
AI-searchable knowledge base. Ask questions in plain language, get answers
grounded in the original sources — with citations.

## Monorepo layout

```
/backend   FastAPI (Python) — API, RAG pipeline, ingestion workers
/web       Next.js (App Router) — web dashboard
/mobile    React Native (Expo) — iOS + Android
```

## Core principles

- **Grounded** — every answer cites its source.
- **Tenant isolation** — enforced at the DB level (RLS); verified by automated tests.
- **Start small** — working MVP before the full product.

## Status

Phase 0 — Foundation. See the full plan and checklist in the Obsidian vault
(`SecondBrain.md` and `SecondBrain/Phase 0 — Foundation.md`).

## Getting started

1. Copy `.env.example` → `.env` and fill in secrets.
2. Backend: see [`backend/README.md`](backend/README.md).
3. Web: see [`web/README.md`](web/README.md).
4. Mobile: see [`mobile/README.md`](mobile/README.md).
