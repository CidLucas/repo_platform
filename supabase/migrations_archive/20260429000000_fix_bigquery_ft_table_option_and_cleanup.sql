-- =============================================================================
-- Migration: Fix BigQuery foreign table OPTIONS and clean up stale FTs
-- Date: 2026-04-29
-- Problem: The `table` option in active foreign tables used "dataset.table"
--   format, but the Supabase wrappers BigQuery FDW prepends the server's
--   dataset_id to that value, producing "dataset.dataset.table" which BigQuery
--   rejects as "Dataset project:dataset.dataset was not found".
-- Fix: Use "project_id:dataset_id.table_name" (colon notation) so the FDW
--   parses the full reference from the option itself, and drop all stale FTs
--   accumulated from previous failed setup attempts.
-- =============================================================================

BEGIN;

-- Step 1: Fix bigquery_table reference and ALTER the active FT's table option
-- to use project_id:dataset_id.table_name format.
DO $$
DECLARE
  v_rec RECORD;
  v_correct_ref TEXT;
BEGIN
  FOR v_rec IN
    SELECT
      bft.foreign_table_name,
      bft.table_name         AS bare_table_name,
      bft.client_id,
      bs.project_id,
      bs.dataset_id
    FROM public.bigquery_foreign_tables bft
    JOIN public.bigquery_servers bs
      ON bs.client_id::TEXT = bft.client_id::TEXT
    WHERE bft.foreign_table_name IS NOT NULL
  LOOP
    v_correct_ref := v_rec.project_id || ':' || v_rec.dataset_id || '.' || v_rec.bare_table_name;

    -- Update stored reference in metadata table
    UPDATE public.bigquery_foreign_tables
    SET bigquery_table = v_correct_ref
    WHERE client_id::TEXT = v_rec.client_id::TEXT;

    -- Alter the actual PostgreSQL foreign table option.
    -- Try SET (option already exists) first, fall back to ADD.
    BEGIN
      EXECUTE format(
        'ALTER FOREIGN TABLE %I OPTIONS (SET table %L)',
        v_rec.foreign_table_name, v_correct_ref
      );
    EXCEPTION WHEN OTHERS THEN
      BEGIN
        EXECUTE format(
          'ALTER FOREIGN TABLE %I OPTIONS (ADD table %L)',
          v_rec.foreign_table_name, v_correct_ref
        );
      EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Could not fix table option for FT %: %',
          v_rec.foreign_table_name, SQLERRM;
      END;
    END;
  END LOOP;
END;
$$;

-- Step 2: Drop all stale FTs that are not referenced in bigquery_foreign_tables.
DO $$
DECLARE
  v_ft TEXT;
BEGIN
  FOR v_ft IN
    SELECT ft.foreign_table_name
    FROM information_schema.foreign_tables ft
    WHERE ft.foreign_table_schema = 'public'
      AND ft.foreign_table_name LIKE 'bq_%'
      AND ft.foreign_table_name NOT IN (
        SELECT COALESCE(foreign_table_name, '')
        FROM public.bigquery_foreign_tables
      )
  LOOP
    BEGIN
      EXECUTE format('DROP FOREIGN TABLE IF EXISTS %I CASCADE', v_ft);
    EXCEPTION WHEN OTHERS THEN
      RAISE WARNING 'Could not drop stale FT %: %', v_ft, SQLERRM;
    END;
  END LOOP;
END;
$$;

-- Step 3: Update create_bigquery_foreign_table_from_schema so future FTs are
-- built with the correct project:dataset.table reference by reading project_id
-- from bigquery_servers instead of trusting whatever bigquery_table contains.
DROP FUNCTION IF EXISTS public.create_bigquery_foreign_table_from_schema(TEXT, JSONB) CASCADE;

CREATE OR REPLACE FUNCTION public.create_bigquery_foreign_table_from_schema(
  p_client_id TEXT,
  p_columns   JSONB
)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public AS $$
DECLARE
  v_server_name    TEXT;
  v_project_id     TEXT;
  v_dataset_id     TEXT;
  v_ft_name        TEXT;
  v_old_ft         TEXT;
  v_bare_table     TEXT;
  v_bigquery_ref   TEXT;
  v_col            RECORD;
  v_col_defs       TEXT := '';
  v_pg_type        TEXT;
  v_error_msg      TEXT;
  v_random_suffix  TEXT;
BEGIN
  -- Look up server details for this client
  SELECT server_name, project_id, dataset_id
  INTO v_server_name, v_project_id, v_dataset_id
  FROM public.bigquery_servers
  WHERE client_id::text = p_client_id::text
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No BigQuery server found for this client');
  END IF;

  -- Get the bare table name registered for this client
  SELECT table_name INTO v_bare_table
  FROM public.bigquery_foreign_tables
  WHERE client_id::text = p_client_id::text
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_bare_table IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No foreign table metadata found for this client');
  END IF;

  -- Build the fully-qualified BigQuery reference (colon notation).
  -- The wrappers FDW parses "project:dataset.table" from the `table` option
  -- directly, so the server's dataset_id is not prepended a second time.
  v_bigquery_ref := v_project_id || ':' || v_dataset_id || '.' || v_bare_table;

  -- Build column definitions
  FOR v_col IN
    SELECT value AS col FROM jsonb_array_elements(p_columns)
  LOOP
    v_pg_type := public._bq_type_to_postgres_type((v_col.col->>'type')::text);
    IF v_col_defs != '' THEN v_col_defs := v_col_defs || ', '; END IF;
    v_col_defs := v_col_defs || format('%I %s', v_col.col->>'name', v_pg_type);
  END LOOP;

  IF v_col_defs = '' THEN
    RETURN jsonb_build_object('success', false, 'error', 'p_columns array is empty');
  END IF;

  -- Generate unique FT name derived from the bare table name
  v_random_suffix := SUBSTRING(MD5(gen_random_uuid()::text), 1, 8);
  v_ft_name := 'bq_ft_' ||
    REGEXP_REPLACE(LOWER(v_bare_table), '[^a-z0-9_]', '_', 'g') ||
    '_' || v_random_suffix;

  BEGIN
    -- Drop the previously active FT for this client to avoid accumulation
    BEGIN
      SELECT foreign_table_name INTO v_old_ft
      FROM public.bigquery_foreign_tables
      WHERE client_id::text = p_client_id::text
      ORDER BY created_at DESC LIMIT 1;

      IF v_old_ft IS NOT NULL AND v_old_ft != v_ft_name THEN
        EXECUTE format('DROP FOREIGN TABLE IF EXISTS %I CASCADE', v_old_ft);
      END IF;
    EXCEPTION WHEN OTHERS THEN
      NULL; -- non-fatal
    END;

    EXECUTE format(
      'CREATE FOREIGN TABLE %I (%s) SERVER %I OPTIONS (table %L)',
      v_ft_name, v_col_defs, v_server_name, v_bigquery_ref
    );

    UPDATE public.bigquery_foreign_tables
    SET foreign_table_name = v_ft_name,
        columns            = p_columns,
        server_name        = v_server_name,
        bigquery_table     = v_bigquery_ref
    WHERE client_id::text = p_client_id::text;

    RETURN jsonb_build_object(
      'success',            true,
      'foreign_table_name', v_ft_name,
      'bigquery_ref',       v_bigquery_ref,
      'columns_count',      jsonb_array_length(p_columns)
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$$;

COMMIT;
