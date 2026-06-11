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
-- The helper below returns NULL (not an error) when a setting is not set,
-- which means an unauthenticated query sees no rows at all (deny-by-default).

-- ---------------------------------------------------------------------------
-- Convenience helpers (inlined in policies for portability)
-- ---------------------------------------------------------------------------
-- current_setting('app.current_org_id',  true)  -> uuid  or NULL
-- current_setting('app.current_user_id', true)  -> uuid  or NULL
-- current_setting('app.current_user_role', true) -> text or NULL
--
-- The second argument 'true' makes current_setting() return NULL instead of
-- raising an error when the setting has not been initialised.

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
    AS RESTRICTIVE
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
    AS RESTRICTIVE
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
    AS RESTRICTIVE
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
    AS RESTRICTIVE
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
-- NOTE: FORCE ROW LEVEL SECURITY ensures that table *owners* (superusers
-- acting as the table owner) are also subject to these policies. Application
-- queries should use a limited-privilege role (e.g. supabase's `anon` or
-- `authenticated`) — they are always subject to RLS regardless of this flag.
-- ---------------------------------------------------------------------------
