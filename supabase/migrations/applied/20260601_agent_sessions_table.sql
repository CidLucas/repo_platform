-- Migration: criar tabela agent_sessions para standalone agent router
-- Criada em 2026-06-01 para suportar /v1/sessions/* endpoints do agent_api

CREATE TABLE IF NOT EXISTS public.agent_sessions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   UUID        NOT NULL,
    agent_catalog_id UUID   NOT NULL REFERENCES public.agent_catalog(id) ON DELETE CASCADE,
    status      TEXT        NOT NULL DEFAULT 'pending',
    collected_context JSONB NOT NULL DEFAULT '{}',
    uploaded_document_ids TEXT[] NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS: só o próprio cliente pode ver/editar suas sessões
ALTER TABLE public.agent_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "agent_sessions_own_client" ON public.agent_sessions
    USING (client_id = (SELECT client_id FROM public.clientes_blu WHERE id = auth.uid() LIMIT 1));

-- Índice para listagem por cliente
CREATE INDEX IF NOT EXISTS idx_agent_sessions_client_id ON public.agent_sessions(client_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_status ON public.agent_sessions(client_id, status);
