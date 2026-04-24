-- Migration: client_routines — per-tenant automation registry
-- Phase: Landing Onboarding Wire-up, Phase 1 (Foundation)
-- Date: 2026-04-23
--
-- First-class registry for built-in automations selected in the landing
-- CommandRules step. The scheduler is TBD; this table is the contract the
-- future scheduler + the CommandRules UI will agree on.

CREATE TABLE IF NOT EXISTS public.client_routines (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id      uuid        NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
  routine_id     text        NOT NULL,
  enabled        boolean     NOT NULL DEFAULT true,
  config         jsonb       NOT NULL DEFAULT '{}'::jsonb,
  notify_channel text        NOT NULL DEFAULT 'email'
    CHECK (notify_channel IN ('email', 'whatsapp', 'app')),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, routine_id)
);

COMMENT ON TABLE public.client_routines IS
  'Per-tenant registry of enabled routines / automations. '
  'routine_id mirrors apps/landing/src/onboarding/state.ts::RoutineId.';
COMMENT ON COLUMN public.client_routines.routine_id IS
  'Logical routine identifier (e.g. daily_sales_digest, low_stock_alert). Backing scheduler TBD.';
COMMENT ON COLUMN public.client_routines.config IS
  'Per-routine parameters (cron, thresholds, recipients). Shape depends on routine_id.';

CREATE INDEX IF NOT EXISTS idx_client_routines_client
  ON public.client_routines (client_id) WHERE enabled;

-- RLS -------------------------------------------------------------------------
ALTER TABLE public.client_routines ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS client_routines_select ON public.client_routines;
CREATE POLICY client_routines_select ON public.client_routines
  FOR SELECT TO authenticated
  USING (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_routines_insert ON public.client_routines;
CREATE POLICY client_routines_insert ON public.client_routines
  FOR INSERT TO authenticated
  WITH CHECK (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_routines_update ON public.client_routines;
CREATE POLICY client_routines_update ON public.client_routines
  FOR UPDATE TO authenticated
  USING (client_id::text = public.get_my_client_id())
  WITH CHECK (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_routines_delete ON public.client_routines;
CREATE POLICY client_routines_delete ON public.client_routines
  FOR DELETE TO authenticated
  USING (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS client_routines_service_role ON public.client_routines;
CREATE POLICY client_routines_service_role ON public.client_routines
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);
