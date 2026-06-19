-- =============================================================================
-- Migration: sbm_synthesis_index
-- Purpose: Optimized indexes for the weekly synthesis query (T4.1).
--   Queries curated=true, non-expired memories grouped by entity for
--   LightRAG insertion via sbm_to_lightrag_synthesis skill.
--
-- Design Decision: DD-T41-03
--   Query: SELECT * FROM shared_business_memory
--          WHERE client_id = $1 AND curated = true AND expires_at IS NULL
--          ORDER BY entity_type, entity_name, updated_at DESC
--
-- Dependencies:
--   - 20260619000000_shared_business_memory.sql (base table)
--   - 20260619000002_shared_memory_integrity.sql (adds curated + expires_at)
--
-- IMPORTANT: Both indexes use CREATE INDEX CONCURRENTLY to avoid locking
-- the production table. CONCURRENTLY requires running OUTSIDE a transaction
-- block — do NOT wrap in BEGIN/COMMIT.
--
-- NÃO aplicar automaticamente. Lucas revisa.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. idx_sbm_synthesis_weekly — partial index for the main synthesis query
-- ---------------------------------------------------------------------------
-- Covers: client_id filter + curated=true + expires_at IS NULL
-- Partial WHERE clause keeps the index small (only curated, non-expired rows).
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sbm_synthesis_weekly
    ON public.shared_business_memory (client_id, curated, expires_at)
    WHERE curated = true AND expires_at IS NULL;

COMMENT ON INDEX public.idx_sbm_synthesis_weekly IS
    'Optimizes the weekly SBM→LightRAG synthesis query: curated=true, non-expired facts per client.';

-- ---------------------------------------------------------------------------
-- 2. idx_sbm_entity_temporal — index for temporal grouping by entity
-- ---------------------------------------------------------------------------
-- Covers: ORDER BY entity_type, entity_name, updated_at DESC
-- Enables efficient grouping when processing entities in Python (DD-T41-04).
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sbm_entity_temporal
    ON public.shared_business_memory (client_id, entity_type, entity_name, updated_at DESC);

COMMENT ON INDEX public.idx_sbm_entity_temporal IS
    'Optimizes temporal grouping by entity: ORDER BY entity_type, entity_name, updated_at DESC.';

-- ---------------------------------------------------------------------------
-- Row-Level Security
-- ---------------------------------------------------------------------------
-- RLS indexes are per-row — Postgres enforces policies AFTER index scan.
-- These indexes do NOT bypass RLS (they only speed up the WHERE clause).
-- The USING clause in the RLS policy (client_id = current_setting('app.client_id'))
-- applies as an additional filter after the index scan.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- Verification (run after applying):
--   EXPLAIN SELECT * FROM shared_business_memory
--   WHERE client_id = '<uuid>' AND curated = true AND expires_at IS NULL
--   ORDER BY entity_type, entity_name, updated_at DESC;
--
-- Expected: Index Scan using idx_sbm_synthesis_weekly or idx_sbm_entity_temporal
-- ---------------------------------------------------------------------------
