-- Migrar process_pending_jobs para ler config de public.app_config
-- em vez de GUCs (ALTER DATABASE não é permitido no plano atual).
--
-- Insere as chaves em app_config e recria a função.

BEGIN;

-- 1. Inserir/atualizar chaves de configuração
INSERT INTO public.app_config (key, value) VALUES
  ('supabase_url',            'https://haruewffnubdgyofftut.supabase.co'),
  ('edge_function_base_url',  'https://haruewffnubdgyofftut.supabase.co/functions/v1'),
  ('service_role_key',        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhhcnVld2ZmbnViZGd5b2ZmdHV0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NDE2NTk4MCwiZXhwIjoyMDc5NzQxOTgwfQ.blB-QPXT_WnGmZcaqWb0w5e3WvTprKDcC5nWN6_PeTw')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- 2. Recriar process_pending_jobs lendo de app_config
DROP FUNCTION IF EXISTS analytics_v2.process_pending_jobs();

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
  SELECT value INTO v_base_url FROM public.app_config WHERE key = 'edge_function_base_url';
  SELECT value INTO v_jwt      FROM public.app_config WHERE key = 'service_role_key';

  IF v_base_url IS NULL OR v_base_url = '' THEN
    RAISE EXCEPTION '[process_pending_jobs] edge_function_base_url not set in app_config';
  END IF;
  IF v_jwt IS NULL OR v_jwt = '' THEN
    RAISE EXCEPTION '[process_pending_jobs] service_role_key not set in app_config';
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
'Cron dispatcher — lê edge_function_base_url e service_role_key de public.app_config. '
'Claims até 15 jobs pending (bigquery_sync | refresh_dashboards) por tick via pg_net.';

COMMIT;
