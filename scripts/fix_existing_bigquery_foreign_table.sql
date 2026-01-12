-- =====================================================================
-- Reset BigQuery FDW Server and Foreign Tables (COMPLETE REBUILD)
-- =====================================================================
-- This script COMPLETELY RESETS the FDW infrastructure to use ONLY
-- user-provided values from the connector modal (NO hardcodes).
--
-- It:
-- 1. Drops the old FDW server (which was hardcoded)
-- 2. Recreates the FDW server with user-provided values
-- 3. Drops all old foreign tables for this client
-- 4. Creates new foreign table with correct user-provided values
-- 5. Updates all metadata with user-provided values
--
-- CRITICAL: This uses the 'bigquery_servers' table as the source of truth.
-- The service account JSON, dataset ID, and location MUST be already
-- stored in bigquery_servers table with the correct values.
-- =====================================================================

DO $$
DECLARE
  v_client_id text := 'e0e9c949_18fe_4d9a_9295_d5dfb2cc9723';
  v_project_id text;
  v_dataset_id text;
  v_location text;
  v_table_name text;
  v_service_account_json jsonb;
  v_server_name text;
  v_old_server_name text;
  v_old_foreign_table_name text;
  v_foreign_table_name text;
  v_full_bigquery_path text;
  v_table_subquery text;
  v_column_defs text;
  v_columns jsonb;
  v_sa_key_options text;
  v_vault_key_id uuid;
BEGIN
  -- Step 1: GET USER-PROVIDED VALUES from bigquery_servers
  -- This table should have been populated by the connector modal
  SELECT bs.project_id, bs.dataset_id, bs.location, bs.server_name,
         bs.vault_key_id, bft.table_name, bft.columns
  INTO v_project_id, v_dataset_id, v_location, v_old_server_name,
       v_vault_key_id, v_table_name, v_columns
  FROM public.bigquery_servers bs
  LEFT JOIN public.bigquery_foreign_tables bft ON bs.client_id = bft.client_id
  WHERE bs.client_id = v_client_id;

  IF v_project_id IS NULL THEN
    RAISE EXCEPTION 'No bigquery_servers entry found for client %. Did the connector modal store the values?', v_client_id;
  END IF;

  IF v_table_name IS NULL THEN
    RAISE EXCEPTION 'No table_name found in bigquery_foreign_tables for client %', v_client_id;
  END IF;

  -- Retrieve service account JSON from vault
  SELECT decrypted_secret::jsonb INTO v_service_account_json
  FROM vault.decrypted_secrets
  WHERE id = v_vault_key_id
  LIMIT 1;

  IF v_service_account_json IS NULL THEN
    RAISE EXCEPTION 'Could not decrypt service account JSON for vault_key_id %', v_vault_key_id;
  END IF;

  RAISE NOTICE '========== STARTING FDW SERVER RESET ==========';
  RAISE NOTICE 'Client: %', v_client_id;
  RAISE NOTICE 'Project ID: %', v_project_id;
  RAISE NOTICE 'Dataset ID: %', v_dataset_id;
  RAISE NOTICE 'Table Name: %', v_table_name;
  RAISE NOTICE 'Location: %', v_location;
  RAISE NOTICE 'Old Server Name: %', v_old_server_name;

  -- Step 2: DROP OLD FDW SERVER (if it exists)
  -- This ensures we remove all hardcoded options
  IF v_old_server_name IS NOT NULL THEN
    RAISE NOTICE 'Dropping old FDW server: %', v_old_server_name;
    EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_old_server_name);
    RAISE NOTICE 'Old FDW server dropped';
  END IF;

  -- Step 3: DROP ALL OLD FOREIGN TABLES for this client
  -- Find and drop all foreign tables
  FOR v_old_foreign_table_name IN
    SELECT foreign_table_name
    FROM public.bigquery_foreign_tables
    WHERE client_id = v_client_id
  LOOP
    RAISE NOTICE 'Dropping old foreign table: %', v_old_foreign_table_name;
    EXECUTE format('DROP FOREIGN TABLE IF EXISTS %s CASCADE', v_old_foreign_table_name);
  END LOOP;

  -- Delete old metadata entries
  DELETE FROM public.bigquery_foreign_tables
  WHERE client_id = v_client_id;
  RAISE NOTICE 'Cleaned up old bigquery_foreign_tables metadata';

  -- Step 4: CREATE NEW FDW SERVER with USER-PROVIDED VALUES ONLY
  -- Generate server name
  v_server_name := 'bigquery_' || replace(v_client_id, '-', '_');

  -- Build the service account key option
  v_sa_key_options := 'sa_key=' || v_service_account_json::text;

  RAISE NOTICE 'Creating new FDW server: %', v_server_name;
  RAISE NOTICE 'Dataset ID option: %', v_dataset_id;
  RAISE NOTICE 'Location option: %', v_location;

  -- Create server with user-provided values (NO hardcodes)
  EXECUTE format(
    'CREATE SERVER %I
     FOREIGN DATA WRAPPER wrappers_fdw
     OPTIONS (
       %s,
       project_id %L,
       dataset_id %L,
       location %L
     )',
    v_server_name,
    v_sa_key_options,
    v_project_id,
    v_dataset_id,
    v_location  -- USER-PROVIDED LOCATION, not hardcoded!
  );

  RAISE NOTICE 'FDW server created successfully: %', v_server_name;

  -- Step 5: CREATE NEW FOREIGN TABLE with USER-PROVIDED VALUES
  v_foreign_table_name := 'bigquery_' || replace(v_client_id, '-', '_') || '_' || v_table_name;

  -- Build BigQuery path with backticks
  v_full_bigquery_path := '`' || v_project_id || '`.`' || v_dataset_id || '`.`' || v_table_name || '`';
  v_table_subquery := '(select * from ' || v_full_bigquery_path || ')';

  -- Column definitions
  v_columns := '[
    {"name": "id_pedido", "type": "text"},
    {"name": "data_transacao", "type": "text"},
    {"name": "nome_emitter", "type": "text"},
    {"name": "cnpj_emitter", "type": "text"},
    {"name": "nome_receiver", "type": "text"},
    {"name": "cpf_cnpj_receiver", "type": "text"},
    {"name": "descricao_produto", "type": "text"},
    {"name": "quantidade", "type": "text"},
    {"name": "valor_unitario", "type": "text"},
    {"name": "valor_total", "type": "text"},
    {"name": "status", "type": "text"}
  ]'::jsonb;

  SELECT string_agg(
    quote_ident(col->>'name') || ' ' || (col->>'type'),
    ', '
  )
  FROM jsonb_array_elements(v_columns) AS col
  INTO v_column_defs;

  RAISE NOTICE 'Creating new foreign table: %', v_foreign_table_name;
  RAISE NOTICE 'BigQuery path: %', v_full_bigquery_path;
  RAISE NOTICE 'Location from user input: %', v_location;

  -- Create foreign table with USER-PROVIDED location
  EXECUTE format(
    'CREATE FOREIGN TABLE %s (%s)
     SERVER %I
     OPTIONS (
       table %L,
       location %L
     )',
    v_foreign_table_name,
    v_column_defs,
    v_server_name,
    v_table_subquery,
    v_location  -- USER-PROVIDED, not hardcoded!
  );

  RAISE NOTICE 'Foreign table created: %', v_foreign_table_name;

  -- Step 6: UPDATE bigquery_servers with new server name
  UPDATE public.bigquery_servers
  SET
    server_name = v_server_name,
    updated_at = NOW()
  WHERE client_id = v_client_id;

  RAISE NOTICE 'Updated bigquery_servers with new server name: %', v_server_name;

  -- Step 7: INSERT NEW METADATA
  INSERT INTO public.bigquery_foreign_tables (
    client_id,
    table_name,
    foreign_table_name,
    bigquery_table,
    server_name,
    columns,
    location
  ) VALUES (
    v_client_id,
    v_table_name,
    v_foreign_table_name,
    v_full_bigquery_path,
    v_server_name,
    v_columns,
    v_location  -- USER-PROVIDED!
  );

  RAISE NOTICE 'Registered new foreign table metadata';

  -- Step 8: REGISTER DATA SOURCE
  DELETE FROM public.client_data_sources
  WHERE client_id = v_client_id
    AND source_type = 'bigquery';

  INSERT INTO public.client_data_sources (
    client_id,
    source_type,
    resource_type,
    storage_type,
    storage_location,
    column_mapping,
    sync_status,
    last_synced_at
  ) VALUES (
    v_client_id,
    'bigquery',
    v_table_name,  -- USER-PROVIDED table name
    'foreign_table',
    v_foreign_table_name,
    NULL,
    'active',
    NOW()
  );

  RAISE NOTICE 'Registered data source: % / %', v_table_name, v_foreign_table_name;
  RAISE NOTICE '========== FDW SERVER RESET COMPLETE ==========';

END;
$$;

-- =====================================================================
-- VERIFICATION QUERIES
-- =====================================================================

-- Check bigquery_servers (source of truth for user-provided values)
RAISE NOTICE '=== bigquery_servers ===';
SELECT
  client_id,
  server_name,
  project_id,
  dataset_id,
  location,
  (SELECT table_name FROM public.bigquery_foreign_tables WHERE client_id = 'e0e9c949_18fe_4d9a_9295_d5dfb2cc9723' LIMIT 1) as table_name
FROM public.bigquery_servers
WHERE client_id = 'e0e9c949_18fe_4d9a_9295_d5dfb2cc9723';

-- Check bigquery_foreign_tables metadata
RAISE NOTICE '=== bigquery_foreign_tables ===';
SELECT
  client_id,
  table_name,
  foreign_table_name,
  bigquery_table,
  server_name,
  location
FROM public.bigquery_foreign_tables
WHERE client_id = 'e0e9c949_18fe_4d9a_9295_d5dfb2cc9723';

-- Check FDW server configuration
RAISE NOTICE '=== FDW Server Options ===';
SELECT
  srvname,
  srvoptions
FROM pg_foreign_server
WHERE srvname LIKE '%e0e9c949%';

-- Check data source registry
RAISE NOTICE '=== client_data_sources ===';
SELECT
  client_id,
  source_type,
  resource_type,
  storage_location,
  sync_status
FROM public.client_data_sources
WHERE client_id = 'e0e9c949_18fe_4d9a_9295_d5dfb2cc9723'
  AND source_type = 'bigquery';
