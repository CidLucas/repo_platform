-- Migration: Sync Infrastructure RPCs
-- This migration creates:
-- 1. Watermark columns on connector_sync_history
-- 2. sincronizar_dados_cliente - Master sync orchestrator
-- 3. atualizar_agregados - Dimension refresh with incremental support

BEGIN;

-- =============================================================================
-- PHASE 1: Add watermark columns to connector_sync_history
-- =============================================================================

ALTER TABLE public.connector_sync_history
ADD COLUMN IF NOT EXISTS last_watermark_value TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS watermark_column TEXT DEFAULT 'updated_at',
ADD COLUMN IF NOT EXISTS sync_mode TEXT DEFAULT 'full'; -- 'full' or 'incremental'

COMMENT ON COLUMN public.connector_sync_history.last_watermark_value IS 'Last value of watermark_column from source for incremental sync';
COMMENT ON COLUMN public.connector_sync_history.watermark_column IS 'Column name to use for incremental sync (default: updated_at)';
COMMENT ON COLUMN public.connector_sync_history.sync_mode IS 'full = complete reload, incremental = only new/updated records';

-- =============================================================================
-- PHASE 2: Create sincronizar_dados_cliente RPC
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
BEGIN
    -- 1. Get data source configuration
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
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Data source not found for client_id and credential_id'
        );
    END IF;

    v_foreign_table := v_data_source.storage_location;
    v_column_mapping := v_data_source.column_mapping;

    -- 2. Get last sync watermark
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
    ELSE
        v_sync_mode := 'incremental';
        v_where_clause := format('%I > %L', v_watermark_column, v_last_watermark);
    END IF;

    -- 3. Create sync history record
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
        v_watermark_column,
        'analytics_v2.vendas',
        v_data_source.id
    )
    RETURNING id INTO v_sync_id;

    -- 4. Set client context for RLS
    PERFORM set_config('app.current_cliente_id', p_client_id::text, true);

    -- 5. Clear existing data if full sync
    IF v_sync_mode = 'full' THEN
        DELETE FROM analytics_v2.vendas WHERE client_id = p_client_id::text;
    END IF;

    -- 6. Extract data from BigQuery via FDW
    v_extract_result := public.extract_bigquery_data(
        p_foreign_table := v_foreign_table,
        p_destination_table := 'analytics_v2.vendas',
        p_column_mapping := v_column_mapping,
        p_where_clause := v_where_clause,
        p_limit := NULL
    );

    IF NOT (v_extract_result->>'success')::boolean THEN
        -- Update sync history with error
        UPDATE public.connector_sync_history
        SET status = 'failed',
            sync_completed_at = now(),
            duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time))::integer,
            error_message = v_extract_result->>'error',
            error_details = v_extract_result
        WHERE id = v_sync_id;

        RETURN v_extract_result;
    END IF;

    v_rows_inserted := (v_extract_result->>'rows_inserted')::integer;

    -- 7. Get new watermark (max value from inserted records)
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

    -- 8. Refresh dimension aggregates
    v_aggregate_result := analytics_v2.atualizar_agregados(p_client_id);

    -- 9. Update sync history with success
    UPDATE public.connector_sync_history
    SET status = 'completed',
        sync_completed_at = now(),
        duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time))::integer,
        records_inserted = v_rows_inserted,
        records_processed = v_rows_inserted,
        progress_percent = 100,
        last_watermark_value = COALESCE(v_new_watermark, v_last_watermark)
    WHERE id = v_sync_id;

    -- 10. Update data source last_synced_at
    UPDATE public.client_data_sources
    SET last_synced_at = now(),
        sync_status = 'completed'
    WHERE id = v_data_source.id;

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
        -- Update sync history with error
        UPDATE public.connector_sync_history
        SET status = 'failed',
            sync_completed_at = now(),
            duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time))::integer,
            error_message = SQLERRM,
            error_details = jsonb_build_object('sqlstate', SQLSTATE, 'message', SQLERRM)
        WHERE id = v_sync_id;

        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'sync_id', v_sync_id
        );
END;
$function$;

COMMENT ON FUNCTION public.sincronizar_dados_cliente IS 'Master sync orchestrator: extracts from BigQuery FDW → analytics_v2.vendas → refreshes dimension aggregates';

-- =============================================================================
-- PHASE 3: Create atualizar_agregados RPC
-- =============================================================================

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_agregados(
    p_client_id UUID
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
BEGIN
    -- ==========================================================================
    -- UPDATE CLIENTES (customers) dimension from vendas
    -- ==========================================================================
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

    -- ==========================================================================
    -- UPDATE FORNECEDORES (suppliers) dimension from vendas
    -- ==========================================================================
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

    -- ==========================================================================
    -- UPDATE PRODUTOS dimension from vendas
    -- ==========================================================================
    WITH vendas_por_produto AS (
        SELECT
            produto_id,
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
          AND produto_id IS NOT NULL
        GROUP BY produto_id, client_id
    ),
    meses_ativos_produto AS (
        SELECT
            produto_id,
            COUNT(DISTINCT date_trunc('month', data_transacao)) AS meses
        FROM analytics_v2.vendas
        WHERE client_id = v_client_id_text
          AND produto_id IS NOT NULL
        GROUP BY produto_id
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
    LEFT JOIN meses_ativos_produto map ON vpp.produto_id = map.produto_id
    WHERE p.produto_id = vpp.produto_id
      AND p.client_id = vpp.client_id;

    GET DIAGNOSTICS v_produtos_updated = ROW_COUNT;

    RETURN jsonb_build_object(
        'success', true,
        'clientes_updated', v_clientes_updated,
        'fornecedores_updated', v_fornecedores_updated,
        'produtos_updated', v_produtos_updated
    );

EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM
        );
END;
$function$;

COMMENT ON FUNCTION analytics_v2.atualizar_agregados IS 'Refreshes dimension table aggregates (clientes, fornecedores, produtos) from vendas fact table';

-- =============================================================================
-- PHASE 4: Create trigger for auto-populating dimensions on vendas INSERT
-- =============================================================================

CREATE OR REPLACE FUNCTION analytics_v2.vendas_populate_dimensions()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'pg_catalog', 'analytics_v2'
AS $function$
BEGIN
    -- Auto-insert new cliente if not exists
    IF NEW.cliente_cpf_cnpj IS NOT NULL THEN
        INSERT INTO analytics_v2.clientes (cliente_id, client_id, cpf_cnpj, nome)
        VALUES (NEW.cliente_id, NEW.client_id, NEW.cliente_cpf_cnpj, COALESCE(NEW.cliente_cpf_cnpj, 'Desconhecido'))
        ON CONFLICT (client_id, cpf_cnpj) DO NOTHING;
    END IF;

    -- Auto-insert new fornecedor if not exists
    IF NEW.fornecedor_cnpj IS NOT NULL THEN
        INSERT INTO analytics_v2.fornecedores (fornecedor_id, client_id, cnpj, nome)
        VALUES (NEW.fornecedor_id, NEW.client_id, NEW.fornecedor_cnpj, COALESCE(NEW.fornecedor_cnpj, 'Desconhecido'))
        ON CONFLICT (client_id, cnpj) DO NOTHING;
    END IF;

    RETURN NEW;
END;
$function$;

-- Create unique constraints for ON CONFLICT to work
CREATE UNIQUE INDEX IF NOT EXISTS idx_clientes_client_cpf_cnpj
    ON analytics_v2.clientes(client_id, cpf_cnpj);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fornecedores_client_cnpj
    ON analytics_v2.fornecedores(client_id, cnpj);

-- Create trigger
DROP TRIGGER IF EXISTS trg_vendas_populate_dimensions ON analytics_v2.vendas;

CREATE TRIGGER trg_vendas_populate_dimensions
    BEFORE INSERT ON analytics_v2.vendas
    FOR EACH ROW
    EXECUTE FUNCTION analytics_v2.vendas_populate_dimensions();

-- =============================================================================
-- PHASE 5: Grant permissions
-- =============================================================================

GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente TO authenticated;
GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente TO service_role;
GRANT EXECUTE ON FUNCTION analytics_v2.atualizar_agregados TO authenticated;
GRANT EXECUTE ON FUNCTION analytics_v2.atualizar_agregados TO service_role;

COMMIT;
