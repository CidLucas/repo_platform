-- Migration: onboarding_bootstrap_tx RPC — atomic tenant provisioning
-- Phase: Landing Onboarding Wire-up, Phase 4 (LaunchPad)
-- Date: 2026-04-23
--
-- Called by supabase/functions/onboarding-bootstrap. Wraps the SQL side of
-- LaunchPad in one transaction so the tenant is either fully provisioned
-- (Context 2.0 columns + enabled agents + routines + completion stamp) or
-- nothing changes.
--
-- SECURITY INVOKER — every write is caller-scoped via RLS
-- (client_enabled_agents, client_routines, clientes_vizu all use
-- public.get_my_client_id()). No service-role bypass here; the edge
-- function uses service role only for the Langfuse HTTP step that
-- happens outside this RPC.
--
-- Idempotent: re-running with the same payload is a no-op
--   * ON CONFLICT DO UPDATE on client_enabled_agents / client_routines
--   * onboarding_completed_at preserved via COALESCE

CREATE OR REPLACE FUNCTION public.onboarding_bootstrap_tx(p_payload jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_client_id         uuid;
  v_company_profile   jsonb;
  v_current_moment    jsonb;
  v_team_structure    jsonb;
  v_policies          jsonb;
  v_available_tools   jsonb;
  v_agents            jsonb;
  v_routines          jsonb;
  v_notify_channel    text;
  v_nome_empresa      text;
  v_agent_count       int := 0;
  v_routine_count     int := 0;
  v_agent             text;
  v_routine           text;
BEGIN
  IF p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object' THEN
    RAISE EXCEPTION 'onboarding_bootstrap_tx: p_payload must be a JSON object';
  END IF;

  -- Resolve tenant via the standard RLS helper. Fail closed.
  SELECT NULLIF(public.get_my_client_id(), '')::uuid INTO v_client_id;
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'onboarding_bootstrap_tx: no tenant for current user';
  END IF;

  -- Unpack sections (all optional; defaults leave column untouched).
  v_company_profile := p_payload -> 'company_profile';
  v_current_moment  := p_payload -> 'current_moment';
  v_team_structure  := p_payload -> 'team_structure';
  v_policies        := p_payload -> 'policies';
  v_available_tools := p_payload -> 'available_tools';
  v_agents          := COALESCE(p_payload -> 'agents', '[]'::jsonb);
  v_routines        := COALESCE(p_payload -> 'routines', '[]'::jsonb);
  v_notify_channel  := COALESCE(p_payload ->> 'notify_channel', 'email');
  v_nome_empresa    := p_payload ->> 'nome_empresa';

  -- 1. UPDATE clientes_vizu with Context 2.0 sections + completion stamp.
  UPDATE public.clientes_vizu
     SET company_profile         = COALESCE(v_company_profile, company_profile),
         current_moment          = COALESCE(v_current_moment,  current_moment),
         team_structure          = COALESCE(v_team_structure,  team_structure),
         policies                = COALESCE(v_policies,        policies),
         available_tools         = COALESCE(v_available_tools, available_tools),
         nome_empresa            = COALESCE(v_nome_empresa,    nome_empresa),
         onboarding_completed_at = COALESCE(onboarding_completed_at, now()),
         updated_at              = now()
   WHERE client_id = v_client_id;

  -- 2. UPSERT client_enabled_agents. Validate each slug against
  --    agent_catalog via FK (any drift fails the TX).
  FOR v_agent IN
    SELECT jsonb_array_elements_text(v_agents)
  LOOP
    INSERT INTO public.client_enabled_agents (
      client_id, agent_slug, enabled, source
    ) VALUES (
      v_client_id, v_agent, true, 'onboarding'
    )
    ON CONFLICT (client_id, agent_slug)
    DO UPDATE SET enabled = true;
    v_agent_count := v_agent_count + 1;
  END LOOP;

  -- 3. UPSERT client_routines. Notify channel is a single value for the
  --    whole wizard — every routine inherits it unless overridden later.
  FOR v_routine IN
    SELECT jsonb_array_elements_text(v_routines)
  LOOP
    INSERT INTO public.client_routines (
      client_id, routine_id, enabled, notify_channel
    ) VALUES (
      v_client_id, v_routine, true, v_notify_channel
    )
    ON CONFLICT (client_id, routine_id)
    DO UPDATE SET enabled        = true,
                  notify_channel = EXCLUDED.notify_channel,
                  updated_at     = now();
    v_routine_count := v_routine_count + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'client_id',     v_client_id,
    'agents',        v_agent_count,
    'routines',      v_routine_count
  );
END;
$$;

COMMENT ON FUNCTION public.onboarding_bootstrap_tx(jsonb) IS
  'Atomic LaunchPad provisioning: Context 2.0 sections + enabled agents + routines + '
  'onboarding_completed_at. Called by supabase/functions/onboarding-bootstrap. '
  'SECURITY INVOKER — all writes caller-scoped via RLS. Idempotent.';

GRANT EXECUTE ON FUNCTION public.onboarding_bootstrap_tx(jsonb) TO authenticated;
