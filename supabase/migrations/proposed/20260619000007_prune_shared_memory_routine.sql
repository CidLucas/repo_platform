-- ============================================================================
-- Migration: 20260619000007_prune_shared_memory_routine.sql
-- Issue:     #32 — Fase 4: Política de retenção e prune da shared memory
-- Task:      T4.4d — Routine Engine cron job prune_shared_memory (03:00 UTC)
-- DD:        DD-04 — Routine Engine (Python cron), NÃO pg_cron
--            DD-05 — Operação silenciosa, alerta só se >100 registros
--            DD-07 — Verificar checkpoint de backup antes de rodar
-- ============================================================================
-- Registra a rotina prune_shared_memory no catálogo cross_agent_routines.
-- Escopo GLOBAL (manutenção da tabela toda, não per-tenant).
-- Executa diariamente às 03:00 UTC.
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
    'prune_shared_memory',
    'Prune Shared Memory',
    'cron',
    '{
        "type": "cron",
        "expression": "0 3 * * *",
        "timezone": "UTC",
        "scope": "global"
    }'::jsonb,
    'home',
    'system',
    '[
        {
            "id": "run_prune",
            "step": 1,
            "type": "skill",
            "skill_slug": "prune_shared_memory",
            "description": "Two-phase prune of shared_business_memory: soft-delete expired records, then hard-delete archived records past retention window. Checks backup completion first.",
            "on_failure": "continue",
            "task_template": "Run the shared_business_memory prune routine. Phase 1: soft-delete records where soft_delete_at <= NOW(). Phase 2: hard-delete records where hard_delete_at <= NOW() AND archived=true. Log counts per phase as checkpoint. Alert only if total_affected > 100."
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
-- NOTA: Sem enrollment automático em client_routines.
-- Esta rotina tem scope=global — não executa per-tenant.
-- O Routine Engine deve detectar scope=global no trigger_config e executar
-- UMA vez (não N vezes para cada cliente).
-- ----------------------------------------------------------------------------

COMMIT;

-- ============================================================================
-- Verificação manual (executar após aplicar o seed):
-- ============================================================================
-- 1. Conferir catálogo:
--    SELECT id, name, trigger_type, trigger_config
--    FROM public.cross_agent_routines
--    WHERE id = 'prune_shared_memory';
--
-- 2. Simular sweep do dispatcher (ver se a rotina aparece):
--    SELECT id, name, trigger_config
--    FROM public.cross_agent_routines
--    WHERE trigger_type = 'cron'
--      AND trigger_config->>'scope' = 'global';
-- ============================================================================
