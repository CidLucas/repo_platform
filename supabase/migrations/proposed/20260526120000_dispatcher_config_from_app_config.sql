-- SECURITY FIX (rev2): dispatcher process_pending_jobs via Vault
-- Substitui a versão anterior que armazenava service_role_key em public.app_config.
--
-- Padrão correto: vault.decrypted_secrets WHERE name = 'app_service_role_key'
-- O segredo já está no Vault (criado em 20260526_etl_dispatcher_v2_vault).
--
-- Esta migration:
--   1. Insere supabase_url e edge_function_base_url em app_config (sem segredos)
--   2. Recria process_pending_jobs lendo o JWT exclusivamente do Vault
--   3. NÃO insere service_role_key em nenhuma tabela pública

BEGIN;

-- 1. Configurações não-sensíveis em app_config (URL é informação pública)
INSERT INTO public.app_config (key, value) VALUES
  ('supabase_url',           'https://haruewffnubdgyofftut.supabase.co'),
  ('edge_function_base_url', 'https://haruewffnubdgyofftut.supabase.co/functions/v1')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Garantir que service_role_key NÃO existe em app_config
DELETE FROM public.app_config WHERE key = 'service_role_key';

-- 2. Recriar process_pending_jobs com Vault
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
BEGIN
  -- Lê service_role_key exclusivamente do Vault (criptografado at rest)
  SELECT decrypted_secret INTO v_jwt
  FROM vault.decrypted_secrets
  WHERE name = 'app_service_role_key'
  LIMIT 1;

  IF v_jwt IS NULL OR v_jwt = '' THEN
    RAISE EXCEPTION '[process_pending_jobs] vault.secrets app_service_role_key not found';
  END IF;

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
    RETURNING rj.job_id, rj.job_type
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
'Cron dispatcher — lê JWT exclusivamente do Vault (app_service_role_key). '
'Claims até 15 jobs pending (bigquery_sync | refresh_dashboards) por tick via pg_net. '
'SECURITY: nunca lê segredos de public.app_config.';

COMMIT;
