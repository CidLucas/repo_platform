-- Migration: Phase 2 (I2.1) — pg_cron schedules for client_insights routines.
--
-- Two jobs:
--   1. `expire-stale-insights`       07:50 America/Sao_Paulo daily (10:50 UTC)
--      Marks active insights older than 7 days as `expired`. Pure SQL — no
--      external dependency, works immediately after this migration applies.
--
--   2. `daily-insights-run-all`      08:00 America/Sao_Paulo daily (11:00 UTC)
--      Triggers the Python routine `daily_insights.run_all_enabled` via
--      `pg_net.http_post` to a Cloud Run / Edge Function wrapper URL stored
--      in `vault.decrypted_secrets` under the name `daily_insights_runner_url`.
--      If the secret is not yet provisioned the trigger logs a NOTICE and
--      returns gracefully — the cron stays scheduled and starts working as
--      soon as the secret + wrapper are deployed.
--
-- Brazil has no DST since 2019, so 11:00 UTC == 08:00 BRT year-round.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

-- ─────────────────────────────────────────────────────────────────────
-- 1. Trigger function for the Python routine
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.trigger_daily_insights_run()
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_url     text;
  v_token   text;
  v_request_id bigint;
BEGIN
  -- Wrapper URL (e.g. https://<cloud-run>.a.run.app/internal/routines/daily-insights/run-all
  -- or https://<project>.functions.supabase.co/daily-insights-runner).
  SELECT decrypted_secret INTO v_url
    FROM vault.decrypted_secrets
   WHERE name = 'daily_insights_runner_url';

  IF v_url IS NULL OR v_url = '' THEN
    RAISE NOTICE 'trigger_daily_insights_run: vault secret daily_insights_runner_url not set — skipping';
    RETURN NULL;
  END IF;

  -- Optional shared-secret auth header. Optional — the wrapper can also
  -- accept the project anon/service key.
  SELECT decrypted_secret INTO v_token
    FROM vault.decrypted_secrets
   WHERE name = 'daily_insights_runner_token';

  v_request_id := net.http_post(
    url     => v_url,
    headers => jsonb_build_object(
      'Content-Type',  'application/json',
      'Authorization', COALESCE('Bearer ' || v_token, '')
    ),
    body    => jsonb_build_object(
      'period',       '30d',
      'window_days',  30,
      'max_insights', 5,
      'triggered_by', 'pg_cron',
      'triggered_at', now()
    ),
    timeout_milliseconds => 10 * 60 * 1000  -- 10 min ceiling for fan-out
  );

  RAISE NOTICE 'trigger_daily_insights_run: dispatched net.http_post id=%', v_request_id;
  RETURN v_request_id;
END;
$$;

REVOKE ALL ON FUNCTION public.trigger_daily_insights_run() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.trigger_daily_insights_run() TO service_role;

COMMENT ON FUNCTION public.trigger_daily_insights_run IS
  'Phase 2 (I2.1): pg_cron-side dispatcher for routine.daily_insights.run_all_enabled.';

-- ─────────────────────────────────────────────────────────────────────
-- 2. Cron schedules — unschedule first so the migration is idempotent
-- ─────────────────────────────────────────────────────────────────────

DO $$
BEGIN
  PERFORM cron.unschedule('expire-stale-insights')
    WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'expire-stale-insights');
EXCEPTION WHEN OTHERS THEN
  -- pg_cron raises when job missing; ignore.
  NULL;
END $$;

DO $$
BEGIN
  PERFORM cron.unschedule('daily-insights-run-all')
    WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'daily-insights-run-all');
EXCEPTION WHEN OTHERS THEN
  NULL;
END $$;

-- 07:50 BRT == 10:50 UTC daily
SELECT cron.schedule(
  'expire-stale-insights',
  '50 10 * * *',
  $$ SELECT public.expire_stale_insights(7); $$
);

-- 08:00 BRT == 11:00 UTC daily
SELECT cron.schedule(
  'daily-insights-run-all',
  '0 11 * * *',
  $$ SELECT public.trigger_daily_insights_run(); $$
);

COMMIT;
