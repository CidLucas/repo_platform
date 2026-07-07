-- Routines system fix (2026-07-07)
--
-- Problema 1 — aba config vazia: auto_enroll_catalog_routines() só materializava
-- rotinas com visibility='user' (6 de 24). As rotinas 'builtin' e 'optional'
-- (financeiro_monitor, cash_flow_alert, clientes_monitor, compras_monitor, ...)
-- nunca ganhavam linha em client_routines, então não apareciam na aba config de
-- nenhuma sala e nunca eram disparadas pelo poller.
--
-- Problema 2 — salvar config / criar rotina custom falhava: o frontend grava em
-- client_routines linhas com routine_id fora do catálogo ('<domain>.config' para
-- config global da sala e 'custom.<timestamp>' para rotinas criadas pelo usuário).
-- A FK client_routines_routine_id_fkey -> cross_agent_routines(id) rejeitava
-- esses inserts ("Erro ao salvar." na UI). O modelo de rotinas custom guarda os
-- steps na própria linha de client_routines, por design fora do catálogo.
--
-- Problema 3 — insights nunca chegavam às salas: as salas leem client_insights
-- via get_my_insights(p_room), mas nenhuma rotina do catálogo tinha step
-- storage.save_insights — a tabela estava vazia desde sempre. daily_insights
-- gerava um digest JSON livre e só criava um alerta. Os steps são refeitos para
-- emitir insights estruturados por sala e persistí-los.

begin;

-- ---------------------------------------------------------------------------
-- (1a) Enroll de todas as visibilidades voltadas ao usuário
-- ---------------------------------------------------------------------------
create or replace function public.auto_enroll_catalog_routines()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.client_routines (
    client_id, routine_id, source, status, active,
    config, trigger_type, trigger_config
  )
  select
    new.client_id,
    r.id,
    'catalog',
    'inactive',
    false,
    '{}'::jsonb,
    r.trigger_type,
    r.trigger_config
  from public.cross_agent_routines r
  where r.visibility in ('user', 'builtin', 'optional')
  on conflict do nothing;

  return new;
end;
$$;

-- (1b) Backfill para clientes existentes (linhas inativas; usuário ativa na aba config)
insert into public.client_routines (
  client_id, routine_id, source, status, active, config, trigger_type, trigger_config
)
select c.client_id, r.id, 'catalog', 'inactive', false, '{}'::jsonb, r.trigger_type, r.trigger_config
from public.clientes_blu c
cross join public.cross_agent_routines r
where r.visibility in ('user', 'builtin', 'optional')
on conflict (client_id, routine_id) do nothing;

-- ---------------------------------------------------------------------------
-- (2) routine_id de client_routines não é sempre um id de catálogo
--     ('custom.<ts>', '<domain>.config') — a FK contradiz o design.
-- ---------------------------------------------------------------------------
alter table public.client_routines
  drop constraint if exists client_routines_routine_id_fkey;

-- ---------------------------------------------------------------------------
-- (3) daily_insights: gerar insights estruturados por sala e persistir em
--     client_insights (storage.save_insights), mantendo o alerta com o digest.
-- ---------------------------------------------------------------------------
update public.cross_agent_routines
set steps = $steps$[
  {
    "id": "fetch_kpis",
    "step": 1,
    "type": "function",
    "function": "analytics.get_kpi_snapshots",
    "inputs": {"window_days": 30, "baseline_days": 90},
    "on_failure": "halt"
  },
  {
    "id": "generate_insights",
    "step": 2,
    "type": "skill",
    "skill_slug": "insights_synthesis",
    "task_template": "Voce e o InsightsMonitor da {{nome_empresa}}. Analise os KPIs abaixo e gere insights acionaveis para os paineis das salas da plataforma.\n\nKPIs:\n{{kpi_summary}}\n\nResponda APENAS com um objeto JSON valido (sem markdown, sem texto fora do JSON) neste formato exato:\n{\"digest\": \"resumo executivo em 2-4 frases: performance financeira, comercial, alertas criticos e nivel de atencao (normal/atencao/critico)\", \"insights\": [{\"room\": \"financeiro\", \"kpi\": \"nome_do_kpi\", \"title\": \"titulo curto (max 80 chars)\", \"observation\": \"o que os dados mostram\", \"recommendation\": \"acao sugerida\", \"severity\": \"info\", \"metric_value\": null, \"baseline_value\": null, \"variance_pct\": null}]}\n\nRegras:\n- room deve ser exatamente um de: financeiro, clientes, compras, estrategia, agenda\n- severity deve ser exatamente um de: info, warning, error (warning para quedas/atencao; error apenas para problemas criticos)\n- 1 a 2 insights por dimensao que tenha dados relevantes, maximo 6 no total\n- se uma integracao estiver ausente, gere no maximo 1 insight severity=info sobre isso\n- preencha metric_value/baseline_value/variance_pct com numeros quando disponiveis nos KPIs, senao null",
    "outputs": {
      "digest": "resumo executivo em texto",
      "insights": "lista de insights estruturados por sala"
    },
    "on_failure": "halt"
  },
  {
    "id": "save_insights",
    "step": 3,
    "type": "artifact",
    "function": "storage.save_insights",
    "inputs": {"insights": "{{insights}}"},
    "on_failure": "continue"
  },
  {
    "id": "push_digest",
    "step": 4,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "Insights Diarios",
      "body": "{{digest}}",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "on_failure": "continue"
  }
]$steps$::jsonb
where id = 'daily_insights';

commit;
