-- 20260525_p3_1_refactor_bq_secdef.sql
-- P3.1: Durable fix (Option A) for BigQuery SECDEF functions.
-- Goal: stop trusting the caller-supplied p_client_id. Always derive the tenant
-- from get_my_client_id() and IGNORE p_client_id (kept in signature for backward
-- compatibility with the existing frontend that still passes it).
--
-- This makes cross-tenant access STRUCTURALLY impossible, instead of relying
-- on a runtime mismatch check that could be removed by accident in the future.

BEGIN;

-- ---------------------------------------------------------------------------
-- create_bigquery_server: IGNORE p_client_id, always use get_my_client_id()
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.create_bigquery_server(
  p_client_id           text,     -- deprecated: ignored, kept for FE compat
  p_service_account_key jsonb,
  p_project_id          text,
  p_dataset_id          text,
  p_location            text DEFAULT 'US'
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $function$
DECLARE
  v_my_client_id          uuid;
  v_server_name           text;
  v_vault_key_id          uuid;
  v_secret_name           text;
  v_name_uuid             uuid;
  v_existing_server_name  text;
  v_existing_vault_key_id uuid;
  v_error_msg             text;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;
  -- p_client_id intentionally ignored — tenant ALWAYS comes from JWT.

  IF p_service_account_key IS NULL
     OR (p_service_account_key->>'type') != 'service_account'
     OR (p_service_account_key->>'project_id') IS NULL
     OR (p_service_account_key->>'private_key') IS NULL THEN
    RAISE EXCEPTION 'Invalid service account key';
  END IF;

  BEGIN
    v_server_name := 'bigquery_' || v_my_client_id::text;

    SELECT server_name, vault_key_id
      INTO v_existing_server_name, v_existing_vault_key_id
      FROM public.bigquery_servers
     WHERE client_id = v_my_client_id
     LIMIT 1;

    IF v_existing_server_name IS NOT NULL THEN
      RETURN jsonb_build_object(
        'success', true,
        'server_name', v_existing_server_name,
        'vault_key_id', v_existing_vault_key_id,
        'message', 'BigQuery server already exists for this tenant'
      );
    END IF;

    v_name_uuid   := gen_random_uuid();
    v_secret_name := 'bigquery_service_account_' || v_name_uuid::text;

    SELECT vault.create_secret(p_service_account_key::text, v_secret_name)
      INTO v_vault_key_id;

    IF v_vault_key_id IS NULL THEN
      RAISE EXCEPTION 'Failed to store credentials in Vault';
    END IF;

    EXECUTE format(
      'CREATE SERVER IF NOT EXISTS %I FOREIGN DATA WRAPPER bigquery_wrapper OPTIONS (project_id %L, dataset_id %L, location %L, sa_key_id %L)',
      v_server_name, p_project_id, p_dataset_id, p_location, v_vault_key_id::text
    );

    INSERT INTO public.bigquery_servers (
      client_id, server_name, project_id, dataset_id,
      vault_key_id, location, created_at, updated_at
    )
    VALUES (
      v_my_client_id, v_server_name, p_project_id, p_dataset_id,
      v_vault_key_id, p_location, now(), now()
    )
    ON CONFLICT (client_id) DO NOTHING;

    RETURN jsonb_build_object(
      'success',      true,
      'server_name',  v_server_name,
      'vault_key_id', v_vault_key_id
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    BEGIN EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN NULL; END;
    IF v_vault_key_id IS NOT NULL THEN
      BEGIN DELETE FROM vault.secrets WHERE id = v_vault_key_id;
      EXCEPTION WHEN OTHERS THEN NULL; END;
    END IF;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$function$;

-- ---------------------------------------------------------------------------
-- drop_bigquery_server: IGNORE p_client_id
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.drop_bigquery_server(p_client_id text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $function$
DECLARE
  v_my_client_id uuid;
  v_server_name  text;
  v_vault_key_id uuid;
  v_error_msg    text;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;
  -- p_client_id intentionally ignored.

  BEGIN
    SELECT server_name, vault_key_id
      INTO v_server_name, v_vault_key_id
      FROM public.bigquery_servers
     WHERE client_id = v_my_client_id
     LIMIT 1;

    IF v_server_name IS NULL THEN
      RETURN jsonb_build_object('success', true, 'message', 'No BigQuery server found for this tenant');
    END IF;

    BEGIN EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN NULL; END;

    IF v_vault_key_id IS NOT NULL THEN
      BEGIN DELETE FROM vault.secrets WHERE id = v_vault_key_id;
      EXCEPTION WHEN OTHERS THEN NULL; END;
    END IF;

    DELETE FROM public.client_data_sources
     WHERE client_id = v_my_client_id AND source_type = 'bigquery';
    DELETE FROM public.bigquery_foreign_tables WHERE server_name = v_server_name;
    DELETE FROM public.bigquery_servers        WHERE server_name = v_server_name;

    RETURN jsonb_build_object('success', true, 'message', 'BigQuery server and registry removed');

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$function$;

-- ---------------------------------------------------------------------------
-- create_bigquery_foreign_table: IGNORE p_client_id
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table(
  p_client_id      text,    -- deprecated: ignored
  p_table_name     text,
  p_bigquery_table text,
  p_location       text    DEFAULT 'US',
  p_timeout_ms     integer DEFAULT 300000,
  p_credential_id  bigint  DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $function$
DECLARE
  v_my_client_id   uuid;
  v_data_source_id uuid;
  v_server_name    text;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  BEGIN
    SELECT server_name INTO v_server_name
      FROM public.bigquery_servers
     WHERE client_id = v_my_client_id
     LIMIT 1;

    IF v_server_name IS NULL THEN
      RAISE EXCEPTION 'BigQuery server not configured for this tenant. Call create_bigquery_server first.';
    END IF;

    INSERT INTO public.bigquery_foreign_tables (
      id, client_id, table_name, bigquery_table, server_name, columns, location, created_at, credential_id
    )
    VALUES (
      gen_random_uuid(), v_my_client_id, p_table_name,
      p_bigquery_table, v_server_name, '[]'::jsonb, p_location, now(), p_credential_id
    )
    ON CONFLICT (client_id, table_name) DO UPDATE SET
      bigquery_table = EXCLUDED.bigquery_table,
      server_name    = EXCLUDED.server_name,
      location       = EXCLUDED.location,
      columns        = '[]'::jsonb,
      credential_id  = EXCLUDED.credential_id;

    INSERT INTO public.client_data_sources (
      id, client_id, credential_id, source_type, resource_type,
      storage_type, storage_location, source_columns, sync_status, created_at, updated_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id, p_credential_id,
      'bigquery', 'table', 'bigquery_fdw', p_bigquery_table,
      '[]'::jsonb, 'discovery_pending', now(), now()
    )
    ON CONFLICT (client_id, source_type, resource_type) DO UPDATE SET
      source_columns = '[]'::jsonb,
      sync_status    = 'discovery_pending',
      credential_id  = EXCLUDED.credential_id,
      updated_at     = now()
    RETURNING id INTO v_data_source_id;

    RETURN jsonb_build_object(
      'success',        true,
      'data_source_id', v_data_source_id,
      'sync_status',    'discovery_pending'
    );

  EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
  END;
END;
$function$;

COMMIT;
