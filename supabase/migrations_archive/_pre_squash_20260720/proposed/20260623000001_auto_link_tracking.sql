-- 20260623000001_auto_link_tracking.sql
-- Behavior B1 (Issue #28, Fase 3): Auto-link tracking columns
--
-- Adiciona colunas de tracking em public.shared_business_memory para
-- suportar a feature de auto-linking de entidades:
--   - last_auto_link_at: timestamp da última execução de auto-link
--   - auto_link_count:  contador acumulado de auto-links criados
--
-- Estas colunas alimentam observabilidade e rate limiting no job
-- de auto-linking que liga entidades semanticamente próximas.
--
-- A tabela public.shared_memory_links NÃO é alterada (anti-goal #2):
-- ela é a tabela de destino onde os links são gravados; a instrumentação
-- fica exclusivamente em shared_business_memory.
--
-- Idempotente: usa ADD COLUMN IF NOT EXISTS — pode ser reaplicada
-- sem erro. O transaction wrapper BEGIN/COMMIT garante rollback
-- atômico em caso de falha parcial.
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

-- 1. last_auto_link_at — wall-clock do último auto-link executado
ALTER TABLE public.shared_business_memory
    ADD COLUMN IF NOT EXISTS last_auto_link_at TIMESTAMPTZ;

COMMENT ON COLUMN public.shared_business_memory.last_auto_link_at IS
    'Timestamp (with timezone) of the most recent auto-link run that
     processed this memory entry. NULL means it has never been
     processed by the auto-linker. Used for throttling and
     observability of the auto-link pipeline (Issue #28, Fase 3).';

-- 2. auto_link_count — contador de auto-links criados para esta entry
ALTER TABLE public.shared_business_memory
    ADD COLUMN IF NOT EXISTS auto_link_count INTEGER DEFAULT 0;

COMMENT ON COLUMN public.shared_business_memory.auto_link_count IS
    'Cumulative number of auto-generated links pointing away from
     this memory entry. Defaults to 0; incremented by the auto-link
     routine after successfully writing to shared_memory_links.
     Used to detect high-fanout hubs and to prioritize re-linking.';

COMMIT;

-- ──────────────────────────────────────────────────────────────────────
-- DOWN (rollback) — manual, NÃO executado por este migration
-- ──────────────────────────────────────────────────────────────────────
-- BEGIN;
-- ALTER TABLE public.shared_business_memory
--     DROP COLUMN IF EXISTS auto_link_count;
-- ALTER TABLE public.shared_business_memory
--     DROP COLUMN IF EXISTS last_auto_link_at;
-- COMMIT;
-- ──────────────────────────────────────────────────────────────────────
