-- 20260619000003_snapshot_templates.sql
-- Fase 0 / T0.6: Pre-requisitos para Snapshot Templates (Issue #22)
--
-- (1) Adiciona versão ao shared_business_memory para versionamento incremental
-- (2) Adiciona 'snapshot' aos CHECK constraints de entity_type
--     (shared_business_memory + shared_memory_links)
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Adicionar coluna version ao shared_business_memory
-- ---------------------------------------------------------------------------

ALTER TABLE public.shared_business_memory
    ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1;

COMMENT ON COLUMN public.shared_business_memory.version IS
    'Incremental version number — incremented on every upsert update';

-- ---------------------------------------------------------------------------
-- 2. Atualizar CHECK constraint de entity_type em shared_business_memory
--    Adicionar 'snapshot' à lista de tipos válidos.
-- ---------------------------------------------------------------------------

-- Drop e recria a constraint (operação idempotente)
ALTER TABLE public.shared_business_memory
    DROP CONSTRAINT IF EXISTS shared_business_memory_entity_type_check;

ALTER TABLE public.shared_business_memory
    ADD CONSTRAINT shared_business_memory_entity_type_check
        CHECK (entity_type IN (
            'skill', 'client', 'contact', 'supplier', 'user', 'snapshot'
        ));

-- ---------------------------------------------------------------------------
-- 3. Atualizar CHECK constraint de entity_type em shared_memory_links
--    (source_entity_type e target_entity_type também aceitam 'snapshot')
-- ---------------------------------------------------------------------------

ALTER TABLE public.shared_memory_links
    DROP CONSTRAINT IF EXISTS shared_memory_links_source_entity_type_check;

ALTER TABLE public.shared_memory_links
    ADD CONSTRAINT shared_memory_links_source_entity_type_check
        CHECK (source_entity_type IN (
            'skill', 'client', 'contact', 'supplier', 'user', 'snapshot'
        ));

ALTER TABLE public.shared_memory_links
    DROP CONSTRAINT IF EXISTS shared_memory_links_target_entity_type_check;

ALTER TABLE public.shared_memory_links
    ADD CONSTRAINT shared_memory_links_target_entity_type_check
        CHECK (target_entity_type IN (
            'skill', 'client', 'contact', 'supplier', 'user', 'snapshot'
        ));

COMMIT;
