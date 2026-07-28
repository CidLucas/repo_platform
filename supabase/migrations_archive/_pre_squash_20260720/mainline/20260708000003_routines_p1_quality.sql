-- P1 quality fixes for the routines system (diagnóstico 2026-07-08)
--
-- P1-6 (F7): per-client timezone for cron evaluation.
--   The poller (_check_cron_routines) now evaluates cron expressions in the
--   client's timezone: trigger_config.timezone (per subscription, JSONB — no
--   schema change needed) > clientes_blu.timezone > 'America/Sao_Paulo'.
--
-- P1-5 (F4): execution status 'partial' — soft-failed steps (on_failure=continue,
--   skill without structured output) no longer hide behind 'completed'.
--   Baseline has no CHECK on client_routine_executions.status; the DO block only
--   rewrites a constraint if prod drifted and has one.
--
-- P1-7 (F9): unschedule the legacy pg_cron job process_pending_routine_executions
--   (jobid 5 in prod). It converts 'pending' executions into approval_requests
--   using legacy step keys (action/agent) that catalog steps don't have — any
--   execution entering as 'pending' today becomes a malformed approval request.
--   The function itself is kept (unscheduled) for rollback.

-- ── P1-6: client timezone ───────────────────────────────────────────────────
ALTER TABLE public.clientes_blu
  ADD COLUMN IF NOT EXISTS timezone text NOT NULL DEFAULT 'America/Sao_Paulo';

COMMENT ON COLUMN public.clientes_blu.timezone IS
  'IANA timezone used to evaluate cron routine schedules (P1-6). Per-subscription override: client_routines.trigger_config->>timezone.';

-- ── P1-5: allow status 'partial' if a CHECK constraint exists (drift-safe) ──
DO $$
DECLARE
  _con record;
  _found boolean := false;
BEGIN
  FOR _con IN
    SELECT conname
    FROM pg_constraint
    WHERE conrelid = 'public.client_routine_executions'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) ILIKE '%status%'
  LOOP
    _found := true;
    EXECUTE format('ALTER TABLE public.client_routine_executions DROP CONSTRAINT %I', _con.conname);
  END LOOP;

  IF _found THEN
    EXECUTE $c$
      ALTER TABLE public.client_routine_executions
        ADD CONSTRAINT client_routine_executions_status_check
        CHECK (status IN ('pending','dispatched','executing','completed','failed','partial','awaiting_approval'))
        NOT VALID
    $c$;
  END IF;
END $$;

-- ── P1-7: disarm the legacy pending→approval_requests converter ─────────────
DO $$
DECLARE
  _jid bigint;
BEGIN
  SELECT jobid INTO _jid
  FROM cron.job
  WHERE jobname = 'process_pending_routine_executions'
     OR command ILIKE '%process_pending_routine_executions%'
  LIMIT 1;

  IF _jid IS NOT NULL THEN
    PERFORM cron.unschedule(_jid);
    RAISE NOTICE 'Unscheduled legacy pg_cron job % (process_pending_routine_executions)', _jid;
  ELSE
    RAISE NOTICE 'Legacy job process_pending_routine_executions not found — nothing to unschedule';
  END IF;
END $$;
