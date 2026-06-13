-- Migration: 20260611000002_tables.sql
-- Core schema: organizations, users, contacts, interactions.
-- All tenant-scoped tables carry org_id referencing organizations(id).

-- ---------------------------------------------------------------------------
-- organizations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizations (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- users
-- Tenant-scoped; role is either 'admin' (sees all org data) or
-- 'agent' (sees only their own contacts/interactions).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email       text        NOT NULL,
    full_name   text,
    role        text        NOT NULL CHECK (role IN ('admin', 'agent')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT  users_email_org_uniq UNIQUE (org_id, email)
);

-- ---------------------------------------------------------------------------
-- contacts
-- Tenant-scoped; also owner-scoped (user_id = the agent who owns the contact).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contacts (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     uuid        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        text        NOT NULL,
    email       text,
    phone       text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- interactions
-- Tenant-scoped + owner-scoped; carries a 1536-dim pgvector embedding so that
-- semantic search stays inside the org_id boundary enforced by RLS.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interactions (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id      uuid        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    contact_id   uuid        REFERENCES contacts(id) ON DELETE SET NULL,
    type         text        NOT NULL CHECK (type IN ('call', 'email', 'message', 'crm_note')),
    content      text        NOT NULL,
    raw_file_url text,
    embedding    vector(1536),          -- OpenAI text-embedding-3-small dimensionality
    created_at   timestamptz NOT NULL DEFAULT now()
);
