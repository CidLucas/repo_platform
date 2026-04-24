-- =============================================================================
-- Migration: Adjust stale running threshold for pg_cron worker
-- Date: 2026-04-22
-- Reason:
--   sincronizar_dados_cliente can run up to 25 minutes (statement_timeout).
--   Marking jobs stale at 15 minutes can create false failures and allow
--   duplicate enqueues while a valid job is still running.
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION analytics_v2.cleanup_stale_sync_jobs()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
DECLARE
  v_count INTEGER;
BEGIN
  UPDATE analytics_v2.reg_jobs
  SET
    status        = 'failed',
    error_message = 'Job timed out: exceeded 35-minute safety window. Retry to re-enqueue.',
    completed_at  = now(),
    updated_at    = now()
  WHERE
    status      = 'running'
    AND job_type = 'bigquery_sync'
    AND started_at < now() - interval '35 minutes';

  GET DIAGNOSTICS v_count = ROW_COUNT;

  IF v_count > 0 THEN
    RAISE LOG '[cleanup_stale_sync_jobs] Marked % stale job(s) as failed', v_count;
  END IF;
END;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.cleanup_stale_sync_jobs() TO postgres;
GRANT EXECUTE ON FUNCTION analytics_v2.cleanup_stale_sync_jobs() TO service_role;

COMMIT;
