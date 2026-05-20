-- ─────────────────────────────────────────────────────────────────────────────
-- Register daily_insights as a first-class catalog routine.
--
-- This migrates the orphaned daily_insights CLI script into the unified
-- catalog + execution queue system, so it runs via the existing
-- pg_cron → dispatch_routine_executions() → /internal/routines/run-dispatched
-- pipeline instead of a standalone scheduler.
--
-- Changes:
--   1. Add visibility column to cross_agent_routines ('user' | 'system').
--      System routines are always-on, hidden from RoutinesPanel.
--   2. Allow 'system' as source and 'cron' as trigger_type in client_routines.
--   3. Seed daily_insights into cross_agent_routines catalog.
--   4. Auto-enroll all existing tenants in client_routines.
--   5. DB trigger to auto-enroll every new tenant going forward.
-- ─────────────────────────────────────────────────────────────────────────────


-- ── 1. Add visibility to cross_agent_routines ────────────────────────────────

ALTER TABLE public.cross_agent_routines
  ADD COLUMN IF NOT EXISTS visibility text DEFAULT 'user';

ALTER TABLE public.cross_agent_routines
  DROP CONSTRAINT IF EXISTS cross_agent_routines_visibility_check;

ALTER TABLE public.cross_agent_routines
  ADD CONSTRAINT cross_agent_routines_visibility_check
  CHECK (visibility IN ('user', 'system'));


-- ── 2. Extend client_routines constraints ────────────────────────────────────
--
-- 'system' source: always-on routine managed by platform, not user-created.
-- 'cron' trigger_type: mirrors cross_agent_routines.trigger_type values.

ALTER TABLE public.client_routines
  DROP CONSTRAINT IF EXISTS client_routines_source_check;

ALTER TABLE public.client_routines
  ADD CONSTRAINT client_routines_source_check
  CHECK (source IN ('catalog', 'custom', 'system'));

ALTER TABLE public.client_routines
  DROP CONSTRAINT IF EXISTS client_routines_trigger_type_check;

ALTER TABLE public.client_routines
  ADD CONSTRAINT client_routines_trigger_type_check
  CHECK (trigger_type IN ('manual', 'document', 'schedule', 'event', 'numeric', 'cron'));


-- ── 3. Seed daily_insights into catalog ─────────────────────────────────────
--
-- Single function step: calls insights.run_daily from routine_functions.py,
-- which wraps daily_insights.run_for_client(client_id).
-- 'room' = 'home' because insights span all rooms (not domain-specific).

INSERT INTO public.cross_agent_routines (
  id, name, room, trigger_type, trigger_config, steps, created_at, visibility
)
VALUES (
  'daily_insights',
  'Insights Diários',
  'home',
  'cron',
  '{"expression": "0 6 * * *"}'::jsonb,
  '[{
    "id": "generate_insights",
    "step": 1,
    "type": "function",
    "function": "insights.run_daily",
    "on_failure": "halt"
  }]'::jsonb,
  now(),
  'system'
)
ON CONFLICT (id) DO UPDATE SET
  name           = EXCLUDED.name,
  trigger_type   = EXCLUDED.trigger_type,
  trigger_config = EXCLUDED.trigger_config,
  steps          = EXCLUDED.steps,
  visibility     = EXCLUDED.visibility;


-- ── 4. Auto-enroll all existing tenants ─────────────────────────────────────
--
-- ON CONFLICT DO NOTHING relies on the existing UNIQUE (client_id, routine_id)
-- constraint on client_routines, so re-running this migration is safe.

INSERT INTO public.client_routines (
  id, client_id, routine_id, notify_channel, config,
  source, status, active, trigger_type, trigger_config, created_at
)
SELECT
  gen_random_uuid(),
  c.client_id,
  'daily_insights',
  'app',
  '{}'::jsonb,
  'system',
  'active',
  true,
  'cron',
  '{"expression": "0 6 * * *"}'::jsonb,
  now()
FROM public.clientes_blu c
ON CONFLICT (client_id, routine_id) DO NOTHING;


-- ── 5. DB trigger: auto-enroll new tenants in all system routines ────────────
--
-- Fires AFTER INSERT on clientes_blu. Enrolls the new client into every
-- cross_agent_routines row where visibility='system'.
-- Safe to run multiple times: ON CONFLICT (client_id, routine_id) DO NOTHING.

CREATE OR REPLACE FUNCTION public.auto_enroll_system_routines()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.client_routines (
    id, client_id, routine_id, notify_channel, config,
    source, status, active, trigger_type, trigger_config, created_at
  )
  SELECT
    gen_random_uuid(),
    NEW.client_id,
    r.id,
    'app',
    '{}'::jsonb,
    'system',
    'active',
    true,
    r.trigger_type,
    r.trigger_config,
    now()
  FROM public.cross_agent_routines r
  WHERE r.visibility = 'system'
  ON CONFLICT (client_id, routine_id) DO NOTHING;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_auto_enroll_system_routines ON public.clientes_blu;

CREATE TRIGGER trg_auto_enroll_system_routines
  AFTER INSERT ON public.clientes_blu
  FOR EACH ROW EXECUTE FUNCTION public.auto_enroll_system_routines();
