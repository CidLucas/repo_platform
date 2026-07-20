-- ============================================================================
-- Migration: 20260603_onboarding_complete_routine_and_context_gaps.sql
-- Contexto: Plano Onboarding + Geração de Contexto
-- Objetivo: fechar a rotina onboarding_complete com steps executáveis.
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. Rotina onboarding_complete (UPSERT)
-- ----------------------------------------------------------------------------
-- Aceita o evento `onboarding_completed` e gera contexto/context_gaps
-- usando apenas steps suportados pelo engine atual.

INSERT INTO public.cross_agent_routines (
  id,
  name,
  trigger_type,
  trigger_config,
  room,
  visibility,
  steps,
  config_schema
) VALUES (
  'onboarding_complete',
  'Onboarding Complete',
  'event',
  '{"event_type":"onboarding_completed","cooldown_hours":24}'::jsonb,
  'home',
  'system',
  '[
    {
      "id": "build_context",
      "step": 1,
      "type": "skill",
      "outputs": {
        "structured_context": "contexto estruturado gerado a partir do onboarding",
        "context_map_md": "markdown do context_map.md"
      },
      "on_failure": "continue",
      "skill_slug": "onboarding_context_build",
      "task_template": "Transforme os dados de onboarding em contexto estruturado.\n\nDados do onboarding:\n{{onboarding_state}}\n"
    },
    {
      "id": "save_context_map",
      "step": 2,
      "type": "artifact",
      "artifact_type": "document",
      "function": "storage.save_context_document",
      "inputs": {
        "file_name": "context_map.md",
        "content": "{{structured_context.context_map_md}}",
        "title": "Context Map — {{nome_empresa}}",
        "document_type": "context_map"
      },
      "on_failure": "continue"
    },
    {
      "id": "upsert_clientes_blu_context",
      "step": 3,
      "type": "function",
      "inputs": {
        "company_profile": "{{structured_context.company_profile}}",
        "brand_voice": "{{structured_context.brand_voice}}"
      },
      "function": "analytics.upsert_clientes_blu_context",
      "on_failure": "continue"
    },
    {
      "id": "upsert_client_goals",
      "step": 4,
      "type": "function",
      "inputs": {
        "goals": "{{structured_context.goals}}"
      },
      "function": "analytics.upsert_client_goals",
      "on_failure": "continue"
    },
    {
      "id": "init_home_state",
      "step": 5,
      "type": "function",
      "inputs": {
        "summary": "{{structured_context.home_summary}}",
        "dimension": "home",
        "ttl_hours": 24,
        "structured": {
          "company_name": "{{nome_empresa}}",
          "tier": "{{tier}}"
        }
      },
      "function": "memory.write_dimension_state",
      "on_failure": "continue"
    }
  ]'::jsonb,
  '[]'::jsonb
) ON CONFLICT (id) DO UPDATE
SET
  trigger_type = EXCLUDED.trigger_type,
  trigger_config = EXCLUDED.trigger_config,
  room = EXCLUDED.room,
  visibility = EXCLUDED.visibility,
  steps = EXCLUDED.steps,
  config_schema = EXCLUDED.config_schema;

-- ----------------------------------------------------------------------------
-- 2. Tabela context_gaps
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.context_gaps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  gap_description TEXT NOT NULL,
  priority TEXT NOT NULL DEFAULT 'media',
  status TEXT NOT NULL DEFAULT 'pending',
  asked_at TIMESTAMPTZ,
  answered_at TIMESTAMPTZ,
  answer_content TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_context_gaps_client
  ON public.context_gaps (client_id);

CREATE INDEX IF NOT EXISTS idx_context_gaps_status
  ON public.context_gaps (client_id, status, priority, asked_at);

ALTER TABLE public.context_gaps ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cg_client_isolation ON public.context_gaps;
CREATE POLICY cg_client_isolation
  ON public.context_gaps
  FOR ALL
  TO authenticated
  USING (client_id = public.get_my_client_id());

CREATE OR REPLACE FUNCTION public.set_context_gaps_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_context_gaps_updated_at ON public.context_gaps;
CREATE TRIGGER trg_set_context_gaps_updated_at
  BEFORE UPDATE ON public.context_gaps
  FOR EACH ROW
  EXECUTE FUNCTION public.set_context_gaps_updated_at();

COMMENT ON TABLE public.context_gaps IS
  'Gaps de contexto identificados pelo context-gatherer, com perguntas direcionadas por tema e status de resposta.';

COMMIT;
