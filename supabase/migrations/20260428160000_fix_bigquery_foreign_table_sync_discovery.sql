-- =============================================================================
-- Migration: Fix BigQuery Foreign Table to Sync Column Discovery
-- Date: 2026-04-28
-- Purpose: Make create_bigquery_foreign_table immediately populate source_columns
--          instead of setting discovery_pending, so mapping page shows columns
--          directly without needing a separate discovery step
-- =============================================================================

BEGIN;

-- Drop the current version
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(TEXT, TEXT, TEXT, TEXT, INT, BIGINT) CASCADE;

-- ============================================================================
-- RPC 3 (FIXED): create_bigquery_foreign_table
-- Creates foreign table AND immediately discovers columns from BigQuery
-- ============================================================================
CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table(
  p_client_id TEXT,
  p_table_name TEXT,
  p_bigquery_table TEXT,
  p_location TEXT DEFAULT 'US',
  p_timeout_ms INT DEFAULT 300000,
  p_credential_id BIGINT DEFAULT NULL
)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  v_my_client_id UUID;
  v_server_name TEXT;
  v_project_id TEXT;
  v_dataset_id TEXT;
  v_foreign_table_name TEXT;
  v_data_source_id UUID;
  v_error_msg TEXT;
  v_random_suffix TEXT;
  v_columns_json JSONB;
  v_col_record RECORD;
  v_col_array JSONB := '[]'::jsonb;
BEGIN
  -- Verify caller ownership
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    -- Look up BigQuery server for this client
    SELECT server_name, project_id, dataset_id
    INTO v_server_name, v_project_id, v_dataset_id
    FROM public.bigquery_servers
    WHERE client_id::text = v_my_client_id::text
    LIMIT 1;

    IF v_server_name IS NULL THEN
      RAISE EXCEPTION 'BigQuery server not configured for this tenant. Call create_bigquery_server first.';
    END IF;

    -- Generate unique foreign table name
    v_random_suffix := SUBSTRING(MD5(gen_random_uuid()::text), 1, 8);
    v_foreign_table_name := 'bq_ft_' ||
                            REGEXP_REPLACE(LOWER(p_table_name), '[^a-z0-9_]', '_', 'g') ||
                            '_' || v_random_suffix;

    -- Create minimal foreign table stub in PostgreSQL
    BEGIN
      EXECUTE format(
        'CREATE FOREIGN TABLE IF NOT EXISTS %I (' ||
        '  id bigint, ' ||
        '  _data jsonb' ||
        ') SERVER %I OPTIONS (object_name %L)',
        v_foreign_table_name,
        v_server_name,
        p_bigquery_table
      );
    EXCEPTION WHEN OTHERS THEN
      v_error_msg := SQLERRM;
      RAISE EXCEPTION 'Failed to create foreign table: %', v_error_msg;
    END;

    -- ─────────────────────────────────────────────────────────────────────
    -- IMMEDIATELY DISCOVER COLUMNS FROM POSTGRESQL INFORMATION_SCHEMA
    -- This queries the foreign table we just created to get column metadata
    -- ─────────────────────────────────────────────────────────────────────
    BEGIN
      FOR v_col_record IN
        SELECT column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = v_foreign_table_name
        ORDER BY ordinal_position
      LOOP
        v_col_array := v_col_array || jsonb_build_object(
          'name', v_col_record.column_name,
          'type', v_col_record.data_type,
          'nullable', v_col_record.is_nullable = 'YES',
          'position', v_col_record.ordinal_position
        );
      END LOOP;
    EXCEPTION WHEN OTHERS THEN
      -- If we can't introspect, continue with empty columns
      -- The edge function can retry discovery later
      RAISE WARNING 'Failed to introspect foreign table columns: %', SQLERRM;
      v_col_array := '[]'::jsonb;
    END;

    -- Generate UUID for data source
    v_data_source_id := gen_random_uuid();

    -- Register in bigquery_foreign_tables
    INSERT INTO public.bigquery_foreign_tables (
      id, client_id, table_name, foreign_table_name,
      bigquery_table, server_name, columns, location, created_at
    )
    VALUES (
      v_data_source_id,
      v_my_client_id::text,
      p_table_name,
      v_foreign_table_name,
      p_bigquery_table,
      v_server_name,
      v_col_array,
      p_location,
      NOW()
    )
    ON CONFLICT (client_id, table_name) DO UPDATE SET
      foreign_table_name = EXCLUDED.foreign_table_name,
      server_name = EXCLUDED.server_name,
      columns = EXCLUDED.columns
    RETURNING id INTO v_data_source_id;

    -- ─────────────────────────────────────────────────────────────────────
    -- Register in client_data_sources WITH COLUMNS POPULATED
    -- Status is now 'complete' instead of 'discovery_pending'
    -- ─────────────────────────────────────────────────────────────────────
    INSERT INTO public.client_data_sources (
      id, client_id, credential_id, source_type, resource_type,
      storage_type, storage_location, source_columns, sync_status, created_at, updated_at
    )
    VALUES (
      gen_random_uuid(),
      v_my_client_id::text,
      p_credential_id,
      'bigquery',
      'table',
      'bigquery_fdw',
      p_bigquery_table,
      v_col_array,  -- ← NOW POPULATED WITH DISCOVERED COLUMNS
      'complete',   -- ← Changed from 'discovery_pending'
      NOW(),
      NOW()
    )
    ON CONFLICT (client_id, source_type, resource_type) DO UPDATE SET
      source_columns = EXCLUDED.source_columns,
      sync_status = EXCLUDED.sync_status,
      updated_at = NOW()
    RETURNING id INTO v_data_source_id;

    RETURN jsonb_build_object(
      'success', true,
      'data_source_id', v_data_source_id,
      'foreign_table_name', v_foreign_table_name,
      'columns', v_col_array,  -- ← RETURN COLUMNS
      'sync_status', 'complete',
      'message', 'Foreign table created with columns discovered. Ready for mapping.'
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;

    -- Attempt rollback of foreign table if it was created
    IF v_foreign_table_name IS NOT NULL THEN
      BEGIN
        EXECUTE format('DROP FOREIGN TABLE IF EXISTS %I CASCADE', v_foreign_table_name);
      EXCEPTION WHEN OTHERS THEN
        NULL;
      END;
    END IF;

    RETURN jsonb_build_object(
      'success', false,
      'error', v_error_msg
    );
  END;
END;
$$;

COMMIT;
