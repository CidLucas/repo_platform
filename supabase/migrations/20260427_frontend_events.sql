-- =============================================================================
-- Migration: frontend_events table + RPC
-- Date: 2026-04-27
-- Purpose:
--   Lightweight client-side event store for D1 engagement indicators:
--     - dashboard.insight.ctr         (user clicks "Explicar" on an insight card)
--     - dashboard.chat_rail.opened    (user opens the chat rail via chip or button)
--     - dashboard.demo_live.switch    (user clicks "Conectar minha loja" from demo banner)
--
--   The activation funnel dashboard (Phase D4) reads these to measure post-signup
--   product engagement, complementing the signup-→-connector funnel.
-- =============================================================================

BEGIN;

-- ── Table ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.frontend_events (
  id         bigserial PRIMARY KEY,
  client_id  uuid        NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
  event_name text        NOT NULL,
  properties jsonb       NOT NULL DEFAULT '{}',
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS frontend_events_client_name_idx
  ON public.frontend_events (client_id, event_name, occurred_at DESC);

CREATE INDEX IF NOT EXISTS frontend_events_name_day_idx
  ON public.frontend_events (event_name, date_trunc('day', occurred_at));

-- ── RLS ───────────────────────────────────────────────────────────────────────
ALTER TABLE public.frontend_events ENABLE ROW LEVEL SECURITY;

-- Tenants may only insert their own events; no reads via RLS (admin only).
CREATE POLICY "tenant_insert_own_events"
  ON public.frontend_events
  FOR INSERT
  WITH CHECK (
    client_id = (
      SELECT client_id FROM public.clientes_vizu
      WHERE auth_user_id = auth.uid()
      LIMIT 1
    )
  );

-- ── RPC — record_frontend_event ───────────────────────────────────────────────
-- Called from the dashboard SPA. Resolves client_id from the JWT automatically.
CREATE OR REPLACE FUNCTION public.record_frontend_event(
  p_event_name  text,
  p_properties  jsonb DEFAULT '{}'
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_client_id uuid;
BEGIN
  SELECT client_id INTO v_client_id
  FROM public.clientes_vizu
  WHERE auth_user_id = auth.uid()
  LIMIT 1;

  IF v_client_id IS NULL THEN
    RETURN; -- unauthenticated or no tenant mapping — silent no-op
  END IF;

  INSERT INTO public.frontend_events (client_id, event_name, properties)
  VALUES (v_client_id, p_event_name, coalesce(p_properties, '{}'));
END;
$$;

COMMENT ON FUNCTION public.record_frontend_event(text, jsonb) IS
  'Fire-and-forget frontend event tracking for D1 engagement indicators. '
  'Resolves client_id from JWT; silently ignores unauthenticated calls.';

-- ── Analytics view — d1_engagement_summary ───────────────────────────────────
-- Used by the activation funnel dashboard to show D1 metric totals.
CREATE OR REPLACE VIEW public.d1_engagement_summary AS
SELECT
  event_name,
  COUNT(DISTINCT client_id)              AS unique_tenants,
  COUNT(*)                               AS total_events,
  COUNT(*) FILTER (WHERE occurred_at >= now() - interval '7 days')  AS events_last_7d,
  COUNT(*) FILTER (WHERE occurred_at >= now() - interval '24 hours') AS events_last_24h
FROM public.frontend_events
WHERE event_name IN (
  'dashboard.insight.ctr',
  'dashboard.chat_rail.opened',
  'dashboard.demo_live.switch'
)
GROUP BY event_name
ORDER BY total_events DESC;

COMMENT ON VIEW public.d1_engagement_summary IS
  'Aggregated D1 engagement indicator counts for the internal activation funnel dashboard.';

COMMIT;
