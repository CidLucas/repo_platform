-- Migration: Phase 3A (P3.3) — pg_cron schedule for RFQ follow-up dispatcher.
--
-- Hits POST <rfq_follow_ups_url>/internal/rfq/follow-ups/run every 30 min.
-- The wrapper URL (full path including /internal/rfq/follow-ups/run) is
-- read from `vault.decrypted_secrets.rfq_follow_ups_url`. Optional bearer
-- token from `rfq_follow_ups_token`.
--
-- If the secret is not provisioned the trigger logs a NOTICE and is a
-- no-op, so the cron stays scheduled and starts firing as soon as Ops
-- inserts the URL.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

CREATE OR REPLACE FUNCTION public.trigger_rfq_follow_ups()
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_url        text;
  v_token      text;
  v_request_id bigint;
BEGIN
  SELECT decrypted_secret INTO v_url
    FROM vault.decrypted_secrets
   WHERE name = 'rfq_follow_ups_url';

  IF v_url IS NULL OR v_url = '' THEN
    RAISE NOTICE 'trigger_rfq_follow_ups: vault secret rfq_follow_ups_url not set — skipping';
    RETURN NULL;
  END IF;

  SELECT decrypted_secret INTO v_token
    FROM vault.decrypted_secrets
   WHERE name = 'rfq_follow_ups_token';

  v_request_id := net.http_post(
    url     => v_url,
    headers => jsonb_build_object(
      'Content-Type',  'application/json',
      'Authorization', COALESCE('Bearer ' || v_token, '')
    ),
    body    => jsonb_build_object(
      'triggered_by', 'pg_cron',
      'triggered_at', now()
    ),
    timeout_milliseconds => 5 * 60 * 1000
  );

  RETURN v_request_id;
END;
$$;

REVOKE ALL ON FUNCTION public.trigger_rfq_follow_ups() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.trigger_rfq_follow_ups() TO service_role;

COMMENT ON FUNCTION public.trigger_rfq_follow_ups IS
  'Phase 3A (P3.3): pg_cron-side dispatcher for the RFQ follow-up endpoint.';

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'rfq-follow-ups') THEN
    PERFORM cron.unschedule('rfq-follow-ups');
  END IF;
END $$;

-- Every 30 minutes, year-round (no DST in Brazil).
SELECT cron.schedule(
  'rfq-follow-ups',
  '*/30 * * * *',
  $$ SELECT public.trigger_rfq_follow_ups(); $$
);

COMMIT;
