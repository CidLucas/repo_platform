-- P14: Inline refresh_dashboards in process_pending_jobs dispatcher
--
-- Why: etl-refresh-dashboards EF is 132 LOC that does nothing but:
--   1. Validate the system-invocation auth
--   2. Load the reg_jobs row
--   3. Call public.refresh_client_dashboards(client_id) RPC
--   4. Mark the job completed/failed
--
-- All four steps are pure SQL. The EF adds 132 LOC + a pg_net round-trip +
-- a 60s edge runtime limit + cold-start latency for no observable benefit.
--
-- This migration supersedes the dispatcher proposals (proposed/20260526_*)
-- with a single inline version. The bigquery_sync path still POSTs to
-- etl-bigquery-ingest via pg_net (that EF is 491 LOC with daisy-chain and
-- a 60s wall budget; can't be inlined).
--
-- This migration is idempotent: DROP IF EXISTS on the function, then CREATE.
-- If the function doesn't exist yet (e.g. the proposed migrations were never
-- applied), the DROP is a no-op and the CREATE establishes the new version.

BEGIN;

DROP FUNCTION IF EXISTS analytics_v2.process_pending_jobs();

CREATE OR REPLACE FUNCTION analytics_v2.process_pending_jobs()
RETURNS TABLE (job_id uuid, request_id bigint)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public, vault, extensions
AS $$
DECLARE
  v_base_url text := 'https://haruewffnubdgyofftut.supabase.co/functions/v1';
  v_jwt      text;
  v_job      RECORD;
  v_request  bigint;
  v_refresh_err text;
BEGIN
  -- Read service_role_key exclusively from Vault (encrypted at rest).
  -- NEVER read from public.app_config — that path was reverted in rev2
  -- of the dispatcher (see proposed/20260526120000_dispatcher_config_from_app_config.sql).
  SELECT decrypted_secret INTO v_jwt
  FROM vault.decrypted_secrets
  WHERE name = 'app_service_role_key'
  LIMIT 1;

  IF v_jwt IS NULL OR v_jwt = '' THEN
    RAISE EXCEPTION '[process_pending_jobs] vault.secrets app_service_role_key not found';
  END IF;

  -- Claim up to 15 pending jobs (bigquery_sync | refresh_dashboards) per tick.
  -- FOR UPDATE SKIP LOCKED so concurrent dispatcher ticks don't double-claim.
  FOR v_job IN
    UPDATE analytics_v2.reg_jobs rj
    SET status     = 'running',
        started_at = now(),
        updated_at = now()
    WHERE rj.job_id IN (
      SELECT j2.job_id FROM analytics_v2.reg_jobs j2
      WHERE j2.status   = 'pending'
        AND j2.job_type IN ('bigquery_sync', 'refresh_dashboards')
      ORDER BY j2.created_at
      LIMIT 15
      FOR UPDATE SKIP LOCKED
    )
    RETURNING rj.job_id, rj.job_type, rj.client_id
  LOOP
    IF v_job.job_type = 'refresh_dashboards' THEN
      -- INLINE path: the work is a single SQL RPC + a status update.
      -- The etl-refresh-dashboards EF used to do this; now the dispatcher
      -- does it directly. Saves one pg_net round-trip + 132 LOC of EF.
      BEGIN
        PERFORM public.refresh_client_dashboards(v_job.client_id);
        UPDATE analytics_v2.reg_jobs
        SET status       = 'completed',
            completed_at = now(),
            updated_at   = now()
        WHERE job_id = v_job.job_id;
        v_request := NULL;  -- no pg_net request id for inline path
      EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_refresh_err = MESSAGE_TEXT;
        UPDATE analytics_v2.reg_jobs
        SET status        = 'failed',
            error_message = v_refresh_err,
            updated_at    = now()
        WHERE job_id = v_job.job_id;
        v_request := NULL;
      END;
    ELSE
      -- bigquery_sync: keep the pg_net POST. The EF is 491 LOC with
      -- daisy-chain (when 25s wall budget is hit) and the SQL would
      -- not fit in a 60s edge call.
      SELECT net.http_post(
        url := v_base_url || '/etl-bigquery-ingest',
        headers := jsonb_build_object(
          'Content-Type',  'application/json',
          'Authorization', 'Bearer ' || v_jwt
        ),
        body := jsonb_build_object('job_id', v_job.job_id),
        timeout_milliseconds := 5000
      ) INTO v_request;
    END IF;

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
'Cron dispatcher — lê JWT exclusivamente do Vault (app_service_role_key). '
'Claims até 15 jobs pending (bigquery_sync | refresh_dashboards) por tick. '
'  - refresh_dashboards: INLINE (call refresh_client_dashboards RPC + '
'    update status) — no edge function round-trip. '
'  - bigquery_sync: pg_net POST to /etl-bigquery-ingest (still needed '
'    for the daisy-chain BQ ETL). '
'SECURITY: nunca lê segredos de public.app_config.';

COMMIT;
