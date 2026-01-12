-- =====================================================================
-- Quick Fix for BigQuery Foreign Tables
-- =====================================================================
-- This fixes the backtick quoting without changing table_name
-- (table_name stays as 'invoices' - the resource type)
-- =====================================================================

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
    -- Build CORRECT path with ALL backticks: `project`.`dataset`.`table`
    -- The actual BigQuery table is 'productsinvoices' in dataset 'dataform'
    v_full_bigquery_path := '`' || v_rec.project_id || '`.`' || v_rec.dataset_id || '`.`productsinvoices`';

    -- Build subquery format
    v_table_subquery := '(select * from ' || v_full_bigquery_path || ')';

    -- Build column definitions
    SELECT string_agg(quote_ident(col->>'name') || ' ' || (col->>'type'), ', ')
    FROM jsonb_array_elements(v_rec.columns) AS col
    INTO v_column_defs;

    -- Drop existing foreign table
    EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s', v_rec.foreign_table_name);

    -- Recreate with SUBQUERY format and proper backticks
    EXECUTE format(
      'CREATE FOREIGN TABLE %s (%s) SERVER %I OPTIONS (table %L, location %L)',
      v_rec.foreign_table_name,
      v_column_defs,
      v_rec.server_name,
      v_table_subquery,
      v_rec.location
    );

    -- Update ONLY bigquery_table column (don't change table_name!)
    UPDATE public.bigquery_foreign_tables
    SET bigquery_table = v_full_bigquery_path
    WHERE client_id = v_rec.client_id AND table_name = v_rec.table_name;

    RAISE NOTICE 'Fixed: % → %', v_rec.foreign_table_name, v_table_subquery;
  END LOOP;
END;
$$;

-- Verify the fix
SELECT
  foreign_table_name,
  bigquery_table,
  table_name
FROM public.bigquery_foreign_tables ft
JOIN public.bigquery_servers s ON ft.server_name = s.server_name
WHERE s.project_id = 'analytics-big-query-242119';

-- Expected output:
-- foreign_table_name: bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_invoices
-- bigquery_table: `analytics-big-query-242119`.`dataform`.`productsinvoices`
-- table_name: invoices (unchanged - this is the resource type)
