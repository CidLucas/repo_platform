-- =============================================================================
-- Fix: client_routines trigger_type inheritance from catalog.
--
-- Root cause: new client_routines subscriptions default to trigger_type='manual'
-- regardless of the catalog routine's trigger_type. This means:
--   • The SQL dispatcher (checks cr.trigger_type IN ('cron','schedule')) skips them.
--   • The schedule pills in the UI are hidden (effectiveTriggerType === 'manual').
--   • Routines never fire automatically even when the catalog says 'cron'.
--
-- This migration:
--   1. Extends client_routines.trigger_type check to allow 'cron' (was only
--      'schedule', 'manual', 'document', 'event', 'numeric').
--   2. Backfills existing client_routines rows that still have trigger_type='manual'
--      to inherit trigger_type+trigger_config from their catalog routine.
--   3. Updates onboarding_bootstrap_tx() to copy trigger_type/config from the
--      catalog when creating subscriptions.
-- =============================================================================

-- ── 1. Extend trigger_type check constraint in client_routines ────────────────
-- Allow 'cron' alongside the existing values so the catalog value can be stored
-- directly on the client row without a lossy 'cron' → 'schedule' mapping.
ALTER TABLE public.client_routines
  DROP CONSTRAINT IF EXISTS client_routines_trigger_type_check;

ALTER TABLE public.client_routines
  ADD CONSTRAINT client_routines_trigger_type_check
  CHECK (trigger_type IN ('manual', 'document', 'schedule', 'cron', 'event', 'numeric'));

-- ── 2. Backfill existing rows that were stuck at 'manual' ────────────────────
-- Only updates rows where:
--   a) client's trigger_type is 'manual' (not a custom override), and
--   b) a catalog routine exists with a non-manual trigger_type.
-- Preserves existing client overrides for trigger_config.
UPDATE public.client_routines cr
SET
  trigger_type   = car.trigger_type,
  trigger_config = CASE
    WHEN cr.trigger_config = '{}'::jsonb OR cr.trigger_config IS NULL
    THEN car.trigger_config
    ELSE cr.trigger_config
  END
FROM public.cross_agent_routines car
WHERE cr.routine_id    = car.id
  AND cr.trigger_type  = 'manual'
  AND car.trigger_type != 'manual';

-- ── 3. Update onboarding_bootstrap_tx to inherit catalog trigger settings ─────
CREATE OR REPLACE FUNCTION public.onboarding_bootstrap_tx(p_payload jsonb)
  RETURNS jsonb
  LANGUAGE plpgsql
  SET search_path TO 'public', 'pg_temp'
AS $function$
DECLARE
  v_client_id   uuid := public.get_my_client_id();
  v_agent_slug  text;
  v_routine_id  text;
  v_agents_ct   integer := 0;
  v_routines_ct integer := 0;
  v_notify      text;
  v_cat_trigger text;
  v_cat_config  jsonb;
BEGIN
  -- Provision the tenant row on first onboarding if it doesn't exist yet.
  IF v_client_id IS NULL THEN
    INSERT INTO public.clientes_blu (external_user_id, api_key, nome_empresa, created_at, updated_at)
    VALUES (
      (auth.jwt() ->> 'sub'),
      gen_random_uuid()::text,
      COALESCE(NULLIF(trim(p_payload->>'nome_empresa'), ''), 'Empresa'),
      now(),
      now()
    )
    ON CONFLICT (external_user_id) DO NOTHING
    RETURNING client_id INTO v_client_id;

    -- Handle race: row existed by the time we inserted
    IF v_client_id IS NULL THEN
      SELECT client_id INTO v_client_id
      FROM public.clientes_blu
      WHERE external_user_id = (auth.jwt() ->> 'sub');
    END IF;

    IF v_client_id IS NULL THEN
      RAISE EXCEPTION 'Failed to provision tenant for user %', (auth.jwt() ->> 'sub');
    END IF;
  END IF;

  v_notify := COALESCE(p_payload->>'notify_channel', 'app');

  UPDATE public.clientes_blu SET
    nome_empresa            = COALESCE(NULLIF(trim(p_payload->>'nome_empresa'), ''), nome_empresa),
    cpf_cnpj                = COALESCE(NULLIF(trim(p_payload->>'cnpj'), ''),        cpf_cnpj),
    company_profile         = COALESCE(p_payload->'company_profile', company_profile),
    team_structure          = COALESCE(p_payload->'team_structure', team_structure),
    policies                = COALESCE(p_payload->'policies', policies),
    onboarding_completed_at = COALESCE(onboarding_completed_at, now()),
    updated_at              = now()
  WHERE client_id = v_client_id;

  FOR v_agent_slug IN SELECT jsonb_array_elements_text(p_payload->'agents') LOOP
    INSERT INTO public.client_enabled_agents (client_id, agent_slug)
    VALUES (v_client_id, v_agent_slug)
    ON CONFLICT (client_id, agent_slug) DO NOTHING;
    v_agents_ct := v_agents_ct + 1;
  END LOOP;

  FOR v_routine_id IN SELECT jsonb_array_elements_text(p_payload->'routines') LOOP
    -- Look up catalog trigger settings so new subscriptions are ready to fire.
    SELECT trigger_type, trigger_config
    INTO   v_cat_trigger, v_cat_config
    FROM   public.cross_agent_routines
    WHERE  id = v_routine_id;

    -- Fallback for custom routines not in the catalog.
    v_cat_trigger := COALESCE(v_cat_trigger, 'manual');
    v_cat_config  := COALESCE(v_cat_config,  '{}'::jsonb);

    -- Always ensure the routine is active after onboarding (re-onboarding
    -- must not leave rows stuck as inactive from a previous attempt).
    -- On conflict: reset active/status, preserve existing trigger customisation
    -- (don't override a client who already changed their schedule).
    INSERT INTO public.client_routines
      (client_id, routine_id, notify_channel, active, status, trigger_type, trigger_config)
    VALUES
      (v_client_id, v_routine_id, v_notify, true, 'active', v_cat_trigger, v_cat_config)
    ON CONFLICT (client_id, routine_id) DO UPDATE SET
      notify_channel = EXCLUDED.notify_channel,
      active         = true,
      status         = 'active',
      -- Only inherit catalog values when the client row still has defaults
      -- (preserve deliberate client overrides).
      trigger_type   = CASE
        WHEN client_routines.trigger_type = 'manual'
        THEN EXCLUDED.trigger_type
        ELSE client_routines.trigger_type
      END,
      trigger_config = CASE
        WHEN client_routines.trigger_config = '{}'::jsonb
        THEN EXCLUDED.trigger_config
        ELSE client_routines.trigger_config
      END;

    v_routines_ct := v_routines_ct + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'client_id', v_client_id,
    'agents',    v_agents_ct,
    'routines',  v_routines_ct
  );
END;
$function$;
