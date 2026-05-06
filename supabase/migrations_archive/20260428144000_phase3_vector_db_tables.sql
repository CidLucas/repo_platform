-- =============================================================================
-- Migration: Phase 3 — vector_db tables baseline
-- Date: 2026-04-28
-- Purpose: Create vector storage tables for document embeddings and chunks
-- Note: Requires the PostgreSQL vector extension and halfvec type to be available.
-- =============================================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS vector_db;

-- -----------------------------------------------------------------------------
-- vector_db.documents
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vector_db.documents (
  id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id       UUID    NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  title           TEXT,
  file_name       TEXT    NOT NULL,
  file_type       TEXT,
  storage_path    TEXT,
  source          TEXT    NOT NULL DEFAULT 'upload' CHECK (source IN ('upload','chat','url','api')),
  processing_mode TEXT    NOT NULL DEFAULT 'simple' CHECK (processing_mode IN ('simple','complex')),
  status          TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed')),
  scope           TEXT,
  category        TEXT,
  content_hash    TEXT,
  error_message   TEXT,
  chunk_count     INTEGER DEFAULT 0,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_docs_client ON vector_db.documents(client_id);
CREATE INDEX IF NOT EXISTS idx_docs_status ON vector_db.documents(status);
CREATE INDEX IF NOT EXISTS idx_docs_content_hash ON vector_db.documents(content_hash) WHERE content_hash IS NOT NULL;

-- -----------------------------------------------------------------------------
-- vector_db.document_chunks
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vector_db.document_chunks (
  id          INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  document_id UUID        NOT NULL REFERENCES vector_db.documents(id) ON DELETE CASCADE,
  client_id   UUID        NOT NULL,
  content     TEXT        NOT NULL,
  embedding   extensions.halfvec(384),
  chunk_index INTEGER     NOT NULL DEFAULT 0,
  metadata    JSONB       DEFAULT '{}',
  fts         tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', content)) STORED,
  created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON vector_db.document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_client ON vector_db.document_chunks(client_id);
CREATE INDEX IF NOT EXISTS idx_chunks_fts ON vector_db.document_chunks USING gin(fts);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON vector_db.document_chunks USING hnsw (embedding extensions.halfvec_ip_ops);

COMMIT;
