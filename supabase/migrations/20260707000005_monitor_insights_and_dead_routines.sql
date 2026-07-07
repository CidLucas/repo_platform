-- Monitor routines → room insights + remoção de rotinas mortas (2026-07-07)
--
-- (1) Os 4 monitores diários (financeiro/clientes/compras/agenda) geravam apenas
--     texto para dimension_state; agora o skill step também emite insights
--     estruturados (formato de client_insights) e um novo step
--     storage.save_insights os persiste — é o que alimenta os cards das salas.
--     O write_dimension_state passa a usar {{memory_summary}} (o parágrafo) em
--     vez de {{summary}} (que é o JSON bruto truncado do skill).
--
-- (2) Rotinas de evento sem NENHUM emissor no código (eventos órfãos —
--     sale_approved, compra_aprovada, pedido_entregue) são removidas do
--     catálogo: nunca dispararam e não há caminho que as dispare.
--     supplier_management também referenciava room 'operacoes', inexistente no
--     frontend.

begin;

update public.cross_agent_routines
set steps = $steps$[
  {
    "id": "get_cash",
    "step": 1,
    "type": "function",
    "inputs": {},
    "function": "financeiro.get_cash_position",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "get_txs",
    "step": 2,
    "type": "function",
    "inputs": {
      "days": 30
    },
    "function": "financeiro.get_recent_transactions",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "get_kpis",
    "step": 3,
    "type": "function",
    "inputs": {},
    "function": "analytics.get_kpi_snapshots",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "get_projection",
    "step": 4,
    "type": "function",
    "inputs": {
      "threshold": "{{threshold_caixa}}",
      "horizon_days": 60,
      "min_recurring_confidence": 0.7
    },
    "function": "financeiro.get_cash_flow_projection",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "eval_alert",
    "step": 5,
    "type": "function",
    "inputs": {
      "days": 30,
      "saldo": "{{saldo_conta_corrente}}",
      "threshold": "{{threshold_caixa}}",
      "total_debitos": "{{total_debitos}}",
      "runway_days_warn": "{{runway_days_warn}}"
    },
    "function": "financeiro.evaluate_cash_alert",
    "on_failure": "continue"
  },
  {
    "id": "analyze_cashflow",
    "step": 6,
    "type": "skill",
    "on_failure": "continue",
    "skill_slug": "finance_monitor_report",
    "task_template": "Você é o FinanceiroMonitor da {{nome_empresa}}. Analise o estado financeiro atual e produza um resumo compacto (máximo 300 tokens) para ser injetado no contexto do agente.\n\nPOSIÇÃO ATUAL:\n- Saldo total: R$ {{saldo_total}}\n- Conta corrente: R$ {{saldo_conta_corrente}}\n- Período: {{days_lookback}} dias\n- Débitos: R$ {{total_debitos}} | Créditos: R$ {{total_creditos}}\n- Categorias: {{por_categoria}}\n- KPIs: {{kpi_summary}}\n- Avaliação de caixa: {{mensagem}}\n\nPROJEÇÃO (60 dias):\n- Saldo projetado final: R$ {{saldo_projetado_final}}\n- Runway: {{runway_days}} dias até atingir saldo mínimo\n- Recorrentes detectadas: {{recorrentes_detectadas}}\n- Alertas de fluxo: {{alertas}}\n\nGere um parágrafo conciso com: posição atual de caixa, principais movimentos do período, projeção de fluxo para os próximos 60 dias (risco/segurança), anomalias detectadas e nível de atenção (normal/atenção/crítico). Este texto será lido por outro agente — seja direto e factual.\n\nAlem do campo memory_summary (o paragrafo acima), preencha o campo insights com 1 a 3 insights acionaveis para o painel da sala. Cada insight: {\"room\": \"financeiro\", \"kpi\": \"nome_do_kpi\", \"title\": \"titulo curto (max 80 chars)\", \"observation\": \"o que os dados mostram\", \"recommendation\": \"acao sugerida\", \"severity\": \"info\", \"metric_value\": null, \"baseline_value\": null, \"variance_pct\": null}. O campo room deve ser sempre \"financeiro\". severity deve ser exatamente um de: info, warning, error (warning para atencao, error apenas para critico). Preencha metric_value/baseline_value/variance_pct com numeros quando disponiveis, senao null. Se nao houver dados suficientes, retorne insights: [].",
    "outputs": {
      "memory_summary": "resumo para dimension_state",
      "insights": "lista de insights estruturados para os cards da sala"
    }
  },
  {
    "id": "save_insights",
    "step": 7,
    "type": "artifact",
    "function": "storage.save_insights",
    "inputs": {
      "insights": "{{insights}}"
    },
    "on_failure": "continue"
  },
  {
    "id": "write_memory",
    "step": 8,
    "type": "function",
    "inputs": {
      "summary": "{{memory_summary}}",
      "dimension": "financeiro",
      "ttl_hours": 26,
      "structured": {
        "severity": "{{severity}}",
        "runway_days": "{{runway_days}}",
        "saldo_total": "{{saldo_total}}",
        "alertas_fluxo": "{{alertas}}",
        "total_debitos": "{{total_debitos}}",
        "total_creditos": "{{total_creditos}}",
        "saldo_conta_corrente": "{{saldo_conta_corrente}}",
        "saldo_projetado_final": "{{saldo_projetado_final}}",
        "recorrentes_detectadas": "{{recorrentes_detectadas}}"
      }
    },
    "function": "memory.write_dimension_state",
    "on_failure": "continue"
  }
]$steps$::jsonb
where id = 'financeiro_monitor';

update public.cross_agent_routines
set steps = $steps$[
  {
    "id": "get_pipeline",
    "step": 1,
    "type": "function",
    "inputs": {},
    "function": "analytics.get_client_pipeline",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "get_inactive",
    "step": 2,
    "type": "function",
    "inputs": {
      "days_inactive": 90,
      "lookback_months": 3
    },
    "function": "analytics.query_inactive_clients",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "get_nps",
    "step": 3,
    "type": "function",
    "inputs": {},
    "function": "analytics.get_nps_data",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "get_overdue",
    "step": 4,
    "type": "function",
    "inputs": {},
    "function": "analytics.get_overdue_customers",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "analyze_customers",
    "step": 5,
    "type": "skill",
    "outputs": {
      "memory_summary": "resumo de clientes para dimension_state",
      "insights": "lista de insights estruturados para os cards da sala"
    },
    "on_failure": "continue",
    "skill_slug": "clients_monitor_report",
    "task_template": "Você é o ClientesMonitor da {{nome_empresa}}. Analise o estado atual da base de clientes e produza um resumo compacto (máximo 250 tokens) para ser injetado no contexto do agente.\n\nPipeline: {{pipeline_summary}}\nClientes inativos (>{{days_inactive}}d sem compra): {{client_list}}\nNPS: {{nps_summary}}\nInadimplentes: {{overdue_count}} cliente(s)\n\nGere um parágrafo conciso com: saúde da base (ativos/em risco/inativos), alertas de churn, situação de NPS e inadimplência. Nível de atenção: normal/atenção/crítico. Seja direto e factual — este texto será lido por outro agente.\n\nAlem do campo memory_summary (o paragrafo acima), preencha o campo insights com 1 a 3 insights acionaveis para o painel da sala. Cada insight: {\"room\": \"clientes\", \"kpi\": \"nome_do_kpi\", \"title\": \"titulo curto (max 80 chars)\", \"observation\": \"o que os dados mostram\", \"recommendation\": \"acao sugerida\", \"severity\": \"info\", \"metric_value\": null, \"baseline_value\": null, \"variance_pct\": null}. O campo room deve ser sempre \"clientes\". severity deve ser exatamente um de: info, warning, error (warning para atencao, error apenas para critico). Preencha metric_value/baseline_value/variance_pct com numeros quando disponiveis, senao null. Se nao houver dados suficientes, retorne insights: []."
  },
  {
    "id": "save_insights",
    "step": 6,
    "type": "artifact",
    "function": "storage.save_insights",
    "inputs": {
      "insights": "{{insights}}"
    },
    "on_failure": "continue"
  },
  {
    "id": "write_memory",
    "step": 7,
    "type": "function",
    "inputs": {
      "summary": "{{memory_summary}}",
      "dimension": "clientes",
      "ttl_hours": 26,
      "structured": {
        "nps_avg": "{{nps_avg}}",
        "novos_count": "{{novos}}",
        "ativos_count": "{{ativos}}",
        "overdue_count": "{{overdue_count}}",
        "em_risco_count": "{{em_risco}}",
        "inativos_count": "{{inativos}}"
      }
    },
    "function": "memory.write_dimension_state",
    "on_failure": "continue"
  }
]$steps$::jsonb
where id = 'clientes_monitor';

update public.cross_agent_routines
set steps = $steps$[
  {
    "id": "get_inventory",
    "step": 1,
    "type": "function",
    "inputs": {
      "threshold_global": 10
    },
    "function": "analytics.get_inventory_alerts",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "get_suppliers",
    "step": 2,
    "type": "function",
    "inputs": {
      "days": 14
    },
    "function": "analytics.get_supplier_orders",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "analyze_stock",
    "step": 3,
    "type": "skill",
    "outputs": {
      "memory_summary": "resumo de compras para dimension_state",
      "insights": "lista de insights estruturados para os cards da sala"
    },
    "on_failure": "continue",
    "skill_slug": "inventory_digest",
    "task_template": "Você é o ComprasMonitor da {{nome_empresa}}. Analise o estado atual de estoque e compras e produza um resumo compacto (máximo 250 tokens) para ser injetado no contexto do agente.\n\nEstoque:\n{{inventory_summary}}\n\nFornecedores ({{supplier_days}}d):\n{{supplier_summary}}\n\nGere um parágrafo conciso com: SKUs críticos (quantidade e risco de ruptura), alertas de fornecedores com pedidos atrasados, e saúde geral do estoque. Nível de atenção: normal/atenção/crítico. Seja direto e factual — este texto será lido por outro agente.\n\nAlem do campo memory_summary (o paragrafo acima), preencha o campo insights com 1 a 3 insights acionaveis para o painel da sala. Cada insight: {\"room\": \"compras\", \"kpi\": \"nome_do_kpi\", \"title\": \"titulo curto (max 80 chars)\", \"observation\": \"o que os dados mostram\", \"recommendation\": \"acao sugerida\", \"severity\": \"info\", \"metric_value\": null, \"baseline_value\": null, \"variance_pct\": null}. O campo room deve ser sempre \"compras\". severity deve ser exatamente um de: info, warning, error (warning para atencao, error apenas para critico). Preencha metric_value/baseline_value/variance_pct com numeros quando disponiveis, senao null. Se nao houver dados suficientes, retorne insights: []."
  },
  {
    "id": "save_insights",
    "step": 4,
    "type": "artifact",
    "function": "storage.save_insights",
    "inputs": {
      "insights": "{{insights}}"
    },
    "on_failure": "continue"
  },
  {
    "id": "push_stock_card",
    "step": 5,
    "type": "artifact",
    "inputs": {
      "body": "{{inventory_summary}}",
      "title": "📦 Estoque e Compras",
      "priority": "normal",
      "agent_slug": "routine-runner"
    },
    "function": "channels.create_alert",
    "condition": "{{criticos}}",
    "on_failure": "continue"
  },
  {
    "id": "write_memory",
    "step": 6,
    "type": "function",
    "inputs": {
      "summary": "{{memory_summary}}",
      "dimension": "compras",
      "ttl_hours": 26,
      "structured": {
        "total_ok": "{{total_ok}}",
        "fornecedores": "{{fornecedores}}",
        "criticos_count": "{{criticos}}",
        "proximos_count": "{{proximos}}"
      }
    },
    "function": "memory.write_dimension_state",
    "on_failure": "continue"
  }
]$steps$::jsonb
where id = 'compras_monitor';

update public.cross_agent_routines
set steps = $steps$[
  {
    "id": "get_events",
    "step": 1,
    "type": "function",
    "inputs": {},
    "function": "agenda.get_calendar_events",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "get_deadlines",
    "step": 2,
    "type": "function",
    "inputs": {
      "days_ahead": 7
    },
    "function": "agenda.get_upcoming_deadlines",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "get_meetings",
    "step": 3,
    "type": "function",
    "inputs": {
      "hours_ahead": 48
    },
    "function": "agenda.get_upcoming_meetings",
    "on_failure": "continue",
    "parallel_group": "fetch"
  },
  {
    "id": "build_timeline",
    "step": 4,
    "type": "skill",
    "outputs": {
      "memory_summary": "resumo de agenda para dimension_state",
      "insights": "lista de insights estruturados para os cards da sala"
    },
    "on_failure": "continue",
    "skill_slug": "agenda_monitor_report",
    "task_template": "Você é o AgendaMonitor da {{nome_empresa}}. Analise o estado atual da agenda e produza um resumo compacto (máximo 250 tokens) para ser injetado no contexto do agente.\n\nEventos de hoje: {{eventos}}\nPrazos próximos ({{days_ahead}}d): {{prazos}}\nReuniões próximas ({{hours_ahead}}h): {{meeting_count}} reunião(ões)\n\nGere um parágrafo conciso com: compromissos críticos do dia, prazos iminentes (≤3 dias) e conflitos de agenda detectados. Nível de atenção: normal/atenção/crítico. Seja direto e factual — este texto será lido por outro agente.\n\nAlem do campo memory_summary (o paragrafo acima), preencha o campo insights com 1 a 3 insights acionaveis para o painel da sala. Cada insight: {\"room\": \"agenda\", \"kpi\": \"nome_do_kpi\", \"title\": \"titulo curto (max 80 chars)\", \"observation\": \"o que os dados mostram\", \"recommendation\": \"acao sugerida\", \"severity\": \"info\", \"metric_value\": null, \"baseline_value\": null, \"variance_pct\": null}. O campo room deve ser sempre \"agenda\". severity deve ser exatamente um de: info, warning, error (warning para atencao, error apenas para critico). Preencha metric_value/baseline_value/variance_pct com numeros quando disponiveis, senao null. Se nao houver dados suficientes, retorne insights: []."
  },
  {
    "id": "save_insights",
    "step": 5,
    "type": "artifact",
    "function": "storage.save_insights",
    "inputs": {
      "insights": "{{insights}}"
    },
    "on_failure": "continue"
  },
  {
    "id": "write_memory",
    "step": 6,
    "type": "function",
    "inputs": {
      "summary": "{{memory_summary}}",
      "dimension": "agenda",
      "ttl_hours": 26,
      "structured": {
        "eventos": "{{eventos}}",
        "meeting_count": "{{meeting_count}}",
        "prazos_proximos": "{{prazos}}"
      }
    },
    "function": "memory.write_dimension_state",
    "on_failure": "continue"
  }
]$steps$::jsonb
where id = 'agenda_monitor';

-- (2) rotinas mortas: eventos órfãos, sem emissor em nenhum serviço
delete from public.client_routines
 where routine_id in ('sales_followup', 'supplier_management', 'satisfaction_survey');
delete from public.cross_agent_routines
 where id in ('sales_followup', 'supplier_management', 'satisfaction_survey');

commit;
