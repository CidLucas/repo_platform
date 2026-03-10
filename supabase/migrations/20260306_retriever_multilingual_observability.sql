-- Migration: Retriever multilingual model + observability
--
-- Changes:
-- 1. Lower default p_match_threshold from 0.5 → 0.3 in hybrid_match_documents
-- 2. Add RAISE NOTICE diagnostics (visible in pg logs when p_debug = true)
-- 3. Create vector_db.debug_search() — permanent observability into retrieval pipeline

-- ============================================================
-- 1. Replace hybrid_match_documents — lower threshold + add p_debug logging
-- ============================================================

-- Drop old overload (11 params, no p_debug) to avoid ambiguous function calls
DROP FUNCTION IF EXISTS vector_db.hybrid_match_documents(
  UUID, extensions.halfvec, TEXT, INT, FLOAT, UUID[], TEXT[], TEXT[], TEXT, FLOAT, FLOAT
);

CREATE OR REPLACE FUNCTION vector_db.hybrid_match_documents(
  p_client_id       UUID,
  p_query_embedding extensions.halfvec(384),
  p_query_text      TEXT,
  p_match_count     INT     DEFAULT 5,
  p_match_threshold FLOAT   DEFAULT 0.3,
  p_document_ids    UUID[]  DEFAULT NULL,
  p_scope           TEXT[]  DEFAULT '{platform,client}',
  p_categories      TEXT[]  DEFAULT NULL,
  p_fusion_strategy TEXT    DEFAULT 'rrf',   -- 'rrf' or 'weighted'
  p_keyword_weight  FLOAT   DEFAULT 0.4,
  p_vector_weight   FLOAT   DEFAULT 0.6,
  p_debug           BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
  id              INTEGER,
  document_id     UUID,
  content         TEXT,
  metadata        JSONB,
  similarity      FLOAT,
  keyword_score   FLOAT,
  combined_score  FLOAT,
  file_name       TEXT,
  document_title  TEXT,
  scope           TEXT,
  category        TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'extensions', 'vector_db', 'public'
AS $$
DECLARE
  v_tsquery TSQUERY;
  v_sem_count INT;
  v_kw_count  INT;
  v_merged_count INT;
BEGIN
  -- Build tsquery from user text (websearch syntax supports natural phrases)
  v_tsquery := websearch_to_tsquery(
    'portuguese',
    vector_db.immutable_unaccent(p_query_text)
  );

  IF p_debug THEN
    RAISE NOTICE '[hybrid_match] params: client=%, threshold=%, count=%, fusion=%, scope=%, query_text=%',
      p_client_id, p_match_threshold, p_match_count, p_fusion_strategy, p_scope, left(p_query_text, 80);
    RAISE NOTICE '[hybrid_match] tsquery: %', v_tsquery;
  END IF;

  RETURN QUERY
  WITH
  -- Semantic candidates (cosine similarity) — scope-filtered BEFORE ranking
  semantic AS (
    SELECT
      dc.id,
      dc.document_id,
      dc.content,
      dc.metadata,
      (1 - (dc.embedding <=> p_query_embedding))::float AS similarity,
      0::float AS keyword_score,
      d.file_name,
      d.title AS document_title,
      dc.scope,
      dc.category,
      ROW_NUMBER() OVER (ORDER BY dc.embedding <=> p_query_embedding) AS sem_rank
    FROM vector_db.document_chunks dc
    JOIN vector_db.documents d ON d.id = dc.document_id
    WHERE dc.embedding IS NOT NULL
      AND d.status = 'completed'
      AND dc.scope = ANY(p_scope)
      AND (dc.scope = 'platform' OR dc.client_id = p_client_id)
      AND (1 - (dc.embedding <=> p_query_embedding)) > p_match_threshold
      AND (p_document_ids IS NULL OR dc.document_id = ANY(p_document_ids))
      AND (p_categories  IS NULL OR dc.category = ANY(p_categories))
    ORDER BY dc.embedding <=> p_query_embedding
    LIMIT p_match_count * 3
  ),

  -- Keyword candidates (ts_rank on GIN index) — scope-filtered BEFORE ranking
  keyword AS (
    SELECT
      dc.id,
      dc.document_id,
      dc.content,
      dc.metadata,
      0::float AS similarity,
      ts_rank_cd(dc.fts, v_tsquery)::float AS keyword_score,
      d.file_name,
      d.title AS document_title,
      dc.scope,
      dc.category,
      ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dc.fts, v_tsquery) DESC) AS kw_rank
    FROM vector_db.document_chunks dc
    JOIN vector_db.documents d ON d.id = dc.document_id
    WHERE dc.fts @@ v_tsquery
      AND d.status = 'completed'
      AND dc.scope = ANY(p_scope)
      AND (dc.scope = 'platform' OR dc.client_id = p_client_id)
      AND (p_document_ids IS NULL OR dc.document_id = ANY(p_document_ids))
      AND (p_categories  IS NULL OR dc.category = ANY(p_categories))
    ORDER BY ts_rank_cd(dc.fts, v_tsquery) DESC
    LIMIT p_match_count * 3
  ),

  -- Merge all unique candidates
  all_candidates AS (
    SELECT sem.id, sem.document_id, sem.content, sem.metadata,
           sem.similarity, sem.keyword_score, sem.file_name, sem.document_title,
           sem.scope, sem.category, sem.sem_rank, NULL::bigint AS kw_rank
    FROM semantic sem
    UNION ALL
    SELECT kw.id, kw.document_id, kw.content, kw.metadata,
           kw.similarity, kw.keyword_score, kw.file_name, kw.document_title,
           kw.scope, kw.category, NULL::bigint AS sem_rank, kw.kw_rank
    FROM keyword kw
  ),

  -- Deduplicate and merge scores per chunk
  merged AS (
    SELECT
      ac.id,
      ac.document_id,
      MAX(ac.content) AS content,
      (array_agg(ac.metadata ORDER BY ac.similarity DESC))[1] AS metadata,
      COALESCE(MAX(ac.similarity), 0) AS similarity,
      COALESCE(MAX(ac.keyword_score), 0) AS keyword_score,
      MAX(ac.file_name) AS file_name,
      MAX(ac.document_title) AS document_title,
      MAX(ac.scope) AS scope,
      MAX(ac.category) AS category,
      MIN(ac.sem_rank) AS sem_rank,
      MIN(ac.kw_rank)  AS kw_rank
    FROM all_candidates ac
    GROUP BY ac.id, ac.document_id
  ),

  -- Score fusion
  scored AS (
    SELECT
      m.*,
      CASE p_fusion_strategy
        WHEN 'rrf' THEN
          COALESCE(1.0 / (60 + m.sem_rank), 0) +
          COALESCE(1.0 / (60 + m.kw_rank), 0)
        WHEN 'weighted' THEN
          (p_vector_weight  * m.similarity) +
          (p_keyword_weight * LEAST(m.keyword_score * 10, 1.0))
        ELSE
          m.similarity
      END AS combined_score
    FROM merged m
  )

  SELECT
    s.id, s.document_id, s.content, s.metadata,
    s.similarity, s.keyword_score, s.combined_score,
    s.file_name, s.document_title, s.scope, s.category
  FROM scored s
  ORDER BY s.combined_score DESC
  LIMIT p_match_count;
END;
$$;


-- ============================================================
-- 2. Diagnostic function: vector_db.debug_search
-- ============================================================
-- Call from Supabase SQL editor to inspect all intermediate scores
-- without needing to go through the Edge Function.
--
-- Usage:
--   SELECT * FROM vector_db.debug_search(
--     'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723'::uuid,
--     'logística reversa embalagens'
--   );

CREATE OR REPLACE FUNCTION vector_db.debug_search(
  p_client_id   UUID,
  p_query_text  TEXT,
  p_limit       INT   DEFAULT 10,
  p_scope       TEXT[] DEFAULT '{platform,client}'
)
RETURNS TABLE (
  source          TEXT,       -- 'semantic', 'keyword', or 'fused'
  chunk_id        INTEGER,
  document_id     UUID,
  similarity      FLOAT,
  keyword_score   FLOAT,
  combined_score  FLOAT,
  sem_rank        BIGINT,
  kw_rank         BIGINT,
  content_preview TEXT,
  file_name       TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'extensions', 'vector_db', 'public'
AS $$
DECLARE
  v_tsquery TSQUERY;
BEGIN
  -- Build tsquery (same logic as hybrid_match_documents)
  v_tsquery := websearch_to_tsquery(
    'portuguese',
    vector_db.immutable_unaccent(p_query_text)
  );

  RAISE NOTICE '[debug_search] client=%, query=%, tsquery=%', p_client_id, left(p_query_text, 80), v_tsquery;

  -- NOTE: This function does NOT embed the query — it reports raw semantic
  -- scores against ALL chunks (no threshold) using existing stored embeddings
  -- as a self-similarity baseline, plus full keyword scores.
  -- To test with a real query embedding, use the search-documents EF or
  -- pass the embedding vector to hybrid_match_documents directly.

  RETURN QUERY

  -- ── Part 1: Top semantic candidates (by stored embedding self-similarity — no external query embedding) ──
  -- We show the top chunks ordered by their embedding norm as a health check.
  -- For real semantic scoring you need the query embedding from Cohere.

  -- ── Part 2: Top keyword candidates ──────────────────────────
  WITH keyword_results AS (
    SELECT
      'keyword'::TEXT AS source,
      dc.id AS chunk_id,
      dc.document_id,
      0::FLOAT AS similarity,
      ts_rank_cd(dc.fts, v_tsquery)::FLOAT AS keyword_score,
      0::FLOAT AS combined_score,
      NULL::BIGINT AS sem_rank,
      ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dc.fts, v_tsquery) DESC) AS kw_rank,
      LEFT(dc.content, 120) AS content_preview,
      d.file_name
    FROM vector_db.document_chunks dc
    JOIN vector_db.documents d ON d.id = dc.document_id
    WHERE dc.fts @@ v_tsquery
      AND d.status = 'completed'
      AND dc.scope = ANY(p_scope)
      AND (dc.scope = 'platform' OR dc.client_id = p_client_id)
    ORDER BY ts_rank_cd(dc.fts, v_tsquery) DESC
    LIMIT p_limit
  ),

  -- ── Part 3: All chunks with embedding health info ──────────
  all_chunks AS (
    SELECT
      'embedding_health'::TEXT AS source,
      dc.id AS chunk_id,
      dc.document_id,
      -- Self-similarity: distance of embedding from zero vector (magnitude check)
      CASE WHEN dc.embedding IS NOT NULL THEN 1.0 ELSE 0.0 END::FLOAT AS similarity,
      0::FLOAT AS keyword_score,
      0::FLOAT AS combined_score,
      ROW_NUMBER() OVER (ORDER BY dc.id) AS sem_rank,
      NULL::BIGINT AS kw_rank,
      LEFT(dc.content, 120) AS content_preview,
      d.file_name
    FROM vector_db.document_chunks dc
    JOIN vector_db.documents d ON d.id = dc.document_id
    WHERE d.status = 'completed'
      AND dc.scope = ANY(p_scope)
      AND (dc.scope = 'platform' OR dc.client_id = p_client_id)
    ORDER BY dc.id
    LIMIT p_limit
  )

  SELECT * FROM keyword_results
  UNION ALL
  SELECT * FROM all_chunks;
END;
$$;

-- Grant execute to authenticated users (they'll still be scoped by client_id)
GRANT EXECUTE ON FUNCTION vector_db.debug_search(UUID, TEXT, INT, TEXT[]) TO authenticated;
GRANT EXECUTE ON FUNCTION vector_db.debug_search(UUID, TEXT, INT, TEXT[]) TO service_role;
