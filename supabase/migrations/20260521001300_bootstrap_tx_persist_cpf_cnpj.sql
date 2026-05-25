-- ─────────────────────────────────────────────────────────────────────────────
-- FASE 2 · onboarding_bootstrap_tx: persist cpf_cnpj
--
-- Adds cpf_cnpj to the UPDATE so the CNPJ collected in StepInfo is written
-- to clientes_blu immediately at bootstrap time.
-- Only overwrites if the incoming value is non-null (NULLIF guard).
-- ─────────────────────────────────────────────────────────────────────────────

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
BEGIN
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
    INSERT INTO public.client_routines (client_id, routine_id, notify_channel)
    VALUES (v_client_id, v_routine_id, v_notify)
    ON CONFLICT (client_id, routine_id) DO UPDATE SET notify_channel = EXCLUDED.notify_channel;
    v_routines_ct := v_routines_ct + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'client_id', v_client_id,
    'agents',    v_agents_ct,
    'routines',  v_routines_ct
  );
END;
$function$;
