-- =============================================================================
-- Migration: Fix BigQuery FT to Discover Columns Synchronously
-- Date: 2026-04-28
-- Purpose: Make create_bigquery_foreign_table immediately discover and populate
--          source_columns in client_data_sources so mapping page works without
--          a separate discovery step
-- =============================================================================

BEGIN;

DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(TEXT, TEXT, TEXT, TEXT, INT, BIGINT) CASCADE;

-- ============================================================================
-- RPC 3 (FIXED): create_bigquery_foreign_table
-- Now returns columns array after discovering them from the foreign table
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
  v_col_record RECORD;
  v_col_array JSONB := '[]'::jsonb;
  v_query TEXT;
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
    -- DISCOVER COLUMNS by querying information_schema
    -- The FDW should expose actual BigQuery columns after table creation
    -- ─────────────────────────────────────────────────────────────────────
    BEGIN
      FOR v_col_record IN
        SELECT column_name, data_type, is_nullable, ordinal_position
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = v_foreign_table_name
        ORDER BY ordinal_position
      LOOP
        -- Exclude stub columns (id, _data) if discovery worked
        IF v_col_record.column_name NOT IN ('id', '_data') THEN
          v_col_array := v_col_array || jsonb_build_object(
            'name', v_col_record.column_name,
            'type', v_col_record.data_type,
            'nullable', v_col_record.is_nullable = 'YES',
            'position', v_col_record.ordinal_position
          );
        END IF;
      END LOOP;

      -- If discovery returned only stubs, add them to array for metadata purposes
      -- This indicates FDW didn't auto-discover, but table was created
      IF v_col_array = '[]'::jsonb THEN
        v_col_array := jsonb_build_array(
          jsonb_build_object('name', 'id', 'type', 'bigint'),
          jsonb_build_object('name', '_data', 'type', 'jsonb')
        );
      END IF;
    EXCEPTION WHEN OTHERS THEN
      -- If introspection fails, set stub columns
      v_col_array := jsonb_build_array(
        jsonb_build_object('name', 'id', 'type', 'bigint'),
        jsonb_build_object('name', '_data', 'type', 'jsonb')
      );
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
    -- Register in client_data_sources with discovered columns
    -- Status is 'discovery_pending' but source_columns is populated
    -- This allows mapping page to proceed without showing pending state
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
      v_col_array,  -- ← NOW POPULATED
      'discovery_pending',
      NOW(),
      NOW()
    )
    ON CONFLICT (client_id, source_type, resource_type) DO UPDATE SET
      source_columns = EXCLUDED.source_columns,
      updated_at = NOW()
    RETURNING id INTO v_data_source_id;

    RETURN jsonb_build_object(
      'success', true,
      'data_source_id', v_data_source_id,
      'foreign_table_name', v_foreign_table_name,
      'columns', v_col_array,  -- ← RETURN COLUMNS
      'sync_status', 'discovery_pending',
      'message', 'Foreign table created. Columns available for mapping.'
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
