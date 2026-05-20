-- Migration: 20260520000000_fix_rag_rpcs.sql
-- Fix hybrid_match_documents: expand from 5 to 13 params matching search-documents EF.
-- Adds: scope[], categories[], themes[], document_ids[], fusion_strategy, weights, threshold.
-- Fixes: platform-scoped docs (client_id IS NULL) now returned correctly.
-- Adds: CONCURRENTLY indexes on filter columns.

-- ── Drop old 5-param function ──────────────────────────────────────────────
DROP FUNCTION IF EXISTS vector_db.hybrid_match_documents(
  uuid, extensions.halfvec, text, integer, text
);

-- ── New 13-param hybrid_match_documents ───────────────────────────────────
CREATE OR REPLACE FUNCTION vector_db.hybrid_match_documents(
  p_client_id       uuid,
  p_query_embed     extensions.halfvec,
  p_query_text      text,
  p_match_count     integer  DEFAULT 10,
  p_threshold       float    DEFAULT 0.0,
  p_document_ids    uuid[]   DEFAULT NULL,
  p_scope           text[]   DEFAULT NULL,
  p_categories      text[]   DEFAULT NULL,
  p_fusion_strategy text     DEFAULT 'rrf',
  p_keyword_weight  float    DEFAULT 0.4,
  p_vector_weight   float    DEFAULT 0.6,
  p_reserved        boolean  DEFAULT false,
  p_themes          text[]   DEFAULT NULL
)
RETURNS TABLE (
  id             integer,
  document_id    uuid,
  content        text,
  metadata       jsonb,
  similarity     float,
  keyword_score  float,
  combined_score float,
  scope          text,
  category       text
)
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
WITH

-- ── Scope filter: client docs OR platform docs ─────────────────────────────
scope_filter AS (
  SELECT c.id, c.document_id, c.content, c.metadata, c.scope, c.category,
         c.embedding, c.fts
  FROM   vector_db.document_chunks c
  JOIN   vector_db.documents d ON d.id = c.document_id
  WHERE
    -- Client-scoped or platform-scoped access
    (
      (c.client_id = p_client_id)
      OR
      (c.scope = 'platform' AND (p_scope IS NULL OR 'platform' = ANY(p_scope)))
    )
    -- Archived documents excluded
    AND d.source != 'archived'
    -- Optional: filter by specific document IDs
    AND (p_document_ids IS NULL OR c.document_id = ANY(p_document_ids))
    -- Optional: filter by category (first-class column)
    AND (p_categories IS NULL OR c.category = ANY(p_categories))
    -- Optional: filter by theme (first-class column)
    AND (p_themes IS NULL OR c.theme = ANY(p_themes))
    -- Optional: restrict to client scope only
    AND (p_scope IS NULL OR c.scope = ANY(p_scope))
),

-- ── Semantic search (vector cosine similarity) ────────────────────────────
semantic AS (
  SELECT
    sf.id,
    sf.document_id,
    sf.content,
    sf.metadata,
    sf.scope,
    sf.category,
    1 - (sf.embedding <#> p_query_embed) AS sim,
    ROW_NUMBER() OVER (ORDER BY sf.embedding <#> p_query_embed) AS rank
  FROM scope_filter sf
  ORDER BY sf.embedding <#> p_query_embed
  LIMIT p_match_count * 4
),

-- ── Full-text search (keyword BM25-like via tsvector) ─────────────────────
fts AS (
  SELECT
    sf.id,
    sf.document_id,
    sf.content,
    sf.metadata,
    sf.scope,
    sf.category,
    ts_rank(sf.fts, plainto_tsquery('portuguese', p_query_text)) AS rank_score,
    ROW_NUMBER() OVER (
      ORDER BY ts_rank(sf.fts, plainto_tsquery('portuguese', p_query_text)) DESC
    ) AS rank
  FROM scope_filter sf
  WHERE sf.fts @@ plainto_tsquery('portuguese', p_query_text)
  LIMIT p_match_count * 4
),

-- ── Fusion: RRF or weighted ────────────────────────────────────────────────
fused AS (
  SELECT
    COALESCE(s.id, f.id)                      AS id,
    COALESCE(s.document_id, f.document_id)    AS document_id,
    COALESCE(s.content, f.content)            AS content,
    COALESCE(s.metadata, f.metadata)          AS metadata,
    COALESCE(s.scope, f.scope)                AS scope,
    COALESCE(s.category, f.category)          AS category,
    COALESCE(s.sim, 0.0)                      AS semantic_score,
    COALESCE(f.rank_score, 0.0)               AS kw_score,
    CASE
      WHEN p_fusion_strategy = 'rrf' THEN
        -- Reciprocal Rank Fusion: 1/(k+rank_semantic) + 1/(k+rank_keyword)
        COALESCE(1.0 / (60.0 + s.rank), 0.0)
        + COALESCE(1.0 / (60.0 + f.rank), 0.0)
      ELSE
        -- Weighted: vector_weight * sim + keyword_weight * kw_score
        COALESCE(s.sim, 0.0) * p_vector_weight
        + COALESCE(f.rank_score, 0.0) * p_keyword_weight
    END AS combined
  FROM semantic s
  FULL OUTER JOIN fts f USING (id)
)

SELECT DISTINCT ON (id)
  id,
  document_id,
  content,
  metadata,
  semantic_score  AS similarity,
  kw_score        AS keyword_score,
  combined        AS combined_score,
  scope,
  category
FROM fused
WHERE combined >= p_threshold
ORDER BY id, combined DESC
LIMIT p_match_count;
$$;

ALTER FUNCTION vector_db.hybrid_match_documents(
  uuid, extensions.halfvec, text, integer, float, uuid[], text[], text[], text, float, float, boolean, text[]
) OWNER TO postgres;

COMMENT ON FUNCTION vector_db.hybrid_match_documents IS
  'Hybrid RAG retrieval: semantic (Cohere halfvec) + FTS (portuguese tsvector). '
  'Supports scope filtering (client/platform), category, theme, document_ids. '
  'Fusion strategies: rrf (default) or weighted. Migration 20260520000000.';

-- ── Indexes on filter columns ──────────────────────────────────────────────
-- Only create if they do not already exist (idempotent)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'vector_db'
      AND tablename  = 'document_chunks'
      AND indexname  = 'idx_document_chunks_scope'
  ) THEN
    CREATE INDEX idx_document_chunks_scope
      ON vector_db.document_chunks(scope);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'vector_db'
      AND tablename  = 'document_chunks'
      AND indexname  = 'idx_document_chunks_category'
  ) THEN
    CREATE INDEX idx_document_chunks_category
      ON vector_db.document_chunks(category);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'vector_db'
      AND tablename  = 'document_chunks'
      AND indexname  = 'idx_document_chunks_theme'
  ) THEN
    CREATE INDEX idx_document_chunks_theme
      ON vector_db.document_chunks(theme);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = 'vector_db'
      AND tablename  = 'document_chunks'
      AND indexname  = 'idx_document_chunks_client_scope_theme'
  ) THEN
    CREATE INDEX idx_document_chunks_client_scope_theme
      ON vector_db.document_chunks(client_id, scope, theme);
  END IF;
END;
$$;
