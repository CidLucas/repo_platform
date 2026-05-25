-- =============================================================================
-- P1 Anti-entupimento: heartbeat_at + failure_count + status suspended
-- =============================================================================

-- 1. Colunas novas em client_routine_executions
-- ---------------------------------------------------------------------------
ALTER TABLE public.client_routine_executions
  ADD COLUMN IF NOT EXISTS heartbeat_at   timestamptz DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS failure_count  int         DEFAULT 0 NOT NULL;

-- Índice para heartbeat-based reaper (requer heartbeat_at NOT NULL)
CREATE INDEX IF NOT EXISTS idx_routine_exec_heartbeat
  ON public.client_routine_executions (heartbeat_at)
  WHERE status = 'dispatched' AND heartbeat_at IS NOT NULL;

-- 2. Coluna failure_count em client_routines (para circuit breaker)
-- ---------------------------------------------------------------------------
ALTER TABLE public.client_routines
  ADD COLUMN IF NOT EXISTS consecutive_failures int DEFAULT 0 NOT NULL;

-- 3. Atualizar reaper para usar heartbeat_at quando disponível
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.reap_stale_routine_executions()
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $reaper$
DECLARE
  _reaped        int;
  _no_heartbeat  interval := interval '10 minutes';  -- sem nenhum sinal
  _dead_heartbeat interval := interval '5 minutes';  -- heartbeat parou
BEGIN
  UPDATE public.client_routine_executions
  SET
    status       = 'failed',
    result_text  = 'timeout: execução travada (reaper)',
    completed_at = now()
  WHERE status = 'dispatched'
    AND (
      -- Sem heartbeat: usa dispatched_at como referência
      (heartbeat_at IS NULL AND dispatched_at < now() - _no_heartbeat)
      OR
      -- Com heartbeat: heartbeat parou de atualizar
      (heartbeat_at IS NOT NULL AND heartbeat_at < now() - _dead_heartbeat)
    );

  GET DIAGNOSTICS _reaped = ROW_COUNT;

  IF _reaped > 0 THEN
    RAISE NOTICE '[reap_stale] Reaped % execution(s)', _reaped;
  END IF;

  RETURN _reaped;
END;
$reaper$;

-- 4. Função circuit breaker: incrementa falhas e suspende se >= max_failures
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.record_routine_failure(
  p_client_id  uuid,
  p_routine_id text,
  p_max_failures int DEFAULT 3
)
RETURNS text   -- retorna novo status: 'active' | 'suspended'
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $cb$
DECLARE
  _new_failures int;
  _new_status   text;
BEGIN
  UPDATE public.client_routines
  SET consecutive_failures = consecutive_failures + 1
  WHERE client_id = p_client_id
    AND routine_id = p_routine_id
  RETURNING consecutive_failures INTO _new_failures;

  IF _new_failures IS NULL THEN
    RETURN 'not_found';
  END IF;

  IF _new_failures >= p_max_failures THEN
    UPDATE public.client_routines
    SET status = 'suspended', active = false
    WHERE client_id = p_client_id
      AND routine_id = p_routine_id;
    _new_status := 'suspended';
    RAISE NOTICE '[circuit_breaker] routine % client % suspended after % failures',
      p_routine_id, p_client_id, _new_failures;
  ELSE
    _new_status := 'active';
  END IF;

  RETURN _new_status;
END;
$cb$;

-- Função de reset: após intervenção manual reativa a rotina
CREATE OR REPLACE FUNCTION public.reset_routine_failures(
  p_client_id  uuid,
  p_routine_id text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $reset$
BEGIN
  UPDATE public.client_routines
  SET consecutive_failures = 0,
      status = 'active',
      active = true
  WHERE client_id = p_client_id
    AND routine_id = p_routine_id;
END;
$reset$;

REVOKE EXECUTE ON FUNCTION public.record_routine_failure(uuid, text, int) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.record_routine_failure(uuid, text, int) TO service_role;

REVOKE EXECUTE ON FUNCTION public.reset_routine_failures(uuid, text) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.reset_routine_failures(uuid, text) TO service_role;

-- 5. Adicionar 'suspended' como valor documentado (sem ENUM — já é text)
-- Comentário na tabela para deixar contrato claro
COMMENT ON COLUMN public.client_routines.status IS
  'Valores: active | inactive | suspended. '
  'suspended = circuit breaker ativado (>= 3 falhas consecutivas). '
  'Resetar com SELECT public.reset_routine_failures(client_id, routine_id).';

COMMENT ON COLUMN public.client_routine_executions.heartbeat_at IS
  'Atualizado pelo agent_api a cada step do grafo. '
  'Reaper usa este campo para detectar execuções travadas com mais precisão.';

COMMENT ON COLUMN public.client_routine_executions.failure_count IS
  'Número de tentativas falhadas desta execução específica (para retry futuro).';
