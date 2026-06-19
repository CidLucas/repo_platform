-- 20260619000000_shared_business_memory.sql
-- Fase 0 / T0.1: Shared Business Memory — tabela base de fatos atômicos
--
-- Agentes compartilham memória via pares (entity, key) em vez de conversa direta.
-- Cada linha é um fato atômico sobre uma entidade de negócio.
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

CREATE TABLE IF NOT EXISTS public.shared_business_memory (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    client_id   uuid NOT NULL
                REFERENCES public.clientes_blu(client_id)
                ON DELETE CASCADE,

    -- Entity taxonomy: qual tipo de entidade de negócio
    entity_type text NOT NULL
                CHECK (entity_type IN (
                    'skill', 'client', 'contact', 'supplier', 'user'
                )),

    -- Nome da entidade (case-insensitive, normalizado para lowercase)
    entity_name text NOT NULL,

    -- Chave do fato atômico (ex: "tom_amigável", "preferência_horário", "regra_negócio")
    key         text NOT NULL
                CHECK (length(key) >= 1 AND length(key) <= 256),

    -- Valor do fato (JSONB para flexibilidade — string, número, array, objeto)
    value       jsonb NOT NULL DEFAULT '{}'::jsonb,

    -- Metadados de proveniência
    source      text NOT NULL DEFAULT 'manual'
                CHECK (source IN (
                    'manual', 'memory_agent', 'specialist', 'migration', 'system'
                )),
    confidence  numeric NOT NULL DEFAULT 1.0
                CHECK (confidence >= 0.0 AND confidence <= 1.0),
    metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,

    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),

    -- Cada (client_id, entity_type, entity_name, key) é único
    CONSTRAINT uq_shared_memory_entry
        UNIQUE (client_id, entity_type, entity_name, key)
);

COMMENT ON TABLE public.shared_business_memory IS
    'Shared Business Memory — atomic facts about business entities (skills, clients, contacts, suppliers, users). '
    'Agents read/write facts here instead of conversing directly. Each row is one key-value fact.';
COMMENT ON COLUMN public.shared_business_memory.entity_type IS
    'Entity taxonomy: skill | client | contact | supplier | user';
COMMENT ON COLUMN public.shared_business_memory.key IS
    'Fact key — e.g. tom_amigavel, preferencia_horario, regra_negocio';
COMMENT ON COLUMN public.shared_business_memory.source IS
    'Provenance: manual | memory_agent | specialist | migration | system';

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

-- Primary query: buscar facts por entidade
CREATE INDEX IF NOT EXISTS idx_sbm_entity
    ON public.shared_business_memory (client_id, entity_type, entity_name);

-- Lookup por chave específica
CREATE INDEX IF NOT EXISTS idx_sbm_key
    ON public.shared_business_memory (client_id, entity_type, entity_name, key);

-- Busca textual nas chaves (para descoberta)
CREATE INDEX IF NOT EXISTS idx_sbm_key_trgm
    ON public.shared_business_memory USING gin (key gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- Updated-at trigger
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.update_shared_business_memory_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_shared_business_memory_updated_at
    ON public.shared_business_memory;
CREATE TRIGGER trg_shared_business_memory_updated_at
    BEFORE UPDATE ON public.shared_business_memory
    FOR EACH ROW
    EXECUTE FUNCTION public.update_shared_business_memory_updated_at();

-- ---------------------------------------------------------------------------
-- Row-Level Security
-- ---------------------------------------------------------------------------

ALTER TABLE public.shared_business_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY client_own_shared_memory
    ON public.shared_business_memory
    AS PERMISSIVE
    FOR ALL
    TO public
    USING (
        client_id = (current_setting('app.client_id'::text, true))::uuid
    );

COMMIT;
