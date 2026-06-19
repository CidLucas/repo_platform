-- 20260619000004_add_agent_entity_types.sql
-- T1.2a: Post-flight Shared Memory — adiciona agent_result e agent_metadata
-- aos entity_types válidos da shared_business_memory.
--
-- Design: DD-02 (3 entity_types: agent_result, agent_metadata, agent_link_pending).
-- agent_link_pending vai como source='agent_pending' na shared_memory_links
-- (não como entity_type na shared_business_memory).
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

-- 1. Remove constraint existente (nome pode variar — CHECK inline ou nomeado)
ALTER TABLE public.shared_business_memory
    DROP CONSTRAINT IF EXISTS shared_business_memory_entity_type_check;

-- 2. Adiciona nova constraint com agent_result e agent_metadata
ALTER TABLE public.shared_business_memory
    ADD CONSTRAINT shared_business_memory_entity_type_check
    CHECK (entity_type IN (
        'skill', 'client', 'contact', 'supplier', 'user',
        'agent_result', 'agent_metadata'
    ));

-- 3. Atualiza comentário da coluna
COMMENT ON COLUMN public.shared_business_memory.entity_type IS
    'Entity taxonomy: skill | client | contact | supplier | user | agent_result | agent_metadata';

-- 4. Atualiza comentário da tabela
COMMENT ON TABLE public.shared_business_memory IS
    'Shared Business Memory — atomic facts about business entities (skills, clients, contacts, suppliers, users, agent results, agent metadata). '
    'Agents read/write facts here instead of conversing directly. Each row is one key-value fact.';

-- 5. Adiciona 'agent_pending' como source válido na shared_memory_links
-- (links sugeridos por agentes no post-flight, validados depois pela rotina T4.4)
ALTER TABLE public.shared_memory_links
    DROP CONSTRAINT IF EXISTS shared_memory_links_source_check;

ALTER TABLE public.shared_memory_links
    ADD CONSTRAINT shared_memory_links_source_check
    CHECK (source IN (
        'manual', 'memory_agent', 'specialist', 'migration', 'system', 'agent_pending'
    ));

COMMENT ON COLUMN public.shared_memory_links.source IS
    'Provenance: manual | memory_agent | specialist | migration | system | agent_pending';

COMMIT;
