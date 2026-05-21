-- ─────────────────────────────────────────────────────────────────────────────
-- MC-03 · Morning Chain seed update
--
-- 1. morning_sync: add on_complete.fire_event = 'morning_ready' to the
--    final alert step so daily_briefing is automatically triggered after sync.
-- 2. daily_briefing: change trigger from cron to event 'morning_ready' so
--    it only fires when morning_sync completes, not on a fixed schedule.
-- ─────────────────────────────────────────────────────────────────────────────

-- Update morning_sync steps to add on_complete hook on the alert step
UPDATE public.cross_agent_routines
SET steps = '[
  {
    "id": "check_health",
    "step": 1,
    "type": "function",
    "function": "integrations.check_health",
    "inputs": {"stale_hours": 8},
    "on_failure": "halt"
  },
  {
    "id": "get_schedule",
    "step": 2,
    "type": "function",
    "function": "analytics.get_daily_schedule",
    "inputs": {},
    "on_failure": "continue"
  },
  {
    "id": "alert",
    "step": 3,
    "type": "artifact",
    "function": "channels.create_alert",
    "inputs": {
      "title": "🔌 Sincronização da Manhã",
      "body": "{{health_report}}",
      "priority": "{{alert_priority}}",
      "agent_slug": "routine-runner"
    },
    "on_failure": "halt",
    "on_complete": {
      "fire_event": "morning_ready"
    }
  }
]'::jsonb
WHERE id = 'morning_sync';


-- Switch daily_briefing from cron to event trigger
UPDATE public.cross_agent_routines
SET trigger_type   = 'event',
    trigger_config = '{"event_type": "morning_ready"}'::jsonb
WHERE id = 'daily_briefing';
