-- =============================================================================
-- 20260526070000_etl_dispatcher_via_pg_net.sql
--
-- Commit 2 of the FDW→Edge Function migration.
--
-- Adds:
--   1. public.get_credential_service_account(p_credential_id bigint)
--        SECURITY DEFINER helper that decrypts the vault entry tied to a
--        credencial_servico_externo row and returns the service_account_json
--        as jsonb. Called by the etl-bigquery-ingest edge function.
--
--   2. app_settings extension: store edge_function_base_url + service_role_key
--        in pg_settings via ALTER DATABASE so process_pending_jobs() can call
--        the edge function over pg_net without hardcoding secrets in the
--        function body (we set them via cron-time UPDATEs in this migration).
--
--   3. analytics_v2.process_pending_jobs()
--        Replaces process_pending_etl_jobs. Picks pending bigquery_sync jobs
--        and fires an HTTP POST to etl-bigquery-ingest via pg_net. Returns
--        immediately — no synchronous wait. The edge function takes 30-60s on
--        the Polen-sized dataset, way too long to hold a pg_cron worker.
--
--   4. New pg_cron job 'process-pending-bigquery-jobs' running every minute.
--
-- This commit DOES NOT touch:
--   - run_etl_job  (still callable, but unused after this)
--   - process_pending_etl_jobs (DESATIVADO since previous incident)
--   - sincronizar_csv_cliente / process_pending_csv_jobs (commit 3)
-- =============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Vault helper
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.get_credential_service_account(
  p_credential_id bigint
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, vault
AS $$
DECLARE
  v_vault_key uuid;
  v_secret    text;
BEGIN
  SELECT vault_key_id INTO v_vault_key
  FROM public.credencial_servico_externo
  WHERE id = p_credential_id;

  IF v_vault_key IS NULL THEN
    RAISE EXCEPTION 'credencial_servico_externo % has no vault_key_id', p_credential_id;
  END IF;

  SELECT decrypted_secret INTO v_secret
  FROM vault.decrypted_secrets
  WHERE id = v_vault_key;

  IF v_secret IS NULL THEN
    RAISE EXCEPTION 'vault entry % not found for credential %', v_vault_key, p_credential_id;
  END IF;

  RETURN v_secret::jsonb;
END;
$$;

REVOKE ALL ON FUNCTION public.get_credential_service_account(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_credential_service_account(bigint) TO service_role;

COMMENT ON FUNCTION public.get_credential_service_account(bigint) IS
'SECURITY DEFINER helper for the etl-bigquery-ingest edge function. Returns the decrypted service_account_json for a credencial_servico_externo row. service_role only — never expose to authenticated/anon.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. App settings for the dispatcher
--
-- We don't want to hardcode the project URL or service-role key in the
-- function body (committed to git). Setting via ALTER DATABASE keeps them in
-- pg_settings and only accessible to superuser/service_role.
--
-- NOTE: This migration sets placeholders. After applying, run:
--
--   ALTER DATABASE postgres SET app.edge_function_base_url = 'https://<project>.functions.supabase.co';
--   ALTER DATABASE postgres SET app.service_role_key       = '<service-role-jwt>';
--   SELECT pg_reload_conf();
--
-- (Migration intentionally does NOT bake the JWT into the file.)
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
  -- Placeholders only — operator must run the ALTER DATABASE statements above
  -- before activating the cron job at the end of this file. The
  -- process_pending_jobs() function raises a clear error if these are empty.
  NULL;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Dispatcher: pick pending jobs → fire edge function via pg_net
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.process_pending_jobs()
RETURNS TABLE (job_id uuid, request_id bigint)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, analytics_v2, net
AS $$
DECLARE
  v_base_url text := current_setting('app.edge_function_base_url', true);
  v_jwt      text := current_setting('app.service_role_key', true);
  v_job      record;
  v_request  bigint;
BEGIN
  IF v_base_url IS NULL OR v_base_url = '' THEN
    RAISE EXCEPTION 'app.edge_function_base_url is not set. Run: ALTER DATABASE postgres SET app.edge_function_base_url = ''https://<project>.functions.supabase.co'';';
  END IF;
  IF v_jwt IS NULL OR v_jwt = '' THEN
    RAISE EXCEPTION 'app.service_role_key is not set. Run: ALTER DATABASE postgres SET app.service_role_key = ''<service-role-jwt>'';';
  END IF;

  -- Claim up to 5 pending jobs per tick. We mark them 'running' inside the
  -- same transaction so a second cron tick doesn't double-fire.
  FOR v_job IN
    UPDATE analytics_v2.reg_jobs
    SET status = 'running',
        started_at = now(),
        updated_at = now()
    WHERE job_id IN (
      SELECT job_id
      FROM analytics_v2.reg_jobs
      WHERE status = 'pending'
        AND job_type = 'bigquery_sync'
      ORDER BY created_at
      LIMIT 5
      FOR UPDATE SKIP LOCKED
    )
    RETURNING reg_jobs.job_id
  LOOP
    -- Fire-and-forget HTTP POST. pg_net returns a request_id immediately;
    -- the edge function processes asynchronously and updates reg_jobs itself.
    SELECT net.http_post(
      url := v_base_url || '/etl-bigquery-ingest',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'Authorization', 'Bearer ' || v_jwt
      ),
      body := jsonb_build_object('job_id', v_job.job_id),
      timeout_milliseconds := 5000  -- pg_net timeout for the HTTP handshake only
    ) INTO v_request;

    job_id := v_job.job_id;
    request_id := v_request;
    RETURN NEXT;
  END LOOP;

  RETURN;
END;
$$;

REVOKE ALL ON FUNCTION analytics_v2.process_pending_jobs() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION analytics_v2.process_pending_jobs() TO service_role;

COMMENT ON FUNCTION analytics_v2.process_pending_jobs() IS
'Cron-triggered dispatcher. Claims up to 5 pending bigquery_sync jobs per tick and POSTs each to the etl-bigquery-ingest edge function via pg_net. Async — does not wait for the edge function to finish.';

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Cron job
--
-- Created in DISABLED state. After setting app.edge_function_base_url and
-- app.service_role_key, run:
--
--   UPDATE cron.job SET active = true WHERE jobname = 'process-pending-bigquery-jobs';
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
DECLARE
  v_job_id bigint;
BEGIN
  -- Idempotent: remove the previous version if it exists.
  PERFORM cron.unschedule(jobid)
  FROM cron.job
  WHERE jobname = 'process-pending-bigquery-jobs';

  v_job_id := cron.schedule(
    job_name => 'process-pending-bigquery-jobs',
    schedule => '* * * * *',                          -- every minute
    command  => 'SELECT analytics_v2.process_pending_jobs();'
  );

  -- Start disabled — operator activates after setting app.* settings.
  PERFORM cron.alter_job(job_id := v_job_id, active := false);

  RAISE NOTICE 'Created cron job % (disabled). Activate after setting app.edge_function_base_url and app.service_role_key.', v_job_id;
END $$;

COMMIT;
