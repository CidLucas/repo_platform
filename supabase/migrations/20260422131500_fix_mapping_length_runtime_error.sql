-- =============================================================================
-- Migration: Fix mapping length runtime error in sincronizar_dados_cliente
-- Date: 2026-04-22
-- Root cause:
--   jsonb_array_length(jsonb_object_keys_as_array(v_column_mapping))
--   -> jsonb_array_length expects JSONB, but helper returns TEXT[]
--   -> runtime error: function jsonb_array_length(text[]) does not exist
-- =============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.sincronizar_dados_cliente(
  p_client_id        UUID,
  p_credential_id    INTEGER,
  p_force_full_sync  BOOLEAN DEFAULT FALSE
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_data_source    RECORD;
  v_foreign_table  TEXT;
  v_column_mapping JSONB;
  v_resource_type  TEXT;
  v_target_table   TEXT;
  v_sync_id        BIGINT;
  v_job_id         UUID;
  v_rows_inserted  INTEGER := 0;
  v_start_time     TIMESTAMPTZ := now();
  v_sync_mode      TEXT;
  v_last_watermark TIMESTAMPTZ;
  v_watermark_col  TEXT;
  v_where_clause   TEXT;
  v_extract_result JSONB;
BEGIN
  SET LOCAL statement_timeout = '1500000'; -- 25 min

  RAISE LOG '[sincronizar_dados_cliente] START client=%, credential=%, force=%',
    p_client_id, p_credential_id, p_force_full_sync;

  SELECT
    cds.id,
    cds.storage_location,
    cds.column_mapping,
    cds.resource_type,
    cds.source_type
  INTO v_data_source
  FROM public.client_data_sources cds
  WHERE cds.client_id = p_client_id
    AND cds.credential_id = p_credential_id
  ORDER BY cds.atualizado_em DESC
  LIMIT 1;

  IF v_data_source IS NULL THEN
    RAISE LOG '[sincronizar_dados_cliente] ERROR: data source not found for client=%, credential=%',
      p_client_id, p_credential_id;
    RETURN jsonb_build_object(
      'success',       false,
      'error',         'Data source not found. Run column discovery first.',
      'client_id',     p_client_id,
      'credential_id', p_credential_id
    );
  END IF;

  v_foreign_table  := v_data_source.storage_location;
  v_column_mapping := v_data_source.column_mapping;
  v_resource_type  := COALESCE(v_data_source.resource_type, 'invoices');

  IF v_foreign_table IS NULL THEN
    RETURN jsonb_build_object(
      'success', false,
      'error',   'storage_location is NULL — foreign table not yet created'
    );
  END IF;

  v_target_table := CASE v_resource_type
    WHEN 'invoices'   THEN 'analytics_v2.fato_transacoes'
    WHEN 'sales'      THEN 'analytics_v2.fato_transacoes'
    WHEN 'customers'  THEN 'analytics_v2.dim_clientes'
    WHEN 'suppliers'  THEN 'analytics_v2.dim_fornecedores'
    WHEN 'products'   THEN 'analytics_v2.dim_categoria'
    WHEN 'inventory'  THEN 'analytics_v2.dim_inventory'
    ELSE 'analytics_v2.fato_transacoes'
  END;

  RAISE LOG '[sincronizar_dados_cliente] foreign_table=%, target=%, mapping_keys=%',
    v_foreign_table,
    v_target_table,
    CASE
      WHEN v_column_mapping IS NULL THEN 'NULL (will use SELECT *)'
      WHEN jsonb_typeof(v_column_mapping) = 'object' THEN jsonb_object_length(v_column_mapping)::text
      ELSE 'NON_OBJECT (will use mapper as provided)'
    END;

  SELECT
    last_watermark_value,
    COALESCE(watermark_column, 'updated_at')
  INTO v_last_watermark, v_watermark_col
  FROM public.connector_sync_history
  WHERE cliente_vizu_id = p_client_id
    AND credential_id   = p_credential_id
    AND status          = 'completed'
  ORDER BY sync_completed_at DESC
  LIMIT 1;

  IF p_force_full_sync OR v_last_watermark IS NULL THEN
    v_sync_mode    := 'full';
    v_where_clause := NULL;
  ELSE
    v_sync_mode    := 'incremental';
    v_where_clause := format('%I > %L', v_watermark_col, v_last_watermark);
  END IF;

  RAISE LOG '[sincronizar_dados_cliente] sync_mode=%, watermark=%', v_sync_mode, v_last_watermark;

  SELECT job_id INTO v_job_id
  FROM analytics_v2.reg_jobs
  WHERE
    client_id  = p_client_id::text
    AND job_type = 'bigquery_sync'
    AND status   = 'running'
    AND (input_params->>'credential_id')::integer = p_credential_id
  ORDER BY created_at DESC
  LIMIT 1;

  INSERT INTO public.connector_sync_history (
    client_id,
    cliente_vizu_id,
    credential_id,
    status,
    sync_started_at,
    sync_mode,
    watermark_column,
    target_table,
    mapping_id
  ) VALUES (
    p_client_id,
    p_client_id,
    p_credential_id,
    'running',
    v_start_time,
    v_sync_mode,
    v_watermark_col,
    v_target_table,
    v_data_source.id
  )
  RETURNING id INTO v_sync_id;

  IF v_job_id IS NOT NULL THEN
    UPDATE analytics_v2.reg_jobs SET progress_pct = 20, updated_at = now() WHERE job_id = v_job_id;
  END IF;

  IF v_sync_mode = 'full' THEN
    RAISE LOG '[sincronizar_dados_cliente] Full sync: deleting existing rows from %', v_target_table;
    EXECUTE format('DELETE FROM %s WHERE client_id = %L', v_target_table, p_client_id::text);
    GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;
    RAISE LOG '[sincronizar_dados_cliente] Deleted % rows', v_rows_inserted;
  END IF;

  IF v_job_id IS NOT NULL THEN
    UPDATE analytics_v2.reg_jobs SET progress_pct = 30, updated_at = now() WHERE job_id = v_job_id;
  END IF;

  RAISE LOG '[sincronizar_dados_cliente] Extracting from foreign table: %', v_foreign_table;

  v_extract_result := public.extract_bigquery_data(
    p_foreign_table     := v_foreign_table,
    p_destination_table := v_target_table,
    p_column_mapping    := v_column_mapping,
    p_client_id         := p_client_id::text,
    p_where_clause      := v_where_clause,
    p_limit             := NULL
  );

  RAISE LOG '[sincronizar_dados_cliente] Extract result: %', v_extract_result;

  IF NOT COALESCE((v_extract_result->>'success')::boolean, false) THEN
    UPDATE public.connector_sync_history
    SET
      status            = 'failed',
      sync_completed_at = now(),
      error_message     = v_extract_result->>'error',
      error_details     = v_extract_result
    WHERE id = v_sync_id;

    RETURN jsonb_build_object(
      'success', false,
      'error',   COALESCE(v_extract_result->>'error', 'extract_bigquery_data returned failure'),
      'details', v_extract_result,
      'sync_id', v_sync_id
    );
  END IF;

  v_rows_inserted := COALESCE((v_extract_result->>'rows_inserted')::integer, 0);

  IF v_job_id IS NOT NULL THEN
    UPDATE analytics_v2.reg_jobs SET progress_pct = 80, updated_at = now() WHERE job_id = v_job_id;
  END IF;

  BEGIN
    PERFORM public.atualizar_agregados(p_client_id::text);
    RAISE LOG '[sincronizar_dados_cliente] Aggregates refreshed for client %', p_client_id;
  EXCEPTION WHEN OTHERS THEN
    RAISE LOG '[sincronizar_dados_cliente] WARN: aggregate refresh failed: % — continuing', SQLERRM;
  END;

  UPDATE public.connector_sync_history
  SET
    status            = 'completed',
    sync_completed_at = now(),
    records_inserted  = v_rows_inserted,
    records_processed = v_rows_inserted,
    progress_percent  = 100
  WHERE id = v_sync_id;

  UPDATE public.client_data_sources
  SET last_synced_at = now(), sync_status = 'completed'
  WHERE id = v_data_source.id;

  RAISE LOG '[sincronizar_dados_cliente] DONE rows=%, duration=%s',
    v_rows_inserted,
    EXTRACT(EPOCH FROM (now() - v_start_time))::integer;

  RETURN jsonb_build_object(
    'success',          true,
    'sync_id',          v_sync_id,
    'sync_mode',        v_sync_mode,
    'target_table',     v_target_table,
    'rows_inserted',    v_rows_inserted,
    'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))::integer
  );

EXCEPTION WHEN OTHERS THEN
  RAISE LOG '[sincronizar_dados_cliente] EXCEPTION: % (SQLSTATE: %)', SQLERRM, SQLSTATE;

  IF v_sync_id IS NOT NULL AND v_sync_id > 0 THEN
    UPDATE public.connector_sync_history
    SET
      status            = 'failed',
      sync_completed_at = now(),
      error_message     = SQLERRM,
      error_details     = jsonb_build_object('sqlstate', SQLSTATE, 'message', SQLERRM)
    WHERE id = v_sync_id;
  END IF;

  RETURN jsonb_build_object(
    'success', false,
    'error',   SQLERRM,
    'sync_id', v_sync_id
  );
END;
$$;

GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente(uuid, integer, boolean) TO authenticated, service_role, postgres;

COMMIT;
