-- =============================================================================
-- Migration: BigQuery RPC Functions for FDW Server & Foreign Table Management
-- Date: 2026-04-28
-- Purpose: Implement create_bigquery_server, drop_bigquery_server,
--          create_bigquery_foreign_table for async column discovery
-- =============================================================================

BEGIN;

-- Drop any conflicting function versions
DROP FUNCTION IF EXISTS public.create_bigquery_server(UUID, JSONB, TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS public.drop_bigquery_server(UUID) CASCADE;
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table(UUID, TEXT, TEXT, TEXT, INT, BIGINT) CASCADE;

-- ============================================================================
-- Helper: Type mapping from BigQuery to PostgreSQL
-- ============================================================================
CREATE OR REPLACE FUNCTION public._bq_type_to_postgres_type(p_bq_type TEXT)
RETURNS TEXT LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
  v_bq_type_lower TEXT := LOWER(p_bq_type);
BEGIN
  CASE v_bq_type_lower
    -- Numeric types
    WHEN 'int64', 'integer' THEN RETURN 'bigint';
    WHEN 'int32' THEN RETURN 'integer';
    WHEN 'float64', 'float' THEN RETURN 'double precision';
    WHEN 'float32' THEN RETURN 'real';
    WHEN 'numeric', 'decimal' THEN RETURN 'numeric';

    -- String types
    WHEN 'string' THEN RETURN 'text';
    WHEN 'bytes' THEN RETURN 'bytea';

    -- Boolean
    WHEN 'bool', 'boolean' THEN RETURN 'boolean';

    -- Temporal types
    WHEN 'date' THEN RETURN 'date';
    WHEN 'time', 'time64' THEN RETURN 'time';
    WHEN 'datetime', 'timestamp' THEN RETURN 'timestamp with time zone';

    -- Complex types (stored as JSON)
    WHEN 'record', 'struct' THEN RETURN 'jsonb';
    WHEN 'array' THEN RETURN 'jsonb';
    WHEN 'geography', 'bignumeric' THEN RETURN 'jsonb';

    -- Default fallback
    ELSE RETURN 'text';
  END CASE;
END;
$$;

-- ============================================================================
-- RPC 1: create_bigquery_server
-- Creates FDW server, stores credentials in Vault, registers in bigquery_servers
-- ============================================================================
CREATE OR REPLACE FUNCTION public.create_bigquery_server(
  p_client_id TEXT,
  p_service_account_key JSONB,
  p_project_id TEXT,
  p_dataset_id TEXT,
  p_location TEXT DEFAULT 'US'
)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  v_my_client_id UUID;
  v_server_name TEXT;
  v_vault_key_id UUID;
  v_secret_name TEXT;
  v_existing_server_name TEXT;
  v_error_msg TEXT;
BEGIN
  -- Verify caller ownership
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  -- Validate service account key structure
  IF p_service_account_key IS NULL THEN
    RAISE EXCEPTION 'service_account_key cannot be null';
  END IF;

  IF (p_service_account_key->>'type')::text != 'service_account' THEN
    RAISE EXCEPTION 'Invalid service account key: missing or incorrect type field';
  END IF;

  IF (p_service_account_key->>'project_id')::text IS NULL THEN
    RAISE EXCEPTION 'Invalid service account key: missing project_id field';
  END IF;

  IF (p_service_account_key->>'private_key')::text IS NULL THEN
    RAISE EXCEPTION 'Invalid service account key: missing private_key field';
  END IF;

  BEGIN
    -- Generate unique server name (e.g., bq_server_{client_id}_{timestamp})
    v_server_name := 'bq_server_' ||
                     (v_my_client_id::text)::text ||
                     '_' ||
                     EXTRACT(EPOCH FROM NOW())::bigint::text;

    -- Check if server already exists (idempotency)
    SELECT server_name INTO v_existing_server_name
    FROM public.bigquery_servers
    WHERE client_id::text = v_my_client_id::text
    LIMIT 1;

    IF v_existing_server_name IS NOT NULL THEN
      -- Server already exists for this client; return it
      SELECT vault_key_id INTO v_vault_key_id
      FROM public.bigquery_servers
      WHERE client_id::text = v_my_client_id::text;

      RETURN jsonb_build_object(
        'success', true,
        'server_name', v_existing_server_name,
        'vault_key_id', v_vault_key_id,
        'message', 'BigQuery server already exists for this tenant'
      );
    END IF;

    -- Generate vault key ID
    v_vault_key_id := gen_random_uuid();
    v_secret_name := 'bigquery_service_account_' || v_vault_key_id::text;

    -- Store service account key in Vault via vault.decrypted_secrets
    INSERT INTO vault.decrypted_secrets (name, decrypted_secret)
    VALUES (v_secret_name, p_service_account_key::text)
    ON CONFLICT (name) DO NOTHING;

    -- Verify Vault storage succeeded
    PERFORM 1 FROM vault.decrypted_secrets WHERE name = v_secret_name;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'Failed to store credentials in Vault';
    END IF;

    -- Create PostgreSQL Foreign Data Wrapper server
    EXECUTE format('CREATE SERVER IF NOT EXISTS %I ' ||
                   'FOREIGN DATA WRAPPER bigquery_fdw ' ||
                   'OPTIONS (project_id %L, dataset_id %L, location %L)',
                   v_server_name, p_project_id, p_dataset_id, p_location);

    -- Create user mapping for the server
    EXECUTE format('CREATE USER MAPPING IF NOT EXISTS FOR current_user ' ||
                   'SERVER %I OPTIONS (service_account_json %L)',
                   v_server_name,
                   p_service_account_key::text);

    -- Register in bigquery_servers table
    INSERT INTO public.bigquery_servers (
      client_id, server_name, project_id, dataset_id,
      vault_key_id, location, created_at, updated_at
    )
    VALUES (
      v_my_client_id::text, v_server_name, p_project_id, p_dataset_id,
      v_vault_key_id, p_location, NOW(), NOW()
    )
    ON CONFLICT (client_id) DO NOTHING;

    RETURN jsonb_build_object(
      'success', true,
      'server_name', v_server_name,
      'vault_key_id', v_vault_key_id
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;

    -- Attempt rollback of FDW server if it was created
    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN
      NULL; -- Ignore cleanup errors
    END;

    -- Attempt rollback of Vault entry if it was created
    IF v_vault_key_id IS NOT NULL THEN
      BEGIN
        DELETE FROM vault.decrypted_secrets
        WHERE name = v_secret_name;
      EXCEPTION WHEN OTHERS THEN
        NULL; -- Ignore cleanup errors
      END;
    END IF;

    RETURN jsonb_build_object(
      'success', false,
      'error', v_error_msg
    );
  END;
END;
$$;

-- ============================================================================
-- RPC 2: drop_bigquery_server
-- Removes FDW server, user mapping, credentials, and all registry entries
-- ============================================================================
CREATE OR REPLACE FUNCTION public.drop_bigquery_server(
  p_client_id TEXT
)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  v_my_client_id UUID;
  v_server_name TEXT;
  v_vault_key_id UUID;
  v_secret_name TEXT;
  v_error_msg TEXT;
  v_foreign_table RECORD;
BEGIN
  -- Verify caller ownership
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    -- Look up server for this client
    SELECT server_name, vault_key_id
    INTO v_server_name, v_vault_key_id
    FROM public.bigquery_servers
    WHERE client_id::text = v_my_client_id::text
    LIMIT 1;

    -- If no server found, return success (idempotent)
    IF v_server_name IS NULL THEN
      RETURN jsonb_build_object(
        'success', true,
        'message', 'No BigQuery server found for this tenant'
      );
    END IF;

    -- Drop all foreign tables using this server (CASCADE will handle this)
    FOR v_foreign_table IN
      SELECT foreign_table_name
      FROM public.bigquery_foreign_tables
      WHERE server_name = v_server_name
    LOOP
      BEGIN
        EXECUTE format('DROP FOREIGN TABLE IF EXISTS %I CASCADE',
                       v_foreign_table.foreign_table_name);
      EXCEPTION WHEN OTHERS THEN
        NULL; -- Continue even if table drop fails
      END;
    END LOOP;

    -- Drop user mapping
    BEGIN
      EXECUTE format('DROP USER MAPPING IF EXISTS FOR current_user SERVER %I',
                     v_server_name);
    EXCEPTION WHEN OTHERS THEN
      NULL; -- Ignore if mapping doesn't exist
    END;

    -- Drop server
    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN
      NULL; -- Ignore if server doesn't exist
    END;

    -- Remove from vault
    IF v_vault_key_id IS NOT NULL THEN
      v_secret_name := 'bigquery_service_account_' || v_vault_key_id::text;
      BEGIN
        DELETE FROM vault.decrypted_secrets
        WHERE name = v_secret_name;
      EXCEPTION WHEN OTHERS THEN
        NULL; -- Ignore vault cleanup errors
      END;
    END IF;

    -- Delete from client_data_sources for this BigQuery server
    DELETE FROM public.client_data_sources
    WHERE client_id::text = v_my_client_id::text
      AND source_type = 'bigquery';

    -- Delete from bigquery_foreign_tables (CASCADE should handle, but explicit)
    DELETE FROM public.bigquery_foreign_tables
    WHERE server_name = v_server_name;

    -- Delete from bigquery_servers
    DELETE FROM public.bigquery_servers
    WHERE server_name = v_server_name;

    RETURN jsonb_build_object(
      'success', true,
      'message', 'BigQuery server and all related objects removed'
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object(
      'success', false,
      'error', v_error_msg
    );
  END;
END;
$$;

-- ============================================================================
-- RPC 3: create_bigquery_foreign_table
-- Creates minimal foreign table stub and queues async column discovery
-- ============================================================================
CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table(
  p_client_id TEXT,
  p_table_name TEXT,
  p_bigquery_table TEXT,
  p_location TEXT DEFAULT 'US',
  p_timeout_ms INT DEFAULT 300000,
  p_credential_id BIGINT DEFAULT NULL
)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  v_my_client_id UUID;
  v_server_name TEXT;
  v_project_id TEXT;
  v_dataset_id TEXT;
  v_foreign_table_name TEXT;
  v_data_source_id UUID;
  v_error_msg TEXT;
  v_random_suffix TEXT;
BEGIN
  -- Verify caller ownership
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    -- Look up BigQuery server for this client
    SELECT server_name, project_id, dataset_id
    INTO v_server_name, v_project_id, v_dataset_id
    FROM public.bigquery_servers
    WHERE client_id::text = v_my_client_id::text
    LIMIT 1;

    IF v_server_name IS NULL THEN
      RAISE EXCEPTION 'BigQuery server not configured for this tenant. Call create_bigquery_server first.';
    END IF;

    -- Generate unique foreign table name
    -- Format: bq_ft_{sanitized_table_name}_{random_suffix}
    v_random_suffix := SUBSTRING(MD5(gen_random_uuid()::text), 1, 8);
    v_foreign_table_name := 'bq_ft_' ||
                            REGEXP_REPLACE(LOWER(p_table_name), '[^a-z0-9_]', '_', 'g') ||
                            '_' || v_random_suffix;

    -- Create minimal foreign table stub in PostgreSQL
    -- FDW limitation: we cannot dynamically introspect columns without querying BigQuery,
    -- so we create a minimal stub with just id and data columns initially.
    -- Column discovery happens async via trigger_column_discovery() → edge function.
    BEGIN
      EXECUTE format(
        'CREATE FOREIGN TABLE IF NOT EXISTS %I (' ||
        '  id bigint, ' ||
        '  _data jsonb' ||
        ') SERVER %I OPTIONS (object_name %L)',
        v_foreign_table_name,
        v_server_name,
        v_bigquery_table
      );
    EXCEPTION WHEN OTHERS THEN
      v_error_msg := SQLERRM;
      RAISE EXCEPTION 'Failed to create foreign table: %', v_error_msg;
    END;

    -- Generate UUID for data source
    v_data_source_id := gen_random_uuid();

    -- Register in bigquery_foreign_tables
    INSERT INTO public.bigquery_foreign_tables (
      id, client_id, table_name, foreign_table_name,
      bigquery_table, server_name, columns, location, created_at
    )
    VALUES (
      v_data_source_id,
      v_my_client_id::text,
      p_table_name,
      v_foreign_table_name,
      p_bigquery_table,
      v_server_name,
      '[]'::jsonb,  -- Empty until discovery completes
      p_location,
      NOW()
    )
    ON CONFLICT (client_id, table_name) DO UPDATE SET
      foreign_table_name = EXCLUDED.foreign_table_name,
      server_name = EXCLUDED.server_name
    RETURNING id INTO v_data_source_id;

    -- Register in client_data_sources with discovery_pending status
    -- Async discovery will populate source_columns and update sync_status to 'complete'
    INSERT INTO public.client_data_sources (
      id, client_id, credential_id, source_type, resource_type,
      storage_type, storage_location, sync_status, created_at, updated_at
    )
    VALUES (
      gen_random_uuid(),
      v_my_client_id::text,
      p_credential_id,
      'bigquery',
      'table',
      'bigquery_fdw',
      p_bigquery_table,
      'discovery_pending',  -- Will be updated to 'complete' after async discovery
      NOW(),
      NOW()
    )
    ON CONFLICT (client_id, source_type, resource_type) DO UPDATE SET
      sync_status = 'discovery_pending',
      updated_at = NOW()
    RETURNING id INTO v_data_source_id;

    RETURN jsonb_build_object(
      'success', true,
      'data_source_id', v_data_source_id,
      'foreign_table_name', v_foreign_table_name,
      'sync_status', 'discovery_pending',
      'message', 'Foreign table created. Call trigger_column_discovery() to populate columns.'
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;

    -- Attempt rollback of foreign table if it was created
    IF v_foreign_table_name IS NOT NULL THEN
      BEGIN
        EXECUTE format('DROP FOREIGN TABLE IF EXISTS %I CASCADE', v_foreign_table_name);
      EXCEPTION WHEN OTHERS THEN
        NULL; -- Ignore cleanup errors
      END;
    END IF;

    RETURN jsonb_build_object(
      'success', false,
      'error', v_error_msg
    );
  END;
END;
$$;

-- ============================================================================
-- Comments documenting BigQuery FDW patterns and async discovery
-- ============================================================================

COMMENT ON FUNCTION public._bq_type_to_postgres_type(TEXT) IS
'Helper function to map BigQuery data types to PostgreSQL equivalents.
Used by async discovery to generate CREATE FOREIGN TABLE DDL.';

COMMENT ON FUNCTION public.create_bigquery_server(TEXT, JSONB, TEXT, TEXT, TEXT) IS
'Creates a BigQuery Foreign Data Wrapper (FDW) server.
1. Validates service_account_key has required fields (type, project_id, private_key)
2. Generates unique server name (bq_server_{client_id}_{timestamp})
3. Stores service account key in Vault (returns vault_key_id for tracking)
4. Creates PostgreSQL FDW server and user mapping
5. Registers in bigquery_servers table

Returns JSON with {success, server_name, vault_key_id} or {success: false, error}.
Idempotent: returns existing server if already created for this tenant.';

COMMENT ON FUNCTION public.drop_bigquery_server(TEXT) IS
'Removes all BigQuery FDW artifacts for a tenant.
1. Drops all foreign tables using this server (CASCADE)
2. Drops user mapping
3. Drops server
4. Deletes credentials from Vault
5. Cleans up registry entries in bigquery_servers, bigquery_foreign_tables, client_data_sources

Returns {success: true/false, ...}.
Idempotent: succeeds even if no server exists.';

COMMENT ON FUNCTION public.create_bigquery_foreign_table(TEXT, TEXT, TEXT, TEXT, INT, BIGINT) IS
'Creates a minimal foreign table stub and queues async column discovery.
1. Validates BigQuery server exists (calls create_bigquery_server first)
2. Creates minimal PostgreSQL foreign table (stub with id, _data columns)
3. Registers in bigquery_foreign_tables
4. Inserts into client_data_sources with sync_status=''discovery_pending''

ASYNC DISCOVERY PATTERN:
- This RPC returns immediately with data_source_id and sync_status=''discovery_pending''
- Frontend calls trigger_column_discovery(credential_id) to queue async discovery
- Edge function processes discovery, introspects BigQuery INFORMATION_SCHEMA
- Populates source_columns in client_data_sources with actual columns
- Updates sync_status to ''complete'' when done
- Frontend polls client_data_sources.sync_status until complete

Returns {success, data_source_id, foreign_table_name, sync_status, message} or {success: false, error}.
Rationale for async:
  - Resilient to BigQuery connection timeouts
  - Non-blocking: user can proceed to column mapping immediately
  - Matches existing match-columns and trigger_column_discovery patterns';

COMMIT;
