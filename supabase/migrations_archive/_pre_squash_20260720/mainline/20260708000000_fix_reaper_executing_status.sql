-- Fix reap_stale_routine_executions: never reaped 'executing' rows (2026-07-08)
--
-- claim_routine_executions() sets status='executing' the instant a dispatched
-- execution is claimed by a worker (see baseline migration, function
-- claim_routine_executions). But reap_stale_routine_executions() only ever
-- matched WHERE status = 'dispatched' — so a worker that crashes or hangs
-- mid-execution (dead heartbeat) leaves its row stuck in 'executing' forever.
-- That stuck row then blocks all future dispatches for that client+routine via
-- the in-flight guard in _dispatch_execution_sync (status IN ('pending',
-- 'dispatched', 'executing')).
--
-- Fix: reap 'executing' rows too, using the same heartbeat-based staleness
-- checks already in place (dead heartbeat >5min, or never-claimed >10min).

begin;

create or replace function public.reap_stale_routine_executions()
returns integer
language plpgsql
security definer
set search_path to 'public'
as $function$

declare
  _reaped        int;
  _no_heartbeat  interval := interval '10 minutes';  -- sem nenhum sinal
  _dead_heartbeat interval := interval '5 minutes';  -- heartbeat parou
begin
  update public.client_routine_executions
  set
    status       = 'failed',
    result_text  = 'timeout: execução travada (reaper)',
    completed_at = now()
  where status in ('dispatched', 'executing')
    and (
      -- Sem heartbeat: usa dispatched_at como referência
      (heartbeat_at is null and dispatched_at < now() - _no_heartbeat)
      or
      -- Com heartbeat: heartbeat parou de atualizar
      (heartbeat_at is not null and heartbeat_at < now() - _dead_heartbeat)
    );

  get diagnostics _reaped = row_count;

  if _reaped > 0 then
    raise notice '[reap_stale] Reaped % execution(s)', _reaped;
  end if;

  return _reaped;
end;

$function$;

commit;
