---
title: "SecondBrain — AI Company Brain"
tags: [project, secondbrain, ai, saas, rag]
status: planning
created: 2026-06-11
---

# SecondBrain — AI Company Brain

> Multi-tenant SaaS that acts as a company's "brain" — unifies calls, emails, messaging, and CRM into one AI-searchable knowledge base. Ask questions in plain language, get answers grounded in the original sources.

---

## 1. Overview

An agent finishes a client call, then asks: *"What did I promise this client in our last call?"* The system searches all related calls, emails, and messages and returns a grounded answer **with references**.

**Core principles**
- Every answer is **grounded** — it cites its source.
- **Strict tenant isolation** — no company can ever see another's data.
- **Start small, prove value fast** — working MVP before the full product.

---

## 2. Architecture & Tech Stack

**Flow:** Data sources → ingestion workers (normalize → identify client → chunk) → PostgreSQL + vector embeddings → RAG pipeline (retrieve context → AI answer) → web/mobile.

| Layer | Technology |
|---|---|
| Web dashboard | Next.js (App Router) on Vercel |
| Mobile app | React Native (Expo) — iOS + Android |
| UI | shadcn/ui + Tailwind CSS |
| Backend API | FastAPI (Python) |
| Job queue | arq / Celery + Redis |
| Auth + multi-tenancy | Supabase Auth + Row-Level Security (RLS) |
| Database | PostgreSQL + pgvector (Supabase, EU region) |
| Audio storage | Cloudflare R2 / AWS S3 |
| Transcription | Whisper Large v3 (via Groq) |
| Embeddings | OpenAI text-embedding-3-small |
| AI / RAG | Claude (Haiku for volume, Sonnet for complex) |
| Email | Gmail API + Microsoft Graph (Outlook) |
| Messaging | WhatsApp Business Cloud API |
| CRM | REST API via adapter layer (cheap to add new CRMs) |

**AI providers — who does what**
- **Claude (Anthropic)** — the "brain" that generates answers. Strong reasoning, strong on Hebrew.
- **OpenAI** — embeddings (search indexing). Negligible cost.
- **Groq** — runs the same Whisper model as OpenAI, ~9x cheaper, no quality loss. Main cost-saver.

---

## 3. Data Model

```
Organization                  → one per company account
 └─ Users (admin / agent)      → admin sees all; agent sees own data only
     └─ Contacts (clients)
         └─ Interactions
             ├─ type: call | email | message | crm_note
             ├─ content: processed text (transcript or message body)
             ├─ raw_file_url: storage path (for audio)
             ├─ embedding: vector (for similarity search)
             └─ created_at
```

Multi-tenant isolation enforced at the DB level via RLS — every query (including vector search) is scoped to the user's `org_id`.

---

## 4. Implementation Plan

### Phase 0 — Foundation (~1 week)
Set up repo + EU cloud environment, build the database with multi-tenant isolation (RLS), wire up auth, configure all API keys. **Verify cross-tenant access is blocked before anything else.**

### Phase 1 — MVP Core (~4–6 weeks)
Connect the first data source (email + CRM), index it (chunk + embed), and build the RAG endpoint: ask a question → retrieve context → Claude answer **with sources**. Ship a basic web dashboard.
*Milestone: working end-to-end on real data.*

### Phase 2 — Data Sources & Mobile (~4–6 weeks)
Mobile app, call recording → transcription (Groq Whisper) → indexed & searchable, WhatsApp integration, additional connectors.

### Phase 3 — Templates, Billing & Polish (~3–4 weeks)
Pre-built query templates, remaining dashboard pages, per-org usage metering + billing, edge-case handling, security review before launch.

**Timeline:** MVP in ~6–8 weeks; full product in ~4–6 months.

### Detailed build order
- [ ] Monorepo (`/backend`, `/web`, `/mobile`)
- [ ] Supabase project (Frankfurt region)
- [ ] Tables: `organizations`, `users`, `contacts`, `interactions`
- [ ] Enable `pgvector`; add `embedding` column
- [ ] RLS policies scoped to `org_id`
- [ ] Object storage (R2 / S3) for audio
- [ ] FastAPI + JWT auth + `org_id` middleware
- [ ] Redis + arq worker skeleton
- [ ] CI/CD (GitHub Actions → Hetzner + Vercel)
- [ ] Load secrets: Anthropic, OpenAI, Groq, storage, Supabase
- [ ] **Test: 2 orgs, confirm RLS blocks cross-org access**
- [ ] OAuth connect first data source
- [ ] First sync (90 days) + incremental
- [ ] Normalize → identify client → store interaction
- [ ] Chunk (~500 tokens, 50 overlap) → embed → store vector
- [ ] `POST /brain/query`: embed question → pgvector search (scoped) → context → Claude → answer + sources
- [ ] Prompt caching on system prompt
- [ ] Web: login, Ask page, clients list, client detail
- [ ] **Milestone test: end-to-end + isolation verified**
- [ ] Mobile (Expo): login, recent activity, one-tap record
- [ ] Upload audio → background job → Groq Whisper → chunk → embed → store
- [ ] WhatsApp webhook (start Meta verification early)
- [ ] Templates, settings, billing, edge cases, monitoring, security review

---

## 5. Hosting

- **Frontend:** Vercel
- **Backend + workers:** Hetzner (German DCs — compliance + cost)
- **Database:** Supabase, EU / Frankfurt
- **Cache/queue:** Redis (Upstash or self-hosted)
- **Audio:** Cloudflare R2 (no egress) or S3 `eu-central-1`

All data EU-hosted. Israel has EU adequacy status → simplified Israel↔EU transfers.

---

## 6. Security & Compliance

**Built in from day one**
- Tenant isolation at DB level; verified with automated cross-tenant tests
- Encryption in transit (TLS) and at rest
- Two-factor authentication + role-based access (admin vs agent)
- Audit logs (who accessed what, when)
- Data export & deletion on request
- Data-processing agreements with AI providers — no data used for training (zero-retention)
- Secrets management, encrypted backups, private networking, dependency scanning

**AI-specific**
- Prompt-injection defense — email/call content treated as data, never instructions
- Sensitive-data masking before sending context to external AI
- AI retrieval bound to tenant isolation — cannot pull another company's data

**Legal**
Follows Israel's Privacy Protection Law, **Amendment 13** (effective Aug 2025) — GDPR-aligned, strictly enforced. Includes data-security tiering, breach-notification process, consent/notice. DPO may be required depending on scale.

> **iOS note:** Apple blocks recording of normal cellular calls. Call recording must run through a VoIP / in-app flow — confirm before Phase 2.

> *Final Amendment 13 compliance to be confirmed with the client's Israeli legal counsel. We provide technical implementation, not legal advice.*

---

## 7. Costs

### Subscriptions for development → MVP
*(No call recording in MVP, so no transcription cost.)*

**Pay-as-you-go API keys (load small credit, pay per use)**
- Anthropic (Claude) — AI answers — ~$5–20/mo during dev
- OpenAI — embeddings — ~$5/mo

**Small fixed subscriptions**
- Supabase — Free tier for early dev; Pro $25/mo at pilot
- Hetzner — backend server — ~€5–10/mo
- Domain — ~$12/yr (optional)

**Free — just create accounts**
- GitHub, Vercel (free tier), Google Cloud project (Gmail OAuth)

**Not needed until Phase 2+**
- Groq/Whisper, WhatsApp/Meta, Apple Developer ($99/yr), Google Play ($25)

**Dev-to-MVP total: ~$35–60/month.**

### Running cost (production, per company, ~10 users)

| Configuration | Transcription | AI answers | Infra | **Total/mo** |
|---|---|---|---|---|
| Standard (OpenAI Whisper + Claude Sonnet) | ~$99 | ~$99 | ~$90 | **~$290** |
| **Cost-optimized (Groq Whisper + Claude Haiku)** ✅ | ~$11 | ~$33 | ~$90 | **~$135** |

**Scaling:** ~$90 infra is **shared across all companies**. Each additional company adds only **~$45/mo** in AI usage. Average cost per company drops as you grow.

**Approx request volumes** (per company, ~10 users): ~4,400 Claude queries, ~3,300 transcriptions, ~10,000 embeddings/month. Assumes ~15 calls/day + ~20 questions/day per user. Price clients **per-seat or usage-based** to cover pass-through costs.

---

## 8. What We Need From the Client

1. Confirmation of the **first data source** to connect
2. **Access** to that source (connect email / CRM) for real-data testing
3. Number of users + expected usage (to size pricing)
4. Legal counsel contact for Amendment 13 sign-off

---

## 9. First Steps (Kickoff)

1. **Our side:** repo + EU cloud + secure database foundation
2. **Your side:** grant access to first data source
3. **First working slice:** data in → indexed → ask → sourced answer
4. **Review & iterate:** try MVP, gather feedback, expand

Foundation + first connection running in ~2 weeks; working MVP in ~6–8 weeks.
