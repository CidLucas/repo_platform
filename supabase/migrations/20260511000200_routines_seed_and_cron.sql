-- ─────────────────────────────────────────────────────────────────────────────
-- Schedule pg_cron jobs for routine execution.
--
-- cross_agent_routines seed data already exists (added manually).
-- These cron jobs were defined in archive/20260506000003 but never applied
-- to the active migrations, leaving the execution queue unprocessed and
-- monthly_close never enqueued.
-- ─────────────────────────────────────────────────────────────────────────────

-- Drain pending routine executions every minute
SELECT cron.unschedule(jobid) FROM cron.job WHERE jobname = 'process_pending_routine_executions';

SELECT cron.schedule(
  'process_pending_routine_executions',
  '* * * * *',
  $$ SELECT public.process_pending_routine_executions(); $$
);

-- Enqueue monthly_close check at 23:00 on days 28–31 (function guards last day)
SELECT cron.unschedule(jobid) FROM cron.job WHERE jobname = 'enqueue_monthly_close';

SELECT cron.schedule(
  'enqueue_monthly_close',
  '0 23 28-31 * *',
  $$ SELECT public.enqueue_monthly_close(); $$
);
