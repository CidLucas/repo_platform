-- Migration: Add p_themes filter to hybrid_match_documents
-- word_cloud and usage_context are already leveraged via enhanced FTS tsvector
-- (see 20260310_add_metadata_columns_and_enrich_fts.sql)
-- theme needs an explicit filter parameter for hard categorical filtering.

-- Drop the old overload without p_themes to avoid ambiguity
DROP FUNCTION IF EXISTS vector_db.hybrid_match_documents(
  uuid, halfvec, text, integer, double precision, uuid[], text[], text[], text, double precision, double precision, boolean
);

CREATE OR REPLACE FUNCTION vector_db.hybrid_match_documents(
  p_client_id uuid,
  p_query_embedding halfvec,
  p_query_text text,
  p_match_count integer DEFAULT 5,
  p_match_threshold double precision DEFAULT 0.3,
  p_document_ids uuid[] DEFAULT NULL,
  p_scope text[] DEFAULT '{platform,client}',
  p_categories text[] DEFAULT NULL,
  p_fusion_strategy text DEFAULT 'rrf',
  p_keyword_weight double precision DEFAULT 0.4,
  p_vector_weight double precision DEFAULT 0.6,
  p_debug boolean DEFAULT false,
  p_themes text[] DEFAULT NULL
)
RETURNS TABLE(
  id integer,
  document_id uuid,
  content text,
  metadata jsonb,
  similarity double precision,
  keyword_score double precision,
  combined_score double precision,
  file_name text,
  document_title text,
  scope text,
  category text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'extensions', 'vector_db', 'public'
AS $function$
DECLARE
  v_tsquery TSQUERY;
  v_sem_count INT;
  v_kw_count  INT;
  v_merged_count INT;
BEGIN
  v_tsquery := websearch_to_tsquery(
    'portuguese',
    vector_db.immutable_unaccent(p_query_text)
  );

  IF p_debug THEN
    RAISE NOTICE '[hybrid_match] params: client=%, threshold=%, count=%, fusion=%, scope=%, themes=%, query_text=%',
      p_client_id, p_match_threshold, p_match_count, p_fusion_strategy, p_scope, p_themes, left(p_query_text, 80);
    RAISE NOTICE '[hybrid_match] tsquery: %', v_tsquery;
  END IF;

  RETURN QUERY
  WITH
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
      AND (p_themes      IS NULL OR dc.theme = ANY(p_themes))
    ORDER BY dc.embedding <=> p_query_embedding
    LIMIT p_match_count * 3
  ),

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
      AND (p_themes      IS NULL OR dc.theme = ANY(p_themes))
    ORDER BY ts_rank_cd(dc.fts, v_tsquery) DESC
    LIMIT p_match_count * 3
  ),

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
$function$;
