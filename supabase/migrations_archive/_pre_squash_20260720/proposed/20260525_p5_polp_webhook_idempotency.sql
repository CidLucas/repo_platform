-- 20260525_p5_polp_webhook_idempotency.sql
-- P5: Hardening do webhook Polp
--   1) Idempotência por event_id (UNIQUE)
--   2) Auditoria mínima (status/erro/processed_at)
--
-- NÃO aplicar automaticamente. Lucas revisa.

BEGIN;

CREATE TABLE IF NOT EXISTS public.polp_webhook_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id text NOT NULL,
  event_type text NOT NULL,
  entity text,
  entity_id bigint,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'processed', 'failed')),
  error_message text,
  processed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT polp_webhook_events_event_id_key UNIQUE (event_id)
);

CREATE INDEX IF NOT EXISTS polp_webhook_events_created_at_idx
  ON public.polp_webhook_events (created_at DESC);

CREATE INDEX IF NOT EXISTS polp_webhook_events_status_idx
  ON public.polp_webhook_events (status);

-- RLS habilitada; escrita/leitura apenas via service role
ALTER TABLE public.polp_webhook_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.polp_webhook_events FROM anon, authenticated, PUBLIC;
GRANT ALL ON public.polp_webhook_events TO service_role;

COMMIT;
