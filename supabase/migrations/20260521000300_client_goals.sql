-- Migration: client_goals
-- Metas de negócio por dimensão, com progresso e plano de ação.
-- Criadas pelo usuário via chat ou por agentes especialistas.
-- Incluídas no get_business_memory_snapshot() como contexto de objetivos ativos.

CREATE TABLE IF NOT EXISTS client_goals (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id     uuid NOT NULL REFERENCES clientes_blu(client_id) ON DELETE CASCADE,
    dimension     text NOT NULL,           -- 'compras' | 'financeiro' | 'clientes' | 'agenda' | 'estrategia' | 'documentos' | 'geral'
    title         text NOT NULL,
    description   text,
    target_value  numeric,
    current_value numeric,
    unit          text,                    -- 'BRL' | 'clientes' | 'dias' | '%' | 'unidades'
    deadline      date,
    status        text NOT NULL DEFAULT 'active',  -- 'active' | 'achieved' | 'cancelled' | 'paused'
    action_plan   jsonb,                   -- [{step, owner, due_date, done}]
    source_agent  text,                    -- slug do agente que criou a meta
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT client_goals_dimension_check CHECK (
        dimension IN ('compras', 'financeiro', 'clientes', 'agenda', 'estrategia', 'documentos', 'geral')
    ),
    CONSTRAINT client_goals_status_check CHECK (
        status IN ('active', 'achieved', 'cancelled', 'paused')
    )
);

CREATE INDEX IF NOT EXISTS idx_client_goals_client_id ON client_goals (client_id);
CREATE INDEX IF NOT EXISTS idx_client_goals_active ON client_goals (client_id, dimension)
    WHERE status = 'active';

CREATE OR REPLACE FUNCTION update_client_goals_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_client_goals_updated_at ON client_goals;
CREATE TRIGGER trg_client_goals_updated_at
    BEFORE UPDATE ON client_goals
    FOR EACH ROW EXECUTE FUNCTION update_client_goals_updated_at();

ALTER TABLE client_goals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "client_own_goals"
    ON client_goals
    FOR ALL
    USING (client_id = (current_setting('app.client_id', true))::uuid);

COMMENT ON TABLE client_goals IS
    'Metas de negócio por dimensão. Criadas pelo usuário ou agentes; incluídas no snapshot de memória para contexto de objetivos ativos.';
