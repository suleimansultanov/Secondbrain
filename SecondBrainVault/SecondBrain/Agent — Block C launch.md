---
title: "Agent — Block C launch (DB schema + RLS)"
tags: [secondbrain, agent, managed-agents, phase-0]
status: ready
created: 2026-06-11
---

# Launching the managed agent — Block C (DB schema + RLS)

Goal: a managed agent autonomously implements Phase 0 / Block C and opens a **Pull
Request** (does NOT push to `main`). We review and merge.

---

## Prerequisites (do once)

1. **Repo is pushed to GitHub** (`main` exists on `github.com/suleimansultanov/Secondbrain`).
   The agent clones from GitHub — local files are not enough.
2. **Fine-grained GitHub PAT** with minimum scope:
   - GitHub → Settings → Developer settings → Personal access tokens → Fine-grained
   - Repository access: **Only select repositories → `Secondbrain`**
   - Permissions: **Contents: Read and write**, **Pull requests: Read and write**
   - Copy the token (`github_pat_...`) — used only in Console, never committed.

---

## Console steps (UI)

Open **https://platform.claude.com/workspaces/default/agent-quickstart/**

1. **Model:** `claude-opus-4-8` (critical DB/security work — worth the stronger model).
2. **System prompt:** paste the block below.
3. **MCP servers:** add server → `https://api.githubcopilot.com/mcp/`, name `github`,
   authenticate with the **fine-grained PAT**.
4. **Tools:** enable the **agent toolset** (bash/editor/etc.) and the **github MCP toolset**.
5. **Skills:** none needed.
6. **Mount repo for the session:** attach GitHub repository
   `https://github.com/suleimansultanov/Secondbrain` at mount path `/workspace/repo`
   using the same PAT. (If the quickstart doesn't expose repo mounting, use the
   session snippet in the sessions docs with `resources: [{type: github_repository, ...}]`.)
7. **Run session →** paste the **Task message** below and send.

---

## System prompt (paste into Console)

```
You are an autonomous coding agent working on the SecondBrain repository.

Read /workspace/repo/CLAUDE.md FIRST and follow every rule in it, especially:
- Tenant isolation is sacred: every tenant-scoped table has org_id + PostgreSQL
  Row-Level Security; no query may cross org_id boundaries.
- Never commit secrets (.env, .obsidian/ are gitignored — keep it that way).
- DB changes go in SQL migrations under backend/db/migrations/, never ad-hoc edits.

Working rules:
- Create a new branch named `agent/phase0-block-c-rls`. NEVER push to main.
- Make focused commits with imperative, scoped messages.
- When done, open a Pull Request against main describing what you did and how to
  run the isolation test. Do not merge it yourself.
- If anything about tenant scoping is ambiguous, choose the most restrictive
  (most isolated) option and note it in the PR.
```

## Task message (paste into the session)

```
Implement Phase 0 / Block C — database schema with multi-tenant isolation.

Deliverables (all under /backend):

1. SQL migrations in backend/db/migrations/ (timestamped .sql files):
   - Tables: organizations, users, contacts, interactions.
   - users.role is either 'admin' or 'agent'.
   - Every tenant-scoped table (users, contacts, interactions) has org_id
     referencing organizations(id).
   - interactions: type ('call'|'email'|'message'|'crm_note'), content (text),
     raw_file_url (nullable), created_at (timestamptz default now()).
   - Enable the pgvector extension and add an `embedding vector(1536)` column to
     interactions (1536 = OpenAI text-embedding-3-small).
   - Enable Row-Level Security on organizations, users, contacts, interactions.
   - RLS policies scoped to the current org via a session setting
     (e.g. current_setting('app.current_org_id')): a row is visible only when its
     org_id matches. Admin sees all rows in their org; agent sees only their own
     (user_id) data for contacts/interactions.
   - Add helpful indexes (org_id, and an ivfflat/hnsw index on embedding).

2. A seed script (backend/db/seed.py or .sql) that creates 2 organizations, an
   admin + agent in each, and a couple of contacts/interactions per org.

3. tests/test_rls_isolation.py that proves cross-org access is BLOCKED:
   - Set the org context to org A; assert you can read org A rows.
   - Assert you CANNOT read or write any org B rows (count == 0 / permission error),
     including via a vector similarity query.
   - The test must fail loudly if isolation ever breaks.

4. Update backend/README.md with how to run migrations, seed, and the isolation test.
5. Tick the relevant items in SecondBrainVault/SecondBrain/Phase 0 — Foundation.md (block C).

Constraints:
- Postgres + pgvector (Supabase-compatible). Use plain SQL migrations.
- Do not hardcode secrets; read DATABASE_URL from env.
- Keep the PR focused on Block C only.

When finished, open a PR titled "Phase 0 (block C): DB schema + RLS isolation"
with a checklist of what was done and the exact commands to run the test.
```

---

## While the agent runs

- It works in its own cloud sandbox + its own branch → safe to keep working locally
  on `main` in parallel.
- Review the PR carefully (it's the security-critical part). Pay special attention
  to the RLS policies and that the isolation test genuinely fails on a leak.
- Merge only when the isolation test passes and policies look correct.
