-- =====================================================================
-- Debug BigQuery FDW Configuration
-- Run this in Supabase SQL Editor to diagnose the issue
-- =====================================================================

-- 1. Check what's stored in bigquery_servers metadata
SELECT
    client_id,
    server_name,
    project_id,
    dataset_id,
    location,
    created_at
FROM public.bigquery_servers;

-- 2. Check what's stored in bigquery_foreign_tables metadata
SELECT
    client_id,
    table_name,
    foreign_table_name,
    bigquery_table,  -- This should be `project`.`dataset`.`table` with backticks
    server_name,
    location
FROM public.bigquery_foreign_tables;

-- 3. Check the actual foreign table definition in PostgreSQL
-- This shows what the FDW will use when querying BigQuery
SELECT
    ft.foreign_table_schema,
    ft.foreign_table_name,
    fs.foreign_server_name,
    fto.option_name,
    fto.option_value
FROM information_schema.foreign_tables ft
JOIN information_schema.foreign_table_options fto
    ON ft.foreign_table_catalog = fto.foreign_table_catalog
    AND ft.foreign_table_schema = fto.foreign_table_schema
    AND ft.foreign_table_name = fto.foreign_table_name
JOIN information_schema.foreign_servers fs
    ON ft.foreign_server_catalog = fs.foreign_server_catalog
    AND ft.foreign_server_name = fs.foreign_server_name
WHERE ft.foreign_table_schema = 'bigquery';

-- 4. Check the server options (where project_id and dataset_id are stored)
SELECT
    srvname,
    srvoptions
FROM pg_foreign_server
WHERE srvname LIKE 'bigquery_%';

-- =====================================================================
-- Expected Results After Fix Applied:
-- =====================================================================
-- The 'table' option in step 3 should look like:
--   `analytics-big-query-242119`.`dataform`.`products_invoices`
--
-- If it looks like just 'invoices' or 'products_invoices' without
-- the project/dataset prefix and backticks, the migration hasn't
-- been applied yet.
-- =====================================================================
