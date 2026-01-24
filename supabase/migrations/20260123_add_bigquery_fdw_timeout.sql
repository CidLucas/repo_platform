-- =====================================================================
-- Add Timeout Option to BigQuery FDW Foreign Tables
-- =====================================================================
-- The BigQuery wrapper supports a 'timeout' option (in milliseconds).
-- Default is 30000ms (30 seconds), which is too short for large tables.
-- This migration:
--   1. Updates the create_bigquery_foreign_table function to include timeout
--   2. Recreates existing foreign tables with the new timeout setting
--
-- Reference: https://supabase.com/docs/guides/database/extensions/wrappers/bigquery
-- Created: 2026-01-23
-- =====================================================================

-- Recreate the function with timeout option (5 minutes = 300000ms)
create or replace function public.create_bigquery_foreign_table(
  p_client_id text,
  p_table_name text,
  p_bigquery_table text,
  p_columns jsonb,
  p_location text default 'US',
  p_timeout_ms int default 300000  -- 5 minutes timeout
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
  v_full_bigquery_path := '`' || v_project_id || '`.`' || v_dataset_id || '`.`' || p_bigquery_table || '`';

  -- CRITICAL: Use SUBQUERY format to have full control over BigQuery SQL
  v_table_subquery := '(select * from ' || v_full_bigquery_path || ')';

  -- Build column definitions from jsonb
  select string_agg(
    quote_ident(col->>'name') || ' ' || (col->>'type'),
    ', '
  )
  from jsonb_array_elements(p_columns) as col
  into v_column_defs;

  if v_column_defs is null then
    raise exception 'Invalid columns definition';
  end if;

  -- Drop existing table if it exists (to update timeout)
  execute format('drop foreign table if exists %s', v_foreign_table_name);

  -- Create foreign table with SUBQUERY and TIMEOUT options
  execute format(
    'create foreign table %s (%s)
     server %I
     options (
       table %L,
       location %L,
       timeout %L
     )',
    v_foreign_table_name,
    v_column_defs,
    v_server_name,
    v_table_subquery,
    p_location,
    p_timeout_ms::text
  );

  -- Store metadata
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
    v_full_bigquery_path,
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
    'timeout_ms', p_timeout_ms,
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

comment on function public.create_bigquery_foreign_table is 'Creates a foreign table mapping to BigQuery with configurable timeout (default 5 minutes)';

-- =====================================================================
-- Recreate existing foreign tables with timeout option
-- =====================================================================

do $$
declare
  v_rec record;
  v_full_bigquery_path text;
  v_table_subquery text;
  v_column_defs text;
  v_timeout_ms int := 300000;  -- 5 minutes
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
    v_table_subquery := '(select * from ' || v_full_bigquery_path || ')';

    -- Build column definitions
    select string_agg(
      quote_ident(col->>'name') || ' ' || (col->>'type'),
      ', '
    )
    from jsonb_array_elements(v_rec.columns) as col
    into v_column_defs;

    -- Drop existing foreign table
    execute format('drop foreign table if exists %s', v_rec.foreign_table_name);

    -- Recreate with timeout option
    execute format(
      'create foreign table %s (%s)
       server %I
       options (
         table %L,
         location %L,
         timeout %L
       )',
      v_rec.foreign_table_name,
      v_column_defs,
      v_rec.server_name,
      v_table_subquery,
      coalesce(v_rec.location, 'US'),
      v_timeout_ms::text
    );

    raise notice 'Recreated foreign table % with timeout=%ms', v_rec.foreign_table_name, v_timeout_ms;
  end loop;
end;
$$;
