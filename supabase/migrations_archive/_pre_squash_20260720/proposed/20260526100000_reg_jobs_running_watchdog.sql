-- 20260526100000_reg_jobs_running_watchdog.sql
--
-- Watchdog: any reg_jobs row stuck in status='running' for more than 3 minutes
-- without a heartbeat (updated_at moving) is reset back to 'pending' so the
-- next dispatcher tick can pick it up.
--
-- Why 3 minutes:
--   - Hosted Supabase Edge Functions die at ~150s of CPU/wall time.
--   - Our cooperative chunking yields at 90s, so a healthy invocation lasts
--     <=100s end-to-end. Anything past 180s means the worker was killed
--     mid-flight and the job will never write a terminal status by itself.
--
-- Implementation: a SECURITY DEFINER function + cron entry. Idempotent.

CREATE OR REPLACE FUNCTION analytics_v2.reset_stuck_running_jobs()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
DECLARE
  affected integer;
BEGIN
  UPDATE analytics_v2.reg_jobs
     SET status = 'pending',
         error_message = COALESCE(error_message, '')
                       || CASE WHEN error_message IS NULL OR error_message = ''
                               THEN '' ELSE E'\n' END
                       || 'watchdog: reset from running (updated_at='
                       || updated_at::text || ')',
         updated_at = now()
   WHERE status = 'running'
     AND updated_at < now() - interval '3 minutes';

  GET DIAGNOSTICS affected = ROW_COUNT;
  RETURN affected;
END;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.reset_stuck_running_jobs() TO service_role;

-- Schedule once per minute (cheap; only updates orphans).
DO $$
DECLARE
  jid integer;
BEGIN
  SELECT jobid INTO jid
    FROM cron.job
   WHERE jobname = 'reg_jobs_running_watchdog';
  IF jid IS NOT NULL THEN
    PERFORM cron.unschedule(jid);
  END IF;
  PERFORM cron.schedule(
    'reg_jobs_running_watchdog',
    '* * * * *',
    $cron$ SELECT analytics_v2.reset_stuck_running_jobs(); $cron$
  );
END
$$;
