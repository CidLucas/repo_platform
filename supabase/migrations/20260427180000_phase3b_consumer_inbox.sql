-- Migration: Phase 3B (C3.1, C3.2) — consumer inbox foundation.
--
-- Consolidates inbound consumer messages (WhatsApp + Gmail) into a single
-- threaded inbox so the Comercial agent can draft replies and the
-- dashboard can present a unified view.
--
-- Tables:
--   public.consumer_contacts   one row per (client_id, channel, external_id)
--   public.consumer_messages   one row per inbound/outbound message
--
-- Views:
--   public.consumer_inbox_threads  thread rollup (last message + counts)
--
-- RPCs:
--   list_inbox_threads(p_period text default '30d', p_limit int default 50)
--   get_thread_messages(p_contact_id uuid, p_limit int default 100)
--
-- Tickets: BLU-MVP-050, BLU-MVP-051.

BEGIN;

-- ─────────────────────────────────────────────────────────────────────
-- 1. consumer_contacts
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.consumer_contacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
    channel         TEXT NOT NULL CHECK (channel IN ('whatsapp', 'gmail')),
    external_id     TEXT NOT NULL,                           -- phone (E.164) or email
    display_name    TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (client_id, channel, external_id)
);

CREATE INDEX IF NOT EXISTS idx_consumer_contacts_client
    ON public.consumer_contacts(client_id);

ALTER TABLE public.consumer_contacts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS consumer_contacts_select_own ON public.consumer_contacts;
CREATE POLICY consumer_contacts_select_own
    ON public.consumer_contacts FOR SELECT
    USING (client_id = public.get_my_client_id()::uuid);

DROP POLICY IF EXISTS consumer_contacts_service ON public.consumer_contacts;
CREATE POLICY consumer_contacts_service
    ON public.consumer_contacts FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ─────────────────────────────────────────────────────────────────────
-- 2. consumer_messages
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.consumer_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id       UUID NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
    contact_id      UUID NOT NULL REFERENCES public.consumer_contacts(id) ON DELETE CASCADE,
    channel         TEXT NOT NULL CHECK (channel IN ('whatsapp', 'gmail')),
    direction       TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    status          TEXT NOT NULL DEFAULT 'received'
                    CHECK (status IN ('received', 'draft', 'pending_approval',
                                       'approved', 'sent', 'failed')),
    body            TEXT NOT NULL,
    external_id     TEXT,                                    -- Twilio SID or Gmail msg id
    sent_at         TIMESTAMPTZ,
    failure_reason  TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by      UUID,                                    -- auth.uid() for dashboard sends
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_consumer_messages_contact
    ON public.consumer_messages(contact_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_consumer_messages_client_status
    ON public.consumer_messages(client_id, status);

ALTER TABLE public.consumer_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS consumer_messages_select_own ON public.consumer_messages;
CREATE POLICY consumer_messages_select_own
    ON public.consumer_messages FOR SELECT
    USING (client_id = public.get_my_client_id()::uuid);

DROP POLICY IF EXISTS consumer_messages_service ON public.consumer_messages;
CREATE POLICY consumer_messages_service
    ON public.consumer_messages FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ─────────────────────────────────────────────────────────────────────
-- 3. Inbox thread view + RPCs
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW public.consumer_inbox_threads
WITH (security_invoker = on)
AS
SELECT
    cc.id                                              AS contact_id,
    cc.client_id,
    cc.channel,
    cc.external_id,
    cc.display_name,
    last_msg.body                                      AS last_message_preview,
    last_msg.direction                                 AS last_direction,
    last_msg.status                                    AS last_status,
    last_msg.created_at                                AS last_message_at,
    COALESCE(unread.count, 0)                          AS unread_count,
    COALESCE(total.count, 0)                           AS message_count
  FROM public.consumer_contacts cc
  LEFT JOIN LATERAL (
        SELECT body, direction, status, created_at
          FROM public.consumer_messages cm
         WHERE cm.contact_id = cc.id
         ORDER BY cm.created_at DESC
         LIMIT 1
    ) last_msg ON true
  LEFT JOIN LATERAL (
        SELECT count(*)::int AS count
          FROM public.consumer_messages cm
         WHERE cm.contact_id  = cc.id
           AND cm.direction   = 'inbound'
           AND (cm.metadata ->> 'read')::boolean IS DISTINCT FROM true
    ) unread ON true
  LEFT JOIN LATERAL (
        SELECT count(*)::int AS count
          FROM public.consumer_messages cm
         WHERE cm.contact_id = cc.id
    ) total ON true;

GRANT SELECT ON public.consumer_inbox_threads TO authenticated, service_role;

-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.list_inbox_threads(
    p_limit int DEFAULT 50
)
RETURNS TABLE (
    contact_id              uuid,
    channel                 text,
    external_id             text,
    display_name            text,
    last_message_preview    text,
    last_direction          text,
    last_status             text,
    last_message_at         timestamptz,
    unread_count            int,
    message_count           int
)
LANGUAGE sql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
    SELECT contact_id, channel, external_id, display_name,
           last_message_preview, last_direction, last_status, last_message_at,
           unread_count, message_count
      FROM public.consumer_inbox_threads
     WHERE client_id = public.get_my_client_id()::uuid
     ORDER BY last_message_at DESC NULLS LAST
     LIMIT GREATEST(1, LEAST(p_limit, 200));
$$;

GRANT EXECUTE ON FUNCTION public.list_inbox_threads(int) TO authenticated, service_role;

-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.get_thread_messages(
    p_contact_id uuid,
    p_limit      int DEFAULT 100
)
RETURNS TABLE (
    id          uuid,
    direction   text,
    status      text,
    body        text,
    sent_at     timestamptz,
    created_at  timestamptz,
    metadata    jsonb
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_client_id uuid := public.get_my_client_id()::uuid;
BEGIN
    -- Ensure caller owns the contact (defence-in-depth alongside RLS).
    IF NOT EXISTS (
        SELECT 1 FROM public.consumer_contacts cc
         WHERE cc.id = p_contact_id AND cc.client_id = v_client_id
    ) THEN
        RAISE EXCEPTION 'get_thread_messages: contact not found or not owned'
            USING ERRCODE = '42501';
    END IF;

    RETURN QUERY
        SELECT cm.id, cm.direction, cm.status, cm.body,
               cm.sent_at, cm.created_at, cm.metadata
          FROM public.consumer_messages cm
         WHERE cm.contact_id = p_contact_id
         ORDER BY cm.created_at ASC
         LIMIT GREATEST(1, LEAST(p_limit, 500));
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_thread_messages(uuid, int) TO authenticated, service_role;

-- ─────────────────────────────────────────────────────────────────────
-- 4. Approval-decision trigger for outbound consumer messages
-- ─────────────────────────────────────────────────────────────────────
--
-- When `approval_requests.action = 'send_consumer_reply'` flips to
-- approved/rejected, mirror the decision onto the linked
-- `consumer_messages` row (payload.message_id):
--
--   approved  → status = 'approved'   (separate worker dispatches)
--   rejected  → status = 'failed'     + failure_reason
--
-- The actual send happens via `send_consumer_reply` tool path; this
-- trigger only flips status. The tool/router is responsible for
-- dispatching once status='approved'.

CREATE OR REPLACE FUNCTION public.tg_approval_apply_consumer_message()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_msg_id uuid;
BEGIN
    IF NEW.status NOT IN ('approved', 'rejected') THEN
        RETURN NEW;
    END IF;
    IF OLD.status = NEW.status THEN
        RETURN NEW;
    END IF;
    IF NEW.action <> 'send_consumer_reply' THEN
        RETURN NEW;
    END IF;

    v_msg_id := NULLIF(NEW.payload ->> 'message_id', '')::uuid;
    IF v_msg_id IS NULL THEN
        RAISE LOG 'tg_approval_apply_consumer_message: approval % missing payload.message_id',
                  NEW.id;
        RETURN NEW;
    END IF;

    IF NEW.status = 'approved' THEN
        UPDATE public.consumer_messages
           SET status = 'approved'
         WHERE id = v_msg_id
           AND client_id = NEW.client_id
           AND status IN ('pending_approval', 'draft');
    ELSE
        UPDATE public.consumer_messages
           SET status         = 'failed',
               failure_reason = COALESCE(NEW.decision_reason, 'rejected by approver')
         WHERE id = v_msg_id
           AND client_id = NEW.client_id
           AND status IN ('pending_approval', 'draft');
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS approval_apply_consumer_message ON public.approval_requests;
CREATE TRIGGER approval_apply_consumer_message
    AFTER UPDATE ON public.approval_requests
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION public.tg_approval_apply_consumer_message();

COMMENT ON FUNCTION public.tg_approval_apply_consumer_message IS
    'Phase 3B (C3.2): mirror Approval Engine decisions onto consumer_messages.status.';

COMMIT;
