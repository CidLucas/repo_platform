-- =============================================================================
-- Migration: Add Column Auto-Discovery, Sample Data, and Enhanced Logging
-- Date: 2026-03-02
-- Purpose: Enhance data ingestion pipeline with:
--   1. Automatic column discovery from BigQuery foreign tables
--   2. Sample data extraction for UI preview
--   3. Comprehensive logging throughout sync RPCs
--   4. Progress tracking and error handling improvements
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. COLUMN AUTO-DISCOVERY FUNCTION
-- =============================================================================

-- Discovers columns from a BigQuery foreign table via information_schema
-- and populates client_data_sources.source_columns
CREATE OR REPLACE FUNCTION public.descobrir_colunas_foreign_table(
  p_client_id TEXT,
  p_foreign_table_name TEXT
) RETURNS JSONB AS $$
DECLARE
  v_columns JSONB;
  v_column_count INTEGER;
  v_data_source_id UUID;
BEGIN
  RAISE LOG '[descobrir_colunas] Starting column discovery for client_id=%, foreign_table=%',
    p_client_id, p_foreign_table_name;

  -- Query information_schema to get column metadata
  SELECT jsonb_agg(
    jsonb_build_object(
      'name', column_name,
      'type', data_type,
      'position', ordinal_position,
      'is_nullable', is_nullable,
      'character_maximum_length', character_maximum_length,
      'numeric_precision', numeric_precision,
      'numeric_scale', numeric_scale
    ) ORDER BY ordinal_position
  )
  INTO v_columns
  FROM information_schema.columns
  WHERE table_schema || '.' || table_name = p_foreign_table_name;

  IF v_columns IS NULL THEN
    RAISE LOG '[descobrir_colunas] ERROR: No columns found for foreign table: %', p_foreign_table_name;
    RAISE EXCEPTION 'Foreign table not found or has no columns: %', p_foreign_table_name;
  END IF;

  v_column_count := jsonb_array_length(v_columns);
  RAISE LOG '[descobrir_colunas] Discovered % columns from foreign table %',
    v_column_count, p_foreign_table_name;

  -- Update client_data_sources with discovered columns
  UPDATE public.client_data_sources
  SET
    source_columns = v_columns,
    sync_status = 'pending',
    atualizado_em = NOW()
  WHERE
    client_id = p_client_id
    AND storage_location = p_foreign_table_name
  RETURNING id INTO v_data_source_id;

  IF v_data_source_id IS NULL THEN
    -- No existing record - create one
    RAISE LOG '[descobrir_colunas] No existing data source found, creating new record';

    INSERT INTO public.client_data_sources (
      client_id,
      source_type,
      resource_type,
      storage_type,
      storage_location,
      source_columns,
      sync_status
    ) VALUES (
      p_client_id,
      'bigquery',
      'invoices', -- Default, can be updated later
      'foreign_table',
      p_foreign_table_name,
      v_columns,
      'pending'
    )
    RETURNING id INTO v_data_source_id;

    RAISE LOG '[descobrir_colunas] Created new data source record with id=%', v_data_source_id;
  ELSE
    RAISE LOG '[descobrir_colunas] Updated existing data source id=%', v_data_source_id;
  END IF;

  RETURN jsonb_build_object(
    'success', TRUE,
    'column_count', v_column_count,
    'data_source_id', v_data_source_id,
    'columns', v_columns
  );

EXCEPTION
  WHEN OTHERS THEN
    RAISE LOG '[descobrir_colunas] ERROR: % - %', SQLERRM, SQLSTATE;
    RETURN jsonb_build_object(
      'success', FALSE,
      'error', SQLERRM,
      'error_code', SQLSTATE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.descobrir_colunas_foreign_table IS
  'Automatically discovers column schema from a BigQuery foreign table and updates client_data_sources';

-- =============================================================================
-- 2. SAMPLE DATA EXTRACTION FUNCTION
-- =============================================================================

-- Safely extracts first N rows from BigQuery foreign table for UI preview
CREATE OR REPLACE FUNCTION public.obter_dados_amostrais(
  p_client_id TEXT,
  p_foreign_table_name TEXT,
  p_sample_size INTEGER DEFAULT 10,
  p_timeout_seconds INTEGER DEFAULT 30
) RETURNS JSONB AS $$
DECLARE
  v_sample_data JSONB;
  v_row_count INTEGER;
  v_query TEXT;
  v_start_time TIMESTAMPTZ;
  v_duration_ms INTEGER;
BEGIN
  v_start_time := clock_timestamp();

  RAISE LOG '[obter_dados_amostrais] Starting sample data extraction for client_id=%, table=%, limit=%',
    p_client_id, p_foreign_table_name, p_sample_size;

  -- Set statement timeout to prevent hanging on slow BigQuery queries
  EXECUTE format('SET LOCAL statement_timeout = %L', (p_timeout_seconds * 1000)::TEXT);

  -- Build dynamic query to fetch sample data as JSONB array
  v_query := format(
    'SELECT jsonb_agg(row_to_json(t.*)) FROM (SELECT * FROM %s LIMIT %s) t',
    p_foreign_table_name,
    p_sample_size
  );

  RAISE LOG '[obter_dados_amostrais] Executing query: %', v_query;

  -- Execute query and capture results
  EXECUTE v_query INTO v_sample_data;

  -- Calculate duration
  v_duration_ms := EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)) * 1000;

  IF v_sample_data IS NULL THEN
    v_row_count := 0;
    v_sample_data := '[]'::JSONB;
    RAISE LOG '[obter_dados_amostrais] WARNING: Query returned no rows (empty table or access denied)';
  ELSE
    v_row_count := jsonb_array_length(v_sample_data);
    RAISE LOG '[obter_dados_amostrais] Successfully extracted % sample rows in % ms',
      v_row_count, v_duration_ms;
  END IF;

  -- Update client_data_sources with sample data
  UPDATE public.client_data_sources
  SET
    source_sample_data = v_sample_data,
    atualizado_em = NOW()
  WHERE
    client_id = p_client_id
    AND storage_location = p_foreign_table_name;

  RETURN jsonb_build_object(
    'success', TRUE,
    'row_count', v_row_count,
    'duration_ms', v_duration_ms,
    'sample_data', v_sample_data
  );

EXCEPTION
  WHEN query_canceled THEN
    RAISE LOG '[obter_dados_amostrais] ERROR: Query timeout after %s seconds', p_timeout_seconds;
    RETURN jsonb_build_object(
      'success', FALSE,
      'error', 'Query timeout - BigQuery table may be very large or slow',
      'error_code', 'QUERY_TIMEOUT',
      'timeout_seconds', p_timeout_seconds
    );
  WHEN OTHERS THEN
    RAISE LOG '[obter_dados_amostrais] ERROR: % - %', SQLERRM, SQLSTATE;
    RETURN jsonb_build_object(
      'success', FALSE,
      'error', SQLERRM,
      'error_code', SQLSTATE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.obter_dados_amostrais IS
  'Safely extracts sample rows from BigQuery foreign table with timeout protection';

-- =============================================================================
-- 3. ENHANCED CREATE_BIGQUERY_FOREIGN_TABLE WITH AUTO-DISCOVERY
-- =============================================================================

-- Drop the existing function to recreate with new parameters
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(TEXT, TEXT, TEXT, JSONB, TEXT);

-- Update create_bigquery_foreign_table to automatically discover columns after creation
CREATE FUNCTION public.create_bigquery_foreign_table(
  p_client_id TEXT,
  p_table_name TEXT,
  p_bigquery_table TEXT,
  p_columns JSONB,
  p_location TEXT DEFAULT 'US',
  p_timeout_ms INT DEFAULT 300000,
  p_auto_discover BOOLEAN DEFAULT TRUE -- New parameter
) RETURNS JSONB AS $$
DECLARE
  v_server_name TEXT;
  v_project_id TEXT;
  v_dataset_id TEXT;
  v_foreign_table_name TEXT;
  v_column_defs TEXT;
  v_schema_name TEXT := 'bigquery';
  v_table_subquery TEXT;
  v_full_bigquery_path TEXT;
  v_result JSONB;
  v_discovery_result JSONB;
  v_sample_result JSONB;
  v_start_time TIMESTAMPTZ;
  v_duration_ms INTEGER;
BEGIN
  v_start_time := clock_timestamp();

  RAISE LOG '[create_bigquery_foreign_table] Starting FDW creation for client_id=%, table=%, auto_discover=%',
    p_client_id, p_table_name, p_auto_discover;

  -- Get server name and BigQuery identifiers for client
  SELECT server_name, project_id, dataset_id
  INTO v_server_name, v_project_id, v_dataset_id
  FROM public.bigquery_servers
  WHERE client_id = p_client_id;

  IF v_server_name IS NULL THEN
    RAISE LOG '[create_bigquery_foreign_table] ERROR: No BigQuery server found for client: %', p_client_id;
    RAISE EXCEPTION 'No BigQuery server found for client: %', p_client_id;
  END IF;

  -- Generate foreign table name (Postgres identifier - use underscores)
  v_foreign_table_name := v_schema_name || '.' || p_client_id || '_' || p_table_name;

  RAISE LOG '[create_bigquery_foreign_table] Foreign table name: %', v_foreign_table_name;

  -- Build fully-qualified BigQuery table path with backtick quoting
  v_full_bigquery_path := '`' || v_project_id || '`.`' || v_dataset_id || '`.`' || p_bigquery_table || '`';

  -- Use SUBQUERY format for full control over BigQuery SQL
  v_table_subquery := '(select * from ' || v_full_bigquery_path || ')';

  -- Build column definitions from jsonb
  SELECT string_agg(
    quote_ident(col->>'name') || ' ' || (col->>'type'),
    ', '
  )
  FROM jsonb_array_elements(p_columns) AS col
  INTO v_column_defs;

  IF v_column_defs IS NULL THEN
    RAISE LOG '[create_bigquery_foreign_table] ERROR: Invalid columns definition';
    RAISE EXCEPTION 'Invalid columns definition';
  END IF;

  -- Drop existing table if it exists
  EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s', v_foreign_table_name);
  RAISE LOG '[create_bigquery_foreign_table] Dropped existing foreign table (if any)';

  -- Create foreign table with SUBQUERY and TIMEOUT options
  EXECUTE format(
    'CREATE FOREIGN TABLE %s (%s)
     SERVER %I
     OPTIONS (
       table %L,
       location %L,
       timeout %L
     )',
    v_foreign_table_name,
    v_column_defs,
    v_server_name,
    v_table_subquery,
    p_location,
    p_timeout_ms::TEXT
  );

  v_duration_ms := EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)) * 1000;
  RAISE LOG '[create_bigquery_foreign_table] Foreign table created successfully in % ms', v_duration_ms;

  -- Store metadata
  INSERT INTO public.bigquery_foreign_tables (
    client_id,
    table_name,
    foreign_table_name,
    bigquery_table,
    server_name,
    columns,
    location
  ) VALUES (
    p_client_id,
    p_table_name,
    v_foreign_table_name,
    v_full_bigquery_path,
    v_server_name,
    p_columns,
    p_location
  )
  ON CONFLICT (client_id, table_name)
  DO UPDATE SET
    foreign_table_name = EXCLUDED.foreign_table_name,
    bigquery_table = EXCLUDED.bigquery_table,
    columns = EXCLUDED.columns,
    location = EXCLUDED.location,
    updated_at = NOW();

  v_result := jsonb_build_object(
    'success', TRUE,
    'foreign_table_name', v_foreign_table_name,
    'bigquery_table', v_full_bigquery_path,
    'table_option', v_table_subquery,
    'timeout_ms', p_timeout_ms,
    'columns', p_columns,
    'creation_time_ms', v_duration_ms
  );

  -- Auto-discover columns if requested
  IF p_auto_discover THEN
    RAISE LOG '[create_bigquery_foreign_table] Starting automatic column discovery';

    SELECT public.descobrir_colunas_foreign_table(p_client_id, v_foreign_table_name)
    INTO v_discovery_result;

    v_result := v_result || jsonb_build_object('discovery', v_discovery_result);

    -- Only fetch sample data if discovery succeeded
    IF (v_discovery_result->>'success')::BOOLEAN THEN
      RAISE LOG '[create_bigquery_foreign_table] Starting sample data extraction';

      SELECT public.obter_dados_amostrais(p_client_id, v_foreign_table_name, 10, 30)
      INTO v_sample_result;

      v_result := v_result || jsonb_build_object('sample_data', v_sample_result);
    ELSE
      RAISE LOG '[create_bigquery_foreign_table] Skipping sample data extraction due to discovery failure';
    END IF;
  END IF;

  RAISE LOG '[create_bigquery_foreign_table] Completed successfully';
  RETURN v_result;

EXCEPTION
  WHEN OTHERS THEN
    RAISE LOG '[create_bigquery_foreign_table] ERROR: % - %', SQLERRM, SQLSTATE;
    RETURN jsonb_build_object(
      'success', FALSE,
      'error', SQLERRM,
      'error_code', SQLSTATE,
      'error_detail', SQLSTATE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.create_bigquery_foreign_table IS
  'Creates a foreign table mapping to BigQuery with automatic column discovery and sample data extraction';

-- =============================================================================
-- 4. GRANT PERMISSIONS
-- =============================================================================

GRANT EXECUTE ON FUNCTION public.descobrir_colunas_foreign_table TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.obter_dados_amostrais TO authenticated, service_role;

-- =============================================================================
-- 5. CREATE AUDIT LOG TABLE FOR DETAILED OPERATION TRACKING
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.ingestion_audit_log (
  id BIGSERIAL PRIMARY KEY,
  cliente_vizu_id UUID,
  client_id TEXT,
  credential_id INTEGER,
  sync_id BIGINT, -- FK to connector_sync_history
  operation TEXT NOT NULL, -- 'sync_start', 'extraction', 'transformation', 'load', 'aggregation', 'sync_complete'
  status TEXT NOT NULL, -- 'info', 'warning', 'error', 'success'
  message TEXT,
  details JSONB, -- Structured context (duration_ms, rows_processed, etc.)
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ingestion_audit_log_sync_id ON public.ingestion_audit_log(sync_id);
CREATE INDEX idx_ingestion_audit_log_client_id ON public.ingestion_audit_log(client_id);
CREATE INDEX idx_ingestion_audit_log_created_at ON public.ingestion_audit_log(created_at DESC);
CREATE INDEX idx_ingestion_audit_log_operation ON public.ingestion_audit_log(operation);

-- RLS policy for audit log
ALTER TABLE public.ingestion_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY ingestion_audit_log_client_isolation ON public.ingestion_audit_log
  FOR SELECT
  USING (
    client_id = current_setting('app.current_client_id', TRUE)
    OR cliente_vizu_id = (current_setting('app.current_cliente_id', TRUE))::UUID
  );

CREATE POLICY ingestion_audit_log_service_role ON public.ingestion_audit_log
  FOR ALL
  TO service_role
  USING (TRUE);

GRANT SELECT ON public.ingestion_audit_log TO authenticated;
GRANT ALL ON public.ingestion_audit_log TO service_role;

COMMENT ON TABLE public.ingestion_audit_log IS
  'Detailed audit log for data ingestion pipeline operations with structured logging';

-- =============================================================================
-- 6. HELPER FUNCTION FOR LOGGING
-- =============================================================================

CREATE OR REPLACE FUNCTION public.log_ingestion_event(
  p_sync_id BIGINT,
  p_operation TEXT,
  p_status TEXT,
  p_message TEXT,
  p_details JSONB DEFAULT NULL,
  p_client_id TEXT DEFAULT NULL,
  p_cliente_vizu_id UUID DEFAULT NULL,
  p_credential_id INTEGER DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
  INSERT INTO public.ingestion_audit_log (
    sync_id,
    operation,
    status,
    message,
    details,
    client_id,
    cliente_vizu_id,
    credential_id
  ) VALUES (
    p_sync_id,
    p_operation,
    p_status,
    p_message,
    p_details,
    p_client_id,
    p_cliente_vizu_id,
    p_credential_id
  );

  -- Also log to PostgreSQL log for Supabase dashboard visibility
  RAISE LOG '[ingestion:%] [sync_id:%] [%] %',
    p_operation, p_sync_id, p_status, p_message;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.log_ingestion_event TO service_role;

COMMENT ON FUNCTION public.log_ingestion_event IS
  'Helper function to log ingestion events both to database and PostgreSQL log';

COMMIT;
