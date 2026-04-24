-- =============================================================================
-- Migration: Disable statement_timeout in pg_cron sync worker command
-- Date: 2026-04-22
--
-- Problem:
--   cron sessions inherit statement_timeout=30s and kill long sync jobs.
--
-- Fix:
--   Reschedule worker with a command that first sets statement_timeout=0,
--   then executes analytics_v2.process_pending_sync_jobs().
-- =============================================================================

BEGIN;

-- Replace existing worker schedule safely if present.
DO $$
BEGIN
	IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'process-bigquery-sync-jobs') THEN
		PERFORM cron.unschedule('process-bigquery-sync-jobs');
	END IF;
END;
$$;

SELECT cron.schedule(
	'process-bigquery-sync-jobs',
	'30 seconds',
	$$SET statement_timeout = '0'; SELECT analytics_v2.process_pending_sync_jobs();$$
);

COMMIT;

