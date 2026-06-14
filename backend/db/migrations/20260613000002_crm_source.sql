-- Migration: 20260613000002_crm_source.sql
-- Add source provenance to contacts and interactions so connector syncs can
-- dedup records across runs (one row per external object per org).

ALTER TABLE contacts ADD COLUMN IF NOT EXISTS source text;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS external_id text;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS source text;
ALTER TABLE interactions ADD COLUMN IF NOT EXISTS external_id text;

-- One row per (org, source, external_id). Partial: only connector-imported rows
-- carry an external_id; manually created rows are unconstrained.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_contacts_source
    ON contacts (org_id, source, external_id)
    WHERE external_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uniq_interactions_source
    ON interactions (org_id, source, external_id)
    WHERE external_id IS NOT NULL;
