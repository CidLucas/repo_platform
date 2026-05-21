-- ─────────────────────────────────────────────────────────────────────────────
-- Fase 1 · Arquitetura C — Room Monitors
--
-- FIN-MON-01 · FinanceiroMonitor (built-in, cron diário 06h)
--
-- Coleta posição de caixa + transações + KPIs, gera análise narrativa via LLM
-- e grava o estado no dimension_state via memory.write_dimension_state.
-- O snapshot fica disponível para o User-Facing Agent via get_business_memory_snapshot().
--
-- Steps:
--   1. financeiro.get_cash_position       → saldo_total, saldo_conta_corrente, etc.
--   2. financeiro.get_recent_transactions → total_debitos, total_creditos, por_categoria
--   3. analytics.get_kpi_snapshots        → kpi_summary
--   4. financeiro.evaluate_cash_alert     → mensagem, severity, should_alert
--   5. skill: financeiro (analyze_cashflow) → memory_summary (prose para dimension_state)
--   6. memory.write_dimension_state       → grava dimension_state['financeiro']
-- ─────────────────────────────────────────────────────────────────────────────


INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'financeiro_monitor',
  'Monitor Financeiro Diário',
  'financeiro',
  'financeiro',
  'cron',
  '{"expression": "0 6 * * *"}'::jsonb,
  '[
    {"key": "days_lookback",      "label": "Janela de transações (dias)", "type": "number", "default": 30, "required": false},
    {"key": "threshold_caixa",    "label": "Saldo mínimo de alerta (R$)", "type": "number", "default": 5000, "required": false},
    {"key": "runway_days_warn",   "label": "Alertar se runway < N dias",  "type": "number", "default": 15,  "required": false},
    {"key": "ttl_hours",          "label": "TTL do estado em horas",       "type": "number", "default": 12,  "required": false}
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
      "inputs": {"days": "{{days_lookback}}"},
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
      "id": "eval_alert",
      "step": 4,
      "type": "function",
      "function": "financeiro.evaluate_cash_alert",
      "inputs": {
        "saldo":            "{{saldo_conta_corrente}}",
        "threshold":        "{{threshold_caixa}}",
        "total_debitos":    "{{total_debitos}}",
        "days":             "{{days_lookback}}",
        "runway_days_warn": "{{runway_days_warn}}"
      },
      "on_failure": "continue"
    },
    {
      "id": "analyze_cashflow",
      "step": 5,
      "type": "skill",
      "skill_slug": "financeiro",
      "task_template": "Você é o FinanceiroMonitor da {{nome_empresa}}. Analise o estado financeiro atual e produza um resumo compacto (máximo 250 tokens) para ser injetado no contexto do agente.\n\nDados atuais:\n- Saldo total: R$ {{saldo_total}}\n- Conta corrente: R$ {{saldo_conta_corrente}}\n- Período: {{days_lookback}} dias\n- Débitos: R$ {{total_debitos}} | Créditos: R$ {{total_creditos}}\n- Categorias: {{por_categoria}}\n- KPIs: {{kpi_summary}}\n- Avaliação de caixa: {{mensagem}}\n\nGere um parágrafo conciso com: posição de caixa, principais movimentos, anomalias detectadas e nível de atenção (normal/atenção/crítico). Este texto será lido por outro agente — seja direto e factual.",
      "outputs": {"memory_summary": "resumo financeiro para dimension_state"},
      "on_failure": "continue"
    },
    {
      "id": "write_memory",
      "step": 6,
      "type": "function",
      "function": "memory.write_dimension_state",
      "inputs": {
        "dimension": "financeiro",
        "summary":   "{{memory_summary}}",
        "structured": {
          "saldo_total":          "{{saldo_total}}",
          "saldo_conta_corrente": "{{saldo_conta_corrente}}",
          "total_debitos":        "{{total_debitos}}",
          "total_creditos":       "{{total_creditos}}",
          "severity":             "{{severity}}"
        },
        "ttl_hours": "{{ttl_hours}}"
      },
      "on_failure": "continue"
    }
  ]'::jsonb,
  'builtin'
)
ON CONFLICT (id) DO UPDATE SET
  name          = EXCLUDED.name,
  steps         = EXCLUDED.steps,
  config_schema = EXCLUDED.config_schema,
  trigger_config = EXCLUDED.trigger_config;
