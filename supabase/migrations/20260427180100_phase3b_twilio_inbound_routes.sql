-- Phase 3B (C3.1) — Twilio inbound routing table.
--
-- Maps the Twilio number a message was sent **to** back to a tenant
-- (``client_id``). Without this mapping a single shared Twilio number can
-- only serve one tenant; with it we can multi-tenant the inbound webhook.
--
-- Rows are inserted by Ops when provisioning a tenant's WhatsApp number.

BEGIN;

CREATE TABLE IF NOT EXISTS public.twilio_inbound_routes (
    twilio_number   TEXT PRIMARY KEY,
    client_id       UUID NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
    label           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_twilio_inbound_routes_client
    ON public.twilio_inbound_routes(client_id);

ALTER TABLE public.twilio_inbound_routes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS twilio_inbound_routes_service ON public.twilio_inbound_routes;
CREATE POLICY twilio_inbound_routes_service
    ON public.twilio_inbound_routes FOR ALL TO service_role
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS twilio_inbound_routes_select_own ON public.twilio_inbound_routes;
CREATE POLICY twilio_inbound_routes_select_own
    ON public.twilio_inbound_routes FOR SELECT
    USING (client_id = public.get_my_client_id()::uuid);

COMMIT;
