-- =============================================================================
-- P0 Anti-entupimento: pg_net timeout + stale execution reaper + índice parcial
-- =============================================================================

-- 1. Adicionar timeout_milliseconds no dispatch (30s) e statement_timeout no role
-- ---------------------------------------------------------------------------

-- statement_timeout para service_role: queries pesadas morrem em 120s
ALTER ROLE authenticator SET statement_timeout = '120s';

-- 2. Recriar dispatch_routine_executions com timeout_milliseconds
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.dispatch_routine_executions()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  _url   text;
  _token text;
BEGIN
  SELECT value INTO _url
  FROM public.app_config
  WHERE key IN ('agent_api_core_url', 'atendente_core_url')
  ORDER BY (key = 'agent_api_core_url') DESC
  LIMIT 1;

  SELECT value INTO _token
  FROM public.app_config
  WHERE key IN ('agent_api_routine_dispatch_token', 'routine_dispatch_token')
  ORDER BY (key = 'agent_api_routine_dispatch_token') DESC
  LIMIT 1;

  IF _url IS NULL OR _token IS NULL THEN
    RAISE WARNING '[dispatch_routine_executions] app settings not configured — skipping';
    RETURN;
  END IF;

  PERFORM net.http_post(
    url                  := _url || '/internal/routines/run-dispatched',
    headers              := jsonb_build_object(
      'Content-Type',  'application/json',
      'Authorization', 'Bearer ' || _token
    ),
    body                 := '{}'::jsonb,
    timeout_milliseconds := 30000   -- P0: nunca pendurar além de 30s
  );
END;
$function$;

-- 3. Índice parcial para o reaper (pesquisa só em rows dispatched)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_routine_exec_stale
  ON public.client_routine_executions (dispatched_at)
  WHERE status = 'dispatched';

-- 4. Função reaper: converte execuções travadas em 'failed'
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.reap_stale_routine_executions()
RETURNS int
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $reaper$
DECLARE
  _reaped int;
  _stale_threshold interval := interval '10 minutes';
BEGIN
  UPDATE public.client_routine_executions
  SET
    status       = 'failed',
    result_text  = 'timeout: execução sem resposta por mais de 10 minutos (reaper)',
    completed_at = now()
  WHERE status = 'dispatched'
    AND dispatched_at < now() - _stale_threshold;

  GET DIAGNOSTICS _reaped = ROW_COUNT;

  IF _reaped > 0 THEN
    RAISE NOTICE '[reap_stale_routine_executions] Reaped % stale execution(s)', _reaped;
  END IF;

  RETURN _reaped;
END;
$reaper$;

REVOKE EXECUTE ON FUNCTION public.reap_stale_routine_executions() FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.reap_stale_routine_executions() TO service_role;

-- 5. pg_cron para o reaper a cada 5 minutos
-- ---------------------------------------------------------------------------
SELECT cron.unschedule('reap_stale_routine_executions') WHERE EXISTS (
  SELECT 1 FROM cron.job WHERE jobname = 'reap_stale_routine_executions'
);

SELECT cron.schedule(
  'reap_stale_routine_executions',
  '*/5 * * * *',
  $$ SELECT public.reap_stale_routine_executions(); $$
);
