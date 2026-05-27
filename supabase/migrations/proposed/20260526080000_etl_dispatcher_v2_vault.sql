-- Rev3 dispatcher: alinhado ao schema real reg_jobs (job_id uuid, sem next_run_at, job_type=bigquery_sync)
DROP FUNCTION IF EXISTS analytics_v2.process_pending_jobs();
CREATE OR REPLACE FUNCTION analytics_v2.process_pending_jobs()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, analytics_v2, vault, pg_temp
AS $$
DECLARE
  v_base_url    text := 'https://haruewffnubdgyofftut.functions.supabase.co';
  v_service_key text;
  v_job         record;
  v_request_id  bigint;
  v_dispatched  int := 0;
  v_results     jsonb := '[]'::jsonb;
BEGIN
  SELECT decrypted_secret INTO v_service_key
  FROM vault.decrypted_secrets
  WHERE name = 'app_service_role_key'
  LIMIT 1;

  IF v_service_key IS NULL THEN
    RAISE EXCEPTION 'vault.secrets.app_service_role_key não encontrada';
  END IF;

  FOR v_job IN
    SELECT job_id
    FROM analytics_v2.reg_jobs
    WHERE status = 'pending'
      AND job_type = 'bigquery_sync'
    ORDER BY created_at
    LIMIT 5
    FOR UPDATE SKIP LOCKED
  LOOP
    -- NB: we do NOT set status='running' here. The edge function does that
    -- itself in step 3, and doing it ahead-of-time would make the function
    -- return "already running" on its own load. SKIP LOCKED still prevents
    -- the same row from being dispatched twice within the same tick.

    SELECT net.http_post(
      url     := v_base_url || '/etl-bigquery-ingest',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'Authorization', 'Bearer ' || v_service_key
      ),
      body    := jsonb_build_object('job_id', v_job.job_id),
      timeout_milliseconds := 300000
    ) INTO v_request_id;

    v_dispatched := v_dispatched + 1;
    v_results := v_results || jsonb_build_object(
      'job_id', v_job.job_id,
      'request_id', v_request_id
    );
  END LOOP;

  RETURN jsonb_build_object(
    'dispatched', v_dispatched,
    'results', v_results,
    'timestamp', now()
  );
END;
$$;

REVOKE ALL ON FUNCTION analytics_v2.process_pending_jobs() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION analytics_v2.process_pending_jobs() TO postgres, service_role;
