-- Reaper com retry: execuções travadas (container reiniciado, timeout) eram
-- marcadas 'failed' na primeira ocorrência, sem nova tentativa — 3 execuções
-- de context_report_post_ingestion foram perdidas assim em 2026-07-08.
--
-- Novo comportamento:
--   1. failure_count < 2  → re-despacha (status='dispatched'), incrementa
--      failure_count e zera heartbeat. O próximo tick do claim retoma a
--      execução; o executor pula steps já concluídos via
--      result_metadata._resume_from_step (checkpoint por batch).
--   2. failure_count >= 2 → 'failed' definitivo (comportamento anterior).
--
-- Backoff natural: dispatched_at=now() dá ao retry a janela de 10 min de
-- heartbeat antes de novo reap.

CREATE OR REPLACE FUNCTION public.reap_stale_routine_executions()
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  _retried        int;
  _failed         int;
  _no_heartbeat   interval := interval '10 minutes';  -- sem nenhum sinal
  _dead_heartbeat interval := interval '5 minutes';   -- heartbeat parou
  _max_reaps      int      := 2;                      -- tentativas antes de failed
begin
  -- 1) Retry: re-despacha execuções travadas com tentativas restantes
  update public.client_routine_executions
  set
    status        = 'dispatched',
    dispatched_at = now(),
    heartbeat_at  = null,
    failure_count = coalesce(failure_count, 0) + 1,
    result_text   = 'retomada automática após travamento (reaper, tentativa '
                    || (coalesce(failure_count, 0) + 1)::text || ')'
  where status in ('dispatched', 'executing')
    and (
      (heartbeat_at is null and dispatched_at < now() - _no_heartbeat)
      or
      (heartbeat_at is not null and heartbeat_at < now() - _dead_heartbeat)
    )
    and coalesce(failure_count, 0) < _max_reaps;

  get diagnostics _retried = row_count;

  -- 2) Falha definitiva: tentativas esgotadas
  update public.client_routine_executions
  set
    status       = 'failed',
    result_text  = 'timeout: execução travada (reaper) — tentativas esgotadas',
    completed_at = now()
  where status in ('dispatched', 'executing')
    and (
      (heartbeat_at is null and dispatched_at < now() - _no_heartbeat)
      or
      (heartbeat_at is not null and heartbeat_at < now() - _dead_heartbeat)
    )
    and coalesce(failure_count, 0) >= _max_reaps;

  get diagnostics _failed = row_count;

  if _retried > 0 or _failed > 0 then
    raise notice '[reap_stale] retried % execution(s), failed % execution(s)',
      _retried, _failed;
  end if;

  return _retried + _failed;
end;
$function$;
