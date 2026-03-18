-- ============================================================================
-- Fix Foreign Table Identifier Quoting + Drop Stale Function Overloads
--
-- Problems fixed:
-- 1. When client_id UUID starts with a digit (e.g. 4d086179-...),
--    the generated foreign table name is invalid SQL because unquoted
--    identifiers cannot start with a digit.
--    PostgreSQL error: "trailing junk after numeric literal"
--    Fix: Prefix the table name part with "c_".
--
-- 2. Multiple stale overloads of create_bigquery_foreign_table exist
--    from older migrations. PostgREST cannot disambiguate and returns
--    "syntax error at end of input" (42601).
--    Fix: Drop ALL old overloads before creating the canonical one.
--
-- 3. SECURITY DEFINER + SET search_path = public prevents implicit
--    uuid↔text casts. All comparisons against uuid columns must
--    use explicit p_client_id::uuid casts.
--
-- 4. EXCEPTION handler crashed on NULL v_discovery_ft when the
--    real error occurred before the variable was assigned, masking
--    the actual error message.
-- ============================================================================

-- ============================================================
-- STEP 0: Drop ALL stale overloads of create_bigquery_foreign_table
-- These were created by older migrations and never cleaned up.
-- PostgREST fails with "syntax error at end of input" when multiple
-- overloads exist and it can't determine which to call.
-- ============================================================
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(text, text, text, jsonb, text);
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(text, text, text, jsonb, text, int);
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(text, text, text, jsonb, text, int, boolean);
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(uuid, character varying, character varying, jsonb, character varying);
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(uuid, character varying, character varying, jsonb, character varying, integer, boolean);
-- Also drop the current signature so CREATE FUNCTION works cleanly
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(text, text, text, text, integer, integer);

-- ============================================================
-- STEP 1: Recreate create_bigquery_foreign_table with fixed name building
-- ============================================================
CREATE FUNCTION public.create_bigquery_foreign_table(
  p_client_id       TEXT,
  p_table_name      TEXT,
  p_bigquery_table  TEXT DEFAULT NULL,
  p_location        TEXT DEFAULT 'US',
  p_timeout_ms      INTEGER DEFAULT 300000,
  p_credential_id   INTEGER DEFAULT NULL
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_server_name       TEXT;
  v_project_id        TEXT;
  v_dataset_id        TEXT;
  v_schema_name       TEXT := 'bigquery';
  v_discovery_ft      TEXT;
  v_final_ft          TEXT;
  v_bq_table          TEXT;
  v_full_bq_path      TEXT;
  v_info_schema_query TEXT;
  v_columns           JSONB;
  v_column_count      INTEGER;
  v_column_defs       TEXT;
  v_data_source_id    UUID;
  v_sample_result     JSONB;
  rec                 RECORD;
BEGIN
  RAISE LOG '[create_bq_ft] Starting for client_id=%, table=%, credential=%', p_client_id, p_table_name, p_credential_id;

  -- Resolve actual BigQuery table name
  v_bq_table := COALESCE(p_bigquery_table, p_table_name);

  -- 1. Look up FDW server for this client (explicit cast: client_id is uuid)
  SELECT server_name, project_id, dataset_id
  INTO v_server_name, v_project_id, v_dataset_id
  FROM public.bigquery_servers
  WHERE client_id = p_client_id::uuid
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RAISE EXCEPTION 'No BigQuery server found for client: %', p_client_id;
  END IF;

  -- 2. Build names (prefix with c_ to ensure valid SQL identifier when UUID starts with digit)
  v_discovery_ft := v_schema_name || '.c_' || replace(p_client_id, '-', '_') || '_schema_discovery';
  v_final_ft     := v_schema_name || '.c_' || replace(p_client_id, '-', '_') || '_' || p_table_name;
  v_full_bq_path := '`' || v_project_id || '`.`' || v_dataset_id || '`.`' || v_bq_table || '`';

  -- 3. INFORMATION_SCHEMA discovery via temp foreign table
  v_info_schema_query := '(SELECT column_name, data_type, is_nullable, ordinal_position '
    || 'FROM `' || v_project_id || '`.`' || v_dataset_id || '`.INFORMATION_SCHEMA.COLUMNS '
    || 'WHERE table_name = ''' || v_bq_table || ''')';

  EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s', v_discovery_ft);
  EXECUTE format(
    'CREATE FOREIGN TABLE %s (
       column_name text,
       data_type text,
       is_nullable text,
       ordinal_position bigint
     ) SERVER %I OPTIONS (table %L, location %L, timeout %L)',
    v_discovery_ft, v_server_name, v_info_schema_query, p_location, p_timeout_ms::TEXT
  );

  RAISE LOG '[create_bq_ft] Discovery foreign table created, querying schema...';

  -- 4. Query the discovery table to get actual columns (dynamic SQL required)
  EXECUTE format(
    'SELECT jsonb_agg(
       jsonb_build_object(
         ''name'', column_name,
         ''bq_type'', data_type,
         ''type'', public.bq_type_to_pg(data_type),
         ''position'', ordinal_position,
         ''is_nullable'', is_nullable = ''YES''
       ) ORDER BY ordinal_position
     ) FROM %s', v_discovery_ft
  ) INTO v_columns;

  -- Drop the discovery table immediately
  EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s', v_discovery_ft);

  IF v_columns IS NULL OR jsonb_array_length(v_columns) = 0 THEN
    RAISE EXCEPTION 'No columns discovered for BigQuery table: %.%.%', v_project_id, v_dataset_id, v_bq_table;
  END IF;

  v_column_count := jsonb_array_length(v_columns);
  RAISE LOG '[create_bq_ft] Discovered % columns', v_column_count;

  -- 5. Build column definitions for the real foreign table
  SELECT string_agg(
    quote_ident(col->>'name') || ' ' || (col->>'type'),
    ', '
  )
  FROM jsonb_array_elements(v_columns) AS col
  INTO v_column_defs;

  -- 6. Create the real foreign table
  EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s', v_final_ft);
  EXECUTE format(
    'CREATE FOREIGN TABLE %s (%s) SERVER %I OPTIONS (table %L, location %L, timeout %L)',
    v_final_ft,
    v_column_defs,
    v_server_name,
    '(select * from ' || v_full_bq_path || ')',
    p_location,
    p_timeout_ms::TEXT
  );

  RAISE LOG '[create_bq_ft] Real foreign table created: %', v_final_ft;

  -- 7. Register in bigquery_foreign_tables (upsert by client_id + table_name)
  -- No unique constraint exists, so do delete+insert
  DELETE FROM public.bigquery_foreign_tables
  WHERE client_id = p_client_id::uuid AND table_name = p_table_name;

  INSERT INTO public.bigquery_foreign_tables (
    client_id, table_name, foreign_table_name, bigquery_table,
    server_name, columns, location
  ) VALUES (
    p_client_id::uuid, p_table_name, v_final_ft, v_full_bq_path,
    v_server_name, v_columns, p_location
  );

  -- 8. Create/update client_data_sources with credential_id linkage
  UPDATE public.client_data_sources
  SET source_columns = v_columns,
      storage_location = v_final_ft,
      sync_status = 'discovery_complete',
      atualizado_em = NOW()
  WHERE client_id = p_client_id::uuid
    AND (credential_id = p_credential_id OR storage_location = v_final_ft)
  RETURNING id INTO v_data_source_id;

  IF v_data_source_id IS NULL THEN
    INSERT INTO public.client_data_sources (
      client_id, source_type, resource_type, storage_type,
      storage_location, source_columns, sync_status, credential_id
    ) VALUES (
      p_client_id::uuid, 'bigquery', 'invoices', 'foreign_table',
      v_final_ft, v_columns, 'discovery_complete', p_credential_id
    ) RETURNING id INTO v_data_source_id;
  END IF;

  -- 9. Get sample data
  BEGIN
    SELECT public.obter_dados_amostrais(p_client_id, v_final_ft, 10, 30)
    INTO v_sample_result;
    RAISE LOG '[create_bq_ft] Sample data: %', v_sample_result->>'row_count';
  EXCEPTION WHEN OTHERS THEN
    RAISE LOG '[create_bq_ft] Sample data warning: %', SQLERRM;
    v_sample_result := jsonb_build_object('success', false, 'error', SQLERRM);
  END;

  RETURN jsonb_build_object(
    'success', true,
    'foreign_table_name', v_final_ft,
    'bigquery_table', v_full_bq_path,
    'column_count', v_column_count,
    'columns', v_columns,
    'data_source_id', v_data_source_id,
    'sample_data', v_sample_result
  );

EXCEPTION WHEN OTHERS THEN
  -- Cleanup on failure (guard against NULL if error occurred before variable assignment)
  IF v_discovery_ft IS NOT NULL THEN
    BEGIN
      EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s', v_discovery_ft);
    EXCEPTION WHEN OTHERS THEN
      NULL; -- ignore cleanup errors
    END;
  END IF;
  RAISE LOG '[create_bq_ft] ERROR: % [%]', SQLERRM, SQLSTATE;
  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'error_code', SQLSTATE);
END;
$$;


-- ============================================================
-- STEP 2: Fix trigger_column_discovery - check stored columns, then retry FDW creation
-- ============================================================
CREATE OR REPLACE FUNCTION public.trigger_column_discovery(
  p_credential_id BIGINT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_client_id          TEXT;
  v_table_name         TEXT;
  v_location           TEXT;
  v_foreign_table_name TEXT;
  v_columns            JSONB;
  v_column_count       INTEGER;
  v_data_source_id     UUID;
  v_ft_result          JSONB;
BEGIN
  -- Get credential details
  SELECT
    c.client_id::text,
    c.connection_metadata->>'table_name',
    COALESCE(c.connection_metadata->>'location', 'US')
  INTO v_client_id, v_table_name, v_location
  FROM credencial_servico_externo c
  WHERE c.id = p_credential_id;

  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Credential not found: %', p_credential_id;
  END IF;

  RAISE LOG '[trigger_discovery] Starting for credential=%, client=%, table=%, location=%',
    p_credential_id, v_client_id, v_table_name, v_location;

  -- 1. Check if columns are already stored in client_data_sources (from create_bigquery_foreign_table)
  SELECT cds.id, cds.source_columns, cds.storage_location
  INTO v_data_source_id, v_columns, v_foreign_table_name
  FROM public.client_data_sources cds
  WHERE cds.credential_id = p_credential_id::integer
    AND cds.source_columns IS NOT NULL
    AND jsonb_array_length(cds.source_columns) > 0
  LIMIT 1;

  IF v_columns IS NOT NULL THEN
    v_column_count := jsonb_array_length(v_columns);
    RAISE LOG '[trigger_discovery] Columns already discovered (% cols) in client_data_sources, returning cached', v_column_count;
    RETURN jsonb_build_object(
      'success', true,
      'column_count', v_column_count,
      'data_source_id', v_data_source_id,
      'foreign_table_name', v_foreign_table_name,
      'columns', v_columns,
      'source', 'cached'
    );
  END IF;

  -- 2. Check if columns are stored in bigquery_foreign_tables
  SELECT bft.foreign_table_name, bft.columns
  INTO v_foreign_table_name, v_columns
  FROM public.bigquery_foreign_tables bft
  WHERE bft.client_id = v_client_id::uuid
    AND bft.table_name = v_table_name
  ORDER BY bft.created_at DESC
  LIMIT 1;

  IF v_columns IS NOT NULL AND jsonb_array_length(v_columns) > 0 THEN
    v_column_count := jsonb_array_length(v_columns);
    RAISE LOG '[trigger_discovery] Columns found in bigquery_foreign_tables (% cols), syncing to client_data_sources', v_column_count;

    -- Sync to client_data_sources
    UPDATE public.client_data_sources
    SET source_columns = v_columns,
        storage_location = v_foreign_table_name,
        sync_status = 'discovery_complete',
        atualizado_em = NOW()
    WHERE credential_id = p_credential_id::integer
    RETURNING id INTO v_data_source_id;

    IF v_data_source_id IS NULL THEN
      INSERT INTO public.client_data_sources (
        client_id, source_type, resource_type, storage_type,
        storage_location, source_columns, sync_status, credential_id
      ) VALUES (
        v_client_id::uuid, 'bigquery', 'invoices', 'foreign_table',
        v_foreign_table_name, v_columns, 'discovery_complete', p_credential_id::integer
      ) RETURNING id INTO v_data_source_id;
    END IF;

    RETURN jsonb_build_object(
      'success', true,
      'column_count', v_column_count,
      'data_source_id', v_data_source_id,
      'foreign_table_name', v_foreign_table_name,
      'columns', v_columns,
      'source', 'bigquery_foreign_tables'
    );
  END IF;

  -- 3. No cached data found — the foreign table was never created successfully.
  --    Attempt to create it now via create_bigquery_foreign_table.
  RAISE LOG '[trigger_discovery] No cached columns found. Attempting FDW creation for table=% location=%', v_table_name, v_location;

  v_ft_result := public.create_bigquery_foreign_table(
    p_client_id      := v_client_id,
    p_table_name     := v_table_name,
    p_bigquery_table := v_table_name,
    p_location       := v_location,
    p_timeout_ms     := 300000,
    p_credential_id  := p_credential_id::integer
  );

  RAISE LOG '[trigger_discovery] create_bigquery_foreign_table result: %', v_ft_result;

  -- If create_bigquery_foreign_table succeeded, return its result directly
  IF (v_ft_result->>'success')::boolean THEN
    RETURN jsonb_build_object(
      'success', true,
      'column_count', (v_ft_result->>'column_count')::integer,
      'data_source_id', v_ft_result->>'data_source_id',
      'foreign_table_name', v_ft_result->>'foreign_table_name',
      'columns', v_ft_result->'columns',
      'source', 'created_on_demand'
    );
  ELSE
    -- FDW creation failed — return its error
    RETURN jsonb_build_object(
      'success', false,
      'error', COALESCE(v_ft_result->>'error', 'Foreign table creation failed'),
      'error_code', COALESCE(v_ft_result->>'error_code', 'FDW_CREATION_FAILED'),
      'detail', 'trigger_column_discovery attempted to create the foreign table but it failed. Check BigQuery credentials, server, and dataset configuration.'
    );
  END IF;

EXCEPTION WHEN OTHERS THEN
  RAISE LOG '[trigger_discovery] ERROR: % [%]', SQLERRM, SQLSTATE;
  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'error_code', SQLSTATE);
END;
$$;


-- ============================================================
-- STEP 3: Re-grant permissions (same signature, just refreshing)
-- ============================================================
GRANT EXECUTE ON FUNCTION public.create_bigquery_foreign_table(text, text, text, text, integer, integer) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.trigger_column_discovery(bigint) TO authenticated, service_role;
