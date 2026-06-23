-- ============================================================================
-- Migration: 20260622000001_backup_shared_memory_routine.sql
-- Issue:     #37 — Fase 5: Política de Backup da Shared Memory
-- Task:      T5.5 — Rotina de backup diário (02:00 UTC)
-- DD:        DD-7 — Routine Engine (Python cron), NÃO pg_cron
--            DD-5 — Backup lógico (dump via REST) + PITR nativo (Supabase)
--            DD-6 — Checkpoint em shared_business_memory (entity_type='routine')
--            DD-8 — Buffer de 1h entre backup (02:00) e prune (03:00)
-- ============================================================================
-- Registra a rotina backup_shared_memory no catálogo cross_agent_routines.
-- Escopo GLOBAL (dump da tabela toda, não per-tenant).
-- Executa diariamente às 02:00 UTC.
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
    'backup_shared_memory',
    'Backup Shared Memory',
    'cron',
    '{
        "type": "cron",
        "expression": "0 2 * * *",
        "timezone": "UTC",
        "scope": "global"
    }'::jsonb,
    'home',
    'system',
    '[
        {
            "id": "run_backup",
            "step": 1,
            "type": "skill",
            "skill_slug": "backup_shared_memory",
            "description": "Logical dump of shared_business_memory: fetch all records, compress with gzip, upload to Supabase Storage bucket (shared-memory-backups/YYYY-MM-DD/dump.json.gz), compute sha256, write checkpoint for prune coordination, and prune old backups.",
            "on_failure": "continue",
            "task_template": "Run the shared_business_memory backup routine. Dump all records from shared_business_memory, compress with gzip, upload to shared-memory-backups/{YYYY-MM-DD}/dump.json.gz, compute sha256 checksum, write checkpoint (entity_type='routine', key='current_state:backup_shared_memory'), and prune backups older than 30 days. Consolidate weekly backup if Sunday."
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
--    WHERE id = 'backup_shared_memory';
--
-- 2. Simular sweep do dispatcher:
--    SELECT id, name, trigger_config
--    FROM public.cross_agent_routines
--    WHERE trigger_type = 'cron'
--      AND trigger_config->>'scope' = 'global';
-- ============================================================================
