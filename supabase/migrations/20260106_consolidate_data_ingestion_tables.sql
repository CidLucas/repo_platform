-- =====================================================================
-- Data Ingestion Table Consolidation
-- =====================================================================
-- Purpose: Consolidate overlapping data ingestion tables
--   - data_source_credentials → credencial_servico_externo
--   - data_source_mappings → client_data_sources
--   - ingestion_jobs → connector_sync_history
--
-- This follows the same pattern as the client table consolidation
-- Created: 2026-01-06
-- =====================================================================

BEGIN;

-- =====================================================================
-- Phase 1: Enhance credencial_servico_externo
-- =====================================================================

-- Add missing fields from data_source_credentials
ALTER TABLE credencial_servico_externo
  ADD COLUMN IF NOT EXISTS connection_metadata JSONB,
  ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ;

COMMENT ON COLUMN credencial_servico_externo.connection_metadata IS
  'Additional connection settings (project_id, dataset_id, table_name, etc.)';

COMMENT ON COLUMN credencial_servico_externo.last_sync_at IS
  'Timestamp of last successful sync for this credential';

-- Migrate data from data_source_credentials (if table exists and has data)
DO $$
DECLARE
  v_count INTEGER;
BEGIN
  -- Check if legacy table exists
  SELECT COUNT(*)
  INTO v_count
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name = 'data_source_credentials';

  IF v_count > 0 THEN
    RAISE NOTICE 'Found data_source_credentials table, checking for data...';

    -- Check if any data exists
    EXECUTE 'SELECT COUNT(*) FROM data_source_credentials' INTO v_count;

    IF v_count > 0 THEN
      RAISE NOTICE 'Migrating % records from data_source_credentials...', v_count;

      -- Migrate data
      INSERT INTO credencial_servico_externo (
        client_id,
        nome_servico,
        tipo_servico,
        status,
        credenciais_cifradas,
        connection_metadata,
        last_sync_at,
        created_at,
        updated_at
      )
      SELECT
        client_id::uuid,
        nome_conexao,
        tipo_servico,
        status,
        COALESCE(connection_metadata::text, '{}'),
        connection_metadata,
        last_sync_at,
        created_at,
        updated_at
      FROM data_source_credentials
      WHERE NOT EXISTS (
        SELECT 1 FROM credencial_servico_externo cse
        WHERE cse.client_id = data_source_credentials.client_id::uuid
          AND cse.tipo_servico = data_source_credentials.tipo_servico
      );

      RAISE NOTICE 'Migration from data_source_credentials complete';
    ELSE
      RAISE NOTICE 'No data in data_source_credentials, skipping migration';
    END IF;
  ELSE
    RAISE NOTICE 'data_source_credentials table does not exist, skipping';
  END IF;
END $$;

-- =====================================================================
-- Phase 2: Enhance client_data_sources
-- =====================================================================

-- Add missing FK and fields from data_source_mappings
ALTER TABLE client_data_sources
  ADD COLUMN IF NOT EXISTS credential_id INTEGER REFERENCES credencial_servico_externo(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS source_columns JSONB,
  ADD COLUMN IF NOT EXISTS source_sample_data JSONB,
  ADD COLUMN IF NOT EXISTS unmapped_columns JSONB,
  ADD COLUMN IF NOT EXISTS ignored_columns JSONB,
  ADD COLUMN IF NOT EXISTS match_confidence JSONB,
  ADD COLUMN IF NOT EXISTS is_auto_generated BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS reviewed_by TEXT,
  ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_client_data_sources_credential_id
  ON client_data_sources(credential_id);

COMMENT ON COLUMN client_data_sources.credential_id IS
  'FK to credencial_servico_externo - which credential created this data source';

COMMENT ON COLUMN client_data_sources.source_columns IS
  'Original column schema from source (BigQuery INFORMATION_SCHEMA, CSV headers, etc.)';

COMMENT ON COLUMN client_data_sources.source_sample_data IS
  'Sample rows from source for preview and type inference';

COMMENT ON COLUMN client_data_sources.unmapped_columns IS
  'Source columns that could not be automatically mapped to canonical schema';

COMMENT ON COLUMN client_data_sources.ignored_columns IS
  'Source columns explicitly ignored by user';

COMMENT ON COLUMN client_data_sources.match_confidence IS
  'AI-generated confidence scores for automatic column mapping';

COMMENT ON COLUMN client_data_sources.is_auto_generated IS
  'Whether mapping was auto-generated or manually configured';

COMMENT ON COLUMN client_data_sources.reviewed_by IS
  'User ID who reviewed/approved the mapping';

COMMENT ON COLUMN client_data_sources.reviewed_at IS
  'When the mapping was last reviewed';

-- Migrate data from data_source_mappings (if table exists and has data)
DO $$
DECLARE
  v_count INTEGER;
BEGIN
  -- Check if legacy table exists
  SELECT COUNT(*)
  INTO v_count
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name = 'data_source_mappings';

  IF v_count > 0 THEN
    RAISE NOTICE 'Found data_source_mappings table, checking for data...';

    -- Check if any data exists
    EXECUTE 'SELECT COUNT(*) FROM data_source_mappings' INTO v_count;

    IF v_count > 0 THEN
      RAISE NOTICE 'Migrating % records from data_source_mappings...', v_count;

      -- Migrate data
      INSERT INTO client_data_sources (
        client_id,
        source_type,
        resource_type,
        storage_type,
        storage_location,
        column_mapping,
        credential_id,
        source_columns,
        source_sample_data,
        unmapped_columns,
        ignored_columns,
        match_confidence,
        sync_status,
        is_auto_generated,
        reviewed_by,
        reviewed_at,
        created_at,
        updated_at
      )
      SELECT
        dsm.client_id,
        dsm.source_type,
        dsm.source_resource,
        'unknown',
        COALESCE(dsm.source_table_full_name, ''),
        dsm.column_mapping,
        (SELECT cse.id FROM credencial_servico_externo cse
         WHERE cse.client_id::text = dsm.client_id
           AND cse.tipo_servico = dsm.source_type
         LIMIT 1) as credential_id,
        dsm.source_columns,
        dsm.source_sample_data,
        dsm.unmapped_columns,
        dsm.ignored_columns,
        dsm.match_confidence,
        dsm.status,
        dsm.is_auto_generated,
        dsm.reviewed_by,
        dsm.reviewed_at,
        dsm.created_at,
        dsm.updated_at
      FROM data_source_mappings dsm
      WHERE NOT EXISTS (
        SELECT 1 FROM client_data_sources cds
        WHERE cds.client_id = dsm.client_id
          AND cds.source_type = dsm.source_type
          AND cds.resource_type = dsm.source_resource
      );

      RAISE NOTICE 'Migration from data_source_mappings complete';
    ELSE
      RAISE NOTICE 'No data in data_source_mappings, skipping migration';
    END IF;
  ELSE
    RAISE NOTICE 'data_source_mappings table does not exist, skipping';
  END IF;
END $$;

-- =====================================================================
-- Phase 3: Enhance connector_sync_history
-- =====================================================================

-- Add useful fields from ingestion_jobs
ALTER TABLE connector_sync_history
  ADD COLUMN IF NOT EXISTS client_id UUID,
  ADD COLUMN IF NOT EXISTS job_id TEXT,
  ADD COLUMN IF NOT EXISTS mapping_id UUID,
  ADD COLUMN IF NOT EXISTS target_table TEXT,
  ADD COLUMN IF NOT EXISTS progress_percent INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS error_details JSONB;

-- Add unique constraint on job_id (if not null)
CREATE UNIQUE INDEX IF NOT EXISTS idx_connector_sync_history_job_id
  ON connector_sync_history(job_id) WHERE job_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_connector_sync_history_client_id
  ON connector_sync_history(client_id);

COMMENT ON COLUMN connector_sync_history.client_id IS
  'Redundant with credential FK but useful for direct queries';

COMMENT ON COLUMN connector_sync_history.job_id IS
  'Unique job identifier for tracking across services';

COMMENT ON COLUMN connector_sync_history.mapping_id IS
  'FK to client_data_sources - which mapping was used';

COMMENT ON COLUMN connector_sync_history.target_table IS
  'Destination table name (foreign_table, gold table, etc.)';

COMMENT ON COLUMN connector_sync_history.progress_percent IS
  'Current progress percentage (0-100) for in-progress jobs';

COMMENT ON COLUMN connector_sync_history.error_details IS
  'Detailed error information (stack trace, BigQuery error, etc.)';

-- Migrate data from ingestion_jobs (if table exists and has data)
DO $$
DECLARE
  v_count INTEGER;
BEGIN
  -- Check if legacy table exists
  SELECT COUNT(*)
  INTO v_count
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_name = 'ingestion_jobs';

  IF v_count > 0 THEN
    RAISE NOTICE 'Found ingestion_jobs table, checking for data...';

    -- Check if any data exists
    EXECUTE 'SELECT COUNT(*) FROM ingestion_jobs' INTO v_count;

    IF v_count > 0 THEN
      RAISE NOTICE 'Migrating % records from ingestion_jobs...', v_count;

      -- Migrate data
      INSERT INTO connector_sync_history (
        credential_id,
        client_id,
        status,
        sync_started_at,
        sync_completed_at,
        duration_seconds,
        records_processed,
        records_inserted,
        resource_type,
        error_message,
        job_id,
        mapping_id,
        target_table,
        progress_percent,
        error_details,
        created_at,
        updated_at
      )
      SELECT
        (SELECT cse.id FROM credencial_servico_externo cse
         WHERE cse.client_id::text = ij.client_id
         LIMIT 1) as credential_id,
        ij.client_id::uuid,
        ij.status,
        ij.started_at,
        ij.completed_at,
        EXTRACT(EPOCH FROM (ij.completed_at - ij.started_at))::integer as duration_seconds,
        COALESCE(ij.records_extracted, 0) + COALESCE(ij.records_loaded, 0) as records_processed,
        COALESCE(ij.records_loaded, 0) as records_inserted,
        ij.source_resource,
        ij.error_message,
        ij.job_id,
        ij.mapping_id,
        ij.target_table,
        ij.progress_percent,
        ij.error_details,
        ij.created_at,
        ij.updated_at
      FROM ingestion_jobs ij
      WHERE NOT EXISTS (
        SELECT 1 FROM connector_sync_history csh
        WHERE csh.job_id = ij.job_id
      )
      AND ij.job_id IS NOT NULL;

      RAISE NOTICE 'Migration from ingestion_jobs complete';
    ELSE
      RAISE NOTICE 'No data in ingestion_jobs, skipping migration';
    END IF;
  ELSE
    RAISE NOTICE 'ingestion_jobs table does not exist, skipping';
  END IF;
END $$;

-- =====================================================================
-- Phase 4: Drop Legacy Tables (only if they exist)
-- =====================================================================

-- Drop data_source_credentials
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'data_source_credentials'
  ) THEN
    RAISE NOTICE 'Dropping data_source_credentials...';
    DROP TABLE IF EXISTS data_source_credentials CASCADE;
    RAISE NOTICE 'data_source_credentials dropped';
  ELSE
    RAISE NOTICE 'data_source_credentials does not exist, skipping drop';
  END IF;
END $$;

-- Drop data_source_mappings
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'data_source_mappings'
  ) THEN
    RAISE NOTICE 'Dropping data_source_mappings...';
    DROP TABLE IF EXISTS data_source_mappings CASCADE;
    RAISE NOTICE 'data_source_mappings dropped';
  ELSE
    RAISE NOTICE 'data_source_mappings does not exist, skipping drop';
  END IF;
END $$;

-- Drop ingestion_jobs
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'ingestion_jobs'
  ) THEN
    RAISE NOTICE 'Dropping ingestion_jobs...';
    DROP TABLE IF EXISTS ingestion_jobs CASCADE;
    RAISE NOTICE 'ingestion_jobs dropped';
  ELSE
    RAISE NOTICE 'ingestion_jobs does not exist, skipping drop';
  END IF;
END $$;

-- =====================================================================
-- Phase 5: Update RLS Policies (if needed)
-- =====================================================================

-- No RLS changes needed - tables already have RLS enabled

-- =====================================================================
-- Phase 6: Grant Permissions
-- =====================================================================

-- Ensure service_role and authenticated have access to enhanced tables
GRANT SELECT, INSERT, UPDATE, DELETE ON credencial_servico_externo TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON client_data_sources TO authenticated, service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON connector_sync_history TO authenticated, service_role;

-- =====================================================================
-- Migration Summary
-- =====================================================================

DO $$
DECLARE
  v_cred_count INTEGER;
  v_source_count INTEGER;
  v_history_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO v_cred_count FROM credencial_servico_externo;
  SELECT COUNT(*) INTO v_source_count FROM client_data_sources;
  SELECT COUNT(*) INTO v_history_count FROM connector_sync_history;

  RAISE NOTICE '=====================================================';
  RAISE NOTICE 'Data Ingestion Table Consolidation Complete';
  RAISE NOTICE '=====================================================';
  RAISE NOTICE 'Final record counts:';
  RAISE NOTICE '  - credencial_servico_externo: % records', v_cred_count;
  RAISE NOTICE '  - client_data_sources: % records', v_source_count;
  RAISE NOTICE '  - connector_sync_history: % records', v_history_count;
  RAISE NOTICE '';
  RAISE NOTICE 'Legacy tables dropped:';
  RAISE NOTICE '  - data_source_credentials';
  RAISE NOTICE '  - data_source_mappings';
  RAISE NOTICE '  - ingestion_jobs';
  RAISE NOTICE '=====================================================';
END $$;

COMMIT;
