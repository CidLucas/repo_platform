-- ─────────────────────────────────────────────────────────────────────────────
-- INF-05 · calendar_watch_channels
-- Stores the Google Calendar watch channel registration (channel_id → client)
-- so the webhook receiver can resolve inbound push notifications to a client.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.calendar_watch_channels (
  id           uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
  channel_id   text        NOT NULL,
  client_id    uuid        NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  calendar_id  text        NOT NULL DEFAULT 'primary',
  resource_id  text,
  expires_at   timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (client_id, calendar_id)
);

CREATE INDEX IF NOT EXISTS idx_calendar_watch_channel_id ON public.calendar_watch_channels (channel_id);

ALTER TABLE public.calendar_watch_channels ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service role only" ON public.calendar_watch_channels
  USING (false);  -- only accessible via service_role; no direct user access


-- ─────────────────────────────────────────────────────────────────────────────
-- cross_agent_routines · visibility column
-- 'builtin' = shipped with platform, shown by default to all clients
-- 'optional' = available but not shown unless explicitly enabled
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.cross_agent_routines
  ADD COLUMN IF NOT EXISTS visibility text NOT NULL DEFAULT 'builtin'
    CHECK (visibility IN ('builtin', 'optional', 'hidden'));


-- ─────────────────────────────────────────────────────────────────────────────
-- INF-06 · Schema additions
--
-- NPS fields on dim_clientes and estoque_minimo on dim_inventory.
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE analytics_v2.dim_clientes
  ADD COLUMN IF NOT EXISTS nps_score          numeric,
  ADD COLUMN IF NOT EXISTS nps_data_coletada  date,
  ADD COLUMN IF NOT EXISTS nps_detalhes       jsonb;

ALTER TABLE analytics_v2.dim_inventory
  ADD COLUMN IF NOT EXISTS estoque_minimo     numeric;
