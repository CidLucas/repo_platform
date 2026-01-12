-- =====================================================================
-- Fix BigQuery Connector - Complete Solution
-- =====================================================================
-- This script:
-- 1. Applies the SUBQUERY migration fix
-- 2. Corrects the dataset_id/table_name confusion
-- 3. Recreates foreign tables with proper quoting
-- =====================================================================

-- STEP 1: Apply the migration to fix the function
-- =====================================================================
-- (Copy from 20260107_fix_bigquery_fdw_identifier_quoting.sql)

-- Recreate the function with SUBQUERY approach for proper quoting
CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table(
  p_client_id text,
  p_table_name text,
  p_bigquery_table text,
  p_columns jsonb,
  p_location text DEFAULT 'US'
) RETURNS jsonb AS $$
DECLARE
  v_server_name text;
  v_project_id text;
  v_dataset_id text;
  v_foreign_table_name text;
  v_column_defs text;
  v_schema_name text := 'bigquery';
  v_table_subquery text;
  v_full_bigquery_path text;
BEGIN
  -- Get server name and BigQuery identifiers for client
  SELECT server_name, project_id, dataset_id
  INTO v_server_name, v_project_id, v_dataset_id
  FROM public.bigquery_servers
  WHERE client_id = p_client_id;

  IF v_server_name IS NULL THEN
    RAISE EXCEPTION 'No BigQuery server found for client: %', p_client_id;
  END IF;

  -- Generate foreign table name (Postgres identifier - use underscores)
  v_foreign_table_name := v_schema_name || '.' || p_client_id || '_' || p_table_name;

  -- Build fully-qualified BigQuery table path with backtick quoting
  -- Format: `project-id`.`dataset_id`.`table_name`
  -- Backticks are REQUIRED for project IDs with hyphens
  v_full_bigquery_path := '`' || v_project_id || '`.`' || v_dataset_id || '`.`' || p_bigquery_table || '`';

  -- CRITICAL: Use SUBQUERY format to have full control over BigQuery SQL
  -- Format: (select * from `project`.`dataset`.`table`)
  v_table_subquery := '(select * from ' || v_full_bigquery_path || ')';

  -- Build column definitions from jsonb
  SELECT string_agg(
    quote_ident(col->>'name') || ' ' || (col->>'type'),
    ', '
  )
  FROM jsonb_array_elements(p_columns) AS col
  INTO v_column_defs;

  IF v_column_defs IS NULL THEN
    RAISE EXCEPTION 'Invalid columns definition';
  END IF;

  -- Create foreign table with SUBQUERY in the table option
  EXECUTE format(
    'CREATE FOREIGN TABLE IF NOT EXISTS %s (%s)
     SERVER %I
     OPTIONS (
       table %L,
       location %L
     )',
    v_foreign_table_name,
    v_column_defs,
    v_server_name,
    v_table_subquery,
    p_location
  );

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
    updated_at = now();

  RETURN jsonb_build_object(
    'success', true,
    'foreign_table_name', v_foreign_table_name,
    'bigquery_table', v_full_bigquery_path,
    'table_option', v_table_subquery,
    'columns', p_columns
  );
EXCEPTION
  WHEN OTHERS THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', SQLERRM
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.create_bigquery_foreign_table IS 'Creates a foreign table mapping to BigQuery using subquery format for proper identifier quoting';

-- STEP 2: Fix the incorrect dataset_id in bigquery_servers
-- =====================================================================
-- Change dataset_id from 'productsinvoices' to 'dataform'

UPDATE public.bigquery_servers
SET dataset_id = 'dataform'
WHERE dataset_id = 'productsinvoices'
  AND project_id = 'analytics-big-query-242119';

-- Also update the server OPTIONS to reflect the correct dataset
DO $$
DECLARE
  v_server_name text;
  v_new_options text[];
BEGIN
  FOR v_server_name IN
    SELECT server_name
    FROM public.bigquery_servers
    WHERE dataset_id = 'dataform'
      AND project_id = 'analytics-big-query-242119'
  LOOP
    -- Get current options and rebuild with correct dataset_id
    EXECUTE format(
      'ALTER SERVER %I OPTIONS (SET dataset_id %L)',
      v_server_name,
      'dataform'
    );

    RAISE NOTICE 'Updated server % to use dataset_id=dataform', v_server_name;
  END LOOP;
END;
$$;

-- STEP 3: Fix existing foreign tables
-- =====================================================================
-- Drop and recreate with correct dataset and proper SUBQUERY format

DO $$
DECLARE
  v_rec record;
  v_full_bigquery_path text;
  v_table_subquery text;
  v_column_defs text;
BEGIN
  -- Loop through all existing foreign tables for this project
  FOR v_rec IN
    SELECT
      ft.client_id,
      ft.table_name,
      ft.foreign_table_name,
      ft.columns,
      ft.location,
      ft.server_name,
      s.project_id,
      s.dataset_id
    FROM public.bigquery_foreign_tables ft
    JOIN public.bigquery_servers s ON ft.server_name = s.server_name
    WHERE s.project_id = 'analytics-big-query-242119'
  LOOP
    -- Build the correct fully-qualified path with backticks
    -- Now using 'dataform' as dataset and 'productsinvoices' as table
    v_full_bigquery_path := '`' || v_rec.project_id || '`.`' || v_rec.dataset_id || '`.`productsinvoices`';

    -- Build subquery format for the table option
    v_table_subquery := '(select * from ' || v_full_bigquery_path || ')';

    -- Build column definitions
    SELECT string_agg(
      quote_ident(col->>'name') || ' ' || (col->>'type'),
      ', '
    )
    FROM jsonb_array_elements(v_rec.columns) AS col
    INTO v_column_defs;

    -- Drop existing foreign table (if exists)
    EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s', v_rec.foreign_table_name);

    -- Recreate with SUBQUERY format and correct dataset
    EXECUTE format(
      'CREATE FOREIGN TABLE %s (%s)
       SERVER %I
       OPTIONS (
         table %L,
         location %L
       )',
      v_rec.foreign_table_name,
      v_column_defs,
      v_rec.server_name,
      v_table_subquery,
      v_rec.location
    );

    -- Update metadata to reflect the corrected BigQuery path
    UPDATE public.bigquery_foreign_tables
    SET bigquery_table = v_full_bigquery_path,
        table_name = 'productsinvoices'
    WHERE client_id = v_rec.client_id;

    RAISE NOTICE 'Fixed foreign table % -> %', v_rec.foreign_table_name, v_table_subquery;
  END LOOP;
END;
$$;

-- STEP 4: Verify the fix
-- =====================================================================
SELECT
  'Server Check' AS check_type,
  server_name,
  project_id,
  dataset_id
FROM public.bigquery_servers
WHERE project_id = 'analytics-big-query-242119'

UNION ALL

SELECT
  'Foreign Table Check' AS check_type,
  foreign_table_name AS server_name,
  bigquery_table AS project_id,
  '' AS dataset_id
FROM public.bigquery_foreign_tables ft
JOIN public.bigquery_servers s ON ft.server_name = s.server_name
WHERE s.project_id = 'analytics-big-query-242119';

-- Expected output:
-- Server Check shows: dataset_id = 'dataform'
-- Foreign Table Check shows: bigquery_table = '`analytics-big-query-242119`.`dataform`.`productsinvoices`'
