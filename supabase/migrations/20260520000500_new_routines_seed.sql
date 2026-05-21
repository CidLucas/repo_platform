-- ─────────────────────────────────────────────────────────────────────────────
-- New built-in routines seed
--
-- EPIC-2 Financeiro
--   FIN-04 · Alerta de Fluxo de Caixa (built-in, numeric trigger)
--   FIN-06 · Relatório de Conciliação Mensal (optional, schedule)
--
-- EPIC-3 Clientes
--   CLI-03 · Cobrança de Inadimplentes (built-in, schedule)
--   CLI-06 · Follow-up de Vendas (optional, event)
--   CLI-08 · Reativação de Clientes (optional, schedule)
--
-- EPIC-4 Operações
--   OPS-02 · Nível de Estoque Crítico (built-in, schedule)
--   OPS-04 · Gestão de Fornecedores (built-in, event)
--
-- EPIC-5 Agenda
--   AGD-04 · Prep Reunião (optional, event)
--
-- EPIC-6 Estratégia
--   EST-03 · Padrões Escondidos (optional, schedule)
--   EST-06 · Análise de Concorrência (optional, schedule)
--
-- EPIC-7 Satisfação
--   SAT-03 · Pesquisa de Satisfação (optional, event)
-- ─────────────────────────────────────────────────────────────────────────────


-- ── FIN-04 · Alerta de Fluxo de Caixa ───────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'cash_flow_alert',
  'Alerta de Fluxo de Caixa',
  'financeiro',
  'financeiro',
  'numeric',
  '{"metric": "saldo_conta_corrente", "operator": "lt", "field": "threshold"}'::jsonb,
  '[
    {"key": "threshold",        "label": "Saldo mínimo (R$)",          "type": "number",  "default": 5000, "required": false},
    {"key": "runway_days_warn", "label": "Alertar se runway < N dias", "type": "number",  "default": 15,   "required": false}
  ]'::jsonb,
  '[
    {
      "id": "get_cash",
      "step": 1,
      "type": "function",
      "function": "financeiro.get_cash_position",
      "inputs": {},
      "output_key": "caixa",
      "on_failure": "halt"
    },
    {
      "id": "get_txs",
      "step": 2,
      "type": "function",
      "function": "financeiro.get_recent_transactions",
      "inputs": {"days": 30},
      "on_failure": "continue"
    },
    {
      "id": "eval_alert",
      "step": 3,
      "type": "function",
      "function": "financeiro.evaluate_cash_alert",
      "inputs": {
        "saldo": "{{saldo_conta_corrente}}",
        "threshold": "{{threshold}}",
        "total_debitos": "{{total_debitos}}",
        "days": 30,
        "runway_days_warn": "{{runway_days_warn}}"
      },
      "on_failure": "halt"
    },
    {
      "id": "alert",
      "step": 4,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "⚠️ Alerta de Caixa",
        "body": "{{mensagem}}",
        "priority": "{{severity}}",
        "agent_slug": "routine-runner"
      },
      "condition": "{{should_alert}}",
      "on_failure": "halt"
    }
  ]'::jsonb,
  'builtin'
)
ON CONFLICT (id) DO NOTHING;


-- ── FIN-06 · Relatório de Conciliação Mensal ─────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'monthly_reconciliation',
  'Relatório de Conciliação Mensal',
  'financeiro',
  'financeiro',
  'cron',
  '{"expression": "0 8 5 * *"}'::jsonb,
  '[
    {"key": "dia_do_mes", "label": "Dia do mês para execução", "type": "number", "default": 5, "required": false}
  ]'::jsonb,
  '[
    {
      "id": "get_cash",
      "step": 1,
      "type": "function",
      "function": "financeiro.get_cash_position",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "get_txs",
      "step": 2,
      "type": "function",
      "function": "financeiro.get_recent_transactions",
      "inputs": {"days": 30},
      "on_failure": "continue"
    },
    {
      "id": "get_kpis",
      "step": 3,
      "type": "function",
      "function": "analytics.get_kpi_snapshots",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "generate_report",
      "step": 4,
      "type": "skill",
      "skill_slug": "financeiro",
      "task_template": "Gere um relatório de conciliação mensal detalhado para {{nome_empresa}}.\n\nSaldo atual: {{saldo_total}}\nTransações (30d): débitos R$ {{total_debitos}} / créditos R$ {{total_creditos}}\nTop categorias: {{por_categoria}}\nTop merchants: {{top_merchants}}\nKPIs: {{kpi_summary}}\n\nGere: narrativa de conciliação, alertas de categorias fora do padrão, lista de top merchants.",
      "outputs": {"relatorio": "relatório de conciliação"},
      "on_failure": "continue"
    },
    {
      "id": "push_card",
      "step": 5,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "📋 Conciliação Mensal",
        "body": "{{relatorio}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  'optional'
)
ON CONFLICT (id) DO NOTHING;


-- ── CLI-03 · Cobrança de Inadimplentes ───────────────────────────────────────
-- Flow: fetch overdue → generate messages → HITL approval → push card
-- The approval step pauses the execution; the DB trigger re-dispatches after
-- the operator approves, and the engine resumes at step 4 (push_card).

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'collection_overdue',
  'Cobrança de Inadimplentes',
  'clientes',
  'clientes',
  'cron',
  '{"expression": "0 9 * * 1"}'::jsonb,
  '[
    {"key": "min_dias_atraso", "label": "Dias mínimos de atraso",  "type": "number",  "default": 30,        "required": false},
    {"key": "tom",             "label": "Tom das mensagens",       "type": "select",  "default": "amigavel",
      "options": [
        {"value": "amigavel", "label": "Amigável"},
        {"value": "firme",    "label": "Firme"},
        {"value": "urgente",  "label": "Urgente"}
      ],
      "required": false
    }
  ]'::jsonb,
  '[
    {
      "id": "get_overdue",
      "step": 1,
      "type": "function",
      "function": "analytics.get_overdue_customers",
      "inputs": {"min_dias": "{{min_dias_atraso}}", "max_results": 50},
      "on_failure": "halt"
    },
    {
      "id": "gen_messages",
      "step": 2,
      "type": "llm",
      "prompt_name": "blu/collection_message_v1",
      "outputs": {"mensagens": "lista de mensagens por cliente"},
      "on_failure": "continue"
    },
    {
      "id": "approval",
      "step": 3,
      "type": "approval",
      "inputs": {
        "title": "💰 Revisar Cobranças — {{overdue_count}} clientes",
        "body": "{{mensagens}}",
        "priority": "normal"
      },
      "on_failure": "continue"
    },
    {
      "id": "push_card",
      "step": 4,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "💰 Cobranças Aprovadas",
        "body": "{{overdue_count}} mensagens de cobrança aprovadas e prontas para envio.\n\n{{mensagens}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  'builtin'
)
ON CONFLICT (id) DO UPDATE SET
  steps = EXCLUDED.steps;


-- ── CLI-06 · Follow-up de Vendas ─────────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'sales_followup',
  'Follow-up de Vendas',
  'clientes',
  'clientes',
  'event',
  '{"event_type": "sale_approved"}'::jsonb,
  '[
    {"key": "incluir_crosssell", "label": "Incluir sugestões de cross-sell", "type": "boolean", "default": false, "required": false}
  ]'::jsonb,
  '[
    {
      "id": "get_pipeline",
      "step": 1,
      "type": "function",
      "function": "analytics.get_client_pipeline",
      "inputs": {"segment": "ativos"},
      "on_failure": "continue"
    },
    {
      "id": "gen_followup",
      "step": 2,
      "type": "llm",
      "prompt_name": "blu/followup_v1",
      "outputs": {"followup_mensagem": "mensagem de follow-up"},
      "on_failure": "continue"
    },
    {
      "id": "push_card",
      "step": 3,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "📩 Follow-up de Venda",
        "body": "{{followup_mensagem}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  'optional'
)
ON CONFLICT (id) DO NOTHING;


-- ── CLI-08 · Reativação de Clientes ──────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'client_reactivation',
  'Reativação de Clientes',
  'clientes',
  'clientes',
  'cron',
  '{"expression": "0 9 15 * *"}'::jsonb,
  '[
    {"key": "min_dias_inatividade", "label": "Dias mínimos de inatividade", "type": "number",  "default": 60,   "required": false},
    {"key": "incluir_proposta",     "label": "Incluir proposta especial",   "type": "boolean", "default": false, "required": false}
  ]'::jsonb,
  '[
    {
      "id": "get_pipeline",
      "step": 1,
      "type": "function",
      "function": "analytics.get_client_pipeline",
      "inputs": {"segment": "inativos"},
      "on_failure": "halt"
    },
    {
      "id": "gen_reactivation",
      "step": 2,
      "type": "llm",
      "prompt_name": "blu/reactivation_v1",
      "outputs": {"propostas": "lista de propostas por cliente"},
      "on_failure": "continue"
    },
    {
      "id": "push_card",
      "step": 3,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "🔄 Reativação de Clientes",
        "body": "{{pipeline_summary}}\n\nPropostas geradas para clientes inativos.",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  'optional'
)
ON CONFLICT (id) DO NOTHING;


-- ── OPS-02 · Nível de Estoque Crítico ────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'inventory_alert',
  'Nível de Estoque Crítico',
  'operacoes',
  'operacoes',
  'cron',
  '{"expression": "0 8 * * 1-5"}'::jsonb,
  '[
    {"key": "threshold_global", "label": "Estoque mínimo global (unidades)", "type": "number", "default": 10, "required": false}
  ]'::jsonb,
  '[
    {
      "id": "get_alerts",
      "step": 1,
      "type": "function",
      "function": "analytics.get_inventory_alerts",
      "inputs": {"threshold_global": "{{threshold_global}}"},
      "on_failure": "halt"
    },
    {
      "id": "push_card",
      "step": 2,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "📦 Estoque Crítico",
        "body": "{{inventory_summary}}",
        "priority": "high",
        "agent_slug": "routine-runner"
      },
      "condition": "{{criticos}}",
      "on_failure": "halt"
    }
  ]'::jsonb,
  'builtin'
)
ON CONFLICT (id) DO NOTHING;


-- ── OPS-04 · Gestão de Fornecedores ──────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'supplier_management',
  'Gestão de Fornecedores',
  'operacoes',
  'operacoes',
  'event',
  '{"event_type": "compra_aprovada"}'::jsonb,
  '[]'::jsonb,
  '[
    {
      "id": "get_orders",
      "step": 1,
      "type": "function",
      "function": "analytics.get_supplier_orders",
      "inputs": {"days": 30},
      "on_failure": "halt"
    },
    {
      "id": "push_card",
      "step": 2,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "🚚 Gestão de Fornecedores",
        "body": "{{supplier_summary}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  'builtin'
)
ON CONFLICT (id) DO NOTHING;


-- ── AGD-04 · Prep Reunião ─────────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'meeting_prep',
  'Prep Reunião',
  'agenda',
  'agenda',
  'event',
  '{"event_type": "calendar_changed"}'::jsonb,
  '[]'::jsonb,
  '[
    {
      "id": "get_meetings",
      "step": 1,
      "type": "function",
      "function": "agenda.get_upcoming_meetings",
      "inputs": {"hours_ahead": 24},
      "on_failure": "halt"
    },
    {
      "id": "get_participant_ctx",
      "step": 2,
      "type": "function",
      "function": "web.get_meeting_participant_context",
      "inputs": {"reunioes": "{{reunioes}}"},
      "on_failure": "continue"
    },
    {
      "id": "gen_brief",
      "step": 3,
      "type": "llm",
      "prompt_name": "blu/meeting_brief_v1",
      "outputs": {"briefings": "briefings das reuniões"},
      "on_failure": "continue"
    },
    {
      "id": "push_card",
      "step": 4,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "📋 Prep Reunião",
        "body": "{{meeting_count}} reunião(ões) nas próximas 24h. Briefings gerados.",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  'optional'
)
ON CONFLICT (id) DO NOTHING;


-- ── EST-03 · Padrões Escondidos ───────────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'hidden_patterns',
  'Padrões Escondidos',
  'estrategia',
  'estrategia',
  'cron',
  '{"expression": "0 8 * * 0"}'::jsonb,
  '[
    {
      "key": "dia_da_semana",
      "label": "Dia da semana (0=Dom…6=Sáb)",
      "type": "select",
      "default": "0",
      "options": [
        {"value": "0", "label": "Domingo"},
        {"value": "1", "label": "Segunda"},
        {"value": "5", "label": "Sexta"},
        {"value": "6", "label": "Sábado"}
      ],
      "required": false
    }
  ]'::jsonb,
  '[
    {
      "id": "get_performance",
      "step": 1,
      "type": "function",
      "function": "analytics.get_sales_performance",
      "inputs": {},
      "on_failure": "halt"
    },
    {
      "id": "detect_patterns",
      "step": 2,
      "type": "llm",
      "prompt_name": "blu/hidden_patterns_v1",
      "outputs": {"analise_padroes": "análise de padrões escondidos"},
      "on_failure": "continue"
    },
    {
      "id": "push_card",
      "step": 3,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "🔍 Padrões Escondidos",
        "body": "{{performance_summary}}\n\n{{analise_padroes}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  'optional'
)
ON CONFLICT (id) DO NOTHING;


-- ── EST-06 · Análise de Concorrência ─────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'competitor_analysis',
  'Análise de Concorrência',
  'estrategia',
  'estrategia',
  'cron',
  '{"expression": "0 8 1 * *"}'::jsonb,
  '[
    {
      "key": "concorrentes",
      "label": "Concorrentes (nome → URL)",
      "type": "dict",
      "max_entries": 3,
      "required": false
    },
    {
      "key": "foco",
      "label": "Foco da análise",
      "type": "select",
      "default": "geral",
      "options": [
        {"value": "geral",       "label": "Visão geral"},
        {"value": "precos",      "label": "Preços"},
        {"value": "produtos",    "label": "Produtos"},
        {"value": "comunicacao", "label": "Comunicação"}
      ],
      "required": false
    }
  ]'::jsonb,
  '[
    {
      "id": "get_performance",
      "step": 1,
      "type": "function",
      "function": "analytics.get_sales_performance",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "crawl_competitors",
      "step": 2,
      "type": "function",
      "function": "web.crawl_competitor_pages",
      "inputs": {"concorrentes": "{{concorrentes}}"},
      "on_failure": "continue"
    },
    {
      "id": "gen_analysis",
      "step": 3,
      "type": "llm",
      "prompt_name": "blu/competitor_analysis_v1",
      "outputs": {"analise_concorrencia": "análise de concorrência"},
      "on_failure": "continue"
    },
    {
      "id": "push_card",
      "step": 4,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "🏁 Análise de Concorrência",
        "body": "{{analise_concorrencia}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  'optional'
)
ON CONFLICT (id) DO NOTHING;


-- ── SAT-03 · Pesquisa de Satisfação ──────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'satisfaction_survey',
  'Pesquisa de Satisfação',
  'clientes',
  'clientes',
  'event',
  '{"event_type": "pedido_entregue"}'::jsonb,
  '[]'::jsonb,
  '[
    {
      "id": "get_nps",
      "step": 1,
      "type": "function",
      "function": "analytics.get_nps_data",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "gen_survey",
      "step": 2,
      "type": "llm",
      "prompt_name": "blu/satisfaction_survey_v1",
      "outputs": {"survey_mensagem": "mensagem de pesquisa"},
      "on_failure": "continue"
    },
    {
      "id": "push_card",
      "step": 3,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "⭐ Pesquisa de Satisfação",
        "body": "{{survey_mensagem}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  'optional'
)
ON CONFLICT (id) DO NOTHING;
