-- Migration: 20260611000004_indexes.sql
-- Performance indexes.
--
-- Tenant-filter indexes: every query starts with `org_id = ?`, so a plain
-- btree index on org_id dramatically reduces the rows scanned before RLS.
--
-- Vector index: ivfflat on interactions.embedding for approximate nearest-
-- neighbour (ANN) cosine search within the tenant.  lists=100 is a sensible
-- starting value; tune when the row count grows.

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_users_org_id
    ON users (org_id);

-- ---------------------------------------------------------------------------
-- contacts
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_contacts_org_id
    ON contacts (org_id);

CREATE INDEX IF NOT EXISTS idx_contacts_user_id
    ON contacts (user_id);

-- ---------------------------------------------------------------------------
-- interactions
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_interactions_org_id
    ON interactions (org_id);

CREATE INDEX IF NOT EXISTS idx_interactions_user_id
    ON interactions (user_id);

CREATE INDEX IF NOT EXISTS idx_interactions_contact_id
    ON interactions (contact_id);

CREATE INDEX IF NOT EXISTS idx_interactions_type
    ON interactions (org_id, type);

-- IVFFlat index for approximate nearest-neighbour cosine similarity.
-- operator class: vector_cosine_ops  (matches <=> in queries)
-- The index skips NULL embeddings automatically.
-- Re-index periodically (or switch to HNSW) as the dataset grows.
CREATE INDEX IF NOT EXISTS idx_interactions_embedding_ivfflat
    ON interactions
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- HNSW alternative (pgvector >= 0.5, generally faster at query time):
-- CREATE INDEX IF NOT EXISTS idx_interactions_embedding_hnsw
--     ON interactions
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);
