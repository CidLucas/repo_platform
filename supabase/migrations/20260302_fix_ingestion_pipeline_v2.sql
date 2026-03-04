-- ============================================================================
-- Fix Ingestion Pipeline v2
--
-- Problems fixed:
-- 1. DROP stale uuid-typed overloads of create_bigquery_foreign_table and
--    descobrir_colunas_foreign_table (the uuid overload INSERTs a nonexistent
--    "dataset_id" column into bigquery_foreign_tables)
-- 2. Rewrite create_bigquery_foreign_table with two-step FDW discovery
--    (temp INFORMATION_SCHEMA table → real data table)
-- 3. Fix trigger_column_discovery: wrong foreign table name construction
--    (was dataset.table, should look up from bigquery_foreign_tables)
-- 4. Fix sincronizar_dados_cliente: target analytics_v2.fato_transacoes
--    instead of nonexistent analytics_v2.vendas
-- 5. Fix extract_bigquery_data: handle schema-qualified table names + inject client_id
-- 6. Add credential_id linkage when creating client_data_sources records
-- ============================================================================

-- ============================================================
-- STEP 1: Drop stale function overloads
-- ============================================================

-- Drop the uuid-typed overload that tries to INSERT dataset_id
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(uuid, character varying, character varying, jsonb, character varying, integer, boolean);

-- Drop the uuid-typed descobrir overload that tries unsupported INFORMATION_SCHEMA query
DROP FUNCTION IF EXISTS public.descobrir_colunas_foreign_table(uuid, text);

-- Drop the uuid-typed obter_dados_amostrais overload
DROP FUNCTION IF EXISTS public.obter_dados_amostrais(uuid, integer);

-- Drop old text-typed versions (we'll recreate them)
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(text, text, text, jsonb, text);
DROP FUNCTION IF EXISTS public.descobrir_colunas_foreign_table(text, text);
DROP FUNCTION IF EXISTS public.obter_dados_amostrais(text, text, integer, integer);
DROP FUNCTION IF EXISTS public.trigger_column_discovery(bigint);
DROP FUNCTION IF EXISTS public.extract_bigquery_data(text, text, jsonb, text, integer);
DROP FUNCTION IF EXISTS public.sincronizar_dados_cliente(uuid, integer, boolean);


-- ============================================================
-- STEP 2: BQ type → Postgres type mapping helper
-- ============================================================
CREATE OR REPLACE FUNCTION public.bq_type_to_pg(p_bq_type TEXT)
RETURNS TEXT
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
  RETURN CASE UPPER(TRIM(p_bq_type))
    WHEN 'STRING'    THEN 'text'
    WHEN 'BYTES'     THEN 'bytea'
    WHEN 'INT64'     THEN 'bigint'
    WHEN 'INTEGER'   THEN 'bigint'
    WHEN 'INT'       THEN 'bigint'
    WHEN 'SMALLINT'  THEN 'bigint'
    WHEN 'BIGINT'    THEN 'bigint'
    WHEN 'TINYINT'   THEN 'bigint'
    WHEN 'BYTEINT'   THEN 'bigint'
    WHEN 'FLOAT64'   THEN 'double precision'
    WHEN 'FLOAT'     THEN 'double precision'
    WHEN 'NUMERIC'   THEN 'numeric'
    WHEN 'BIGNUMERIC' THEN 'numeric'
    WHEN 'DECIMAL'   THEN 'numeric'
    WHEN 'BIGDECIMAL' THEN 'numeric'
    WHEN 'BOOL'      THEN 'boolean'
    WHEN 'BOOLEAN'   THEN 'boolean'
    WHEN 'DATE'      THEN 'date'
    WHEN 'DATETIME'  THEN 'timestamp'
    WHEN 'TIME'      THEN 'time'
    WHEN 'TIMESTAMP' THEN 'timestamptz'
    WHEN 'JSON'      THEN 'jsonb'
    WHEN 'GEOGRAPHY' THEN 'text'
    WHEN 'RECORD'    THEN 'jsonb'
    WHEN 'STRUCT'    THEN 'jsonb'
    WHEN 'ARRAY'     THEN 'jsonb'
    ELSE 'text'  -- safe fallback
  END;
END;
$$;


-- ============================================================
-- STEP 3: Rewrite create_bigquery_foreign_table (two-step FDW discovery)
-- ============================================================
CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table(
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

  -- 1. Look up FDW server for this client
  SELECT server_name, project_id, dataset_id
  INTO v_server_name, v_project_id, v_dataset_id
  FROM public.bigquery_servers
  WHERE client_id = p_client_id
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RAISE EXCEPTION 'No BigQuery server found for client: %', p_client_id;
  END IF;

  -- 2. Build names
  v_discovery_ft := v_schema_name || '.' || replace(p_client_id, '-', '_') || '_schema_discovery';
  v_final_ft     := v_schema_name || '.' || replace(p_client_id, '-', '_') || '_' || p_table_name;
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
  WHERE client_id::text = p_client_id AND table_name = p_table_name;

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
  WHERE client_id::text = p_client_id
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
  -- Cleanup on failure
  EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s', v_discovery_ft);
  RAISE LOG '[create_bq_ft] ERROR: % [%]', SQLERRM, SQLSTATE;
  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'error_code', SQLSTATE);
END;
$$;


-- ============================================================
-- STEP 4: Rewrite descobrir_colunas_foreign_table (simple Postgres info_schema version)
-- ============================================================
CREATE OR REPLACE FUNCTION public.descobrir_colunas_foreign_table(
  p_client_id          TEXT,
  p_foreign_table_name TEXT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_schema TEXT;
  v_table  TEXT;
  v_columns JSONB;
  v_column_count INTEGER;
  v_data_source_id UUID;
BEGIN
  -- Parse schema.table
  v_schema := split_part(p_foreign_table_name, '.', 1);
  v_table  := split_part(p_foreign_table_name, '.', 2);

  SELECT jsonb_agg(
    jsonb_build_object(
      'name', column_name,
      'type', data_type,
      'position', ordinal_position,
      'is_nullable', is_nullable = 'YES'
    ) ORDER BY ordinal_position
  )
  INTO v_columns
  FROM information_schema.columns
  WHERE table_schema = v_schema AND table_name = v_table;

  IF v_columns IS NULL THEN
    RAISE EXCEPTION 'Foreign table not found or has no columns: %', p_foreign_table_name;
  END IF;

  v_column_count := jsonb_array_length(v_columns);

  -- Update client_data_sources
  UPDATE public.client_data_sources
  SET source_columns = v_columns, sync_status = 'discovery_complete', atualizado_em = NOW()
  WHERE client_id::text = p_client_id AND storage_location = p_foreign_table_name
  RETURNING id INTO v_data_source_id;

  IF v_data_source_id IS NULL THEN
    INSERT INTO public.client_data_sources (
      client_id, source_type, resource_type, storage_type,
      storage_location, source_columns, sync_status
    ) VALUES (
      p_client_id::uuid, 'bigquery', 'invoices', 'foreign_table',
      p_foreign_table_name, v_columns, 'discovery_complete'
    ) RETURNING id INTO v_data_source_id;
  END IF;

  RETURN jsonb_build_object(
    'success', true,
    'column_count', v_column_count,
    'data_source_id', v_data_source_id,
    'columns', v_columns
  );

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'error_code', SQLSTATE);
END;
$$;


-- ============================================================
-- STEP 5: Rewrite obter_dados_amostrais
-- ============================================================
CREATE OR REPLACE FUNCTION public.obter_dados_amostrais(
  p_client_id          TEXT,
  p_foreign_table_name TEXT,
  p_sample_size        INTEGER DEFAULT 10,
  p_timeout_seconds    INTEGER DEFAULT 30
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_sample_data JSONB;
  v_row_count   INTEGER;
  v_query       TEXT;
BEGIN
  EXECUTE format('SET LOCAL statement_timeout = %L', (p_timeout_seconds * 1000)::TEXT);

  v_query := format(
    'SELECT jsonb_agg(row_to_json(t.*)) FROM (SELECT * FROM %s LIMIT %s) t',
    p_foreign_table_name, p_sample_size
  );
  EXECUTE v_query INTO v_sample_data;

  IF v_sample_data IS NULL THEN
    v_sample_data := '[]'::jsonb;
    v_row_count := 0;
  ELSE
    v_row_count := jsonb_array_length(v_sample_data);
  END IF;

  -- Store sample data in client_data_sources
  UPDATE public.client_data_sources
  SET source_sample_data = v_sample_data, atualizado_em = NOW()
  WHERE client_id::text = p_client_id AND storage_location = p_foreign_table_name;

  RETURN jsonb_build_object('success', true, 'row_count', v_row_count, 'sample_data', v_sample_data);

EXCEPTION
  WHEN query_canceled THEN
    RETURN jsonb_build_object('success', false, 'error', 'Query timeout', 'error_code', 'QUERY_TIMEOUT');
  WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'error_code', SQLSTATE);
END;
$$;


-- ============================================================
-- STEP 6: Rewrite trigger_column_discovery (fix foreign table name lookup)
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
  v_foreign_table_name TEXT;
  v_columns            JSONB;
  v_column_count       INTEGER;
  v_data_source_id     UUID;
BEGIN
  -- Get credential details
  SELECT
    c.client_id::text,
    c.connection_metadata->>'table_name'
  INTO v_client_id, v_table_name
  FROM credencial_servico_externo c
  WHERE c.id = p_credential_id;

  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Credential not found: %', p_credential_id;
  END IF;

  -- Look up the actual foreign table name from bigquery_foreign_tables
  SELECT bft.foreign_table_name
  INTO v_foreign_table_name
  FROM public.bigquery_foreign_tables bft
  WHERE bft.client_id::text = v_client_id
    AND bft.table_name = v_table_name
  ORDER BY bft.created_at DESC
  LIMIT 1;

  IF v_foreign_table_name IS NULL THEN
    -- Fallback: construct it from convention
    v_foreign_table_name := 'bigquery.' || replace(v_client_id, '-', '_') || '_' || v_table_name;
    RAISE LOG '[trigger_discovery] No registry found, using convention: %', v_foreign_table_name;
  END IF;

  RAISE LOG '[trigger_discovery] Using foreign table: %', v_foreign_table_name;

  -- Read columns from Postgres information_schema
  SELECT jsonb_agg(
    jsonb_build_object(
      'name', column_name,
      'type', data_type,
      'position', ordinal_position,
      'is_nullable', is_nullable = 'YES'
    ) ORDER BY ordinal_position
  )
  INTO v_columns
  FROM information_schema.columns
  WHERE table_schema = split_part(v_foreign_table_name, '.', 1)
    AND table_name = split_part(v_foreign_table_name, '.', 2);

  IF v_columns IS NULL THEN
    RAISE EXCEPTION 'Foreign table not found or has no columns: %', v_foreign_table_name;
  END IF;

  v_column_count := jsonb_array_length(v_columns);

  -- Update/create client_data_sources with credential_id linkage
  UPDATE public.client_data_sources
  SET source_columns = v_columns,
      storage_location = v_foreign_table_name,
      sync_status = 'discovery_complete',
      atualizado_em = NOW()
  WHERE credential_id = p_credential_id::integer
  RETURNING id INTO v_data_source_id;

  IF v_data_source_id IS NULL THEN
    -- Try by client_id + storage_location
    UPDATE public.client_data_sources
    SET source_columns = v_columns,
        credential_id = p_credential_id::integer,
        sync_status = 'discovery_complete',
        atualizado_em = NOW()
    WHERE client_id::text = v_client_id AND storage_location = v_foreign_table_name
    RETURNING id INTO v_data_source_id;
  END IF;

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
    'columns', v_columns
  );

EXCEPTION WHEN OTHERS THEN
  RAISE LOG '[trigger_discovery] ERROR: % [%]', SQLERRM, SQLSTATE;
  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'error_code', SQLSTATE);
END;
$$;


-- ============================================================
-- STEP 7: Rewrite extract_bigquery_data (fix schema-qualified names + inject client_id)
-- ============================================================
CREATE OR REPLACE FUNCTION public.extract_bigquery_data(
  p_foreign_table     TEXT,
  p_destination_table TEXT,
  p_column_mapping    JSONB DEFAULT NULL,
  p_client_id         TEXT DEFAULT NULL,
  p_where_clause      TEXT DEFAULT NULL,
  p_limit             INTEGER DEFAULT NULL
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_rows_inserted BIGINT;
  v_select_parts  TEXT[];
  v_insert_cols   TEXT[];
  v_select_clause TEXT;
  v_cols_clause   TEXT;
  v_query         TEXT;
  v_key           TEXT;
  v_val           TEXT;
BEGIN
  IF p_column_mapping IS NULL OR p_column_mapping = '{}'::jsonb THEN
    -- No mapping: direct select *
    v_query := format('INSERT INTO %s SELECT * FROM %s', p_destination_table, p_foreign_table);
  ELSE
    -- Build mapped INSERT: column_mapping = {"source_col": "dest_col", ...}
    FOR v_key, v_val IN SELECT * FROM jsonb_each_text(p_column_mapping)
    LOOP
      v_select_parts := array_append(v_select_parts, quote_ident(v_key));
      v_insert_cols  := array_append(v_insert_cols, quote_ident(v_val));
    END LOOP;

    -- Inject client_id if provided and target has it
    IF p_client_id IS NOT NULL THEN
      v_select_parts := array_append(v_select_parts, quote_literal(p_client_id));
      v_insert_cols  := array_append(v_insert_cols, 'client_id');
    END IF;

    v_select_clause := array_to_string(v_select_parts, ', ');
    v_cols_clause   := array_to_string(v_insert_cols, ', ');

    v_query := format('INSERT INTO %s (%s) SELECT %s FROM %s',
      p_destination_table, v_cols_clause, v_select_clause, p_foreign_table);
  END IF;

  -- WHERE clause
  IF p_where_clause IS NOT NULL THEN
    v_query := v_query || ' WHERE ' || p_where_clause;
  END IF;

  -- LIMIT
  IF p_limit IS NOT NULL THEN
    v_query := v_query || ' LIMIT ' || p_limit;
  END IF;

  RAISE LOG '[extract_bq] Executing: %', v_query;
  EXECUTE v_query;
  GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;

  RETURN jsonb_build_object('success', true, 'rows_inserted', v_rows_inserted, 'query', v_query);

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'query', v_query);
END;
$$;


-- ============================================================
-- STEP 8: Rewrite sincronizar_dados_cliente
-- Target fato_transacoes (not vendas). Multi-entity support.
-- ============================================================
CREATE OR REPLACE FUNCTION public.sincronizar_dados_cliente(
  p_client_id        UUID,
  p_credential_id    INTEGER,
  p_force_full_sync  BOOLEAN DEFAULT FALSE
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_data_source    RECORD;
  v_foreign_table  TEXT;
  v_column_mapping JSONB;
  v_resource_type  TEXT;
  v_target_table   TEXT;
  v_sync_id        BIGINT;
  v_rows_inserted  INTEGER := 0;
  v_start_time     TIMESTAMPTZ := now();
  v_sync_mode      TEXT;
  v_last_watermark TIMESTAMPTZ;
  v_watermark_col  TEXT;
  v_where_clause   TEXT;
  v_extract_result JSONB;
  v_new_watermark  TIMESTAMPTZ;
BEGIN
  -- 1. Get data source config
  SELECT cds.id, cds.storage_location, cds.column_mapping, cds.resource_type, cds.source_type
  INTO v_data_source
  FROM public.client_data_sources cds
  WHERE cds.client_id = p_client_id
    AND cds.credential_id = p_credential_id
  LIMIT 1;

  IF v_data_source IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'Data source not found for client_id and credential_id');
  END IF;

  v_foreign_table  := v_data_source.storage_location;
  v_column_mapping := v_data_source.column_mapping;
  v_resource_type  := COALESCE(v_data_source.resource_type, 'invoices');

  -- 2. Determine target table based on resource_type
  v_target_table := CASE v_resource_type
    WHEN 'invoices'   THEN 'analytics_v2.fato_transacoes'
    WHEN 'sales'      THEN 'analytics_v2.fato_transacoes'
    WHEN 'customers'  THEN 'analytics_v2.dim_clientes'
    WHEN 'suppliers'  THEN 'analytics_v2.dim_fornecedores'
    WHEN 'products'   THEN 'analytics_v2.dim_categoria'
    WHEN 'inventory'  THEN 'analytics_v2.dim_inventory'
    ELSE 'analytics_v2.fato_transacoes'
  END;

  -- 3. Watermark for incremental sync
  SELECT last_watermark_value, COALESCE(watermark_column, 'updated_at')
  INTO v_last_watermark, v_watermark_col
  FROM public.connector_sync_history
  WHERE cliente_vizu_id = p_client_id
    AND credential_id = p_credential_id
    AND status = 'completed'
  ORDER BY sync_completed_at DESC LIMIT 1;

  IF p_force_full_sync OR v_last_watermark IS NULL THEN
    v_sync_mode := 'full';
    v_where_clause := NULL;
  ELSE
    v_sync_mode := 'incremental';
    v_where_clause := format('%I > %L', v_watermark_col, v_last_watermark);
  END IF;

  -- 4. Create sync history record
  INSERT INTO public.connector_sync_history (
    client_id, cliente_vizu_id, credential_id, status,
    sync_started_at, sync_mode, watermark_column, target_table, mapping_id
  ) VALUES (
    p_client_id, p_client_id, p_credential_id, 'running',
    v_start_time, v_sync_mode, v_watermark_col, v_target_table, v_data_source.id
  ) RETURNING id INTO v_sync_id;

  -- 5. Clear existing data if full sync
  IF v_sync_mode = 'full' THEN
    EXECUTE format('DELETE FROM %s WHERE client_id = %L', v_target_table, p_client_id::text);
  END IF;

  -- 6. Extract data via FDW → target table
  v_extract_result := public.extract_bigquery_data(
    p_foreign_table     := v_foreign_table,
    p_destination_table := v_target_table,
    p_column_mapping    := v_column_mapping,
    p_client_id         := p_client_id::text,
    p_where_clause      := v_where_clause,
    p_limit             := NULL
  );

  IF NOT (v_extract_result->>'success')::boolean THEN
    UPDATE public.connector_sync_history
    SET status = 'failed', sync_completed_at = now(),
        error_message = v_extract_result->>'error', error_details = v_extract_result
    WHERE id = v_sync_id;
    RETURN v_extract_result;
  END IF;

  v_rows_inserted := COALESCE((v_extract_result->>'rows_inserted')::integer, 0);

  -- 7. Update sync history with success
  UPDATE public.connector_sync_history
  SET status = 'completed', sync_completed_at = now(),
      records_inserted = v_rows_inserted,
      records_processed = v_rows_inserted,
      progress_percent = 100
  WHERE id = v_sync_id;

  -- 8. Update data source sync status
  UPDATE public.client_data_sources
  SET last_synced_at = now(), sync_status = 'completed'
  WHERE id = v_data_source.id;

  RETURN jsonb_build_object(
    'success', true,
    'sync_id', v_sync_id,
    'sync_mode', v_sync_mode,
    'target_table', v_target_table,
    'rows_inserted', v_rows_inserted,
    'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))::integer
  );

EXCEPTION WHEN OTHERS THEN
  UPDATE public.connector_sync_history
  SET status = 'failed', sync_completed_at = now(),
      error_message = SQLERRM,
      error_details = jsonb_build_object('sqlstate', SQLSTATE, 'message', SQLERRM)
  WHERE id = v_sync_id;

  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'sync_id', v_sync_id);
END;
$$;


-- ============================================================
-- STEP 9: Grant execute permissions
-- ============================================================
GRANT EXECUTE ON FUNCTION public.bq_type_to_pg(text) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.create_bigquery_foreign_table(text, text, text, text, integer, integer) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.descobrir_colunas_foreign_table(text, text) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.obter_dados_amostrais(text, text, integer, integer) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.trigger_column_discovery(bigint) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.extract_bigquery_data(text, text, jsonb, text, text, integer) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente(uuid, integer, boolean) TO authenticated, service_role;
