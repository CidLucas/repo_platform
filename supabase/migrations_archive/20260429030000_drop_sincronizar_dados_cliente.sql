-- =============================================================================
-- Migration: Remove sincronizar_dados_cliente and process_pending_sync_jobs
-- Date: 2026-04-29
--
-- All data intake is now handled asynchronously by the process-job-async
-- edge function. The PL/pgSQL ETL function and its pg_cron fallback poller
-- are no longer needed.
--
-- Removal order:
--   1. Unschedule pg_cron job (references process_pending_sync_jobs)
--   2. Drop process_pending_sync_jobs (references sincronizar_dados_cliente)
--   3. Drop sincronizar_dados_cliente
-- =============================================================================

-- 1. Remove the pg_cron schedule (no-op if already absent)
SELECT cron.unschedule('process-pending-sync-jobs');

-- 2. Drop the synchronous job poller
DROP FUNCTION IF EXISTS public.process_pending_sync_jobs();

-- 3. Drop the ETL function — logic lives in process-job-async edge function
DROP FUNCTION IF EXISTS public.sincronizar_dados_cliente(UUID);
