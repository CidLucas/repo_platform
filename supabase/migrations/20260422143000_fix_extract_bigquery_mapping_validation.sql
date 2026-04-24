-- =============================================================================
-- Migration: Validate mapping columns in extract_bigquery_data
-- Date: 2026-04-22
-- Root cause:
--   p_column_mapping could include stale target columns that do not exist in
--   destination table (e.g., produto_ncm in analytics_v2.fato_transacoes).
--   The function built INSERT columns blindly and failed at runtime.
--
-- Fix:
--   - Keep only mappings where BOTH source and target columns exist.
--   - Skip invalid mappings with LOG entries.
--   - Avoid duplicate client_id column insertion.
--   - Return a clear error when no valid columns remain.
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.extract_bigquery_data(
  p_foreign_table text,
  p_destination_table text,
  p_column_mapping jsonb DEFAULT NULL::jsonb,
  p_client_id text DEFAULT NULL::text,
  p_where_clause text DEFAULT NULL::text,
  p_limit integer DEFAULT NULL::integer
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $function$
DECLARE
  v_rows_inserted BIGINT;
  v_select_parts  TEXT[];
  v_insert_cols   TEXT[];
  v_select_clause TEXT;
  v_cols_clause   TEXT;
  v_query         TEXT;
  v_key           TEXT;
  v_val           TEXT;
  v_dest_schema   TEXT;
  v_dest_table    TEXT;
  v_source_exists BOOLEAN;
  v_target_exists BOOLEAN;
  v_has_client_id BOOLEAN := FALSE;
BEGIN
  -- Parse destination relation (schema.table). Default schema: public
  IF strpos(p_destination_table, '.') > 0 THEN
    v_dest_schema := replace(split_part(p_destination_table, '.', 1), '"', '');
    v_dest_table  := replace(split_part(p_destination_table, '.', 2), '"', '');
  ELSE
    v_dest_schema := 'public';
    v_dest_table  := replace(p_destination_table, '"', '');
  END IF;

  IF p_column_mapping IS NULL OR p_column_mapping = '{}'::jsonb THEN
    v_query := format('INSERT INTO %s SELECT * FROM %s', p_destination_table, p_foreign_table);
  ELSE
    FOR v_key, v_val IN SELECT * FROM jsonb_each_text(p_column_mapping)
    LOOP
      -- Source column exists in foreign table?
      SELECT EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = to_regclass(p_foreign_table)
          AND attnum > 0
          AND NOT attisdropped
          AND attname = v_key
      ) INTO v_source_exists;

      -- Target column exists in destination table?
      SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = v_dest_schema
          AND table_name = v_dest_table
          AND column_name = v_val
      ) INTO v_target_exists;

      IF v_source_exists AND v_target_exists THEN
        v_select_parts := array_append(v_select_parts, quote_ident(v_key));
        v_insert_cols  := array_append(v_insert_cols, quote_ident(v_val));

        IF v_val = 'client_id' THEN
          v_has_client_id := TRUE;
        END IF;
      ELSE
        RAISE LOG '[extract_bq] Skipping invalid mapping source=% target=% source_exists=% target_exists=%',
          v_key, v_val, v_source_exists, v_target_exists;
      END IF;
    END LOOP;

    IF coalesce(array_length(v_insert_cols, 1), 0) = 0 THEN
      RETURN jsonb_build_object(
        'success', false,
        'error', 'No valid mapped columns found for destination table',
        'destination_table', p_destination_table
      );
    END IF;

    IF p_client_id IS NOT NULL AND NOT v_has_client_id THEN
      v_select_parts := array_append(v_select_parts, quote_literal(p_client_id));
      v_insert_cols  := array_append(v_insert_cols, 'client_id');
    END IF;

    v_select_clause := array_to_string(v_select_parts, ', ');
    v_cols_clause   := array_to_string(v_insert_cols, ', ');

    v_query := format(
      'INSERT INTO %s (%s) SELECT %s FROM %s',
      p_destination_table,
      v_cols_clause,
      v_select_clause,
      p_foreign_table
    );
  END IF;

  IF p_where_clause IS NOT NULL THEN
    v_query := v_query || ' WHERE ' || p_where_clause;
  END IF;

  IF p_limit IS NOT NULL THEN
    v_query := v_query || ' LIMIT ' || p_limit;
  END IF;

  RAISE LOG '[extract_bq] Executing: %', v_query;
  EXECUTE v_query;
  GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;

  RETURN jsonb_build_object('success', true, 'rows_inserted', v_rows_inserted, 'query', v_query);

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM, 'query', v_query);
END;
$function$;

GRANT EXECUTE ON FUNCTION public.extract_bigquery_data(text, text, jsonb, text, text, integer)
TO authenticated, service_role, postgres;

COMMIT;
