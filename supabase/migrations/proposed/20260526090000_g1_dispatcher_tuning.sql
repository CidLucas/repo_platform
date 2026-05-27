-- G1: Tuning do dispatcher
-- 1. LIMIT 5 → 15 no process_pending_jobs
-- 2. Expandir job_type para incluir 'refresh_dashboards' no dispatcher
-- 3. Adicionar segundo cron offset 30s para polling efetivo a cada 30s
--
-- Nota: cron mínimo é 1 minuto. Simula 30s com pg_sleep(30) no segundo job.
-- Com daisy-chain (G2) implementada, os dois crons viram safety net apenas.

BEGIN;

-- DROP antes de recriar: assinatura de retorno mudou (jsonb → TABLE).
-- CREATE OR REPLACE não permite mudar RETURNS — obrigatório dropar primeiro.
DROP FUNCTION IF EXISTS analytics_v2.process_pending_jobs();

-- 1. Recriar process_pending_jobs com LIMIT 15 e job_types expandidos
CREATE OR REPLACE FUNCTION analytics_v2.process_pending_jobs()
RETURNS TABLE (job_id uuid, request_id bigint)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public, extensions
AS $$
DECLARE
  v_base_url text;
  v_jwt      text;
  v_job      RECORD;
  v_request  bigint;
BEGIN
  v_base_url := current_setting('app.edge_function_base_url', true);
  v_jwt      := current_setting('app.service_role_key',       true);

  IF v_base_url IS NULL OR v_base_url = '' THEN
    RAISE EXCEPTION '[process_pending_jobs] app.edge_function_base_url not set';
  END IF;
  IF v_jwt IS NULL OR v_jwt = '' THEN
    RAISE EXCEPTION '[process_pending_jobs] app.service_role_key not set';
  END IF;

  FOR v_job IN
    UPDATE analytics_v2.reg_jobs
    SET status     = 'running',
        started_at = now(),
        updated_at = now()
    WHERE job_id IN (
      SELECT job_id
      FROM analytics_v2.reg_jobs
      WHERE status   = 'pending'
        AND job_type IN ('bigquery_sync', 'refresh_dashboards')
      ORDER BY created_at
      LIMIT 15
      FOR UPDATE SKIP LOCKED
    )
    RETURNING reg_jobs.job_id, reg_jobs.job_type
  LOOP
    -- Route to correct edge function by job_type
    SELECT net.http_post(
      url := v_base_url || CASE v_job.job_type
               WHEN 'refresh_dashboards' THEN '/etl-refresh-dashboards'
               ELSE '/etl-bigquery-ingest'
             END,
      headers := jsonb_build_object(
        'Content-Type',  'application/json',
        'Authorization', 'Bearer ' || v_jwt
      ),
      body := jsonb_build_object('job_id', v_job.job_id),
      timeout_milliseconds := 5000
    ) INTO v_request;

    job_id     := v_job.job_id;
    request_id := v_request;
    RETURN NEXT;
  END LOOP;

  RETURN;
END;
$$;

REVOKE ALL ON FUNCTION analytics_v2.process_pending_jobs() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION analytics_v2.process_pending_jobs() TO service_role;

COMMENT ON FUNCTION analytics_v2.process_pending_jobs() IS
'Cron-triggered dispatcher. Claims up to 15 pending jobs (bigquery_sync | refresh_dashboards) '
'per tick and POSTs each to the correct edge function via pg_net. Async — does not wait for '
'the edge function to finish. Two cron jobs (offset 30s) fire this every 30s effectively.';

-- 2. Segundo cron offset 30s para polling a cada ~30s
--    (cron mínimo é 1 min; pg_sleep(30) simula offset de 30s)
DO $$
DECLARE
  v_job_id bigint;
BEGIN
  PERFORM cron.unschedule(jobid)
  FROM cron.job
  WHERE jobname IN ('process-pending-jobs-b');

  v_job_id := cron.schedule(
    job_name => 'process-pending-jobs-b',
    schedule => '* * * * *',
    command  => 'SELECT pg_sleep(30); SELECT analytics_v2.process_pending_jobs();'
  );

  -- Created disabled — ativar após confirmar que G1+G2 estão em prod:
  -- SELECT cron.alter_job(v_job_id, active := true);
  PERFORM cron.alter_job(v_job_id, active := false);
END;
$$;

COMMIT;
