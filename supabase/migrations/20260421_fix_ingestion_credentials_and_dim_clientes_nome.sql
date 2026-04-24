-- =============================================================================
-- Migration: Fix ingestion credential persistence + dim_clientes nome fallback
-- Date: 2026-04-21
-- Purpose:
--   1. Ensure create_bigquery_server returns vault_key_id to frontend
--   2. Enforce fallback name in analytics_v2.dim_clientes to prevent NOT NULL failures
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1) create_bigquery_server: include vault_key_id in return payload
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.create_bigquery_server(
  p_client_id text,
  p_service_account_key jsonb,
  p_project_id text,
  p_dataset_id text,
  p_location text DEFAULT 'US'
) RETURNS jsonb AS $$
DECLARE
  v_server_name text;
  v_vault_key_id uuid;
  v_key_name text;
  v_existing_vault_key_id uuid;
  v_existing_secret_id uuid;
BEGIN
  IF p_client_id IS NULL OR p_service_account_key IS NULL THEN
    RAISE EXCEPTION 'client_id and service_account_key are required';
  END IF;

  v_server_name := 'bigquery_' || p_client_id;
  v_key_name := v_server_name || '_sa_key';

  IF EXISTS (SELECT 1 FROM public.bigquery_servers WHERE client_id = p_client_id) THEN
    SELECT vault_key_id INTO v_existing_vault_key_id
    FROM public.bigquery_servers
    WHERE client_id = p_client_id;

    EXECUTE format('drop server if exists %I cascade', v_server_name);

    IF v_existing_vault_key_id IS NOT NULL THEN
      PERFORM vault.delete_secret(v_existing_vault_key_id);
    END IF;

    DELETE FROM public.bigquery_servers
    WHERE client_id = p_client_id;
  END IF;

  SELECT id INTO v_existing_secret_id
  FROM vault.secrets
  WHERE name = v_key_name
  LIMIT 1;

  IF v_existing_secret_id IS NOT NULL THEN
    PERFORM vault.delete_secret(v_existing_secret_id);
  END IF;

  SELECT vault.create_secret(
    p_service_account_key::text,
    v_key_name,
    'BigQuery service account for client ' || p_client_id
  ) INTO v_vault_key_id;

  EXECUTE format(
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

  INSERT INTO public.bigquery_servers (
    client_id,
    server_name,
    project_id,
    dataset_id,
    vault_key_id,
    location
  ) VALUES (
    p_client_id,
    v_server_name,
    p_project_id,
    p_dataset_id,
    v_vault_key_id,
    p_location
  );

  RETURN jsonb_build_object(
    'success', true,
    'server_name', v_server_name,
    'client_id', p_client_id,
    'project_id', p_project_id,
    'dataset_id', p_dataset_id,
    'vault_key_id', v_vault_key_id
  );
EXCEPTION
  WHEN OTHERS THEN
    RETURN jsonb_build_object(
      'success', false,
      'error', SQLERRM
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- -----------------------------------------------------------------------------
-- 2) dim_clientes nome fallback: normalize NULL/blank to 'SEM_NOME'
-- -----------------------------------------------------------------------------
DO $$
BEGIN
  IF to_regclass('analytics_v2.dim_clientes') IS NOT NULL THEN
    IF EXISTS (
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = 'analytics_v2'
        AND table_name = 'dim_clientes'
        AND column_name = 'nome'
    ) THEN
      EXECUTE 'ALTER TABLE analytics_v2.dim_clientes ALTER COLUMN nome SET DEFAULT ''SEM_NOME''';
      EXECUTE 'UPDATE analytics_v2.dim_clientes SET nome = ''SEM_NOME'' WHERE nome IS NULL OR btrim(nome) = ''''';
    END IF;
  END IF;
END;
$$;

CREATE OR REPLACE FUNCTION analytics_v2.normalize_dim_clientes_nome()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.nome := COALESCE(NULLIF(btrim(NEW.nome), ''), 'SEM_NOME');
  RETURN NEW;
END;
$$;

DO $$
BEGIN
  IF to_regclass('analytics_v2.dim_clientes') IS NOT NULL THEN
    IF EXISTS (
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = 'analytics_v2'
        AND table_name = 'dim_clientes'
        AND column_name = 'nome'
    ) THEN
      DROP TRIGGER IF EXISTS trg_normalize_dim_clientes_nome ON analytics_v2.dim_clientes;

      CREATE TRIGGER trg_normalize_dim_clientes_nome
      BEFORE INSERT OR UPDATE OF nome
      ON analytics_v2.dim_clientes
      FOR EACH ROW
      EXECUTE FUNCTION analytics_v2.normalize_dim_clientes_nome();
    END IF;
  END IF;
END;
$$;

COMMIT;
