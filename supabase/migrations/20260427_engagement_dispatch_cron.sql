-- =============================================================================
-- Migration: pg_cron + pg_net — Engagement Dispatcher Cron Job
-- Date: 2026-04-27
-- Purpose:
--   Schedule a recurring pg_cron job (hourly) that calls the tool_pool_api
--   engagement-dispatch endpoint via pg_net, triggering Phase D1/D2 email and
--   WhatsApp triggers for all tenants without needing an external scheduler.
--
-- Dependencies:
--   pg_cron  — already enabled by 20260422120000_pg_cron_sync_worker.sql
--   pg_net   — must be enabled below; safe to re-run (CREATE EXTENSION IF NOT EXISTS)
--
-- Operator setup (run once per environment before applying this migration):
--
--   -- Production / Cloud Run URL:
--   INSERT INTO vault.secrets (name, secret)
--   VALUES
--     ('tool_pool_api_url',         'https://YOUR_TOOL_POOL_API_HOST'),
--     ('engagement_dispatch_token', 'YOUR_ENGAGEMENT_DISPATCH_TOKEN')
--   ON CONFLICT (name) DO UPDATE SET secret = EXCLUDED.secret;
--
--   Local dev: leave vault secrets unset — the function logs a warning and returns
--   without firing, so the cron is harmless in a local Supabase instance.
-- =============================================================================

BEGIN;

-- ── Enable pg_net ─────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pg_net SCHEMA extensions;

-- ── Helper function ───────────────────────────────────────────────────────────
-- Reads URL + token from vault.decrypted_secrets and issues an async HTTP POST
-- via pg_net. The request is fire-and-forget: pg_net stores the response in
-- net._http_response for up to 6 hours, readable by operators for debugging.

CREATE OR REPLACE FUNCTION public.trigger_engagement_dispatch()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_url   text;
  v_token text;
  v_req   bigint;
BEGIN
  BEGIN
    SELECT decrypted_secret INTO v_url
    FROM vault.decrypted_secrets
    WHERE name = 'tool_pool_api_url'
    LIMIT 1;
  EXCEPTION WHEN others THEN
    v_url := NULL;
  END;

  BEGIN
    SELECT decrypted_secret INTO v_token
    FROM vault.decrypted_secrets
    WHERE name = 'engagement_dispatch_token'
    LIMIT 1;
  EXCEPTION WHEN others THEN
    v_token := NULL;
  END;

  IF v_url IS NULL OR v_url = '' THEN
    RAISE LOG '[trigger_engagement_dispatch] tool_pool_api_url not set in vault — skipping';
    RETURN;
  END IF;

  SELECT extensions.http_post(
    url     := v_url || '/internal/engagement/dispatch',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || coalesce(v_token, ''),
      'Content-Type',  'application/json'
    ),
    body    := '{}'
  ) INTO v_req;

  RAISE LOG '[trigger_engagement_dispatch] pg_net request queued id=%', v_req;
END;
$$;

COMMENT ON FUNCTION public.trigger_engagement_dispatch() IS
  'Phase D1/D2 engagement cron trigger. Calls tool_pool_api /internal/engagement/dispatch '
  'via pg_net. Reads URL + token from vault.decrypted_secrets. Safe no-op when vault '
  'secrets are absent (local dev).';

-- ── Schedule: every hour at minute 5 (avoids pile-up with other crons) ────────
-- Remove stale schedule if already registered (idempotent re-run).
SELECT cron.unschedule('engagement-dispatch-hourly')
WHERE EXISTS (
  SELECT 1 FROM cron.job WHERE jobname = 'engagement-dispatch-hourly'
);

SELECT cron.schedule(
  'engagement-dispatch-hourly',
  '5 * * * *',
  $$SELECT public.trigger_engagement_dispatch()$$
);

COMMIT;
