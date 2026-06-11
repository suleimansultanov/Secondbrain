-- Migration: 20260611000003_rls.sql
-- Enable Row-Level Security on all four tables and install isolation policies.
--
-- Session-setting contract (must be set by the application layer before any
-- query that touches tenant data):
--
--   SET LOCAL app.current_org_id  = '<org-uuid>';
--   SET LOCAL app.current_user_id = '<user-uuid>';
--   SET LOCAL app.current_user_role = 'admin';   -- or 'agent'
--
-- The settings are LOCAL to the current transaction and are cleared
-- automatically when the transaction ends — no risk of bleed-through.
--
-- POLICY MODEL
-- ------------
-- Each table has a single PERMISSIVE policy. In PostgreSQL, restrictive
-- policies only *narrow* access already granted by a permissive policy; a
-- table with ONLY restrictive policies exposes zero rows to everyone. We
-- therefore use permissive policies that both (a) grant org-scoped access and
-- (b) deny-by-default: when a session setting is not initialised,
-- current_setting(..., true) returns NULL, the comparison evaluates to NULL
-- (not TRUE), and the row is hidden. Unauthenticated queries see nothing.
--
-- current_setting('app.current_org_id',  true)   -> text or NULL
-- current_setting('app.current_user_id', true)   -> text or NULL
-- current_setting('app.current_user_role', true) -> text or NULL
-- (the second argument 'true' returns NULL instead of raising when unset.)

-- ===========================================================================
-- 1. organizations
-- ===========================================================================
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations FORCE ROW LEVEL SECURITY;

-- Drop any pre-existing policies so the migration is idempotent.
DROP POLICY IF EXISTS orgs_isolation ON organizations;

-- An org row is visible only when its id matches the session's current org.
-- No role distinction needed at this level — the org itself is the boundary.
CREATE POLICY orgs_isolation ON organizations
    FOR ALL
    USING (
        id::text = current_setting('app.current_org_id', true)
    )
    WITH CHECK (
        id::text = current_setting('app.current_org_id', true)
    );

-- ===========================================================================
-- 2. users
-- ===========================================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_isolation ON users;

-- Admin sees all users in the org; agent sees only themselves.
CREATE POLICY users_isolation ON users
    FOR ALL
    USING (
        org_id::text = current_setting('app.current_org_id', true)
        AND (
            current_setting('app.current_user_role', true) = 'admin'
            OR
            id::text = current_setting('app.current_user_id', true)
        )
    )
    WITH CHECK (
        org_id::text = current_setting('app.current_org_id', true)
    );

-- ===========================================================================
-- 3. contacts
-- ===========================================================================
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS contacts_isolation ON contacts;

-- Admin sees all contacts in the org; agent sees only contacts they own.
CREATE POLICY contacts_isolation ON contacts
    FOR ALL
    USING (
        org_id::text = current_setting('app.current_org_id', true)
        AND (
            current_setting('app.current_user_role', true) = 'admin'
            OR
            user_id::text = current_setting('app.current_user_id', true)
        )
    )
    WITH CHECK (
        org_id::text = current_setting('app.current_org_id', true)
        AND (
            current_setting('app.current_user_role', true) = 'admin'
            OR
            user_id::text = current_setting('app.current_user_id', true)
        )
    );

-- ===========================================================================
-- 4. interactions
-- ===========================================================================
ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE interactions FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS interactions_isolation ON interactions;

-- Admin sees all interactions in the org; agent sees only their own.
-- The same policy applies to vector-similarity queries — the embedding
-- index is only scanned AFTER the RLS filter prunes cross-org rows.
CREATE POLICY interactions_isolation ON interactions
    FOR ALL
    USING (
        org_id::text = current_setting('app.current_org_id', true)
        AND (
            current_setting('app.current_user_role', true) = 'admin'
            OR
            user_id::text = current_setting('app.current_user_id', true)
        )
    )
    WITH CHECK (
        org_id::text = current_setting('app.current_org_id', true)
        AND (
            current_setting('app.current_user_role', true) = 'admin'
            OR
            user_id::text = current_setting('app.current_user_id', true)
        )
    );

-- ---------------------------------------------------------------------------
-- NOTES
-- ---------------------------------------------------------------------------
-- 1. FORCE ROW LEVEL SECURITY ensures that table *owners* are also subject to
--    these policies. Application queries should use a limited-privilege role
--    (e.g. Supabase's `authenticated`) — always subject to RLS.
--
-- 2. SEEDING / ADMIN MIGRATIONS: because FORCE RLS applies to the owner too,
--    bulk inserts that do NOT set the session settings (e.g. backend/db/seed.py)
--    must run as a role that BYPASSES RLS — a superuser or a role with the
--    BYPASSRLS attribute (on Supabase, the `postgres` / service role). Otherwise
--    the WITH CHECK clauses reject the inserts with SQLSTATE 42501.
-- ---------------------------------------------------------------------------
