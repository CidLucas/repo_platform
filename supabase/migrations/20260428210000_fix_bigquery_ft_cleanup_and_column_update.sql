-- =============================================================================
-- Migration: Remove stub FT creation, create actual FT on discovery
-- Date: 2026-04-28
-- =============================================================================

BEGIN;

-- ============================================================================
-- RPC: create_bigquery_foreign_table (no stub)
-- Only registers metadata — actual FT is created by discover-bigquery-columns
-- after fetching real schema from BigQuery API.
-- ============================================================================
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(TEXT, TEXT, TEXT, TEXT, INT, BIGINT) CASCADE;

CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table(
  p_client_id   TEXT,
  p_table_name  TEXT,
  p_bigquery_table TEXT,
  p_location    TEXT    DEFAULT 'US',
  p_timeout_ms  INT     DEFAULT 300000,
  p_credential_id BIGINT DEFAULT NULL
)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  v_my_client_id    UUID;
  v_data_source_id  UUID;
  v_error_msg       TEXT;
  v_pending_ft_name TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    -- Verify server exists
    IF NOT EXISTS (
      SELECT 1 FROM public.bigquery_servers
      WHERE client_id::text = v_my_client_id::text
    ) THEN
      RAISE EXCEPTION 'BigQuery server not configured for this tenant. Call create_bigquery_server first.';
    END IF;

    -- Drop any existing FT for this (client, table) to prevent accumulation
    DELETE FROM public.bigquery_foreign_tables
    WHERE client_id::text = v_my_client_id::text
      AND table_name = p_table_name;

    -- Generate placeholder FT name (will be replaced when discovery creates the real FT)
    v_pending_ft_name := 'bq_pending_' ||
      REGEXP_REPLACE(LOWER(p_table_name), '[^a-z0-9_]', '_', 'g') ||
      '_' || SUBSTRING(MD5(gen_random_uuid()::text), 1, 6);

    -- Register metadata with placeholder FT name
    INSERT INTO public.bigquery_foreign_tables (
      id, client_id, table_name, foreign_table_name,
      bigquery_table, server_name, columns, location, created_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id::text, p_table_name, v_pending_ft_name,
      p_bigquery_table, NULL, '[]'::jsonb, p_location, NOW()
    )
    RETURNING id INTO v_data_source_id;

    -- Register data source (columns will be populated by discovery)
    INSERT INTO public.client_data_sources (
      id, client_id, credential_id, source_type, resource_type,
      storage_type, storage_location, source_columns, sync_status, created_at, updated_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id::text, p_credential_id,
      'bigquery', 'table', 'bigquery_fdw', p_bigquery_table,
      '[]'::jsonb, 'discovery_pending', NOW(), NOW()
    )
    ON CONFLICT (client_id, source_type, resource_type) DO UPDATE SET
      source_columns = '[]'::jsonb,
      sync_status    = 'discovery_pending',
      credential_id  = EXCLUDED.credential_id,
      updated_at     = NOW()
    RETURNING id INTO v_data_source_id;

    RETURN jsonb_build_object(
      'success',        true,
      'data_source_id', v_data_source_id,
      'sync_status',    'discovery_pending',
      'message',        'Metadata registered. Calling discover-bigquery-columns to create FT with real schema.'
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$$;

-- ============================================================================
-- RPC: create_bigquery_foreign_table_from_schema
-- Called by discover-bigquery-columns edge function after fetching real schema
-- from BigQuery API. Creates the actual FT with properly-typed columns.
-- ============================================================================
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table_from_schema(TEXT, JSONB) CASCADE;

CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table_from_schema(
  p_client_id TEXT,
  p_columns   JSONB
)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  v_server_name    TEXT;
  v_ft_name        TEXT;
  v_bigquery_table TEXT;
  v_col            RECORD;
  v_col_defs       TEXT := '';
  v_pg_type        TEXT;
  v_error_msg      TEXT;
  v_random_suffix  TEXT;
BEGIN
  -- Get server name for this client
  SELECT server_name INTO v_server_name
  FROM public.bigquery_servers
  WHERE client_id::text = p_client_id::text
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No BigQuery server found for this client');
  END IF;

  -- Look up the most-recent FT metadata for this client (registered by create_bigquery_foreign_table)
  SELECT bigquery_table
  INTO v_bigquery_table
  FROM public.bigquery_foreign_tables
  WHERE client_id::text = p_client_id::text
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_bigquery_table IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No foreign table metadata found for this client');
  END IF;

  -- Build column definitions
  FOR v_col IN
    SELECT value AS col FROM jsonb_array_elements(p_columns)
  LOOP
    v_pg_type := public._bq_type_to_postgres_type((v_col.col->>'type')::text);
    IF v_col_defs != '' THEN v_col_defs := v_col_defs || ', '; END IF;
    v_col_defs := v_col_defs || format('%I %s', v_col.col->>'name', v_pg_type);
  END LOOP;

  IF v_col_defs = '' THEN
    RETURN jsonb_build_object('success', false, 'error', 'p_columns array is empty');
  END IF;

  -- Generate unique FT name
  v_random_suffix := SUBSTRING(MD5(gen_random_uuid()::text), 1, 8);
  v_ft_name := 'bq_ft_' ||
    REGEXP_REPLACE(LOWER(SPLIT_PART(v_bigquery_table, '.', -1)), '[^a-z0-9_]', '_', 'g') ||
    '_' || v_random_suffix;

  BEGIN
    -- Create the FT with real columns and proper BigQuery table option
    -- Use 'table' option for BigQuery FDW (not 'object_name')
    EXECUTE format(
      'CREATE FOREIGN TABLE %I (%s) SERVER %I OPTIONS (table %L)',
      v_ft_name, v_col_defs, v_server_name, v_bigquery_table
    );

    -- Update FT metadata with the actual FT name and columns
    UPDATE public.bigquery_foreign_tables
    SET foreign_table_name = v_ft_name,
        columns            = p_columns,
        server_name        = v_server_name
    WHERE client_id::text = p_client_id::text;

    RETURN jsonb_build_object(
      'success',           true,
      'foreign_table_name', v_ft_name,
      'columns_count',     jsonb_array_length(p_columns)
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$$;

COMMIT;
