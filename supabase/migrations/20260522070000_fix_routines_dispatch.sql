-- =============================================================================
-- Fix: restore routine execution dispatch to the Python agent_api.
--
-- Root cause: 20260521004000 removed the pg_cron job that called the Python
-- endpoint. 20260520000100 left a SQL-only enqueuer (RETURNS integer) that
-- creates dispatched rows but nobody claims+executes them.
-- 20260522001000 tried to fix this but failed because:
--   a) dispatch_routine_executions() had RETURNS integer and couldn't be
--      replaced with RETURNS void via CREATE OR REPLACE; and
--   b) it read from public.app_config which didn't exist.
--
-- This migration:
--   1. Creates public.app_config (key/value runtime config store).
--   2. Drops any existing dispatch_routine_executions() regardless of return type.
--   3. Recreates it as RETURNS void, calling the Python /run-dispatched endpoint
--      via net.http_post(), reading URL+token from app_config.
--   4. Ensures the pg_cron job is scheduled every minute.
-- =============================================================================

-- ── 1. app_config table ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.app_config (
  key        text PRIMARY KEY,
  value      text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.app_config IS
  'Runtime key/value configuration for the platform. '
  'Values that must be set for routine dispatch: '
  'agent_api_core_url (e.g. https://api.example.com/v1), '
  'agent_api_routine_dispatch_token (matches ROUTINE_DISPATCH_TOKEN env var in agent_api).';

-- Seed placeholder rows so the operator knows what to fill in.
INSERT INTO public.app_config (key, value)
VALUES
  ('agent_api_core_url',              ''),
  ('agent_api_routine_dispatch_token', '')
ON CONFLICT (key) DO NOTHING;

-- RLS: only service_role can read/write
ALTER TABLE public.app_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS app_config_service_only ON public.app_config;
CREATE POLICY app_config_service_only ON public.app_config
  USING (false);  -- blocks anon/authenticated; service_role bypasses RLS

REVOKE ALL ON TABLE public.app_config FROM anon, authenticated;
GRANT  ALL ON TABLE public.app_config TO service_role;

-- ── 2. Drop existing dispatch_routine_executions() regardless of return type ──
-- There are two competing signatures in migration history; drop both to allow
-- a clean CREATE.
DROP FUNCTION IF EXISTS public.dispatch_routine_executions() CASCADE;

-- ── 3. Recreate as RETURNS void — calls Python endpoint via pg_net ────────────
CREATE FUNCTION public.dispatch_routine_executions()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'net'
AS $fn$
DECLARE
  _url   text;
  _token text;
BEGIN
  SELECT value INTO _url
  FROM   public.app_config
  WHERE  key = 'agent_api_core_url';

  SELECT value INTO _token
  FROM   public.app_config
  WHERE  key = 'agent_api_routine_dispatch_token';

  IF _url IS NULL OR _url = '' OR _token IS NULL OR _token = '' THEN
    RAISE WARNING '[dispatch_routine_executions] app_config not configured — '
                  'set agent_api_core_url and agent_api_routine_dispatch_token '
                  'in public.app_config to enable automatic routine execution.';
    RETURN;
  END IF;

  PERFORM net.http_post(
    url                  := _url || '/internal/routines/run-dispatched',
    headers              := jsonb_build_object(
      'Content-Type',  'application/json',
      'Authorization', 'Bearer ' || _token
    ),
    body                 := '{}'::jsonb,
    timeout_milliseconds := 30000
  );
END;
$fn$;

REVOKE EXECUTE ON FUNCTION public.dispatch_routine_executions() FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.dispatch_routine_executions() TO service_role;

COMMENT ON FUNCTION public.dispatch_routine_executions() IS
  'Called by pg_cron every minute. Invokes POST /internal/routines/run-dispatched '
  'on the Python agent_api so it can (a) evaluate cron/numeric triggers and '
  '(b) claim + execute dispatched routine executions. '
  'Requires agent_api_core_url and agent_api_routine_dispatch_token in app_config.';

-- ── 4. Ensure pg_cron job is scheduled every minute ──────────────────────────
-- Unschedule any legacy names first (idempotent).
SELECT cron.unschedule(jobid)
FROM   cron.job
WHERE  jobname IN (
  'dispatch_routine_executions',
  'dispatch_routine_executions_to_agent'
);

SELECT cron.schedule(
  'dispatch_routine_executions',
  '* * * * *',
  $$ SELECT public.dispatch_routine_executions(); $$
);
