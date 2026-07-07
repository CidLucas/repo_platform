-- Restaura o embed PostgREST client_routines -> cross_agent_routines (2026-07-07)
--
-- 20260707000004 dropou a FK client_routines_routine_id_fkey porque rotinas
-- custom ('custom.<ts>') e config de sala ('<domain>.config') usam routine_id
-- fora do catálogo por design. Efeito colateral: o PostgREST usava essa FK para
-- resolver o embed `cross_agent_routines(...)` do frontend (api/routines.ts),
-- que passou a responder 400 PGRST200 ("Could not find a relationship").
--
-- Correção: computed relationship — função com o nome da tabela embedada
-- recebendo a linha de client_routines. ROWS 1 faz o PostgREST tratar como
-- to-one (objeto, não array), igual ao comportamento da FK. Linhas custom
-- simplesmente retornam embed nulo, sem quebrar a query.

begin;

create or replace function public.cross_agent_routines(public.client_routines)
returns setof public.cross_agent_routines
language sql
stable
rows 1
as $$
  select * from public.cross_agent_routines where id = $1.routine_id
$$;

comment on function public.cross_agent_routines(public.client_routines) is
  'Computed relationship PostgREST: substitui a FK client_routines_routine_id_fkey removida em 20260707000004 para manter o embed cross_agent_routines(...) do frontend.';

commit;

notify pgrst, 'reload schema';
