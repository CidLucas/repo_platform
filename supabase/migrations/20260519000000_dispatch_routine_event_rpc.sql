-- ─────────────────────────────────────────────────────────────────────────────
-- dispatch_routine_event()
--
-- Server-side helper for event-triggered routines.  Called from Edge Functions
-- (e.g. onboarding-bootstrap) via service-role client after a domain event
-- occurs.  Mirrors the guard logic in Python's _dispatch_execution_sync() so
-- the two code paths stay consistent.
--
-- Guards (in order):
--   1. Routine exists in cross_agent_routines with trigger_type = 'event'
--   2. Client has an active subscription in client_routines
--   3. No in-flight execution already running for this client + routine
--
-- On success: inserts a 'dispatched' execution row and stamps last_run_at.
-- Returns the new execution UUID, or NULL if any guard blocked the dispatch.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.dispatch_routine_event(
  p_routine_id  text,
  p_client_id   uuid,
  p_trigger_data jsonb DEFAULT '{}'::jsonb
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_exec_id       uuid;
  v_now           timestamptz := now();
  v_routine_exists boolean;
  v_subscription  record;
BEGIN
  -- 1. Confirm the routine exists and is event-triggered
  SELECT EXISTS (
    SELECT 1 FROM public.cross_agent_routines
    WHERE id = p_routine_id
      AND trigger_type = 'event'
  ) INTO v_routine_exists;

  IF NOT v_routine_exists THEN
    RAISE WARNING '[dispatch_routine_event] routine % not found or not event-triggered', p_routine_id;
    RETURN NULL;
  END IF;

  -- 2. Confirm the client has an active subscription
  SELECT id INTO v_subscription
  FROM public.client_routines
  WHERE routine_id = p_routine_id
    AND client_id  = p_client_id
    AND active     = true
    AND status     = 'active'
  LIMIT 1;

  IF NOT FOUND THEN
    RAISE WARNING '[dispatch_routine_event] no active subscription for routine % / client %', p_routine_id, p_client_id;
    RETURN NULL;
  END IF;

  -- 3. Guard: skip if an execution is already in-flight for this routine + client
  IF EXISTS (
    SELECT 1 FROM public.client_routine_executions
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND status IN ('pending', 'dispatched', 'executing')
  ) THEN
    RAISE NOTICE '[dispatch_routine_event] in-flight execution exists for routine % / client % — skipping', p_routine_id, p_client_id;
    RETURN NULL;
  END IF;

  -- 4. Insert as dispatched
  INSERT INTO public.client_routine_executions
    (client_id, routine_id, triggered_by, trigger_data, status, dispatched_at)
  VALUES
    (p_client_id, p_routine_id, 'event', p_trigger_data, 'dispatched', v_now)
  RETURNING id INTO v_exec_id;

  -- 5. Stamp last_run_at so pollers don't double-fire
  UPDATE public.client_routines
  SET last_run_at = v_now
  WHERE id = v_subscription.id;

  RETURN v_exec_id;
END;
$$;

-- Only callable by service_role (same posture as claim_routine_executions and
-- dispatch_routine_executions).  JWT-authenticated users must never enqueue
-- executions directly.
REVOKE EXECUTE ON FUNCTION public.dispatch_routine_event(text, uuid, jsonb) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.dispatch_routine_event(text, uuid, jsonb) FROM anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.dispatch_routine_event(text, uuid, jsonb) TO service_role;
