-- ============================================================================
-- Onboarding completion split: bootstrap ≠ finalize
-- ============================================================================
-- Antes:
--   onboarding_bootstrap_tx marcava onboarding_completed_at = now() já no
--   passo Dados (step 3). Isso fazia o reload pós-step3 entregar o cliente ao
--   app mesmo sem o Mapeamento (step 4) — perdíamos o sinal de quem ainda não
--   ligou dados.
--
-- Depois:
--   1. onboarding_bootstrap_tx NÃO toca em onboarding_completed_at.
--   2. Nova RPC public.finalize_onboarding() é chamada pelo frontend no
--      submit do passo 4 (Mapeamento), depois do mapping_confirmed=true e do
--      kickoff do ETL. Ela:
--        - seta onboarding_completed_at = now() (idempotente: COALESCE)
--        - dispara a routine onboarding_complete (mesma chamada que estava
--          em waitUntil na edge function — agora é síncrona, dentro da RPC,
--          via dispatch_routine_event SECDEF se existir)
--
-- Cliente que pular o Mapeamento fica com onboarding_completed_at = NULL →
-- o frontend o devolve ao step 'info'/'data'/'mapping' a cada login, e o
-- backoffice consegue listar "onboardings incompletos" trivialmente:
--   SELECT client_id, created_at FROM clientes_blu
--   WHERE onboarding_completed_at IS NULL ORDER BY created_at DESC;
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. onboarding_bootstrap_tx — REMOVER set de onboarding_completed_at
-- ----------------------------------------------------------------------------
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
    -- NOTE: onboarding_completed_at é setado SÓ por finalize_onboarding()
    -- após o passo 4 (Mapeamento). Não tocar aqui.
    updated_at              = now()
  WHERE client_id = v_client_id;

  FOR v_agent_slug IN SELECT jsonb_array_elements_text(p_payload->'agents') LOOP
    INSERT INTO public.client_enabled_agents (client_id, agent_slug)
    VALUES (v_client_id, v_agent_slug)
    ON CONFLICT (client_id, agent_slug) DO NOTHING;
    v_agents_ct := v_agents_ct + 1;
  END LOOP;

  FOR v_routine_id IN SELECT jsonb_array_elements_text(p_payload->'routines') LOOP
    SELECT trigger_type, trigger_config
    INTO   v_cat_trigger, v_cat_config
    FROM   public.cross_agent_routines
    WHERE  id = v_routine_id;

    v_cat_trigger := COALESCE(v_cat_trigger, 'manual');
    v_cat_config  := COALESCE(v_cat_config,  '{}'::jsonb);

    INSERT INTO public.client_routines
      (client_id, routine_id, notify_channel, active, status, trigger_type, trigger_config)
    VALUES
      (v_client_id, v_routine_id, v_notify, true, 'active', v_cat_trigger, v_cat_config)
    ON CONFLICT (client_id, routine_id) DO UPDATE SET
      notify_channel = EXCLUDED.notify_channel,
      active         = true,
      status         = 'active',
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

-- ----------------------------------------------------------------------------
-- 2. finalize_onboarding — chamada pelo frontend após Mapeamento confirmado
-- ----------------------------------------------------------------------------
-- SECURITY INVOKER + RLS: a UPDATE em clientes_blu passa pelas policies
-- existentes (tenant_isolation), então só atinge o próprio client_id do JWT.
-- Idempotente: COALESCE preserva onboarding_completed_at se já setado.
CREATE OR REPLACE FUNCTION public.finalize_onboarding()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_client_id      uuid := public.get_my_client_id();
  v_completed_at   timestamptz;
  v_was_already    boolean := false;
  v_dispatch_exec  uuid;
BEGIN
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'finalize_onboarding: no client_id for caller (JWT sub=%)', (auth.jwt() ->> 'sub');
  END IF;

  SELECT onboarding_completed_at INTO v_completed_at
  FROM public.clientes_blu
  WHERE client_id = v_client_id;

  IF v_completed_at IS NOT NULL THEN
    v_was_already := true;
  ELSE
    UPDATE public.clientes_blu
       SET onboarding_completed_at = now(),
           updated_at = now()
     WHERE client_id = v_client_id
       AND onboarding_completed_at IS NULL
    RETURNING onboarding_completed_at INTO v_completed_at;
  END IF;

  -- Dispara routine onboarding_complete (best-effort). Antes era waitUntil
  -- na edge function, mas o frontend timeoutava no seed Langfuse e o
  -- waitUntil era abortado. Síncrono aqui resolve.
  IF NOT v_was_already THEN
    BEGIN
      SELECT public.dispatch_routine_event(
        'onboarding_complete',
        v_client_id,
        jsonb_build_object('event_type', 'onboarding_completed')
      ) INTO v_dispatch_exec;
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'finalize_onboarding: dispatch_routine_event failed for %: %', v_client_id, SQLERRM;
    END;
  END IF;

  RETURN jsonb_build_object(
    'client_id', v_client_id,
    'onboarding_completed_at', v_completed_at,
    'was_already_completed', v_was_already,
    'routine_execution_id', v_dispatch_exec
  );
END;
$$;

REVOKE ALL ON FUNCTION public.finalize_onboarding() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.finalize_onboarding() FROM anon;
GRANT  EXECUTE ON FUNCTION public.finalize_onboarding() TO authenticated, service_role;

COMMENT ON FUNCTION public.finalize_onboarding() IS
  'Marca o onboarding como concluído (clientes_blu.onboarding_completed_at) e dispara a routine onboarding_complete. Chamada pelo frontend no submit do passo 4 (Mapeamento). Idempotente.';

COMMIT;

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================
-- 1. Função criada e RLS-scoped:
--    SELECT prosecdef, proacl FROM pg_proc WHERE proname='finalize_onboarding';
-- 2. Bootstrap não toca mais o campo:
--    \df+ public.onboarding_bootstrap_tx
-- 3. Listar incompletos pro backoffice:
--    SELECT client_id, nome_empresa, created_at
--    FROM public.clientes_blu
--    WHERE onboarding_completed_at IS NULL
--    ORDER BY created_at DESC;
