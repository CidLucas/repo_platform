-- ─────────────────────────────────────────────────────────────────────────────
-- fire_event_for_client()
--
-- Routes a domain event to every catalog routine that is subscribed to that
-- event type for a given client.  Built on top of dispatch_routine_event() so
-- all existing guards (active subscription, in-flight check, last_run_at
-- stamp) are enforced automatically.
--
-- Optional per-client category filter:
--   If client_routines.trigger_config->>'category' is set, the event is only
--   dispatched when p_trigger_data->>'category' matches it.  A NULL or absent
--   filter means "fire on any category".
--
-- Returns the number of executions actually dispatched (0 if all guards
-- blocked or no subscriptions found).
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.fire_event_for_client(
  p_event_type   text,
  p_client_id    uuid,
  p_trigger_data jsonb DEFAULT '{}'::jsonb
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_count            integer := 0;
  v_exec_id          uuid;
  r                  record;
  v_category_filter  text;
  v_incoming_category text;
BEGIN
  v_incoming_category := p_trigger_data->>'category';

  -- Find all catalog routines matching this event type that the client is
  -- actively subscribed to.
  FOR r IN
    SELECT
      car.id            AS routine_id,
      cr.trigger_config AS client_trigger_config
    FROM public.cross_agent_routines car
    JOIN public.client_routines cr
      ON  cr.routine_id = car.id
      AND cr.client_id  = p_client_id
      AND cr.active     = true
      AND cr.status     = 'active'
    WHERE car.trigger_type              = 'event'
      AND car.trigger_config->>'event_type' = p_event_type
  LOOP
    -- Apply optional per-client category filter
    v_category_filter := r.client_trigger_config->>'category';

    IF v_category_filter IS NOT NULL
       AND v_category_filter <> ''
       AND v_category_filter IS DISTINCT FROM v_incoming_category
    THEN
      CONTINUE;  -- category mismatch — skip this subscription
    END IF;

    -- Dispatch (all remaining guards are inside dispatch_routine_event)
    v_exec_id := public.dispatch_routine_event(r.routine_id, p_client_id, p_trigger_data);
    IF v_exec_id IS NOT NULL THEN
      v_count := v_count + 1;
    END IF;
  END LOOP;

  RETURN v_count;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.fire_event_for_client(text, uuid, jsonb) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.fire_event_for_client(text, uuid, jsonb) FROM anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.fire_event_for_client(text, uuid, jsonb) TO service_role;
