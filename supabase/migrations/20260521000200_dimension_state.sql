-- Migration: dimension_state
-- Armazena o estado compacto e legível por LLM de cada dimensão de negócio por cliente.
-- Escrito pelos Room Monitors ao final de cada execução de rotina.
-- Lido pelo get_business_memory_snapshot() no context_service.

CREATE TABLE IF NOT EXISTS dimension_state (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   uuid NOT NULL REFERENCES clientes_blu(client_id) ON DELETE CASCADE,
    dimension   text NOT NULL,           -- 'compras' | 'financeiro' | 'clientes' | 'agenda' | 'estrategia' | 'documentos'
    summary     text NOT NULL,           -- prose compacto ~250 tokens para injeção em prompts
    structured  jsonb,                   -- dados numéricos/estruturados para leitura programática
    valid_until timestamptz,             -- TTL; NULL = sempre válido
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT dimension_state_client_dimension_key UNIQUE (client_id, dimension),
    CONSTRAINT dimension_state_dimension_check CHECK (
        dimension IN ('compras', 'financeiro', 'clientes', 'agenda', 'estrategia', 'documentos')
    )
);

-- Índice para leituras rápidas por cliente (join no snapshot)
CREATE INDEX IF NOT EXISTS idx_dimension_state_client_id ON dimension_state (client_id);

-- Índice parcial: só estados ainda válidos (ou sem TTL)
CREATE INDEX IF NOT EXISTS idx_dimension_state_valid ON dimension_state (client_id, dimension)
    WHERE valid_until IS NULL OR valid_until > now();

-- Auto-atualiza updated_at
CREATE OR REPLACE FUNCTION update_dimension_state_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_dimension_state_updated_at ON dimension_state;
CREATE TRIGGER trg_dimension_state_updated_at
    BEFORE UPDATE ON dimension_state
    FOR EACH ROW EXECUTE FUNCTION update_dimension_state_updated_at();

-- RLS: cliente só acessa a própria linha
ALTER TABLE dimension_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "client_own_dimension_state"
    ON dimension_state
    FOR ALL
    USING (client_id = (current_setting('app.client_id', true))::uuid);

COMMENT ON TABLE dimension_state IS
    'Estado compacto de cada dimensão de negócio. Escrito por Room Monitors, lido pelo snapshot de memória do agente principal.';
