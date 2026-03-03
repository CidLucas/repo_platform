-- =============================================================================
-- Migration: Enhance Sync RPCs with Comprehensive Logging
-- Date: 2026-03-02
-- Purpose: Add detailed logging to data sync pipeli ne with progress tracking
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. ENHANCED sincronizar_dados_cliente WITH LOGGING AND PROGRESS TRACKING
-- =============================================================================

CREATE OR REPLACE FUNCTION public.sincronizar_dados_cliente(
    p_client_id UUID,
    p_credential_id INTEGER,
    p_force_full_sync BOOLEAN DEFAULT FALSE
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'pg_catalog', 'public', 'analytics_v2'
AS $function$
DECLARE
    v_data_source RECORD;
    v_foreign_table TEXT;
    v_column_mapping JSONB;
    v_last_watermark TIMESTAMPTZ;
    v_watermark_column TEXT;
    v_where_clause TEXT;
    v_sync_id BIGINT;
    v_extract_result JSONB;
    v_aggregate_result JSONB;
    v_rows_inserted INTEGER := 0;
    v_sync_mode TEXT;
    v_new_watermark TIMESTAMPTZ;
    v_start_time TIMESTAMPTZ := now();
    v_step_start TIMESTAMPTZ;
    v_step_duration INTEGER;
BEGIN
    -- === STEP 1: Get data source configuration (Progress: 10%) ===
    v_step_start := clock_timestamp();

    RAISE LOG '[sincronizar_dados_cliente] Starting sync for client_id=%, credential_id=%, force_full=%',
        p_client_id, p_credential_id, p_force_full_sync;

    SELECT
        cds.id,
        cds.storage_location,
        cds.column_mapping,
        cds.source_type
    INTO v_data_source
    FROM public.client_data_sources cds
    WHERE cds.client_id = p_client_id::text
      AND cds.credential_id = p_credential_id
    LIMIT 1;

    IF v_data_source IS NULL THEN
        RAISE LOG '[sincronizar_dados_cliente] ERROR: Data source not found for client_id=%, credential_id=%',
            p_client_id, p_credential_id;

        RETURN jsonb_build_object(
            'success', false,
            'error', 'Data source not found for client_id and credential_id'
        );
    END IF;

    v_foreign_table := v_data_source.storage_location;
    v_column_mapping := v_data_source.column_mapping;

    v_step_duration := EXTRACT(EPOCH FROM (clock_timestamp() - v_step_start)) * 1000;
    RAISE LOG '[sincronizar_dados_cliente] Data source retrieved: storage_location=%, mapping_keys=%, duration=%ms',
        v_foreign_table, jsonb_object_keys(v_column_mapping), v_step_duration;

    -- === STEP 2: Determine sync mode (Progress: 15%) ===
    v_step_start := clock_timestamp();

    SELECT
        last_watermark_value,
        COALESCE(watermark_column, 'updated_at')
    INTO v_last_watermark, v_watermark_column
    FROM public.connector_sync_history
    WHERE cliente_vizu_id = p_client_id
      AND credential_id = p_credential_id
      AND status = 'completed'
    ORDER BY sync_completed_at DESC
    LIMIT 1;

    -- Determine sync mode
    IF p_force_full_sync OR v_last_watermark IS NULL THEN
        v_sync_mode := 'full';
        v_where_clause := NULL;
        RAISE LOG '[sincronizar_dados_cliente] Sync mode: FULL (force_full_sync=% or no prior watermark)',
            p_force_full_sync;
    ELSE
        v_sync_mode := 'incremental';
        v_where_clause := format('%I > %L', v_watermark_column, v_last_watermark);
        RAISE LOG '[sincronizar_dados_cliente] Sync mode: INCREMENTAL (watermark_column=%, last_watermark=%)',
            v_watermark_column, v_last_watermark;
    END IF;

    -- === STEP 3: Create sync history record (Progress: 20%) ===
    INSERT INTO public.connector_sync_history (
        client_id,
        cliente_vizu_id,
        credential_id,
        status,
        sync_started_at,
        sync_mode,
        watermark_column,
        target_table,
        mapping_id,
        progress_percent
    ) VALUES (
        p_client_id,
        p_client_id,
        p_credential_id,
        'running',
        v_start_time,
        v_sync_mode,
        v_watermark_column,
        'analytics_v2.vendas',
        v_data_source.id,
        20
    )
    RETURNING id INTO v_sync_id;

    RAISE LOG '[sincronizar_dados_cliente] Created sync history record: sync_id=%', v_sync_id;

    -- Log sync start event
    PERFORM public.log_ingestion_event(
        v_sync_id,
        'sync_start',
        'info',
        'Data synchronization started',
        jsonb_build_object(
            'sync_mode', v_sync_mode,
            'foreign_table', v_foreign_table,
            'column_mapping_keys', (SELECT jsonb_object_keys(v_column_mapping))
        ),
        p_client_id::text,
        p_client_id,
        p_credential_id
    );

    -- === STEP 4: Set client context for RLS (Progress: 25%) ===
    PERFORM set_config('app.current_cliente_id', p_client_id::text, true);
    RAISE LOG '[sincronizar_dados_cliente] RLS context set: app.current_cliente_id=%', p_client_id;

    -- === STEP 5: Clear existing data if full sync (Progress: 30%) ===
    IF v_sync_mode = 'full' THEN
        v_step_start := clock_timestamp();

        DELETE FROM analytics_v2.vendas WHERE client_id = p_client_id::text;
        GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;

        v_step_duration := EXTRACT(EPOCH FROM (clock_timestamp() - v_step_start)) * 1000;
        RAISE LOG '[sincronizar_dados_cliente] Deleted % existing rows from analytics_v2.vendas in %ms',
            v_rows_inserted, v_step_duration;

        PERFORM public.log_ingestion_event(
            v_sync_id,
            'clear_data',
            'info',
            format('Cleared %s existing rows for full sync', v_rows_inserted),
            jsonb_build_object('rows_deleted', v_rows_inserted, 'duration_ms', v_step_duration),
            p_client_id::text,
            p_client_id,
            p_credential_id
        );

        UPDATE public.connector_sync_history
        SET progress_percent = 30
        WHERE id = v_sync_id;
    END IF;

    -- === STEP 6: Extract data from BigQuery via FDW (Progress: 30% → 70%) ===
    v_step_start := clock_timestamp();

    RAISE LOG '[sincronizar_dados_cliente] Starting data extraction from foreign table: %', v_foreign_table;

    PERFORM public.log_ingestion_event(
        v_sync_id,
        'extraction_start',
        'info',
        'Starting data extraction from BigQuery',
        jsonb_build_object(
            'foreign_table', v_foreign_table,
            'where_clause', v_where_clause
        ),
        p_client_id::text,
        p_client_id,
        p_credential_id
    );

    UPDATE public.connector_sync_history
    SET progress_percent = 40
    WHERE id = v_sync_id;

    v_extract_result := public.extract_bigquery_data(
        p_foreign_table := v_foreign_table,
        p_destination_table := 'analytics_v2.vendas',
        p_column_mapping := v_column_mapping,
        p_where_clause := v_where_clause,
        p_limit := NULL,
        p_sync_id := v_sync_id  -- Pass sync_id for progress tracking
    );

    IF NOT (v_extract_result->>'success')::boolean THEN
        v_step_duration := EXTRACT(EPOCH FROM (clock_timestamp() - v_step_start)) * 1000;

        RAISE LOG '[sincronizar_dados_cliente] ERROR during extraction: % (duration: %ms)',
            v_extract_result->>'error', v_step_duration;

        -- Log extraction failure
        PERFORM public.log_ingestion_event(
            v_sync_id,
            'extraction_failed',
            'error',
            v_extract_result->>'error',
            v_extract_result || jsonb_build_object('duration_ms', v_step_duration),
            p_client_id::text,
            p_client_id,
            p_credential_id
        );

        -- Update sync history with error
        UPDATE public.connector_sync_history
        SET status = 'failed',
            sync_completed_at = now(),
            duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time))::integer,
            error_message = v_extract_result->>'error',
            error_details = v_extract_result,
            progress_percent = 0
        WHERE id = v_sync_id;

        RETURN v_extract_result;
    END IF;

    v_rows_inserted := (v_extract_result->>'rows_inserted')::integer;
    v_step_duration := EXTRACT(EPOCH FROM (clock_timestamp() - v_step_start)) * 1000;

    RAISE LOG '[sincronizar_dados_cliente] Extraction completed: rows_inserted=%, duration=%ms',
        v_rows_inserted, v_step_duration;

    PERFORM public.log_ingestion_event(
        v_sync_id,
        'extraction_complete',
        'success',
        format('Successfully extracted %s rows', v_rows_inserted),
        v_extract_result || jsonb_build_object('total_duration_ms', v_step_duration),
        p_client_id::text,
        p_client_id,
        p_credential_id
    );

    UPDATE public.connector_sync_history
    SET progress_percent = 70,
        records_processed = v_rows_inserted
    WHERE id = v_sync_id;

    -- === STEP 7: Get new watermark (Progress: 75%) ===
    v_step_start := clock_timestamp();

    EXECUTE format(
        'SELECT max(%I) FROM analytics_v2.vendas WHERE client_id = $1',
        CASE v_watermark_column
            WHEN 'updated_at' THEN 'atualizado_em'
            WHEN 'created_at' THEN 'criado_em'
            ELSE 'atualizado_em'
        END
    )
    INTO v_new_watermark
    USING p_client_id::text;

    RAISE LOG '[sincronizar_dados_cliente] New watermark: % (column: %)',
        v_new_watermark, v_watermark_column;

    UPDATE public.connector_sync_history
    SET progress_percent = 75,
        last_watermark_value = COALESCE(v_new_watermark, v_last_watermark)
    WHERE id = v_sync_id;

    -- === STEP 8: Refresh dimension aggregates (Progress: 75% → 90%) ===
    v_step_start := clock_timestamp();

    RAISE LOG '[sincronizar_dados_cliente] Starting dimension aggregate refresh';

    PERFORM public.log_ingestion_event(
        v_sync_id,
        'aggregation_start',
        'info',
        'Starting dimension aggregate refresh',
        jsonb_build_object('target_dimensions', jsonb_build_array('clientes', 'fornecedores', 'produtos')),
        p_client_id::text,
        p_client_id,
        p_credential_id
    );

    UPDATE public.connector_sync_history
    SET progress_percent = 80
    WHERE id = v_sync_id;

    v_aggregate_result := analytics_v2.atualizar_agregados(p_client_id, v_sync_id);

    v_step_duration := EXTRACT(EPOCH FROM (clock_timestamp() - v_step_start)) * 1000;

    RAISE LOG '[sincronizar_dados_cliente] Aggregation completed in %ms: %',
        v_step_duration, v_aggregate_result;

    PERFORM public.log_ingestion_event(
        v_sync_id,
        'aggregation_complete',
        'success',
        'Dimension aggregates refreshed successfully',
        v_aggregate_result || jsonb_build_object('duration_ms', v_step_duration),
        p_client_id::text,
        p_client_id,
        p_credential_id
    );

    -- === STEP 9: Update sync history with success (Progress: 100%) ===
    UPDATE public.connector_sync_history
    SET status = 'completed',
        sync_completed_at = now(),
        duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time))::integer,
        records_inserted = v_rows_inserted,
        records_processed = v_rows_inserted,
        progress_percent = 100,
        last_watermark_value = COALESCE(v_new_watermark, v_last_watermark)
    WHERE id = v_sync_id;

    RAISE LOG '[sincronizar_dados_cliente] Sync completed successfully: sync_id=%, total_duration=%s',
        v_sync_id, EXTRACT(EPOCH FROM (now() - v_start_time))::integer;

    -- === STEP 10: Update data source last_synced_at ===
    UPDATE public.client_data_sources
    SET last_synced_at = now(),
        sync_status = 'completed',
        atualizado_em = now()
    WHERE id = v_data_source.id;

    PERFORM public.log_ingestion_event(
        v_sync_id,
        'sync_complete',
        'success',
        format('Sync completed: %s rows inserted in %s seconds', v_rows_inserted, EXTRACT(EPOCH FROM (now() - v_start_time))::integer),
        jsonb_build_object(
            'rows_inserted', v_rows_inserted,
            'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))::integer,
            'sync_mode', v_sync_mode,
            'watermark', v_new_watermark,
            'aggregates', v_aggregate_result
        ),
        p_client_id::text,
        p_client_id,
        p_credential_id
    );

    RETURN jsonb_build_object(
        'success', true,
        'sync_id', v_sync_id,
        'sync_mode', v_sync_mode,
        'rows_inserted', v_rows_inserted,
        'watermark', v_new_watermark,
        'aggregates', v_aggregate_result,
        'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))::integer
    );

EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG '[sincronizar_dados_cliente] EXCEPTION: % - % (SQLSTATE: %)',
            SQLERRM, SQLSTATE, SQLSTATE;

        -- Log exception
        PERFORM public.log_ingestion_event(
            v_sync_id,
            'sync_failed',
            'error',
            SQLERRM,
            jsonb_build_object(
                'sqlstate', SQLSTATE,
                'message', SQLERRM,
                'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))::integer
            ),
            p_client_id::text,
            p_client_id,
            p_credential_id
        );

        -- Update sync history with error
        UPDATE public.connector_sync_history
        SET status = 'failed',
            sync_completed_at = now(),
            duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time))::integer,
            error_message = SQLERRM,
            error_details = jsonb_build_object('sqlstate', SQLSTATE, 'message', SQLERRM),
            progress_percent = 0
        WHERE id = v_sync_id;

        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'sync_id', v_sync_id,
            'sqlstate', SQLSTATE
        );
END;
$function$;

COMMENT ON FUNCTION public.sincronizar_dados_cliente IS
  'Master sync orchestrator with comprehensive logging and progress tracking: BigQuery FDW → analytics_v2.vendas → dimension aggregates';

-- =============================================================================
-- 2. ENHANCED atualizar_agregados WITH LOGGING
-- =============================================================================

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_agregados(
    p_client_id UUID,
    p_sync_id BIGINT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'pg_catalog', 'analytics_v2', 'public'
AS $function$
DECLARE
    v_clientes_updated INTEGER := 0;
    v_fornecedores_updated INTEGER := 0;
    v_produtos_updated INTEGER := 0;
    v_client_id_text TEXT := p_client_id::text;
    v_start_time TIMESTAMPTZ := clock_timestamp();
    v_step_start TIMESTAMPTZ;
    v_step_duration INTEGER;
BEGIN
    RAISE LOG '[atualizar_agregados] Starting aggregate refresh for client_id=%', p_client_id;

    -- === UPDATE CLIENTES (customers) dimension ===
    v_step_start := clock_timestamp();

    WITH vendas_por_cliente AS (
        SELECT
            cliente_cpf_cnpj AS cpf_cnpj,
            client_id,
            COUNT(DISTINCT pedido_id) AS total_pedidos,
            SUM(valor_total) AS receita_total,
            AVG(valor_total) AS ticket_medio,
            SUM(quantidade) AS quantidade_total,
            COUNT(DISTINCT pedido_id) FILTER (WHERE data_transacao >= now() - interval '30 days') AS pedidos_ultimos_30_dias,
            MIN(data_transacao)::date AS data_primeira_compra,
            MAX(data_transacao)::date AS data_ultima_compra,
            EXTRACT(DAY FROM now() - MAX(data_transacao))::integer AS dias_recencia
        FROM analytics_v2.vendas
        WHERE client_id = v_client_id_text
          AND cliente_cpf_cnpj IS NOT NULL
        GROUP BY cliente_cpf_cnpj, client_id
    ),
    meses_ativos AS (
        SELECT
            cliente_cpf_cnpj AS cpf_cnpj,
            COUNT(DISTINCT date_trunc('month', data_transacao)) AS meses
        FROM analytics_v2.vendas
        WHERE client_id = v_client_id_text
          AND cliente_cpf_cnpj IS NOT NULL
        GROUP BY cliente_cpf_cnpj
    )
    UPDATE analytics_v2.clientes c
    SET
        total_pedidos = vpc.total_pedidos,
        receita_total = vpc.receita_total,
        ticket_medio = vpc.ticket_medio,
        quantidade_total = vpc.quantidade_total,
        pedidos_ultimos_30_dias = vpc.pedidos_ultimos_30_dias,
        data_primeira_compra = vpc.data_primeira_compra,
        data_ultima_compra = vpc.data_ultima_compra,
        dias_recencia = vpc.dias_recencia,
        frequencia_mensal = CASE WHEN ma.meses > 0 THEN vpc.total_pedidos::numeric / ma.meses ELSE 0 END,
        atualizado_em = now()
    FROM vendas_por_cliente vpc
    LEFT JOIN meses_ativos ma ON vpc.cpf_cnpj = ma.cpf_cnpj
    WHERE c.cpf_cnpj = vpc.cpf_cnpj
      AND c.client_id = vpc.client_id;

    GET DIAGNOSTICS v_clientes_updated = ROW_COUNT;
    v_step_duration := EXTRACT(EPOCH FROM (clock_timestamp() - v_step_start)) * 1000;

    RAISE LOG '[atualizar_agregados] Updated % clientes in %ms', v_clientes_updated, v_step_duration;

    -- === UPDATE FORNECEDORES (suppliers) dimension ===
    v_step_start := clock_timestamp();

    WITH vendas_por_fornecedor AS (
        SELECT
            fornecedor_cnpj AS cnpj,
            client_id,
            COUNT(DISTINCT pedido_id) AS total_pedidos_recebidos,
            SUM(valor_total) AS receita_total,
            AVG(valor_total) AS ticket_medio,
            COUNT(DISTINCT produto_id) AS total_produtos_fornecidos,
            MIN(data_transacao)::date AS data_primeira_transacao,
            MAX(data_transacao)::date AS data_ultima_transacao,
            EXTRACT(DAY FROM now() - MAX(data_transacao))::integer AS dias_recencia
        FROM analytics_v2.vendas
        WHERE client_id = v_client_id_text
          AND fornecedor_cnpj IS NOT NULL
        GROUP BY fornecedor_cnpj, client_id
    ),
    meses_ativos_fornecedor AS (
        SELECT
            fornecedor_cnpj AS cnpj,
            COUNT(DISTINCT date_trunc('month', data_transacao)) AS meses
        FROM analytics_v2.vendas
        WHERE client_id = v_client_id_text
          AND fornecedor_cnpj IS NOT NULL
        GROUP BY fornecedor_cnpj
    )
    UPDATE analytics_v2.fornecedores f
    SET
        total_pedidos_recebidos = vpf.total_pedidos_recebidos,
        receita_total = vpf.receita_total,
        ticket_medio = vpf.ticket_medio,
        total_produtos_fornecidos = vpf.total_produtos_fornecidos,
        data_primeira_transacao = vpf.data_primeira_transacao,
        data_ultima_transacao = vpf.data_ultima_transacao,
        dias_recencia = vpf.dias_recencia,
        frequencia_mensal = CASE WHEN maf.meses > 0 THEN vpf.total_pedidos_recebidos::numeric / maf.meses ELSE 0 END,
        atualizado_em = now()
    FROM vendas_por_fornecedor vpf
    LEFT JOIN meses_ativos_fornecedor maf ON vpf.cnpj = maf.cnpj
    WHERE f.cnpj = vpf.cnpj
      AND f.client_id = vpf.client_id;

    GET DIAGNOSTICS v_fornecedores_updated = ROW_COUNT;
    v_step_duration := EXTRACT(EPOCH FROM (clock_timestamp() - v_step_start)) * 1000;

    RAISE LOG '[atualizar_agregados] Updated % fornecedores in %ms', v_fornecedores_updated, v_step_duration;

    -- === UPDATE PRODUTOS (products) dimension ===
    v_step_start := clock_timestamp();

    WITH vendas_por_produto AS (
        SELECT
            produto_descricao AS nome,
            client_id,
            SUM(quantidade) AS quantidade_total_vendida,
            SUM(valor_total) AS receita_total,
            AVG(valor_unitario) AS preco_medio,
            COUNT(DISTINCT pedido_id) AS total_pedidos,
            AVG(quantidade) AS quantidade_media_por_pedido,
            MAX(data_transacao)::date AS data_ultima_venda,
            EXTRACT(DAY FROM now() - MAX(data_transacao))::integer AS dias_recencia
        FROM analytics_v2.vendas
        WHERE client_id = v_client_id_text
          AND produto_descricao IS NOT NULL
        GROUP BY produto_descricao, client_id
    ),
    meses_ativos_produto AS (
        SELECT
            produto_descricao AS nome,
            COUNT(DISTINCT date_trunc('month', data_transacao)) AS meses
        FROM analytics_v2.vendas
        WHERE client_id = v_client_id_text
          AND produto_descricao IS NOT NULL
        GROUP BY produto_descricao
    )
    UPDATE analytics_v2.produtos p
    SET
        quantidade_total_vendida = vpp.quantidade_total_vendida,
        receita_total = vpp.receita_total,
        preco_medio = vpp.preco_medio,
        total_pedidos = vpp.total_pedidos,
        quantidade_media_por_pedido = vpp.quantidade_media_por_pedido,
        data_ultima_venda = vpp.data_ultima_venda,
        dias_recencia = vpp.dias_recencia,
        frequencia_mensal = CASE WHEN map.meses > 0 THEN vpp.total_pedidos::numeric / map.meses ELSE 0 END,
        atualizado_em = now()
    FROM vendas_por_produto vpp
    LEFT JOIN meses_ativos_produto map ON vpp.nome = map.nome
    WHERE p.nome = vpp.nome
      AND p.client_id = vpp.client_id;

    GET DIAGNOSTICS v_produtos_updated = ROW_COUNT;
    v_step_duration := EXTRACT(EPOCH FROM (clock_timestamp() - v_step_start)) * 1000;

    RAISE LOG '[atualizar_agregados] Updated % produtos in %ms', v_produtos_updated, v_step_duration;

    -- Log aggregate completion
    IF p_sync_id IS NOT NULL THEN
        PERFORM public.log_ingestion_event(
            p_sync_id,
            'aggregation_dimensions',
            'success',
            format('Dimension aggregates updated: %s clientes, %s fornecedores, %s produtos',
                v_clientes_updated, v_fornecedores_updated, v_produtos_updated),
            jsonb_build_object(
                'clientes_updated', v_clientes_updated,
                'fornecedores_updated', v_fornecedores_updated,
                'produtos_updated', v_produtos_updated,
                'total_duration_ms', EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)) * 1000
            ),
            v_client_id_text,
            p_client_id,
            NULL
        );
    END IF;

    RAISE LOG '[atualizar_agregados] Completed in %ms: clientes=%, fornecedores=%, produtos=%',
        EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)) * 1000,
        v_clientes_updated, v_fornecedores_updated, v_produtos_updated;

    RETURN jsonb_build_object(
        'success', TRUE,
        'clientes_updated', v_clientes_updated,
        'fornecedores_updated', v_fornecedores_updated,
        'produtos_updated', v_produtos_updated,
        'duration_ms', EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)) * 1000
    );

EXCEPTION
    WHEN OTHERS THEN
        RAISE LOG '[atualizar_agregados] ERROR: % - %', SQLERRM, SQLSTATE;

        RETURN jsonb_build_object(
            'success', FALSE,
            'error', SQLERRM,
            'sqlstate', SQLSTATE
        );
END;
$function$;

COMMENT ON FUNCTION analytics_v2.atualizar_agregados IS
  'Refresh dimension table aggregates (clientes, fornecedores, produtos) from vendas fact table with detailed logging';

COMMIT;
