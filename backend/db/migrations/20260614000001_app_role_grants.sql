-- Migration: 20260614000001_app_role_grants.sql
-- Make RLS actually enforceable at runtime.
--
-- WHY
-- ---
-- All tenant tables have FORCE ROW LEVEL SECURITY, but RLS is only enforced for
-- a connection whose current role does NOT have the BYPASSRLS attribute. The
-- app/worker connect via DATABASE_URL as Supabase's `postgres` role, which
-- BYPASSES RLS — so the policies were silently inert at runtime.
--
-- The fix (idiomatic Supabase): every tenant-scoped transaction switches to the
-- `authenticated` role (`SET LOCAL ROLE authenticated`) before touching data, so
-- RLS applies. This migration ensures that role has the privileges it needs and
-- can be assumed by `postgres`.
--
-- Idempotent: safe to run more than once.

-- Allow the app connection role (postgres) to SET ROLE authenticated.
GRANT authenticated TO postgres;

-- Schema + table privileges for the runtime role. Row visibility is still
-- governed entirely by the RLS policies; these grants only allow the role to
-- issue the statements at all.
GRANT USAGE ON SCHEMA public TO authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON
    organizations,
    users,
    contacts,
    interactions,
    interaction_chunks
TO authenticated;
