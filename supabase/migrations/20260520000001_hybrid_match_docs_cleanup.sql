-- Migration: 20260520000001_hybrid_match_docs_cleanup.sql
-- Removes dead p_reserved parameter, adds theme to RETURNS TABLE.
-- Documents FTS language constraint (Portuguese hardcoded — known limitation).

-- ── Drop previous 13-param version (had unused p_reserved) ────────────────
DROP FUNCTION IF EXISTS vector_db.hybrid_match_documents(
  uuid, extensions.halfvec, text, integer, float, uuid[], text[], text[], text, float, float, boolean, text[]
);

-- ── Canonical 12-param hybrid_match_documents ─────────────────────────────
-- NOTE: FTS uses 'portuguese' language config. Keyword scoring degrades for
-- non-Portuguese content. Future work: add p_fts_language parameter if
-- multi-language support is required.
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
  category       text,
  theme          text
)
LANGUAGE sql STABLE SECURITY DEFINER
AS $$
WITH

-- ── Scope filter: client docs OR platform docs ─────────────────────────────
-- Line A: client-owned chunks accessed via client_id match (scope='client').
-- Line B: platform chunks accessed when 'platform' is in p_scope (client_id IS NULL).
-- Line C: final AND restricts to exact scopes when caller specifies p_scope,
--         e.g. p_scope=['platform'] excludes client docs even if client_id matches.
scope_filter AS (
  SELECT c.id, c.document_id, c.content, c.metadata, c.scope, c.category, c.theme,
         c.embedding, c.fts
  FROM   vector_db.document_chunks c
  JOIN   vector_db.documents d ON d.id = c.document_id
  WHERE
    (
      (c.client_id = p_client_id)                                                    -- Line A
      OR
      (c.scope = 'platform' AND (p_scope IS NULL OR 'platform' = ANY(p_scope)))      -- Line B
    )
    AND d.source != 'archived'
    AND (p_document_ids IS NULL OR c.document_id = ANY(p_document_ids))
    AND (p_categories IS NULL OR c.category = ANY(p_categories))
    AND (p_themes IS NULL OR c.theme = ANY(p_themes))
    AND (p_scope IS NULL OR c.scope = ANY(p_scope))                                  -- Line C
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
    sf.theme,
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
    sf.theme,
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
    COALESCE(s.theme, f.theme)                AS theme,
    COALESCE(s.sim, 0.0)                      AS semantic_score,
    COALESCE(f.rank_score, 0.0)               AS kw_score,
    CASE
      WHEN p_fusion_strategy = 'rrf' THEN
        COALESCE(1.0 / (60.0 + s.rank), 0.0)
        + COALESCE(1.0 / (60.0 + f.rank), 0.0)
      ELSE
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
  category,
  theme
FROM fused
WHERE combined >= p_threshold
ORDER BY id, combined DESC
LIMIT p_match_count;
$$;

ALTER FUNCTION vector_db.hybrid_match_documents(
  uuid, extensions.halfvec, text, integer, float, uuid[], text[], text[], text, float, float, text[]
) OWNER TO postgres;

COMMENT ON FUNCTION vector_db.hybrid_match_documents IS
  'Hybrid RAG retrieval: semantic (Cohere halfvec) + FTS (portuguese tsvector). '
  'Supports scope filtering (client/platform), category, theme, document_ids. '
  'Fusion strategies: rrf (default) or weighted. Returns theme as first-class column. '
  'Migration 20260520000001 (cleanup: removed p_reserved, added theme to RETURNS).';
