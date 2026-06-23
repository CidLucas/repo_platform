-- 20260619_shared_business_memory_versions.sql
-- Fase 0 / T5.x: Version Storage — arquivo histórico de versões da shared_business_memory
--
-- Cada vez que um upsert sobrescreve uma row em shared_business_memory,
-- a versão anterior é arquivada nesta tabela. Permite recuperar o histórico
-- completo de alterações de cada fato na memória compartilhada.
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

CREATE TABLE IF NOT EXISTS public.shared_business_memory_versions (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Referência à row original em shared_business_memory (opcional — a row pode
    -- já ter sido deletada)
    memory_id   uuid,

    client_id   uuid NOT NULL
                REFERENCES public.clientes_blu(client_id)
                ON DELETE CASCADE,

    -- Composite key da memória original (idêntico a shared_business_memory)
    entity_type text NOT NULL,
    entity_name text NOT NULL,
    key         text NOT NULL
                CHECK (length(key) >= 1 AND length(key) <= 256),

    -- Snapshot do valor naquele momento
    value       jsonb NOT NULL DEFAULT '{}'::jsonb,

    -- Metadados de proveniência (cópia do metadata da row original)
    metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,

    -- Proveniência
    source      text NOT NULL DEFAULT 'manual'
                CHECK (source IN (
                    'manual', 'memory_agent', 'specialist', 'migration', 'system'
                )),
    confidence  real NOT NULL DEFAULT 1.0
                CHECK (confidence >= 0.0 AND confidence <= 1.0),

    -- Número da versão (do campo version da row original)
    version     integer NOT NULL CHECK (version >= 1),

    -- Timestamps
    archived_at         timestamptz NOT NULL DEFAULT now(),
    original_created_at timestamptz,
    original_updated_at timestamptz
);

COMMENT ON TABLE public.shared_business_memory_versions IS
    'Versioned snapshots of shared_business_memory rows. '
    'Each row captures the full state of a memory fact at the moment it was '
    'superseded by a newer version. Supports historical audit and rollback.';

COMMENT ON COLUMN public.shared_business_memory_versions.memory_id IS
    'UUID of the current row in shared_business_memory (may be NULL if row was deleted)';

COMMENT ON COLUMN public.shared_business_memory_versions.version IS
    'Version number at the time this snapshot was taken';

COMMENT ON COLUMN public.shared_business_memory_versions.archived_at IS
    'Timestamp when this version was archived (i.e., when it was superseded)';

COMMENT ON COLUMN public.shared_business_memory_versions.original_created_at IS
    'created_at timestamp from the original shared_business_memory row';

COMMENT ON COLUMN public.shared_business_memory_versions.original_updated_at IS
    'updated_at timestamp from the original shared_business_memory row';

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

-- Primary query: listar todas as versões de um fato
CREATE INDEX IF NOT EXISTS idx_sbm_versions_lookup
    ON public.shared_business_memory_versions
    (client_id, entity_type, entity_name, key, version DESC);

-- Busca por memory_id (para invalidar versões quando a row original é deletada)
CREATE INDEX IF NOT EXISTS idx_sbm_versions_memory_id
    ON public.shared_business_memory_versions (memory_id);

-- Busca por data de arquivamento (para pruning)
CREATE INDEX IF NOT EXISTS idx_sbm_versions_archived_at
    ON public.shared_business_memory_versions (client_id, archived_at);

-- ---------------------------------------------------------------------------
-- Row-Level Security
-- ---------------------------------------------------------------------------

ALTER TABLE public.shared_business_memory_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY client_own_memory_versions
    ON public.shared_business_memory_versions
    AS PERMISSIVE
    FOR ALL
    TO public
    USING (
        client_id = (current_setting('app.client_id'::text, true))::uuid
    );

COMMIT;
