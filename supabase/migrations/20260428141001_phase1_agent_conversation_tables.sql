-- =============================================================================
-- Migration: Phase 1 — Agent conversation and unified messaging baseline
-- Date: 2026-04-28
-- Purpose: Conversation thread container + channel-agnostic messages table
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- conversa: thread/session container for agent conversations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.conversa (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id  UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conversa_client ON public.conversa(client_id);

-- -----------------------------------------------------------------------------
-- messages: unified channel-agnostic message store
--   - agent chat:    channel='chat', role=user|assistant|system|tool, session_id set
--   - WhatsApp/SMS:  channel='whatsapp'|'sms', direction=inbound|outbound, provider='twilio'
--   - email:         channel='email', provider='sendgrid'|etc
--   - sender_ref:    external identifier (phone number, email address, dim_clientes ref)
--   - contact info comes from analytics_v2.dim_clientes, not a local contacts table
-- -----------------------------------------------------------------------------
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

COMMIT;
