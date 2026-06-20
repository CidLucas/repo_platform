-- ============================================================================
-- Seed: sbm_lightrag_weekly_synthesis
-- Issue: #29 (Fase 4 — Diretório handoffs/ estruturado)
-- Task:  T4.1d — Rotina semanal no Routine Engine
-- DD:    DD-T41-02 — routine_type='skill', trigger cron domingo 23h BRT
-- ============================================================================
-- Cria a rotina de catálogo em cross_agent_routines e inscreve todos os
-- clientes ativos (deleted_at IS NULL) em client_routines para execução
-- semanal automática (domingo 23h, America/Sao_Paulo).
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. UPSERT da rotina no catálogo (cross_agent_routines)
-- ----------------------------------------------------------------------------

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
    'sbm_lightrag_weekly_synthesis',
    'SBM → LightRAG Weekly Synthesis',
    'cron',
    '{
        "type": "cron",
        "expression": "0 23 * * 0",
        "timezone": "America/Sao_Paulo"
    }'::jsonb,
    'home',
    'system',
    '[
        {
            "id": "run_synthesis",
            "step": 1,
            "type": "skill",
            "skill_slug": "sbm_to_lightrag_synthesis",
            "on_failure": "continue",
            "task_template": "Execute the SBM to LightRAG knowledge graph synthesis for {{nome_empresa}} (client_id={{client_id}}). Sync all curated shared_business_memory records into LightRAG entities, then write a knowledge_graph_summary with graph statistics."
        }
    ]'::jsonb,
    '[]'::jsonb
) ON CONFLICT (id) DO UPDATE
SET
    name           = EXCLUDED.name,
    trigger_type   = EXCLUDED.trigger_type,
    trigger_config = EXCLUDED.trigger_config,
    room           = EXCLUDED.room,
    visibility     = EXCLUDED.visibility,
    steps          = EXCLUDED.steps,
    config_schema  = EXCLUDED.config_schema;

-- ----------------------------------------------------------------------------
-- 2. Enrollment automático — todos os clientes ativos
--    scope: per_tenant (roda para cada client_id ativo)
-- ----------------------------------------------------------------------------
-- Insere uma row em client_routines para cada cliente ativo que ainda não
-- possui esta rotina. Configurações:
--   - active: true
--   - status: 'active'
--   - trigger_type: 'cron' (herda do catálogo)
--   - trigger_config: null (usa o do catálogo como fallback)
--   - source: 'catalog'
--   - notify_channel: 'app'
--   - consecutive_failures: 0
--
-- O trigger poller (_check_cron_routines) varre client_routines com
-- active=true, status='active', routine_id='sbm_lightrag_weekly_synthesis'
-- e avalia a expressão cron contra last_run_at para dispatcher.

INSERT INTO public.client_routines (
    client_id,
    routine_id,
    name,
    notify_channel,
    active,
    status,
    source,
    trigger_type,
    trigger_config,
    config,
    consecutive_failures
)
SELECT
    cb.client_id,
    'sbm_lightrag_weekly_synthesis',
    'SBM → LightRAG Weekly Synthesis',
    'app',
    true,
    'active',
    'catalog',
    'cron',
    NULL::jsonb,
    '{}'::jsonb,
    0
FROM public.clientes_blu cb
WHERE cb.deleted_at IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM public.client_routines cr
      WHERE cr.client_id  = cb.client_id
        AND cr.routine_id = 'sbm_lightrag_weekly_synthesis'
  );

COMMIT;

-- ============================================================================
-- Verificação manual (executar após aplicar o seed):
-- ============================================================================
-- 1. Conferir catálogo:
--    SELECT id, name, trigger_type, trigger_config
--    FROM public.cross_agent_routines
--    WHERE id = 'sbm_lightrag_weekly_synthesis';
--
-- 2. Conferir enrollment:
--    SELECT cr.client_id, cb.nome_empresa, cr.active, cr.status, cr.last_run_at
--    FROM public.client_routines cr
--    JOIN public.clientes_blu cb ON cb.client_id = cr.client_id
--    WHERE cr.routine_id = 'sbm_lightrag_weekly_synthesis'
--    ORDER BY cb.nome_empresa;
--
-- 3. Simular sweep do dispatcher (ver se a rotina aparece):
--    SELECT id, name, trigger_config
--    FROM public.cross_agent_routines
--    WHERE trigger_type = 'cron';
-- ============================================================================
