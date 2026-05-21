-- ─────────────────────────────────────────────────────────────────────────────
-- Fase 1 · Arquitetura C — Room Monitors
--
-- OPS-MON-01 · ComprasMonitor (built-in, cron diário 07h)
--
-- Steps:
--   1. analytics.get_inventory_alerts  → criticos, proximos, total_ok, inventory_summary
--   2. analytics.get_supplier_orders   → fornecedores, supplier_summary
--   3. skill: compras (analyze_stock)  → memory_summary (prose para dimension_state)
--   4. memory.write_dimension_state    → grava dimension_state['compras'] TTL 24h
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'compras_monitor',
  'Monitor de Compras Diário',
  'compras',
  'compras',
  'cron',
  '{"expression": "0 7 * * *"}'::jsonb,
  '[
    {"key": "threshold_global", "label": "Estoque mínimo global (fallback)",  "type": "number", "default": 10, "required": false},
    {"key": "supplier_days",    "label": "Janela de pedidos de fornecedor (d)", "type": "number", "default": 30, "required": false},
    {"key": "ttl_hours",        "label": "TTL do estado em horas",               "type": "number", "default": 24, "required": false}
  ]'::jsonb,
  '[
    {
      "id": "get_inventory",
      "step": 1,
      "type": "function",
      "function": "analytics.get_inventory_alerts",
      "inputs": {"threshold_global": "{{threshold_global}}"},
      "on_failure": "continue"
    },
    {
      "id": "get_suppliers",
      "step": 2,
      "type": "function",
      "function": "analytics.get_supplier_orders",
      "inputs": {"days": "{{supplier_days}}"},
      "on_failure": "continue"
    },
    {
      "id": "analyze_stock",
      "step": 3,
      "type": "skill",
      "skill_slug": "compras",
      "task_template": "Você é o ComprasMonitor da {{nome_empresa}}. Analise o estado atual de estoque e compras e produza um resumo compacto (máximo 250 tokens) para ser injetado no contexto do agente.\n\nEstoque:\n{{inventory_summary}}\n\nFornecedores ({{supplier_days}}d):\n{{supplier_summary}}\n\nGere um parágrafo conciso com: SKUs críticos (quantidade e risco de ruptura), alertas de fornecedores com pedidos atrasados, e saúde geral do estoque. Nível de atenção: normal/atenção/crítico. Seja direto e factual — este texto será lido por outro agente.",
      "outputs": {"memory_summary": "resumo de compras para dimension_state"},
      "on_failure": "continue"
    },
    {
      "id": "write_memory",
      "step": 4,
      "type": "function",
      "function": "memory.write_dimension_state",
      "inputs": {
        "dimension": "compras",
        "summary":   "{{memory_summary}}",
        "structured": {
          "criticos_count":  "{{criticos}}",
          "proximos_count":  "{{proximos}}",
          "total_ok":        "{{total_ok}}",
          "fornecedores":    "{{fornecedores}}"
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
