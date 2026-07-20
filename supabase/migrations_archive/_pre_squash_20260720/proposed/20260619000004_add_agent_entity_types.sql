-- 20260619000004_add_agent_entity_types.sql
-- Issue: #17 (T1.1) e #18 (T1.2) — Pre-flight e Post-flight Shared Memory
-- Adiciona entity types para agent lifecycle: agent_result, agent_metadata, agent_pending
--
-- Esta migration faz o UNION de todos os entity types já definidos nas migrações
-- 00003 conflitantes (routine_checkpoint_rpc + snapshot_templates) e adiciona
-- os novos tipos 'agent_result' e 'agent_metadata'.
--
-- É IDEMPOTENTE (DROP IF EXISTS + ADD) — pode ser re-executada sem erro.
-- Deve ser aplicada DEPOIS de ambas as 00003.
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

-- ===========================================================================
-- 1. Atualizar CHECK constraint de entity_type em shared_business_memory
--    UNION de todos os tipos: 00000 + 00003_snapshot_templates + 
--    00003_routine_checkpoint_rpc + novos (agent_result, agent_metadata)
-- ===========================================================================

ALTER TABLE public.shared_business_memory
    DROP CONSTRAINT IF EXISTS shared_business_memory_entity_type_check;

ALTER TABLE public.shared_business_memory
    ADD CONSTRAINT shared_business_memory_entity_type_check
        CHECK (entity_type IN (
            'skill', 'client', 'contact', 'supplier', 'user',  -- originais (00000)
            'snapshot', 'routine',                              -- de 00003_*
            'agent_result', 'agent_metadata'                    -- NOVOS (T1.1 + T1.2)
        ));

COMMENT ON COLUMN public.shared_business_memory.entity_type IS
    'Entity taxonomy: skill | client | contact | supplier | user | snapshot | routine | agent_result | agent_metadata';

-- ===========================================================================
-- 2. Atualizar CHECK constraints de entity_type em shared_memory_links
--    (source_entity_type e target_entity_type)
-- ===========================================================================

ALTER TABLE public.shared_memory_links
    DROP CONSTRAINT IF EXISTS shared_memory_links_source_entity_type_check;

ALTER TABLE public.shared_memory_links
    ADD CONSTRAINT shared_memory_links_source_entity_type_check
        CHECK (source_entity_type IN (
            'skill', 'client', 'contact', 'supplier', 'user',
            'snapshot', 'routine',
            'agent_result', 'agent_metadata'
        ));

ALTER TABLE public.shared_memory_links
    DROP CONSTRAINT IF EXISTS shared_memory_links_target_entity_type_check;

ALTER TABLE public.shared_memory_links
    ADD CONSTRAINT shared_memory_links_target_entity_type_check
        CHECK (target_entity_type IN (
            'skill', 'client', 'contact', 'supplier', 'user',
            'snapshot', 'routine',
            'agent_result', 'agent_metadata'
        ));

-- ===========================================================================
-- 3. Adicionar 'agent_pending' ao CHECK de source em shared_memory_links
--    (T1.1 + T1.2 — agent lifecycle source tracking)
-- ===========================================================================

ALTER TABLE public.shared_memory_links
    DROP CONSTRAINT IF EXISTS shared_memory_links_source_check;

ALTER TABLE public.shared_memory_links
    ADD CONSTRAINT shared_memory_links_source_check
        CHECK (source IN (
            'manual', 'memory_agent', 'specialist', 'migration', 'system',
            'agent_pending'  -- NOVO (T1.1)
        ));

COMMENT ON COLUMN public.shared_memory_links.source IS
    'Provenance: manual | memory_agent | specialist | migration | system | agent_pending';

-- ===========================================================================
-- 4. Índices para queries de pre-flight
--    - idx_sbm_preflight_lookup: busca por client_id + entity_type + entity_name
--    - idx_sbm_preflight_keys: busca filtrada por key prefix
-- ===========================================================================

CREATE INDEX IF NOT EXISTS idx_sbm_preflight_lookup
    ON public.shared_business_memory (client_id, entity_type, entity_name, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_sbm_preflight_keys
    ON public.shared_business_memory (client_id, entity_type, entity_name, key, updated_at DESC);

COMMIT;
