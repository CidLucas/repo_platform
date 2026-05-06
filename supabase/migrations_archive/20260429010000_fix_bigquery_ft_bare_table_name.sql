-- =============================================================================
-- Migration: Use bare table name in BigQuery FT OPTIONS; add canonical ref helper
-- Date: 2026-04-29
-- Problem: The Supabase wrappers BigQuery FDW always constructs the full table
--   path as "{server.project_id}.{server.dataset_id}.{OPTIONS.table}".
--   Storing "project:dataset.table" in OPTIONS produced
--   "project.dataset.project:dataset.table" which BigQuery rejects.
-- Fix: OPTIONS (table ...) must contain only the bare table name.
--   A shared helper _bq_canonical_ref() builds the full dot-notation reference
--   for metadata storage — all code must use it rather than inline formatting.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Canonical reference helper (metadata / display only — NOT for FT OPTIONS)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public._bq_canonical_ref(
  p_project_id TEXT,
  p_dataset_id TEXT,
  p_table_name TEXT
) RETURNS TEXT LANGUAGE sql IMMUTABLE AS $$
  SELECT p_project_id || '.' || p_dataset_id || '.' || p_table_name;
$$;

-- ---------------------------------------------------------------------------
-- 2. Fix every active FT in bigquery_foreign_tables to use the bare table name
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  v_rec RECORD;
BEGIN
  FOR v_rec IN
    SELECT bft.foreign_table_name, bft.table_name
    FROM public.bigquery_foreign_tables bft
    WHERE bft.foreign_table_name IS NOT NULL
      AND bft.table_name IS NOT NULL
  LOOP
    BEGIN
      EXECUTE format(
        'ALTER FOREIGN TABLE %I OPTIONS (SET "table" %L)',
        v_rec.foreign_table_name, v_rec.table_name
      );
    EXCEPTION WHEN OTHERS THEN
      BEGIN
        EXECUTE format(
          'ALTER FOREIGN TABLE %I OPTIONS (ADD "table" %L)',
          v_rec.foreign_table_name, v_rec.table_name
        );
      EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Could not fix table option for FT %: %',
          v_rec.foreign_table_name, SQLERRM;
      END;
    END;
  END LOOP;
END;
$$;

-- ---------------------------------------------------------------------------
-- 3. Update bigquery_table metadata column to canonical dot-notation format
-- ---------------------------------------------------------------------------
UPDATE public.bigquery_foreign_tables bft
SET bigquery_table = public._bq_canonical_ref(bs.project_id, bs.dataset_id, bft.table_name)
FROM public.bigquery_servers bs
WHERE bs.client_id::TEXT = bft.client_id::TEXT
  AND bft.table_name IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 4. Replace create_bigquery_foreign_table_from_schema
--    - FT OPTIONS (table) = bare table name only
--    - bigquery_table metadata = _bq_canonical_ref(project, dataset, table)
-- ---------------------------------------------------------------------------
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
  v_col            RECORD;
  v_col_defs       TEXT := '';
  v_pg_type        TEXT;
  v_error_msg      TEXT;
  v_random_suffix  TEXT;
BEGIN
  SELECT server_name, project_id, dataset_id
  INTO v_server_name, v_project_id, v_dataset_id
  FROM public.bigquery_servers
  WHERE client_id::text = p_client_id::text
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No BigQuery server found for this client');
  END IF;

  SELECT table_name INTO v_bare_table
  FROM public.bigquery_foreign_tables
  WHERE client_id::text = p_client_id::text
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_bare_table IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No foreign table metadata found for this client');
  END IF;

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

  v_random_suffix := SUBSTRING(MD5(gen_random_uuid()::text), 1, 8);
  v_ft_name := 'bq_ft_' ||
    REGEXP_REPLACE(LOWER(v_bare_table), '[^a-z0-9_]', '_', 'g') ||
    '_' || v_random_suffix;

  BEGIN
    BEGIN
      SELECT foreign_table_name INTO v_old_ft
      FROM public.bigquery_foreign_tables
      WHERE client_id::text = p_client_id::text
      ORDER BY created_at DESC LIMIT 1;

      IF v_old_ft IS NOT NULL AND v_old_ft != v_ft_name THEN
        EXECUTE format('DROP FOREIGN TABLE IF EXISTS %I CASCADE', v_old_ft);
      END IF;
    EXCEPTION WHEN OTHERS THEN
      NULL;
    END;

    -- OPTIONS (table) uses the bare table name only.
    -- The FDW constructs the full path as: {server.project_id}.{server.dataset_id}.{bare_table}
    EXECUTE format(
      'CREATE FOREIGN TABLE %I (%s) SERVER %I OPTIONS (table %L)',
      v_ft_name, v_col_defs, v_server_name, v_bare_table
    );

    UPDATE public.bigquery_foreign_tables
    SET foreign_table_name = v_ft_name,
        columns            = p_columns,
        server_name        = v_server_name,
        -- Store canonical dot-notation reference for display; NOT used as FT OPTIONS
        bigquery_table     = public._bq_canonical_ref(v_project_id, v_dataset_id, v_bare_table)
    WHERE client_id::text = p_client_id::text;

    RETURN jsonb_build_object(
      'success',            true,
      'foreign_table_name', v_ft_name,
      'bigquery_ref',       public._bq_canonical_ref(v_project_id, v_dataset_id, v_bare_table),
      'columns_count',      jsonb_array_length(p_columns)
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$$;

COMMIT;
