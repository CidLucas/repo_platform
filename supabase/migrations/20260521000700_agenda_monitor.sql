-- ─────────────────────────────────────────────────────────────────────────────
-- Fase 1 · Arquitetura C — Room Monitors
--
-- AGD-MON-01 · AgendaMonitor (built-in, cron diário 05h30 — antes dos outros monitors)
--
-- Steps:
--   1. agenda.get_calendar_events      → eventos do dia, busy_slots
--   2. agenda.get_upcoming_deadlines   → prazos próximos (7 dias)
--   3. agenda.get_upcoming_meetings    → reuniões próximas 24h
--   4. skill: agenda (build_timeline)  → memory_summary (prose para dimension_state)
--   5. memory.write_dimension_state    → grava dimension_state['agenda'] TTL 6h
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines
  (id, name, room, trigger_domain, trigger_type, trigger_config, config_schema, steps, visibility)
VALUES (
  'agenda_monitor',
  'Monitor de Agenda Diário',
  'agenda',
  'agenda',
  'cron',
  '{"expression": "30 5 * * *"}'::jsonb,
  '[
    {"key": "days_ahead",  "label": "Dias à frente para prazos",    "type": "number", "default": 7,  "required": false},
    {"key": "hours_ahead", "label": "Horas à frente para reuniões", "type": "number", "default": 24, "required": false},
    {"key": "ttl_hours",   "label": "TTL do estado em horas",        "type": "number", "default": 6,  "required": false}
  ]'::jsonb,
  '[
    {
      "id": "get_events",
      "step": 1,
      "type": "function",
      "function": "agenda.get_calendar_events",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "get_deadlines",
      "step": 2,
      "type": "function",
      "function": "agenda.get_upcoming_deadlines",
      "inputs": {"days_ahead": "{{days_ahead}}"},
      "on_failure": "continue"
    },
    {
      "id": "get_meetings",
      "step": 3,
      "type": "function",
      "function": "agenda.get_upcoming_meetings",
      "inputs": {"hours_ahead": "{{hours_ahead}}"},
      "on_failure": "continue"
    },
    {
      "id": "build_timeline",
      "step": 4,
      "type": "skill",
      "skill_slug": "agenda",
      "task_template": "Você é o AgendaMonitor da {{nome_empresa}}. Analise o estado atual da agenda e produza um resumo compacto (máximo 250 tokens) para ser injetado no contexto do agente.\n\nEventos de hoje: {{eventos}}\nPrazos próximos ({{days_ahead}}d): {{prazos}}\nReuniões próximas ({{hours_ahead}}h): {{meeting_count}} reunião(ões)\n\nGere um parágrafo conciso com: compromissos críticos do dia, prazos iminentes (≤3 dias) e conflitos de agenda detectados. Nível de atenção: normal/atenção/crítico. Seja direto e factual — este texto será lido por outro agente.",
      "outputs": {"memory_summary": "resumo de agenda para dimension_state"},
      "on_failure": "continue"
    },
    {
      "id": "write_memory",
      "step": 5,
      "type": "function",
      "function": "memory.write_dimension_state",
      "inputs": {
        "dimension": "agenda",
        "summary":   "{{memory_summary}}",
        "structured": {
          "meeting_count":   "{{meeting_count}}",
          "eventos":         "{{eventos}}",
          "prazos_proximos": "{{prazos}}"
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
