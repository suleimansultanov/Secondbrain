-- Migration: 20260613000001_interaction_chunks.sql
-- Phase 1: chunk storage for RAG.
--
-- An interaction's text is split into ~500-token chunks; each chunk gets its own
-- embedding so semantic search retrieves the most relevant passages (not whole
-- interactions). Chunks are tenant-scoped and owner-scoped exactly like their
-- parent interaction, and protected by the same RLS model.

CREATE TABLE IF NOT EXISTS interaction_chunks (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    interaction_id uuid        NOT NULL REFERENCES interactions(id) ON DELETE CASCADE,
    user_id        uuid        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chunk_index    int         NOT NULL,
    content        text        NOT NULL,
    embedding      vector(1536),
    created_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT interaction_chunks_uniq UNIQUE (interaction_id, chunk_index)
);

-- ---------------------------------------------------------------------------
-- Row-Level Security (same model as interactions)
-- ---------------------------------------------------------------------------
ALTER TABLE interaction_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE interaction_chunks FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS interaction_chunks_isolation ON interaction_chunks;

-- Admin sees all chunks in the org; agent sees only their own.
-- The same policy gates vector-similarity queries — RLS prunes cross-org rows
-- before the ivfflat index is scanned.
CREATE POLICY interaction_chunks_isolation ON interaction_chunks
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
-- Indexes
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_chunks_org_id
    ON interaction_chunks (org_id);

CREATE INDEX IF NOT EXISTS idx_chunks_interaction_id
    ON interaction_chunks (interaction_id);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding_ivfflat
    ON interaction_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
