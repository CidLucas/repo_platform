-- 20260630000000_schedule_process_pending_jobs.sql
-- Schedule the analytics_v2.process_pending_jobs() dispatcher in pg_cron.
--
-- Context:
--   The dispatcher function was created by 20260625_p14_inline_refresh_dashboards_in_dispatcher.sql
--   (applied). It claims up to 15 pending jobs per tick (bigquery_sync via pg_net
--   to etl-bigquery-ingest; refresh_dashboards inline via refresh_client_dashboards).
--
--   Without a cron.schedule call, the function is dead code — the only
--   cron.schedule calls referencing process_pending_jobs are in `proposed/`
--   and were intentionally created disabled (proposed/20260526070000 +
--   proposed/20260526090000).
--
--   The current fix for MV refresh (run-csv-etl direct RPC + reg_jobs enqueue
--   from sincronizar_csv_cliente) depends on the dispatcher actually running,
--   otherwise refresh_dashboards jobs accumulate in `pending` forever and
--   analytics_v2.mv_resumo_dashboard / mv_series_temporal stay stale.
--
-- Schedule: '* * * * *' (every minute). pg_cron minimum granularity is 1m.
-- The dispatcher itself does its own FOR UPDATE SKIP LOCKED claim, so back-to-back
-- ticks are safe.
--
-- Idempotency: cron.unschedule on the jobname first, then cron.schedule.
-- Re-runs are safe.
--
-- NÃO aplicar automaticamente. Operador revisa antes de ativar.

BEGIN;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
    PERFORM cron.unschedule(jobid) FROM cron.job WHERE jobname = 'process-pending-jobs';
    PERFORM cron.schedule(
      'process-pending-jobs',
      '* * * * *',  -- every minute (pg_cron minimum)
      $cmd$ SELECT analytics_v2.process_pending_jobs(); $cmd$
    );
  ELSE
    RAISE NOTICE 'pg_cron extension not installed — skipping schedule (apply this migration after pg_cron is enabled)';
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- VERIFICAÇÃO PÓS-APLICAÇÃO
-- ============================================================================
-- SELECT jobname, schedule, active FROM cron.job WHERE jobname = 'process-pending-jobs';
-- Forçar tick manual: SELECT analytics_v2.process_pending_jobs();
-- Verificar jobs: SELECT job_id, client_id, job_type, status, error_message
--                 FROM analytics_v2.reg_jobs
--                 WHERE job_type = 'refresh_dashboards'
--                 ORDER BY created_at DESC LIMIT 10;
-- Verificar MVs: SELECT count(*) FROM analytics_v2.mv_resumo_dashboard;
