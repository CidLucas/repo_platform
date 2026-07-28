-- 20260619T3.1a_shared_memory_embedding.sql
-- Issue #25 / T3.1a: Vector Store — embedding column + HNSW index + search RPC
--
-- (1) Adiciona coluna embedding halfvec(384) ao shared_business_memory
-- (2) Cria índice HNSW para busca vetorial (inner product)
-- (3) Adiciona coluna version (se ausente — migration 00003 também adiciona)
-- (4) Cria RPC public.search_shared_memory() para busca semântica
--
-- Padrão seguido de vector_db.document_chunks + hybrid_match_documents()
-- Cohere embed-multilingual-light-v3.0 gera vetores de 384 dimensões.
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

-- ===========================================================================
-- 1. Coluna embedding halfvec(384)
-- ===========================================================================

ALTER TABLE public.shared_business_memory
    ADD COLUMN IF NOT EXISTS embedding extensions.halfvec(384);

COMMENT ON COLUMN public.shared_business_memory.embedding IS
    'Cohere embed-multilingual-light-v3.0 embedding vector (384 dimensions). '
    'Used for semantic search via inner product similarity.';

-- ===========================================================================
-- 2. Índice HNSW para busca vetorial (inner product)
-- ===========================================================================

CREATE INDEX IF NOT EXISTS idx_sbm_embedding
    ON public.shared_business_memory
    USING hnsw (embedding extensions.halfvec_ip_ops);

COMMENT ON INDEX idx_sbm_embedding IS
    'HNSW index for semantic search on shared_business_memory.embedding. '
    'Uses halfvec inner product (cosine similarity approximation for normalized vectors).';

-- ===========================================================================
-- 3. Coluna version (idempotente — migration 00003 também adiciona)
-- ===========================================================================

ALTER TABLE public.shared_business_memory
    ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;

COMMENT ON COLUMN public.shared_business_memory.version IS
    'Incremental version number — incremented on every upsert update. '
    'Used for snapshot diffing and optimistic concurrency.';

-- ===========================================================================
-- 4. RPC: public.search_shared_memory()
--    Busca semântica em shared_business_memory via inner product.
--    Padrão: vector_db.hybrid_match_documents() (baseline L2692-2727)
-- ===========================================================================

CREATE OR REPLACE FUNCTION public.search_shared_memory(
    p_client_id       uuid,
    p_query_embed     extensions.halfvec(384),
    p_match_count     int   DEFAULT 10,
    p_match_threshold float DEFAULT 0.3,
    p_entity_type     text  DEFAULT NULL,
    p_category        text  DEFAULT NULL
)
RETURNS TABLE (
    id            uuid,
    entity_type   text,
    entity_name   text,
    key           text,
    value         jsonb,
    category      text,
    source        text,
    confidence    numeric,
    similarity    float
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT
        sbm.id,
        sbm.entity_type,
        sbm.entity_name,
        sbm.key,
        sbm.value,
        sbm.category,
        sbm.source,
        sbm.confidence,
        (1 - (sbm.embedding <#> p_query_embed))::float AS similarity
    FROM public.shared_business_memory sbm
    WHERE sbm.client_id = p_client_id
      AND sbm.embedding IS NOT NULL
      AND (p_entity_type IS NULL OR sbm.entity_type = p_entity_type)
      AND (p_category IS NULL OR sbm.category = p_category)
      AND 1 - (sbm.embedding <#> p_query_embed) > p_match_threshold
    ORDER BY sbm.embedding <#> p_query_embed
    LIMIT p_match_count;
$$;

COMMENT ON FUNCTION public.search_shared_memory IS
    'Semantic search in shared_business_memory using embedding inner product. '
    'Returns facts ranked by similarity (1.0 = identical, 0.0 = orthogonal). '
    'Filters: client_id (required), entity_type, category, match_threshold. '
    'Uses HNSW index idx_sbm_embedding for fast approximate nearest neighbor search. '
    'OPERATOR: <#> = negative inner product; 1 - (<#>) = cosine similarity for normalized vectors. '
    'SECURITY DEFINER + SET search_path = '''' for safe service_role bypass of RLS.';

COMMIT;
