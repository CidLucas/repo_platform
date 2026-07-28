-- ============================================================================
-- Fix: onboarding não dispara a rotina onboarding_complete
-- ----------------------------------------------------------------------------
-- Causa raiz (produção):
--   1. `onboarding_complete` estava com visibility='user' → auto_enroll_catalog
--      cria client_routines com active=false/status='inactive'. Como
--      dispatch_routine_event() exige subscription active+'active', o dispatch
--      sempre retornava NULL ("no active subscription"). A migration 20260603
--      pretendia visibility='system'; algo reverteu em prod.
--   2. finalize_onboarding() (única via de dispatch pós-P12) dependia dessa
--      subscription já estar ativa.
--
-- Correção:
--   A. Restaura visibility='system' no catálogo (estado pretendido).
--   B. finalize_onboarding() passa a GARANTIR uma subscription ativa da rotina
--      de sistema onboarding_complete (upsert active) ANTES de disparar —
--      desacoplando o dispatch do caminho de enrollment/visibility.
--   C. Backfill: ativa subscriptions onboarding_complete já existentes.
--
-- NOTA: o fix de frontend (chamar supabase.rpc('finalize_onboarding') ao final
-- do onboarding) é complementar e vive em apps/blu_v3.
-- ============================================================================

-- A. Restaura visibility de sistema no catálogo -----------------------------
UPDATE public.cross_agent_routines
SET visibility = 'system'
WHERE id = 'onboarding_complete'
  AND visibility IS DISTINCT FROM 'system';

-- B. finalize_onboarding robusta --------------------------------------------
CREATE OR REPLACE FUNCTION public.finalize_onboarding()
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO 'public', 'pg_temp'
AS $function$
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
      -- Garante subscription ativa para a rotina de sistema onboarding_complete
      -- ANTES do dispatch. dispatch_routine_event() exige active+'active';
      -- não podemos depender do enrollment (visibility) ter deixado ativo.
      INSERT INTO public.client_routines
        (client_id, routine_id, notify_channel, active, status, source, trigger_type, trigger_config)
      SELECT
        v_client_id, r.id, 'app', true, 'active', 'system', r.trigger_type, r.trigger_config
      FROM public.cross_agent_routines r
      WHERE r.id = 'onboarding_complete'
      ON CONFLICT (client_id, routine_id) DO UPDATE SET
        active = true,
        status = 'active';

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
$function$;

REVOKE ALL ON FUNCTION public.finalize_onboarding() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.finalize_onboarding() FROM anon;
GRANT  EXECUTE ON FUNCTION public.finalize_onboarding() TO authenticated, service_role;

-- C. Backfill: ativa subscriptions onboarding_complete existentes -----------
UPDATE public.client_routines
SET active = true,
    status = 'active',
    source = 'system'
WHERE routine_id = 'onboarding_complete'
  AND (active = false OR status <> 'active');
