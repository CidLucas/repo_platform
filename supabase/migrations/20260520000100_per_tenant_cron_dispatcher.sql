-- ─────────────────────────────────────────────────────────────────────────────
-- INF-01 · Per-tenant cron dispatcher
--
-- dispatch_routine_executions() evaluates each active client_routines row
-- with trigger_type IN ('cron','schedule') and enqueues an execution when
-- the client's configured cron expression is due.
--
-- Design:
--   • Each client may override the catalog expression via
--     client_routines.trigger_config->>'expression'.
--   • "Due" = next_run(expr, last_run_at) <= now().
--   • First-time enable (last_run_at IS NULL): stamp last_run_at = now()
--     so the first fire happens at the next proper interval.
--   • In-flight guard: skip if a 'pending'/'dispatched'/'executing' execution
--     already exists for this client + routine.
--   • Stamp last_run_at immediately when enqueueing to prevent double-fire
--     within the same dispatcher tick.
--
-- Called by pg_cron every minute (job registered below).
-- The Python TriggerPoller (routines.py _check_cron_routines) remains the
-- primary scheduler; this SQL dispatcher is a resilience fallback and is
-- intentionally idempotent with the Python path.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.dispatch_routine_executions()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_cr        record;
  v_car       record;
  v_expr      text;
  v_last_run  timestamptz;
  v_now       timestamptz := now();
  v_enqueued  integer := 0;
  v_exec_id   uuid;
BEGIN
  FOR v_cr IN
    SELECT cr.id,
           cr.client_id,
           cr.routine_id,
           cr.trigger_config,
           cr.last_run_at
    FROM   public.client_routines cr
    WHERE  cr.trigger_type IN ('cron', 'schedule')
      AND  cr.active  = true
      AND  cr.status  = 'active'
    ORDER BY cr.last_run_at NULLS FIRST
  LOOP
    -- Resolve expression: per-client override first, then catalog default
    v_expr := coalesce(
      v_cr.trigger_config->>'expression',
      (
        SELECT trigger_config->>'expression'
        FROM   public.cross_agent_routines
        WHERE  id = v_cr.routine_id
        LIMIT  1
      )
    );

    IF v_expr IS NULL OR v_expr = '' THEN
      CONTINUE;
    END IF;

    v_last_run := v_cr.last_run_at;

    -- First-time enable: stamp last_run_at = now so the next fire is correct
    IF v_last_run IS NULL THEN
      UPDATE public.client_routines
        SET last_run_at = v_now
      WHERE id = v_cr.id;
      CONTINUE;
    END IF;

    -- Check if the next scheduled run is due.
    -- cron_next_after() is provided by the pg_cron extension on Supabase.
    -- If the function is not available, fall back to a 1-minute window check
    -- against the catalog's default expression granularity.
    BEGIN
      IF cron.next_run_time(v_expr, v_last_run) > v_now THEN
        CONTINUE;  -- not due yet
      END IF;
    EXCEPTION WHEN undefined_function OR invalid_schema_name THEN
      -- pg_cron helper not available — use simple interval fallback:
      -- treat any expression as "fire once per minute at minimum"
      IF v_last_run > v_now - interval '55 seconds' THEN
        CONTINUE;
      END IF;
    END;

    -- In-flight guard: skip if an execution is already running
    IF EXISTS (
      SELECT 1
      FROM   public.client_routine_executions
      WHERE  client_id  = v_cr.client_id
        AND  routine_id = v_cr.routine_id
        AND  status IN ('pending', 'dispatched', 'executing')
    ) THEN
      CONTINUE;
    END IF;

    -- Enqueue a dispatched execution
    INSERT INTO public.client_routine_executions
      (client_id, routine_id, triggered_by, trigger_data, status, dispatched_at)
    VALUES
      (v_cr.client_id, v_cr.routine_id, 'cron',
       jsonb_build_object('expression', v_expr),
       'dispatched', v_now)
    RETURNING id INTO v_exec_id;

    -- Stamp last_run_at to prevent double-fire in the same tick
    UPDATE public.client_routines
      SET last_run_at = v_now
    WHERE id = v_cr.id;

    v_enqueued := v_enqueued + 1;

    RAISE NOTICE '[dispatch_routine_executions] enqueued routine=% client=% exec=%',
      v_cr.routine_id, v_cr.client_id, v_exec_id;
  END LOOP;

  RETURN v_enqueued;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.dispatch_routine_executions() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.dispatch_routine_executions() FROM anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.dispatch_routine_executions() TO service_role;

-- ─────────────────────────────────────────────────────────────────────────────
-- pg_cron job: run the SQL dispatcher every minute alongside the ETL jobs.
-- The Python TriggerPoller also runs per-tick; both paths are idempotent.
-- ─────────────────────────────────────────────────────────────────────────────

SELECT cron.schedule(
  'dispatch_routine_executions',
  '* * * * *',
  $$ SELECT public.dispatch_routine_executions(); $$
);
