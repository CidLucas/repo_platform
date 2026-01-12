-- =====================================================================
-- Fix BigQuery FDW Identifier Quoting
-- =====================================================================
-- This migration fixes a critical bug where BigQuery identifiers containing
-- hyphens (e.g., project IDs like 'analytics-big-query-242119') were not
-- properly quoted with backticks, causing BigQuery syntax errors like:
--   "Syntax error: Expected end of input but got "-" at [1:224]"
--
-- SOLUTION: Use the SUBQUERY format for the 'table' option, which gives us
-- full control over the BigQuery SQL syntax with proper backtick quoting.
--
-- Instead of:  table 'invoices'  (FDW constructs query, may not quote properly)
-- We use:      table '(select * from `project-id`.`dataset`.`table`)'
--
-- Created: 2026-01-07
-- =====================================================================

-- Recreate the function with SUBQUERY approach for proper quoting
create or replace function public.create_bigquery_foreign_table(
  p_client_id text,
  p_table_name text,
  p_bigquery_table text,
  p_columns jsonb,
  p_location text default 'US'
) returns jsonb as $$
declare
  v_server_name text;
  v_project_id text;
  v_dataset_id text;
  v_foreign_table_name text;
  v_column_defs text;
  v_schema_name text := 'bigquery';
  v_table_subquery text;
  v_full_bigquery_path text;
begin
  -- Get server name and BigQuery identifiers for client
  select server_name, project_id, dataset_id
  into v_server_name, v_project_id, v_dataset_id
  from public.bigquery_servers
  where client_id = p_client_id;

  if v_server_name is null then
    raise exception 'No BigQuery server found for client: %', p_client_id;
  end if;

  -- Generate foreign table name (Postgres identifier - use underscores)
  v_foreign_table_name := v_schema_name || '.' || p_client_id || '_' || p_table_name;

  -- Build fully-qualified BigQuery table path with backtick quoting
  -- Format: `project-id`.`dataset_id`.`table_name`
  -- Backticks are REQUIRED for project IDs with hyphens (e.g., 'analytics-big-query-242119')
  v_full_bigquery_path := '`' || v_project_id || '`.`' || v_dataset_id || '`.`' || p_bigquery_table || '`';

  -- CRITICAL: Use SUBQUERY format to have full control over BigQuery SQL
  -- This ensures the FDW passes our exact query to BigQuery with proper quoting
  -- Format: (select * from `project`.`dataset`.`table`)
  v_table_subquery := '(select * from ' || v_full_bigquery_path || ')';

  -- Build column definitions from jsonb
  -- Format: [{"name": "id", "type": "bigint"}, {"name": "name", "type": "text"}]
  select string_agg(
    quote_ident(col->>'name') || ' ' || (col->>'type'),
    ', '
  )
  from jsonb_array_elements(p_columns) as col
  into v_column_defs;

  if v_column_defs is null then
    raise exception 'Invalid columns definition';
  end if;

  -- Create foreign table with SUBQUERY in the table option
  -- The subquery format gives us full control over BigQuery SQL syntax
  execute format(
    'create foreign table if not exists %s (%s)
     server %I
     options (
       table %L,
       location %L
     )',
    v_foreign_table_name,
    v_column_defs,
    v_server_name,
    v_table_subquery,
    p_location
  );

  -- Store metadata (store the full BigQuery path for reference)
  insert into public.bigquery_foreign_tables (
    client_id,
    table_name,
    foreign_table_name,
    bigquery_table,
    server_name,
    columns,
    location
  ) values (
    p_client_id,
    p_table_name,
    v_foreign_table_name,
    v_full_bigquery_path,  -- Store the path, not the subquery
    v_server_name,
    p_columns,
    p_location
  )
  on conflict (client_id, table_name)
  do update set
    foreign_table_name = excluded.foreign_table_name,
    bigquery_table = excluded.bigquery_table,
    columns = excluded.columns,
    location = excluded.location,
    updated_at = now();

  return jsonb_build_object(
    'success', true,
    'foreign_table_name', v_foreign_table_name,
    'bigquery_table', v_full_bigquery_path,
    'table_option', v_table_subquery,
    'columns', p_columns
  );
exception
  when others then
    return jsonb_build_object(
      'success', false,
      'error', sqlerrm
    );
end;
$$ language plpgsql security definer;

comment on function public.create_bigquery_foreign_table is 'Creates a foreign table mapping to BigQuery using subquery format for proper identifier quoting';

-- =====================================================================
-- Fix existing foreign tables (if any)
-- =====================================================================
-- This updates existing foreign tables to use the SUBQUERY format.
-- It drops and recreates each foreign table with the proper syntax.

do $$
declare
  v_rec record;
  v_full_bigquery_path text;
  v_table_subquery text;
  v_column_defs text;
begin
  -- Loop through all existing foreign tables
  for v_rec in
    select
      ft.client_id,
      ft.table_name,
      ft.foreign_table_name,
      ft.columns,
      ft.location,
      ft.server_name,
      s.project_id,
      s.dataset_id
    from public.bigquery_foreign_tables ft
    join public.bigquery_servers s on ft.server_name = s.server_name
  loop
    -- Build the correct fully-qualified path with backticks
    v_full_bigquery_path := '`' || v_rec.project_id || '`.`' || v_rec.dataset_id || '`.`' || v_rec.table_name || '`';

    -- Build subquery format for the table option
    v_table_subquery := '(select * from ' || v_full_bigquery_path || ')';

    -- Build column definitions
    select string_agg(
      quote_ident(col->>'name') || ' ' || (col->>'type'),
      ', '
    )
    from jsonb_array_elements(v_rec.columns) as col
    into v_column_defs;

    -- Drop existing foreign table (if exists)
    execute format('drop foreign table if exists %s', v_rec.foreign_table_name);

    -- Recreate with SUBQUERY format
    execute format(
      'create foreign table %s (%s)
       server %I
       options (
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
    update public.bigquery_foreign_tables
    set bigquery_table = v_full_bigquery_path
    where client_id = v_rec.client_id and table_name = v_rec.table_name;

    raise notice 'Fixed foreign table % -> %', v_rec.foreign_table_name, v_table_subquery;
  end loop;
end;
$$;
