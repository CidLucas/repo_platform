-- =============================================================================
-- Migration: Post-baseline messaging consolidation
-- Date: 2026-04-28
-- Purpose: Unify consumer_messages + mensagem into messages table;
--          drop consumer_contacts, twilio_inbound_routes, rfq_requests, purchase_orders
-- =============================================================================

BEGIN;

-- Drop tables being replaced or removed
DROP TABLE IF EXISTS public.consumer_messages    CASCADE;
DROP TABLE IF EXISTS public.consumer_contacts    CASCADE;
DROP TABLE IF EXISTS public.twilio_inbound_routes CASCADE;
DROP TABLE IF EXISTS public.mensagem             CASCADE;
DROP TABLE IF EXISTS public.purchase_orders      CASCADE;
DROP TABLE IF EXISTS public.rfq_requests         CASCADE;

-- Unified channel-agnostic messages table
-- session_id links to conversa for agent chat threads
-- sender_ref stores the external identifier (phone, email, etc.)
-- channel distinguishes the transport; provider stores the vendor (twilio, sendgrid, etc.)
CREATE TABLE IF NOT EXISTS public.messages (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id   UUID        NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  session_id  UUID        REFERENCES public.conversa(id) ON DELETE SET NULL,
  channel     TEXT        NOT NULL CHECK (channel IN ('chat','whatsapp','sms','email','api')),
  direction   TEXT        CHECK (direction IN ('inbound','outbound')),
  role        TEXT        CHECK (role IN ('user','assistant','system','tool')),
  body        TEXT,
  media_urls  TEXT[],
  status      TEXT        DEFAULT 'received',
  provider    TEXT,
  sender_ref  TEXT,
  metadata    JSONB       DEFAULT '{}',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_client  ON public.messages(client_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session ON public.messages(session_id) WHERE session_id IS NOT NULL;

ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "own client" ON public.messages FOR ALL TO authenticated
  USING (client_id = public.get_my_client_id());

COMMIT;
