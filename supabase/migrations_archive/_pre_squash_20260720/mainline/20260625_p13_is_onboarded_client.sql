-- ============================================================================
-- P13: RPC is_onboarded_client + backfill clientes existentes
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.is_onboarded_client()
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_client_id     uuid := public.get_my_client_id();
  v_completed_at  timestamptz;
  v_created_at    timestamptz;
BEGIN
  IF v_client_id IS NULL THEN
    RETURN false;
  END IF;

  -- Sinal 1: onboarding explicitamente completado
  SELECT onboarding_completed_at, created_at
  INTO   v_completed_at, v_created_at
  FROM   public.clientes_blu
  WHERE  client_id = v_client_id;

  IF v_completed_at IS NOT NULL THEN
    RETURN true;
  END IF;

  -- Sinal 2: cliente possui fontes de dados conectadas
  IF EXISTS (
    SELECT 1 FROM public.client_data_sources
    WHERE  client_id = v_client_id
    LIMIT  1
  ) THEN
    RETURN true;
  END IF;

  -- Sinal 3: agentes configurados E conta existe ha mais de 1 hora
  IF v_created_at IS NOT NULL
     AND v_created_at < now() - interval '1 hour'
     AND EXISTS (
       SELECT 1 FROM public.client_enabled_agents
       WHERE  client_id = v_client_id
       LIMIT  1
     )
  THEN
    RETURN true;
  END IF;

  RETURN false;
END;
$$;

REVOKE ALL ON FUNCTION public.is_onboarded_client() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.is_onboarded_client() FROM anon;
GRANT  EXECUTE ON FUNCTION public.is_onboarded_client() TO authenticated, service_role;

COMMENT ON FUNCTION public.is_onboarded_client() IS
  'Retorna true se o cliente JWT atual deve ser considerado onboarded. Usa onboarding_completed_at, data_sources, e enabled_agents como sinais. Centraliza a logica para evitar duplicacao frontend/backend.';

-- Backfill: marcar onboarding_completed_at para clientes existentes ativos
UPDATE public.clientes_blu cb
SET    onboarding_completed_at = LEAST(
         cb.created_at + interval '1 hour',
         now()
       ),
       updated_at = now()
WHERE  cb.onboarding_completed_at IS NULL
  AND  (
    EXISTS (SELECT 1 FROM public.client_data_sources cds WHERE cds.client_id = cb.client_id)
    OR
    (
      cb.created_at < now() - interval '1 hour'
      AND EXISTS (SELECT 1 FROM public.client_enabled_agents cea WHERE cea.client_id = cb.client_id)
    )
  );

COMMIT;
