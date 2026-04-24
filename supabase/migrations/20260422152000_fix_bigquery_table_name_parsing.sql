-- =============================================================================
-- Migration: Fix BigQuery table name parsing in create_bigquery_foreign_table
-- Date: 2026-04-22
--
-- Problem:
--   p_bigquery_table was treated as a raw table_name. If callers pass
--   fully-qualified values like project.dataset.table or dataset.table,
--   INFORMATION_SCHEMA lookup uses the whole string and discovers 0 columns.
--
-- Fix:
--   - Parse p_bigquery_table into optional project/dataset/table pieces
--   - Override project/dataset from parsed value when provided
--   - Use the parsed table-only name in INFORMATION_SCHEMA filter
--   - Use a sanitized local foreign table identifier based on table-only name
-- =============================================================================

BEGIN;

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

  v_input_table       TEXT;
  v_input_parts       TEXT[];
  v_effective_project TEXT;
  v_effective_dataset TEXT;
  v_table_only        TEXT;
  v_local_table_name  TEXT;
BEGIN
  RAISE LOG '[create_bq_ft] Starting for client_id=%, table=%, credential=%', p_client_id, p_table_name, p_credential_id;

  v_input_table := COALESCE(NULLIF(p_bigquery_table, ''), NULLIF(p_table_name, ''));
  IF v_input_table IS NULL THEN
    RAISE EXCEPTION 'BigQuery table name is required';
  END IF;

  -- Lookup default server routing for this client
  SELECT server_name, project_id, dataset_id
  INTO v_server_name, v_project_id, v_dataset_id
  FROM public.bigquery_servers
  WHERE client_id = p_client_id::uuid
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RAISE EXCEPTION 'No BigQuery server found for client: %', p_client_id;
  END IF;

  v_effective_project := v_project_id;
  v_effective_dataset := v_dataset_id;
  v_table_only := v_input_table;

  -- Parse fully-qualified names:
  --   project.dataset.table
  --   dataset.table
  v_input_parts := string_to_array(replace(v_input_table, '`', ''), '.');

  IF array_length(v_input_parts, 1) = 3 THEN
    v_effective_project := v_input_parts[1];
    v_effective_dataset := v_input_parts[2];
    v_table_only := v_input_parts[3];
  ELSIF array_length(v_input_parts, 1) = 2 THEN
    v_effective_dataset := v_input_parts[1];
    v_table_only := v_input_parts[2];
  END IF;

  IF v_effective_project IS NULL OR v_effective_dataset IS NULL OR v_table_only IS NULL THEN
    RAISE EXCEPTION 'Unable to resolve BigQuery table path from input: %', v_input_table;
  END IF;

  v_bq_table := v_table_only;

  -- Build safe local foreign table identifiers
  v_local_table_name := regexp_replace(v_table_only, '[^a-zA-Z0-9_]+', '_', 'g');
  v_discovery_ft := v_schema_name || '.c_' || replace(p_client_id, '-', '_') || '_schema_discovery';
  v_final_ft     := v_schema_name || '.c_' || replace(p_client_id, '-', '_') || '_' || v_local_table_name;

  v_full_bq_path := '`' || v_effective_project || '`.`' || v_effective_dataset || '`.`' || v_bq_table || '`';

  v_info_schema_query := '(SELECT column_name, data_type, is_nullable, ordinal_position '
    || 'FROM `' || v_effective_project || '`.`' || v_effective_dataset || '`.INFORMATION_SCHEMA.COLUMNS '
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

  EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s', v_discovery_ft);

  IF v_columns IS NULL OR jsonb_array_length(v_columns) = 0 THEN
    RAISE EXCEPTION 'No columns discovered for BigQuery table: %.%.%', v_effective_project, v_effective_dataset, v_bq_table;
  END IF;

  v_column_count := jsonb_array_length(v_columns);

  SELECT string_agg(
    quote_ident(col->>'name') || ' ' || (col->>'type'),
    ', '
  )
  FROM jsonb_array_elements(v_columns) AS col
  INTO v_column_defs;

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

  DELETE FROM public.bigquery_foreign_tables
  WHERE client_id = p_client_id::uuid AND table_name = p_table_name;

  INSERT INTO public.bigquery_foreign_tables (
    client_id, table_name, foreign_table_name, bigquery_table,
    server_name, columns, location
  ) VALUES (
    p_client_id::uuid, p_table_name, v_final_ft, v_full_bq_path,
    v_server_name, v_columns, p_location
  );

  SELECT id
  INTO v_data_source_id
  FROM public.client_data_sources
  WHERE client_id = p_client_id::uuid
    AND credential_id = p_credential_id
  ORDER BY atualizado_em DESC NULLS LAST, id DESC
  LIMIT 1;

  IF v_data_source_id IS NULL THEN
    SELECT id
    INTO v_data_source_id
    FROM public.client_data_sources
    WHERE client_id = p_client_id::uuid
      AND storage_location = v_final_ft
    ORDER BY atualizado_em DESC NULLS LAST, id DESC
    LIMIT 1;
  END IF;

  IF v_data_source_id IS NOT NULL THEN
    UPDATE public.client_data_sources
    SET source_columns = v_columns,
      storage_location = v_final_ft,
      sync_status = 'discovery_complete',
      credential_id = COALESCE(p_credential_id, credential_id),
      atualizado_em = NOW()
    WHERE id = v_data_source_id;
  ELSE
    INSERT INTO public.client_data_sources (
      client_id, source_type, resource_type, storage_type,
      storage_location, source_columns, sync_status, credential_id
    ) VALUES (
      p_client_id::uuid, 'bigquery', 'invoices', 'foreign_table',
      v_final_ft, v_columns, 'discovery_complete', p_credential_id
    ) RETURNING id INTO v_data_source_id;
  END IF;

  BEGIN
    SELECT public.obter_dados_amostrais(p_client_id, v_final_ft, 10, 30)
    INTO v_sample_result;
  EXCEPTION WHEN OTHERS THEN
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
  IF v_discovery_ft IS NOT NULL THEN
    BEGIN
      EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s', v_discovery_ft);
    EXCEPTION WHEN OTHERS THEN
      NULL;
    END;
  END IF;

  RAISE LOG '[create_bq_ft] ERROR: % [%]', SQLERRM, SQLSTATE;
  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'error_code', SQLSTATE);
END;
$$;

GRANT EXECUTE ON FUNCTION public.create_bigquery_foreign_table(text, text, text, text, integer, integer)
TO authenticated, service_role, postgres;

COMMIT;
