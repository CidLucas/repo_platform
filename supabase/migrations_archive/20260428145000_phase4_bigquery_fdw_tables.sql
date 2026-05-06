-- =============================================================================
-- Migration: Phase 4 — BigQuery FDW tables baseline
-- Date: 2026-04-28
-- Purpose: Create BigQuery foreign server and table registry structures
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- bigquery_servers
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.bigquery_servers (
  id           UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id    TEXT  NOT NULL UNIQUE,
  server_name  TEXT  NOT NULL UNIQUE,
  project_id   TEXT  NOT NULL,
  dataset_id   TEXT  NOT NULL,
  vault_key_id UUID  NOT NULL,
  location     TEXT  DEFAULT 'US',
  created_at   TIMESTAMPTZ DEFAULT now(),
  updated_at   TIMESTAMPTZ DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- bigquery_foreign_tables
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.bigquery_foreign_tables (
  id                 UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id          TEXT  NOT NULL,
  table_name         TEXT  NOT NULL,
  foreign_table_name TEXT  NOT NULL,
  bigquery_table     TEXT  NOT NULL,
  server_name        TEXT  NOT NULL REFERENCES public.bigquery_servers(server_name) ON DELETE CASCADE,
  columns            JSONB NOT NULL,
  location           TEXT  DEFAULT 'US',
  created_at         TIMESTAMPTZ DEFAULT now(),
  UNIQUE (client_id, table_name)
);

COMMIT;
