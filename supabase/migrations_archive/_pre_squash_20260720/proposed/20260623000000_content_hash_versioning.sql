-- 20260623000000_content_hash_versioning.sql
-- Fase 0: Versioning Schema — content hash + dedup support
--
-- Adiciona a coluna content_hash em shared_business_memory e
-- shared_business_memory_versions para suportar detecção de mudança,
-- deduplicação de versões e integridade de valor.
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

-- 1. Adicionar content_hash na tabela principal
ALTER TABLE public.shared_business_memory
    ADD COLUMN IF NOT EXISTS content_hash text;

COMMENT ON COLUMN public.shared_business_memory.content_hash IS
    'SHA-256 hash of the JSON value (canonical representation with sort_keys).
     Used for change detection and deduplication across versions.
     Computed client-side via compute_content_hash().';

-- 2. Adicionar content_hash na tabela de versões
ALTER TABLE public.shared_business_memory_versions
    ADD COLUMN IF NOT EXISTS content_hash text;

COMMENT ON COLUMN public.shared_business_memory_versions.content_hash IS
    'SHA-256 hash of the JSON value at the time this version was archived.
     Used for diff detection between versions and dedup on archive.';

-- 3. Index on content_hash for efficient lookup in the versions table
CREATE INDEX IF NOT EXISTS idx_sbm_versions_content_hash
    ON public.shared_business_memory_versions
    (client_id, entity_type, entity_name, key, content_hash);

COMMIT;
