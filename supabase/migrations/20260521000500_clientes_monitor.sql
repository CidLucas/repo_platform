-- ─────────────────────────────────────────────────────────────────────────────
-- Fase 1 · Arquitetura C — Room Monitors
--
-- CLI-MON-01 · ClientesMonitor (built-in, cron diário 06h30)
--
-- Steps:
--   1. analytics.get_client_pipeline  → ativos, em_risco, inativos, novos, pipeline_summary
--   2. analytics.query_inactive_clients → client_list (candidatos a reengajamento)
--   3. analytics.get_nps_data          → nps_avg, nps_summary
--   4. analytics.get_overdue_customers → overdue_list, overdue_count
--   5. skill: crm (segment_customers)  → memory_summary (prose para dimension_state)
--   6. memory.write_dimension_state    → grava dimension_state['clientes'] TTL 48h
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'clientes_monitor',
  'Monitor de Clientes Diário',
  'clientes',
  'clientes',
  'cron',
  '{"expression": "30 6 * * *"}'::jsonb,
  '[
    {"key": "days_inactive",    "label": "Mínimo de dias sem compra (inativo)",  "type": "number", "default": 30,  "required": false},
    {"key": "lookback_months",  "label": "Janela de atividade (meses)",          "type": "number", "default": 3,   "required": false},
    {"key": "ttl_hours",        "label": "TTL do estado em horas",                "type": "number", "default": 48,  "required": false}
  ]'::jsonb,
  '[
    {
      "id": "get_pipeline",
      "step": 1,
      "type": "function",
      "function": "analytics.get_client_pipeline",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "get_inactive",
      "step": 2,
      "type": "function",
      "function": "analytics.query_inactive_clients",
      "inputs": {
        "days_inactive":   "{{days_inactive}}",
        "lookback_months": "{{lookback_months}}"
      },
      "on_failure": "continue"
    },
    {
      "id": "get_nps",
      "step": 3,
      "type": "function",
      "function": "analytics.get_nps_data",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "get_overdue",
      "step": 4,
      "type": "function",
      "function": "analytics.get_overdue_customers",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "analyze_customers",
      "step": 5,
      "type": "skill",
      "skill_slug": "crm",
      "task_template": "Você é o ClientesMonitor da {{nome_empresa}}. Analise o estado atual da base de clientes e produza um resumo compacto (máximo 250 tokens) para ser injetado no contexto do agente.\n\nPipeline: {{pipeline_summary}}\nClientes inativos (>{{days_inactive}}d sem compra): {{client_list}}\nNPS: {{nps_summary}}\nInadimplentes: {{overdue_count}} cliente(s)\n\nGere um parágrafo conciso com: saúde da base (ativos/em risco/inativos), alertas de churn, situação de NPS e inadimplência. Nível de atenção: normal/atenção/crítico. Seja direto e factual — este texto será lido por outro agente.",
      "outputs": {"memory_summary": "resumo de clientes para dimension_state"},
      "on_failure": "continue"
    },
    {
      "id": "write_memory",
      "step": 6,
      "type": "function",
      "function": "memory.write_dimension_state",
      "inputs": {
        "dimension": "clientes",
        "summary":   "{{memory_summary}}",
        "structured": {
          "ativos_count":   "{{ativos}}",
          "em_risco_count": "{{em_risco}}",
          "inativos_count": "{{inativos}}",
          "novos_count":    "{{novos}}",
          "overdue_count":  "{{overdue_count}}",
          "nps_avg":        "{{nps_avg}}"
        },
        "ttl_hours": "{{ttl_hours}}"
      },
      "on_failure": "continue"
    }
  ]'::jsonb,
  'builtin'
)
ON CONFLICT (id) DO UPDATE SET
  name           = EXCLUDED.name,
  steps          = EXCLUDED.steps,
  config_schema  = EXCLUDED.config_schema,
  trigger_config = EXCLUDED.trigger_config;
