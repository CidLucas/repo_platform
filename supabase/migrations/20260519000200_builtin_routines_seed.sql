-- ─────────────────────────────────────────────────────────────────────────────
-- Built-in platform routines — seed
--
-- Six daily/weekly operational routines available to all clients.
-- All use trigger_type='cron'. No LLM steps — pure function + artifact.
-- Cron expressions are in UTC; defaults target BRL timezone (UTC-3).
--
-- Routines:
--   1. daily_briefing          — Plano do Dia          (07:30 BRL = 10:30 UTC)
--   2. morning_sync            — Sincronização da Manhã (07:00 BRL = 10:00 UTC)
--   3. pending_decisions_review— Revisão de Decisões   (08:00 BRL = 11:00 UTC)
--   4. deadline_radar          — Radar de Prazos       (09:00 BRL = 12:00 UTC)
--   5. end_of_day_digest       — Digest do Fim de Dia  (18:00 BRL = 21:00 UTC)
--   6. weekly_summary          — Resumo Semanal        (17:00 BRL Fri = 20:00 UTC Fri)
-- ─────────────────────────────────────────────────────────────────────────────


-- ── 1. Plano do Dia ──────────────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines (id, name, room, trigger_domain, trigger_type, trigger_config, steps, config_schema)
VALUES (
  'daily_briefing',
  'Plano do Dia',
  'estrategia',
  'estrategia',
  'cron',
  '{"expression": "30 10 * * *"}'::jsonb,
  '[
    {
      "id": "get_pending",
      "step": 1,
      "type": "function",
      "function": "analytics.get_pending_approvals",
      "inputs": {"limit": 5},
      "on_failure": "continue"
    },
    {
      "id": "get_kpis",
      "step": 2,
      "type": "function",
      "function": "analytics.get_kpi_snapshots",
      "inputs": {"window_days": 1, "baseline_days": 7},
      "on_failure": "continue"
    },
    {
      "id": "get_agenda",
      "step": 3,
      "type": "function",
      "function": "agenda.get_calendar_events",
      "inputs": {"window_hours": 18},
      "on_failure": "continue"
    },
    {
      "id": "alert",
      "step": 4,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "☀️ Plano do Dia",
        "body": "{{pending_summary}}\n\n{{kpi_summary}}\n\n{{calendar_summary}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  '[
    {"key": "hour",   "label": "Hora",   "type": "int", "default": 10, "required": false},
    {"key": "minute", "label": "Minuto", "type": "int", "default": 30, "required": false}
  ]'::jsonb
)
ON CONFLICT (id) DO NOTHING;


-- ── 2. Sincronização da Manhã ─────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines (id, name, room, trigger_domain, trigger_type, trigger_config, steps, config_schema)
VALUES (
  'morning_sync',
  'Sincronização da Manhã',
  'estrategia',
  'estrategia',
  'cron',
  '{"expression": "0 10 * * *"}'::jsonb,
  '[
    {
      "id": "check_health",
      "step": 1,
      "type": "function",
      "function": "integrations.check_health",
      "inputs": {"stale_hours": 8},
      "on_failure": "halt"
    },
    {
      "id": "alert",
      "step": 2,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "🔌 Sincronização da Manhã",
        "body": "{{health_report}}",
        "priority": "{{alert_priority}}",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  '[]'::jsonb
)
ON CONFLICT (id) DO NOTHING;


-- ── 3. Revisão de Decisões Pendentes ─────────────────────────────────────────

INSERT INTO public.cross_agent_routines (id, name, room, trigger_domain, trigger_type, trigger_config, steps, config_schema)
VALUES (
  'pending_decisions_review',
  'Revisão de Decisões Pendentes',
  'estrategia',
  'estrategia',
  'cron',
  '{"expression": "0 11 * * *"}'::jsonb,
  '[
    {
      "id": "get_overdue",
      "step": 1,
      "type": "function",
      "function": "analytics.get_overdue_approvals",
      "inputs": {"threshold_hours": 24},
      "on_failure": "halt"
    },
    {
      "id": "alert",
      "step": 2,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "⏳ Revisão de Decisões Pendentes",
        "body": "{{overdue_summary}}",
        "priority": "{{alert_priority}}",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  '[
    {"key": "threshold_hours", "label": "Horas para considerar atrasado", "type": "int", "default": 24, "required": false}
  ]'::jsonb
)
ON CONFLICT (id) DO NOTHING;


-- ── 4. Radar de Prazos ────────────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines (id, name, room, trigger_domain, trigger_type, trigger_config, steps, config_schema)
VALUES (
  'deadline_radar',
  'Radar de Prazos',
  'agenda',
  'agenda',
  'cron',
  '{"expression": "0 12 * * *"}'::jsonb,
  '[
    {
      "id": "scan_deadlines",
      "step": 1,
      "type": "function",
      "function": "agenda.get_upcoming_deadlines",
      "inputs": {"days_ahead": 15},
      "on_failure": "halt"
    },
    {
      "id": "alert",
      "step": 2,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "📅 Radar de Prazos",
        "body": "{{deadline_summary}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  '[
    {"key": "days_ahead", "label": "Dias à frente", "type": "int", "default": 15, "required": false}
  ]'::jsonb
)
ON CONFLICT (id) DO NOTHING;


-- ── 5. Digest do Fim de Dia ───────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines (id, name, room, trigger_domain, trigger_type, trigger_config, steps, config_schema)
VALUES (
  'end_of_day_digest',
  'Digest do Fim de Dia',
  'estrategia',
  'estrategia',
  'cron',
  '{"expression": "0 21 * * *"}'::jsonb,
  '[
    {
      "id": "get_activity",
      "step": 1,
      "type": "function",
      "function": "analytics.get_daily_activity",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "get_pending",
      "step": 2,
      "type": "function",
      "function": "analytics.get_pending_approvals",
      "inputs": {"limit": 5},
      "on_failure": "continue"
    },
    {
      "id": "alert",
      "step": 3,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "🌅 Digest do Dia",
        "body": "{{activity_summary}}\n\n**Pendências para amanhã:**\n{{pending_summary}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  '[
    {"key": "hour",   "label": "Hora",   "type": "int", "default": 21, "required": false},
    {"key": "minute", "label": "Minuto", "type": "int", "default": 0,  "required": false}
  ]'::jsonb
)
ON CONFLICT (id) DO NOTHING;


-- ── 6. Resumo Semanal ─────────────────────────────────────────────────────────

INSERT INTO public.cross_agent_routines (id, name, room, trigger_domain, trigger_type, trigger_config, steps, config_schema)
VALUES (
  'weekly_summary',
  'Resumo Semanal',
  'estrategia',
  'estrategia',
  'cron',
  '{"expression": "0 20 * * 5"}'::jsonb,
  '[
    {
      "id": "get_kpis",
      "step": 1,
      "type": "function",
      "function": "analytics.get_kpi_snapshots",
      "inputs": {"window_days": 7, "baseline_days": 28},
      "on_failure": "continue"
    },
    {
      "id": "get_activity",
      "step": 2,
      "type": "function",
      "function": "analytics.get_weekly_activity",
      "inputs": {},
      "on_failure": "continue"
    },
    {
      "id": "alert",
      "step": 3,
      "type": "artifact",
      "function": "channels.create_alert",
      "inputs": {
        "title": "📊 Resumo da Semana",
        "body": "{{kpi_summary}}\n\n{{weekly_activity_summary}}",
        "priority": "normal",
        "agent_slug": "routine-runner"
      },
      "on_failure": "halt"
    }
  ]'::jsonb,
  '[
    {"key": "day_of_week", "label": "Dia da semana (0=Dom…6=Sáb)", "type": "int", "default": 5, "required": false},
    {"key": "hour",        "label": "Hora",                         "type": "int", "default": 20, "required": false}
  ]'::jsonb
)
ON CONFLICT (id) DO NOTHING;
