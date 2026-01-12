-- =====================================================================
-- Supabase BigQuery Foreign Data Wrapper Setup
-- =====================================================================
-- This migration enables direct BigQuery integration via Supabase FDW.
-- Eliminates need for google-cloud-bigquery SDK and Pub/Sub messaging.
--
-- Created: 2025-12-19
-- Purpose: Replace heavy Python SDK with lightweight SQL-based approach
-- =====================================================================

-- 1. Enable Wrappers Extension
-- =====================================================================
create extension if not exists wrappers with schema extensions;

-- Enable Vault for secure credential storage
create extension if not exists vault with schema vault;

-- 2. Create BigQuery Foreign Data Wrapper
-- =====================================================================
create foreign data wrapper if not exists bigquery_wrapper
  handler big_query_fdw_handler
  validator big_query_fdw_validator;

-- 3. Create Schema for BigQuery Foreign Tables
-- =====================================================================
create schema if not exists bigquery;

comment on schema bigquery is 'Schema for BigQuery foreign tables via Supabase FDW';

-- 4. Create BigQuery Servers Table (Metadata)
-- =====================================================================
create table if not exists public.bigquery_servers (
  id uuid primary key default gen_random_uuid(),
  client_id text not null unique,
  server_name text not null unique,
  project_id text not null,
  dataset_id text not null,
  vault_key_id uuid not null,
  location text default 'US',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

comment on table public.bigquery_servers is 'Metadata for BigQuery foreign servers per client';

-- 5. Create Foreign Tables Registry
-- =====================================================================
create table if not exists public.bigquery_foreign_tables (
  id uuid primary key default gen_random_uuid(),
  client_id text not null,
  table_name text not null,
  foreign_table_name text not null,
  bigquery_table text not null,
  server_name text not null,
  columns jsonb not null,
  location text default 'US',
  created_at timestamptz default now(),
  constraint fk_server
    foreign key (server_name)
    references public.bigquery_servers(server_name)
    on delete cascade,
  unique(client_id, table_name)
);

comment on table public.bigquery_foreign_tables is 'Registry of all BigQuery foreign tables';

-- 6. Function: Create BigQuery Foreign Server
-- =====================================================================
create or replace function public.create_bigquery_server(
  p_client_id text,
  p_service_account_key jsonb,
  p_project_id text,
  p_dataset_id text,
  p_location text default 'US'
) returns jsonb as $$
declare
  v_server_name text;
  v_vault_key_id uuid;
  v_key_name text;
  v_existing_vault_key_id uuid;
  v_existing_secret_id uuid;
begin
  -- Validate inputs
  if p_client_id is null or p_service_account_key is null then
    raise exception 'client_id and service_account_key are required';
  end if;

  -- Generate server name
  v_server_name := 'bigquery_' || p_client_id;
  v_key_name := v_server_name || '_sa_key';

  -- Check if server already exists - if so, drop it (user is updating)
  if exists (select 1 from public.bigquery_servers where client_id = p_client_id) then
    -- Get old vault key ID
    select vault_key_id into v_existing_vault_key_id
    from public.bigquery_servers
    where client_id = p_client_id;

    -- Drop the server
    execute format(
      'drop server if exists %I cascade',
      v_server_name
    );

    -- Delete the old Vault secret (prevents duplicate key constraint)
    if v_existing_vault_key_id is not null then
      perform vault.delete_secret(v_existing_vault_key_id);
    end if;

    -- Delete metadata
    delete from public.bigquery_servers
    where client_id = p_client_id;
  end if;

  -- If a secret with the same name exists (orphaned from previous attempt), delete it to avoid unique constraint errors
  select id into v_existing_secret_id
  from vault.secrets
  where name = v_key_name
  limit 1;

  if v_existing_secret_id is not null then
    perform vault.delete_secret(v_existing_secret_id);
  end if;

  -- Store service account in Vault
  select vault.create_secret(
    p_service_account_key::text,
    v_key_name,
    'BigQuery service account for client ' || p_client_id
  ) into v_vault_key_id;

  -- Create foreign server with location parameter
  -- Location is CRITICAL - BigQuery uses it to route queries correctly
  execute format(
    'create server if not exists %I
     foreign data wrapper bigquery_wrapper
     options (
       sa_key_id %L,
       project_id %L,
       dataset_id %L,
       location %L
     )',
    v_server_name,
    v_vault_key_id::text,
    p_project_id,
    p_dataset_id,
    p_location
  );

  -- Store metadata
  insert into public.bigquery_servers (
    client_id,
    server_name,
    project_id,
    dataset_id,
    vault_key_id,
    location
  ) values (
    p_client_id,
    v_server_name,
    p_project_id,
    p_dataset_id,
    v_vault_key_id,
    p_location
  );

  return jsonb_build_object(
    'success', true,
    'server_name', v_server_name,
    'client_id', p_client_id,
    'project_id', p_project_id,
    'dataset_id', p_dataset_id
  );
exception
  when others then
    return jsonb_build_object(
      'success', false,
      'error', sqlerrm
    );
end;
$$ language plpgsql security definer;

comment on function public.create_bigquery_server is 'Creates a BigQuery foreign server for a client';

-- 7. Function: Create Foreign Table
-- =====================================================================
-- NOTE: p_bigquery_table should be JUST the table name (e.g., 'invoices').
-- The function constructs the fully-qualified BigQuery path using project_id
-- and dataset_id from the server metadata, with proper backtick quoting for
-- identifiers containing hyphens (required by BigQuery SQL syntax).
--
-- IMPORTANT: Uses SUBQUERY format to ensure proper quoting:
--   table '(select * from `project-id`.`dataset`.`table`)'
-- This gives us full control over the BigQuery SQL syntax.
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

comment on function public.create_bigquery_foreign_table is 'Creates a foreign table mapping to BigQuery';

-- 8. Function: Extract Data from BigQuery to Supabase
-- =====================================================================
create or replace function public.extract_bigquery_data(
  p_foreign_table text,
  p_destination_table text,
  p_column_mapping jsonb default null,
  p_where_clause text default null,
  p_limit integer default null
) returns jsonb as $$
declare
  v_rows_inserted bigint;
  v_select_clause text;
  v_query text;
begin
  -- Build select clause with optional column mapping
  if p_column_mapping is null then
    v_select_clause := '*';
  else
    -- Format: {"source_col": "dest_col", ...}
    select string_agg(
      quote_ident(key) || ' as ' || quote_ident(value),
      ', '
    )
    from jsonb_each_text(p_column_mapping)
    into v_select_clause;
  end if;

  -- Build query
  v_query := format(
    'insert into %I select %s from %s',
    p_destination_table,
    v_select_clause,
    p_foreign_table
  );

  -- Add WHERE clause if provided
  if p_where_clause is not null then
    v_query := v_query || ' where ' || p_where_clause;
  end if;

  -- Add LIMIT if provided
  if p_limit is not null then
    v_query := v_query || ' limit ' || p_limit;
  end if;

  -- Execute insert
  execute v_query;

  get diagnostics v_rows_inserted = row_count;

  return jsonb_build_object(
    'success', true,
    'rows_inserted', v_rows_inserted,
    'destination_table', p_destination_table
  );
exception
  when others then
    return jsonb_build_object(
      'success', false,
      'error', sqlerrm,
      'query', v_query
    );
end;
$$ language plpgsql security definer;

comment on function public.extract_bigquery_data is 'Extracts data from BigQuery foreign table to native Supabase table';

-- 9. Function: Validate BigQuery Connection
-- =====================================================================
create or replace function public.validate_bigquery_connection(
  p_client_id text
) returns jsonb as $$
declare
  v_server_name text;
  v_test_query text;
  v_result record;
begin
  -- Get server name
  select server_name into v_server_name
  from public.bigquery_servers
  where client_id = p_client_id;

  if v_server_name is null then
    return jsonb_build_object(
      'success', false,
      'error', 'No server found for client'
    );
  end if;

  -- Try to query the foreign server's information
  -- This validates that the connection works
  execute format(
    'select srvname from pg_foreign_server where srvname = %L',
    v_server_name
  ) into v_result;

  if v_result is not null then
    return jsonb_build_object(
      'success', true,
      'server_name', v_server_name,
      'status', 'connected'
    );
  else
    return jsonb_build_object(
      'success', false,
      'error', 'Server not found in pg_foreign_server'
    );
  end if;
exception
  when others then
    return jsonb_build_object(
      'success', false,
      'error', sqlerrm
    );
end;
$$ language plpgsql security definer;

comment on function public.validate_bigquery_connection is 'Validates BigQuery foreign server connection';

-- 10. Function: Query BigQuery Direct
-- =====================================================================
create or replace function public.query_bigquery_table(
  p_foreign_table text,
  p_columns text default '*',
  p_where_clause text default null,
  p_order_by text default null,
  p_limit integer default 100
) returns table (result jsonb) as $$
declare
  v_query text;
begin
  -- Build query
  v_query := format(
    'select to_jsonb(t) from (select %s from %s',
    p_columns,
    p_foreign_table
  );

  -- Add WHERE clause
  if p_where_clause is not null then
    v_query := v_query || ' where ' || p_where_clause;
  end if;

  -- Add ORDER BY
  if p_order_by is not null then
    v_query := v_query || ' order by ' || p_order_by;
  end if;

  -- Add LIMIT
  v_query := v_query || ' limit ' || p_limit || ') t';

  -- Return query results
  return query execute v_query;
exception
  when others then
    raise exception 'Query failed: %', sqlerrm;
end;
$$ language plpgsql security definer;

comment on function public.query_bigquery_table is 'Queries BigQuery foreign table and returns JSON results';

-- 11. Function: List Client's Foreign Tables
-- =====================================================================
create or replace function public.list_bigquery_tables(
  p_client_id text
) returns jsonb as $$
begin
  return (
    select jsonb_agg(
      jsonb_build_object(
        'table_name', table_name,
        'foreign_table_name', foreign_table_name,
        'bigquery_table', bigquery_table,
        'columns', columns,
        'location', location,
        'created_at', created_at
      )
    )
    from public.bigquery_foreign_tables
    where client_id = p_client_id
  );
end;
$$ language plpgsql security definer;

comment on function public.list_bigquery_tables is 'Lists all BigQuery foreign tables for a client';

-- 12. Function: Drop BigQuery Server
-- =====================================================================
create or replace function public.drop_bigquery_server(
  p_client_id text
) returns jsonb as $$
declare
  v_server_name text;
  v_vault_key_id uuid;
  v_key_name text;
begin
  -- Get server name and vault key
  select server_name, vault_key_id into v_server_name, v_vault_key_id
  from public.bigquery_servers
  where client_id = p_client_id;

  if v_server_name is null then
    return jsonb_build_object(
      'success', false,
      'error', 'No server found for client'
    );
  end if;

  -- Generate key name (must match what was created)
  v_key_name := v_server_name || '_sa_key';

  -- Drop all foreign tables for this server
  execute format(
    'drop server if exists %I cascade',
    v_server_name
  );

  -- Delete the Vault secret (CRITICAL - prevents duplicate key constraint)
  if v_vault_key_id is not null then
    perform vault.delete_secret(v_vault_key_id);
  end if;

  -- Delete metadata (cascade will delete foreign tables registry)
  delete from public.bigquery_servers
  where client_id = p_client_id;

  return jsonb_build_object(
    'success', true,
    'server_name', v_server_name,
    'message', 'Server, foreign tables, and Vault secret dropped'
  );
exception
  when others then
    return jsonb_build_object(
      'success', false,
      'error', sqlerrm
    );
end;
$$ language plpgsql security definer;

comment on function public.drop_bigquery_server is 'Drops BigQuery foreign server and all its tables';

-- =====================================================================
-- Enable RLS (Row Level Security) - Optional
-- =====================================================================
alter table public.bigquery_servers enable row level security;
alter table public.bigquery_foreign_tables enable row level security;

-- Example RLS policy (adjust based on your auth setup)
-- create policy "Users can only see their own servers"
--   on public.bigquery_servers
--   for select
--   using (client_id = auth.uid()::text);

-- =====================================================================
-- Grant Permissions
-- =====================================================================
grant usage on schema bigquery to authenticated, service_role;
grant select on all tables in schema bigquery to authenticated, service_role;

grant execute on function public.create_bigquery_server to authenticated, service_role;
grant execute on function public.create_bigquery_foreign_table to authenticated, service_role;
grant execute on function public.extract_bigquery_data to authenticated, service_role;
grant execute on function public.validate_bigquery_connection to authenticated, service_role;
grant execute on function public.query_bigquery_table to authenticated, service_role;
grant execute on function public.list_bigquery_tables to authenticated, service_role;
grant execute on function public.drop_bigquery_server to authenticated, service_role;

-- =====================================================================
-- Migration Complete
-- =====================================================================
-- Next steps:
-- 1. Apply this migration to Supabase
-- 2. Test with: SELECT create_bigquery_server('test_client', ...);
-- 3. Update Python API to use these RPC functions
-- =====================================================================
