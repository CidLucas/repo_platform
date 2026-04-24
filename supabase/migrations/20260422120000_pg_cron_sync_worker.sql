-- =============================================================================
-- Migration: pg_cron Sync Worker
-- Date: 2026-04-22
-- Purpose:
--   1. Stale job janitor: mark jobs stuck in 'running' > 15min as 'failed'
--   2. pg_cron worker: pick up 'pending' bigquery_sync jobs and execute them
--      directly in Postgres — no Edge Function isolate involvement
--   3. Remove the duplicate-job guard that counts 'running' jobs (stale jobs
--      would block retries forever); replace with a smarter pending-only check
--      plus the stale-job timeout
--
-- Architecture:
--   Browser → run-sync Edge Function (enqueue only, < 1s)
--     └─▶ reg_jobs (status: 'pending')
--           └─▶ pg_cron every 30s: process_pending_sync_jobs()
--                 └─▶ sincronizar_dados_cliente() [runs in Postgres, no wall-clock limit]
--                       └─▶ UPDATE reg_jobs (completed/failed)
-- =============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. STALE JOB JANITOR
--    Runs every 5 minutes. Marks any job stuck in 'running' for more than
--    15 minutes as 'failed'. This prevents the duplicate-job guard from
--    permanently blocking retries after an isolate kill.
-- ─────────────────────────────────────────────────────────────────────────────

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
    error_message = 'Job timed out: Edge Function isolate was killed before the sync completed. Retry to re-enqueue.',
    completed_at  = now(),
    updated_at    = now()
  WHERE
    status      = 'running'
    AND job_type = 'bigquery_sync'
    AND started_at < now() - interval '15 minutes';

  GET DIAGNOSTICS v_count = ROW_COUNT;

  IF v_count > 0 THEN
    RAISE LOG '[cleanup_stale_sync_jobs] Marked % stale job(s) as failed', v_count;
  END IF;
END;
$$;

-- Schedule janitor: every 5 minutes
SELECT cron.schedule(
  'cleanup-stale-sync-jobs',
  '*/5 * * * *',
  'SELECT analytics_v2.cleanup_stale_sync_jobs()'
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. pg_cron SYNC WORKER
--    Runs every 30 seconds. Claims one pending bigquery_sync job atomically
--    using FOR UPDATE SKIP LOCKED (prevents double-processing) and executes
--    sincronizar_dados_cliente() directly in Postgres.
--
--    The function runs with no external wall-clock limit — it completes when
--    the BigQuery FDW query finishes or Postgres statement_timeout fires.
--    statement_timeout is set to 25 minutes inside the function (see migration
--    20260422120001_fix_sincronizar_dados_cliente.sql).
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.process_pending_sync_jobs()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
DECLARE
  v_job       analytics_v2.reg_jobs%ROWTYPE;
  v_result    JSONB;
BEGIN
  -- Claim one pending job atomically.
  -- SKIP LOCKED: if another cron tick already claimed this row, skip it.
  SELECT * INTO v_job
  FROM analytics_v2.reg_jobs
  WHERE
    status   = 'pending'
    AND job_type = 'bigquery_sync'
  ORDER BY created_at
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF NOT FOUND THEN
    RETURN; -- Nothing to do
  END IF;

  RAISE LOG '[process_pending_sync_jobs] Claiming job % (client=%, credential=%)',
    v_job.job_id,
    v_job.client_id,
    v_job.input_params->>'credential_id';

  -- Mark as running
  UPDATE analytics_v2.reg_jobs
  SET
    status      = 'running',
    started_at  = now(),
    progress_pct = 5,
    updated_at  = now()
  WHERE job_id = v_job.job_id;

  BEGIN
    -- Execute the sync. sincronizar_dados_cliente returns JSONB with success/error.
    v_result := public.sincronizar_dados_cliente(
      v_job.client_id::uuid,
      (v_job.input_params->>'credential_id')::integer,
      COALESCE((v_job.input_params->>'force_full_sync')::boolean, false)
    );

    IF COALESCE((v_result->>'success')::boolean, false) THEN
      RAISE LOG '[process_pending_sync_jobs] Job % completed successfully: %', v_job.job_id, v_result;
      UPDATE analytics_v2.reg_jobs
      SET
        status       = 'completed',
        progress_pct = 100,
        result       = v_result,
        completed_at = now(),
        updated_at   = now()
      WHERE job_id = v_job.job_id;
    ELSE
      RAISE LOG '[process_pending_sync_jobs] Job % returned failure: %', v_job.job_id, v_result->>'error';
      UPDATE analytics_v2.reg_jobs
      SET
        status        = 'failed',
        error_message = COALESCE(v_result->>'error', 'Sync function returned failure'),
        result        = v_result,
        completed_at  = now(),
        updated_at    = now()
      WHERE job_id = v_job.job_id;
    END IF;

  EXCEPTION WHEN OTHERS THEN
    RAISE LOG '[process_pending_sync_jobs] Job % raised exception: % (SQLSTATE: %)',
      v_job.job_id, SQLERRM, SQLSTATE;
    UPDATE analytics_v2.reg_jobs
    SET
      status        = 'failed',
      error_message = SQLERRM,
      completed_at  = now(),
      updated_at    = now()
    WHERE job_id = v_job.job_id;
  END;
END;
$$;

-- Grant pg_cron's postgres user access to execute these functions
GRANT EXECUTE ON FUNCTION analytics_v2.cleanup_stale_sync_jobs() TO postgres;
GRANT EXECUTE ON FUNCTION analytics_v2.process_pending_sync_jobs() TO postgres;
GRANT EXECUTE ON FUNCTION analytics_v2.cleanup_stale_sync_jobs() TO service_role;
GRANT EXECUTE ON FUNCTION analytics_v2.process_pending_sync_jobs() TO service_role;

-- Schedule worker: every 30 seconds
-- Note: pg_cron with sub-minute intervals requires Postgres 15.1.1.61+
SELECT cron.schedule(
  'process-bigquery-sync-jobs',
  '30 seconds',
  'SELECT analytics_v2.process_pending_sync_jobs()'
);

COMMIT;
