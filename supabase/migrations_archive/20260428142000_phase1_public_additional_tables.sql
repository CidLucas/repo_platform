-- =============================================================================
-- Migration: Phase 1 — Public additional tables baseline
-- Date: 2026-04-28
-- Purpose: Create remaining core public reporting and agent tables
-- Note: consumer_contacts, consumer_messages, twilio_inbound_routes removed —
--       contact data lives in analytics_v2.dim_clientes; messaging in public.messages.
--       purchase_orders and rfq_requests removed — transactions enter via fato_transacoes.
-- =============================================================================

BEGIN;

-- supplier_roster removed: operational supplier data lives in analytics_v2.dim_fornecedores

-- -----------------------------------------------------------------------------
-- report_schedules
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.report_schedules (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id      UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  name           TEXT        NOT NULL,
  report_type    TEXT        NOT NULL,
  cron_expr      TEXT,
  recipients     TEXT[],
  config         JSONB       DEFAULT '{}',
  active         BOOLEAN     DEFAULT true,
  last_run_at    TIMESTAMPTZ,
  next_run_at    TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- report_runs
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.report_runs (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  schedule_id UUID        REFERENCES public.report_schedules(id) ON DELETE CASCADE,
  client_id   UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  status      TEXT        NOT NULL DEFAULT 'pending'
              CHECK (status IN ('pending','running','completed','failed')),
  output_url  TEXT,
  error       TEXT,
  started_at  TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  metadata    JSONB       DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_report_runs_client ON public.report_runs(client_id, started_at DESC);

-- -----------------------------------------------------------------------------
-- client_insights
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.client_insights (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id    UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  dimension    TEXT        NOT NULL,
  title        TEXT        NOT NULL,
  body         TEXT,
  severity     TEXT        DEFAULT 'info' CHECK (severity IN ('info','warning','critical')),
  dismissed    BOOLEAN     DEFAULT false,
  dismissed_at TIMESTAMPTZ,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_insights_client_active ON public.client_insights(client_id, dismissed, generated_at DESC);

-- -----------------------------------------------------------------------------
-- kpi_catalog
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.kpi_catalog (
  slug             TEXT        PRIMARY KEY,
  dimension        TEXT        NOT NULL CHECK (dimension IN ('finance','commercial','inventory','supply','marketing','admin')),
  label            TEXT        NOT NULL,
  formula          TEXT        NOT NULL,
  unit             TEXT        NOT NULL DEFAULT 'number' CHECK (unit IN ('number','currency','percent','days','hours','ratio','count')),
  is_leading       BOOLEAN     NOT NULL DEFAULT false,
  tier_required    TEXT        NOT NULL DEFAULT 'BASIC' CHECK (tier_required IN ('BASIC','SME','PRO','PREMIUM','ENTERPRISE','ADMIN')),
  data_status      TEXT        NOT NULL DEFAULT 'live' CHECK (data_status IN ('live','proxy','external','pending_data')),
  rpc_column       TEXT,
  description      TEXT,
  references_url   TEXT,
  sort_order       INTEGER     NOT NULL DEFAULT 0,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- client_dimension_kpis
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.client_dimension_kpis (
  client_id  UUID  NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  dimension  TEXT  NOT NULL,
  slug       TEXT  NOT NULL REFERENCES public.kpi_catalog(slug) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (client_id, dimension, slug)
);

-- -----------------------------------------------------------------------------
-- agent_catalog
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.agent_catalog (
  id               UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  name             TEXT    NOT NULL,
  slug             TEXT    NOT NULL UNIQUE,
  description      TEXT,
  category         TEXT,
  icon             TEXT,
  agent_config     JSONB   NOT NULL DEFAULT '{}',
  prompt_name      TEXT    NOT NULL,
  required_context JSONB   DEFAULT '[]',
  required_files   JSONB   DEFAULT '{}',
  requires_google  BOOLEAN DEFAULT false,
  tier_required    TEXT    DEFAULT 'BASIC',
  landing_slug     TEXT,
  workflow_graph   JSONB,
  is_active        BOOLEAN DEFAULT true,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- client_enabled_agents
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.client_enabled_agents (
  client_id    UUID  NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  agent_slug   TEXT  NOT NULL REFERENCES public.agent_catalog(slug) ON DELETE CASCADE,
  config       JSONB DEFAULT '{}',
  enabled_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (client_id, agent_slug)
);

-- -----------------------------------------------------------------------------
-- client_routines
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.client_routines (
  id             UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id      UUID    NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  routine_id     TEXT    NOT NULL,
  notify_channel TEXT    NOT NULL DEFAULT 'app' CHECK (notify_channel IN ('email','whatsapp','app')),
  config         JSONB   DEFAULT '{}',
  active         BOOLEAN DEFAULT true,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (client_id, routine_id)
);

-- -----------------------------------------------------------------------------
-- standalone_agent_sessions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.standalone_agent_sessions (
  id                    UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id             UUID    NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  agent_catalog_id      UUID    NOT NULL REFERENCES public.agent_catalog(id) ON DELETE RESTRICT,
  session_id            TEXT    NOT NULL UNIQUE,
  config_status         TEXT    DEFAULT 'configuring' CHECK (config_status IN ('configuring','ready','active','archived')),
  collected_context     JSONB   DEFAULT '{}',
  uploaded_file_ids     UUID[]  DEFAULT ARRAY[]::UUID[],
  uploaded_document_ids UUID[]  DEFAULT ARRAY[]::UUID[],
  google_account_email  TEXT,
  metadata              JSONB   DEFAULT '{}',
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
