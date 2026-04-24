-- Migration: per-client Google Calendar settings
-- Date: 2026-04-23
-- Phase: Dashboard mocks → live data, Phase 1
--
-- Adds public.calendar_settings — read by the google-calendar-events Edge
-- Function (Phase 3) to know which calendar to pull and whether the integration
-- is enabled. RLS-scoped via public.get_my_client_id().

CREATE TABLE IF NOT EXISTS public.calendar_settings (
  client_id    text PRIMARY KEY,
  calendar_id  text NOT NULL DEFAULT 'primary',
  enabled      boolean NOT NULL DEFAULT false,
  range_days   int NOT NULL DEFAULT 7 CHECK (range_days BETWEEN 1 AND 60),
  timezone     text NOT NULL DEFAULT 'America/Sao_Paulo',
  updated_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.calendar_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS calendar_settings_select ON public.calendar_settings;
CREATE POLICY calendar_settings_select ON public.calendar_settings
  FOR SELECT TO authenticated
  USING (client_id = public.get_my_client_id());

DROP POLICY IF EXISTS calendar_settings_insert ON public.calendar_settings;
CREATE POLICY calendar_settings_insert ON public.calendar_settings
  FOR INSERT TO authenticated
  WITH CHECK (client_id = public.get_my_client_id());

DROP POLICY IF EXISTS calendar_settings_update ON public.calendar_settings;
CREATE POLICY calendar_settings_update ON public.calendar_settings
  FOR UPDATE TO authenticated
  USING (client_id = public.get_my_client_id())
  WITH CHECK (client_id = public.get_my_client_id());

DROP POLICY IF EXISTS calendar_settings_service ON public.calendar_settings;
CREATE POLICY calendar_settings_service ON public.calendar_settings
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- Trigger to keep updated_at fresh
CREATE OR REPLACE FUNCTION public.tg_calendar_settings_touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_calendar_settings_touch ON public.calendar_settings;
CREATE TRIGGER trg_calendar_settings_touch
  BEFORE UPDATE ON public.calendar_settings
  FOR EACH ROW
  EXECUTE FUNCTION public.tg_calendar_settings_touch_updated_at();

-- Bootstrap a disabled row for every existing client so the Edge Function
-- gracefully returns `{ disabled: true }` until each client opts in.
INSERT INTO public.calendar_settings (client_id, enabled)
SELECT client_id::text, false
FROM public.clientes_vizu
ON CONFLICT (client_id) DO NOTHING;

COMMENT ON TABLE public.calendar_settings IS
  'Per-client Google Calendar integration settings. RLS-scoped via public.get_my_client_id().';
