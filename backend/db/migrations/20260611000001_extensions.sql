-- Migration: 20260611000001_extensions.sql
-- Enable the pgvector extension required for semantic-search embeddings.
-- Must run as a superuser / Supabase service role before creating tables.

CREATE EXTENSION IF NOT EXISTS vector;
