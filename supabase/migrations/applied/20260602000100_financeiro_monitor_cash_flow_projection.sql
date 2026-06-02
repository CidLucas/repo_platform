-- Migration: financeiro_monitor — adiciona get_cash_flow_projection (FIN-04)
-- Data: 2026-06-02
-- Objetivo: incluir projeção de fluxo de caixa (60 dias) no parallel_group fetch
--           da rotina financeiro_monitor, enriquecendo o dimension_state.structured
--           com dados prospectivos (saldo_projetado_final, runway_days, alertas_fluxo).
-- Impacto: 0 → 7 steps (era 6); task_template da skill finance_monitor_report expandida
--          para narrar sobre futuro além do histórico.

UPDATE cross_agent_routines
SET steps = '[
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
    "inputs": {"days": 30},
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
      "horizon_days": 60,
      "threshold": "{{threshold_caixa}}",
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
      "threshold": 0,
      "total_debitos": "{{total_debitos}}",
      "runway_days_warn": 30
    },
    "function": "financeiro.evaluate_cash_alert",
    "on_failure": "continue"
  },
  {
    "id": "analyze_cashflow",
    "step": 6,
    "type": "skill",
    "skill_slug": "finance_monitor_report",
    "outputs": {
      "memory_summary": "resumo financeiro para dimension_state"
    },
    "on_failure": "continue",
    "task_template": "Você é o FinanceiroMonitor da {{nome_empresa}}. Analise o estado financeiro atual e produza um resumo compacto (máximo 300 tokens) para ser injetado no contexto do agente.\n\nPOSIÇÃO ATUAL:\n- Saldo total: R$ {{saldo_total}}\n- Conta corrente: R$ {{saldo_conta_corrente}}\n- Período: {{days_lookback}} dias\n- Débitos: R$ {{total_debitos}} | Créditos: R$ {{total_creditos}}\n- Categorias: {{por_categoria}}\n- KPIs: {{kpi_summary}}\n- Avaliação de caixa: {{mensagem}}\n\nPROJEÇÃO (60 dias):\n- Saldo projetado final: R$ {{saldo_projetado_final}}\n- Runway: {{runway_days}} dias até atingir saldo mínimo\n- Recorrentes detectadas: {{recorrentes_detectadas}}\n- Alertas de fluxo: {{alertas}}\n\nGere um parágrafo conciso com: posição atual de caixa, principais movimentos do período, projeção de fluxo para os próximos 60 dias (risco/segurança), anomalias detectadas e nível de atenção (normal/atenção/crítico). Este texto será lido por outro agente — seja direto e factual."
  },
  {
    "id": "write_memory",
    "step": 7,
    "type": "function",
    "inputs": {
      "summary": "{{memory_summary}}",
      "dimension": "financeiro",
      "ttl_hours": 26,
      "structured": {
        "severity": "{{severity}}",
        "saldo_total": "{{saldo_total}}",
        "saldo_conta_corrente": "{{saldo_conta_corrente}}",
        "total_debitos": "{{total_debitos}}",
        "total_creditos": "{{total_creditos}}",
        "saldo_projetado_final": "{{saldo_projetado_final}}",
        "runway_days": "{{runway_days}}",
        "recorrentes_detectadas": "{{recorrentes_detectadas}}",
        "alertas_fluxo": "{{alertas}}"
      }
    },
    "function": "memory.write_dimension_state",
    "on_failure": "continue"
  }
]'::jsonb
WHERE id = 'financeiro_monitor';
