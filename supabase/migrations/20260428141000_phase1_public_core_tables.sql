-- =============================================================================
-- Migration: Phase 1 — Public core tables baseline
-- Date: 2026-04-28
-- Purpose: Create core tenant, credential, integration, audit, and event tables
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1.1 credencial_servico_externo
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.credencial_servico_externo (
  id          BIGSERIAL PRIMARY KEY,
  client_id   TEXT        NOT NULL,
  tipo        TEXT        NOT NULL,
  credenciais JSONB       NOT NULL DEFAULT '{}',
  nome        TEXT,
  ativo       BOOLEAN     NOT NULL DEFAULT true,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT credencial_servico_externo_tipo_check CHECK (tipo IN ('bigquery','google_drive','google_sheets','google_docs','google_calendar'))
);
CREATE INDEX IF NOT EXISTS idx_credencial_client_id ON public.credencial_servico_externo(client_id);

-- -----------------------------------------------------------------------------
-- 1.2 clientes_blu
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.clientes_blu (
  client_id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  external_user_id        TEXT        UNIQUE,
  api_key                 TEXT        UNIQUE DEFAULT gen_random_uuid()::text,
  nome_empresa            TEXT        NOT NULL DEFAULT 'Empresa',
  tier                    TEXT        DEFAULT 'free',
  collection_rag          TEXT        DEFAULT 'default_collection',
  company_profile         JSONB,
  team_structure          JSONB,
  policies                JSONB,
  onboarding_state        JSONB       DEFAULT '{}'::jsonb,
  onboarding_completed_at TIMESTAMPTZ,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT clientes_blu_auth_check CHECK (api_key IS NOT NULL OR external_user_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_clientes_blu_external_user ON public.clientes_blu(external_user_id);

-- -----------------------------------------------------------------------------
-- 1.3 client_data_sources
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.client_data_sources (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id         TEXT        NOT NULL,
  credential_id     BIGINT      REFERENCES public.credencial_servico_externo(id) ON DELETE SET NULL,
  source_type       TEXT        NOT NULL,
  resource_type     TEXT        NOT NULL,
  storage_type      TEXT        NOT NULL,
  storage_location  TEXT        NOT NULL,
  column_mapping    JSONB,
  source_columns    JSONB,
  source_sample_data JSONB,
  sync_status       TEXT        DEFAULT 'pending',
  last_synced_at    TIMESTAMPTZ,
  atualizado_em     TIMESTAMPTZ DEFAULT now(),
  error_message     TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT unique_client_source_resource UNIQUE (client_id, source_type, resource_type)
);
CREATE INDEX IF NOT EXISTS idx_cds_client_id ON public.client_data_sources(client_id);
CREATE INDEX IF NOT EXISTS idx_cds_credential_id ON public.client_data_sources(credential_id);

-- -----------------------------------------------------------------------------
-- 1.5 uploaded_files_metadata
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.uploaded_files_metadata (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id     UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  file_name     TEXT        NOT NULL,
  storage_path  TEXT        NOT NULL,
  bucket        TEXT        NOT NULL DEFAULT 'file-uploads',
  mime_type     TEXT,
  size_bytes    BIGINT,
  status        TEXT        DEFAULT 'uploaded',
  metadata      JSONB       DEFAULT '{}'::jsonb,
  content_hash  TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_client ON public.uploaded_files_metadata(client_id);

-- -----------------------------------------------------------------------------
-- 1.6 integration_configs
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.integration_configs (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id     UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  provider      TEXT        NOT NULL,
  config        JSONB       NOT NULL DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (client_id, provider)
);

-- -----------------------------------------------------------------------------
-- 1.7 integration_tokens
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.integration_tokens (
  id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id               UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  provider                TEXT        NOT NULL,
  account_email           TEXT        NOT NULL DEFAULT '',
  access_token_encrypted  TEXT,
  refresh_token_encrypted TEXT,
  token_type              TEXT        DEFAULT 'Bearer',
  scopes                  TEXT[],
  is_default              BOOLEAN     DEFAULT false,
  metadata                JSONB       DEFAULT '{}'::jsonb,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (client_id, provider, account_email)
);
CREATE INDEX IF NOT EXISTS idx_tokens_client_provider ON public.integration_tokens(client_id, provider);

-- -----------------------------------------------------------------------------
-- 1.9 nps_responses
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.nps_responses (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id   UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  score       INTEGER     NOT NULL CHECK (score BETWEEN 0 AND 10),
  comment     TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_nps_client ON public.nps_responses(client_id);

-- -----------------------------------------------------------------------------
-- 1.10 frontend_events
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.frontend_events (
  id         BIGSERIAL   PRIMARY KEY,
  client_id  UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  event_name TEXT        NOT NULL,
  properties JSONB       DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_fe_client_event ON public.frontend_events(client_id, event_name);
CREATE INDEX IF NOT EXISTS idx_fe_created_at ON public.frontend_events(created_at DESC);

-- -----------------------------------------------------------------------------
-- 1.11 audit_log
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.audit_log (
  id          BIGSERIAL   PRIMARY KEY,
  client_id   UUID,
  actor_id    TEXT,
  action      TEXT        NOT NULL,
  entity_type TEXT,
  entity_id   TEXT,
  payload     JSONB       DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_client ON public.audit_log(client_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON public.audit_log(created_at DESC);

-- -----------------------------------------------------------------------------
-- 1.8 calendar_settings  (read by google-calendar-events edge function)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.calendar_settings (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id   UUID        NOT NULL REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  calendar_id TEXT,
  enabled     BOOLEAN     NOT NULL DEFAULT false,
  range_days  INTEGER     NOT NULL DEFAULT 30,
  timezone    TEXT        NOT NULL DEFAULT 'America/Sao_Paulo',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (client_id)
);

-- -----------------------------------------------------------------------------
-- 1.12 approval_requests
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.approval_requests (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id    UUID        REFERENCES public.clientes_blu(client_id) ON DELETE CASCADE,
  requested_by TEXT,
  action_type  TEXT        NOT NULL,
  payload      JSONB       NOT NULL DEFAULT '{}',
  status       TEXT        NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending','approved','rejected','cancelled')),
  decided_by   TEXT,
  decided_at   TIMESTAMPTZ,
  expires_at   TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_approval_client_status ON public.approval_requests(client_id, status);

COMMIT;
