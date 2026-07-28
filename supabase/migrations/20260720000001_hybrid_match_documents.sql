-- 20260625000000_hybrid_match_documents_12param.sql
-- Issue 3.6.1 (Plan: edge-functions-rationalization) — recreate vector_db
-- RPCs to match the 12-param signature the search-documents Edge Function
-- (and its Python port at services/tool_pool_api/.../search_documents/)
-- expect.
--
-- The Deno EF has been calling ``vector_db.hybrid_match_documents`` with
-- 12 parameters since Phase 3 (hybrid fusion): scope, categories, themes,
-- fusion_strategy, keyword_weight, vector_weight. But the only definition
-- in the repo (archive/20260430000000_baseline.sql:2692) had 5 params and
-- the active baseline_v2.sql defines NEITHER function. Result: the EF was
-- silently returning 500 in production, and the whole RAG pipeline
-- (process-document → document_chunks → search) was dead at the SQL layer.
--
-- User confirmed (2026-06-25) that ``vector_db.document_chunks`` and
-- ``vector_db.documents`` DO exist in the live Supabase — just the
-- functions are missing. This migration recreates the 2 functions to
-- match the EF/port's call shape.
--
-- Tables assumed to exist (created outside the repo's migrations):
--   vector_db.documents        (id uuid, client_id uuid, title, file_name, ...)
--   vector_db.document_chunks  (id int, document_id uuid, client_id uuid,
--                               content, embedding halfvec(384), metadata,
--                               fts tsvector, scope, category, theme, ...)
--
-- This migration is idempotent for the first run (CREATE OR REPLACE).
-- If a conflicting signature already exists in some environment, drop it
-- manually first. NO ``IF NOT EXISTS`` on the function bodies because we
-- want the new signature to win.
--
-- ATIVADA em 2026-07-20: promovida de proposed/ como 1a migration pós-baseline.
-- Recria vector_db.match_documents + hybrid_match_documents (halfvec 384,
-- search_path=extensions) que NÃO existem em prod — o RAG de documentos estava
-- morto na camada SQL. Ver 20260720000000_baseline.sql.

BEGIN;

-- ===========================================================================
-- 1. vector_db.match_documents — legacy semantic-only path
--    5 params (same as the Deno EF's "semantic" mode call)
-- ===========================================================================

CREATE OR REPLACE FUNCTION vector_db.match_documents(
    p_client_id     uuid,
    p_query_embed   halfvec(384),
    p_match_count   integer  DEFAULT 10,
    p_match_threshold float  DEFAULT 0.3,
    p_document_ids  uuid[]   DEFAULT NULL
)
RETURNS TABLE (
    id              integer,
    document_id     uuid,
    content         text,
    metadata        jsonb,
    similarity      double precision,
    file_name       text,
    document_title  text,
    scope           text,
    category        text
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = extensions
AS $$
    SELECT
        c.id,
        c.document_id,
        c.content,
        c.metadata,
        (1 - (c.embedding <#> p_query_embed))::float8 AS similarity,
        d.file_name,
        d.title AS document_title,
        c.scope,
        c.category
    FROM vector_db.document_chunks c
    JOIN vector_db.documents d ON d.id = c.document_id
    WHERE c.client_id = p_client_id
      AND c.embedding IS NOT NULL
      AND (1 - (c.embedding <#> p_query_embed)) >= p_match_threshold
      AND (p_document_ids IS NULL OR c.document_id = ANY(p_document_ids))
    ORDER BY c.embedding <#> p_query_embed
    LIMIT p_match_count;
$$;


-- ===========================================================================
-- 2. vector_db.hybrid_match_documents — semantic + keyword fusion (Phase 3)
--    12 params (same as the Deno EF's "hybrid" mode call and the Python
--    port at services/tool_pool_api/.../search_documents/__init__.py)
-- ===========================================================================
--
-- Fusion strategies (matching docs in retriever.py:194-198):
--   - rrf:      1/(60+rank_sem) + 1/(60+rank_kw)
--   - weighted: vector_weight*sim + keyword_weight*kw_rank
--
-- Threshold semantics (looser than match_documents):
--   - In hybrid mode a high-FTS / low-semantic hit can still be valuable,
--     so we keep the row if EITHER similarity >= threshold/2 OR the FTS
--     rank is non-zero. The final ORDER BY combined_score DESC picks the
--     best of the bunch.
-- ===========================================================================

CREATE OR REPLACE FUNCTION vector_db.hybrid_match_documents(
    p_client_id        uuid,
    p_query_embed      halfvec(384),
    p_query_text       text,
    p_match_count      integer  DEFAULT 10,
    p_match_threshold  float    DEFAULT 0.3,
    p_document_ids     uuid[]   DEFAULT NULL,
    p_scope            text[]   DEFAULT ARRAY['platform', 'client'],
    p_categories       text[]   DEFAULT NULL,
    p_fusion_strategy  text     DEFAULT 'rrf',
    p_keyword_weight   float    DEFAULT 0.4,
    p_vector_weight    float    DEFAULT 0.6,
    p_themes           text[]   DEFAULT NULL
)
RETURNS TABLE (
    id              integer,
    document_id     uuid,
    content         text,
    metadata        jsonb,
    similarity      double precision,
    keyword_score   double precision,
    combined_score  double precision,
    scope           text,
    category        text,
    file_name       text,
    document_title  text
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = extensions
AS $$
    WITH semantic_pool AS (
        SELECT
            c.id, c.document_id, c.content, c.metadata,
            c.scope, c.category, c.theme,
            1 - (c.embedding <#> p_query_embed) AS sim
        FROM vector_db.document_chunks c
        WHERE c.client_id = p_client_id
          AND c.embedding IS NOT NULL
          AND (p_document_ids IS NULL OR c.document_id = ANY(p_document_ids))
          AND (p_scope IS NULL OR c.scope = ANY(p_scope))
          AND (p_categories IS NULL OR c.category = ANY(p_categories))
          AND (p_themes IS NULL OR c.theme = ANY(p_themes))
        ORDER BY c.embedding <#> p_query_embed
        LIMIT GREATEST(p_match_count * 3, 30)
    ),
    semantic_ranked AS (
        SELECT *, ROW_NUMBER() OVER (ORDER BY sim DESC NULLS LAST) AS sem_rank
        FROM semantic_pool
    ),
    fts_pool AS (
        SELECT
            c.id, c.document_id, c.content, c.metadata,
            c.scope, c.category, c.theme,
            ts_rank(c.fts, plainto_tsquery('portuguese', p_query_text)) AS rank
        FROM vector_db.document_chunks c
        WHERE c.client_id = p_client_id
          AND c.fts @@ plainto_tsquery('portuguese', p_query_text)
          AND (p_document_ids IS NULL OR c.document_id = ANY(p_document_ids))
          AND (p_scope IS NULL OR c.scope = ANY(p_scope))
          AND (p_categories IS NULL OR c.category = ANY(p_categories))
          AND (p_themes IS NULL OR c.theme = ANY(p_themes))
        ORDER BY rank DESC
        LIMIT GREATEST(p_match_count * 3, 30)
    ),
    fts_ranked AS (
        SELECT *, ROW_NUMBER() OVER (ORDER BY rank DESC) AS fts_rank
        FROM fts_pool
    ),
    fused AS (
        SELECT
            COALESCE(s.id, f.id)                          AS id,
            COALESCE(s.document_id, f.document_id)        AS document_id,
            COALESCE(s.content, f.content)                AS content,
            COALESCE(s.metadata, f.metadata)              AS metadata,
            COALESCE(s.scope, f.scope)                    AS scope,
            COALESCE(s.category, f.category)              AS category,
            COALESCE(s.theme, f.theme)                    AS theme,
            COALESCE(s.sim, 0)::float8                    AS similarity,
            COALESCE(f.rank, 0)::float8                   AS keyword_score,
            CASE
                WHEN p_fusion_strategy = 'weighted' THEN
                    (COALESCE(s.sim, 0) * p_vector_weight
                     + COALESCE(f.rank, 0) * p_keyword_weight)::float8
                ELSE
                    (COALESCE(1.0 / (60.0 + s.sem_rank), 0)
                     + COALESCE(1.0 / (60.0 + f.fts_rank), 0))::float8
            END AS combined_score
        FROM semantic_ranked s
        FULL OUTER JOIN fts_ranked f USING (id)
    )
    SELECT
        fu.id,
        fu.document_id,
        fu.content,
        fu.metadata,
        fu.similarity,
        fu.keyword_score,
        fu.combined_score,
        fu.scope,
        fu.category,
        d.file_name,
        d.title AS document_title
    FROM fused fu
    JOIN vector_db.documents d ON d.id = fu.document_id
    WHERE fu.similarity >= p_match_threshold / 2.0
       OR fu.keyword_score > 0
    ORDER BY fu.combined_score DESC
    LIMIT p_match_count;
$$;


-- ===========================================================================
-- 3. Grants
-- ===========================================================================
-- service_role is used by tool_pool_api's /v1/search-documents router
-- (Phase 3.3) and by the upload-* Deno EFs indirectly. authenticated role
-- is needed if the frontend ever calls the RPC directly via PostgREST.
-- anon is intentionally excluded — RAG is server-side only.

GRANT EXECUTE ON FUNCTION vector_db.match_documents(
    uuid, halfvec, integer, float, uuid[]
) TO service_role, authenticated;

GRANT EXECUTE ON FUNCTION vector_db.hybrid_match_documents(
    uuid, halfvec, text, integer, float, uuid[],
    text[], text[], text, float, float, text[]
) TO service_role, authenticated;


-- ===========================================================================
-- 4. Smoke-test query (commented — uncomment in SQL Editor to verify)
-- ===========================================================================
--
-- SELECT id, similarity, keyword_score, combined_score, file_name
-- FROM vector_db.hybrid_match_documents(
--     '11111111-2222-3333-4444-555555555555'::uuid,  -- client_id
--     (SELECT embedding FROM vector_db.document_chunks LIMIT 1),  -- placeholder
--     'faturamento',
--     5, 0.3,
--     NULL, ARRAY['platform','client'], NULL, 'rrf', 0.4, 0.6, NULL
-- );

COMMIT;
