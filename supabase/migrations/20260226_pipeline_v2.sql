-- =============================================================================
-- Migration: Pipeline V2 - Direct FDW → Dimensions → fato_transacoes
-- Date: 2026-02-26
-- Purpose:
--   1. Ensure unique constraints on dimension tables
--   2. Seed dim_tipo_transacao with default entries
--   3. Rewrite sincronizar_dados_cliente to read from FDW foreign table
--      and write directly to dimensions + fato_transacoes (no staging table)
--   4. Rewrite atualizar_agregados to use fato_transacoes
-- =============================================================================

BEGIN;

-- =============================================================================
-- PHASE 1: Prerequisites - Unique constraints for ON CONFLICT upserts
-- =============================================================================

-- dim_clientes: ensure unique on (client_id, cpf_cnpj)
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_clientes_client_cpf
    ON analytics_v2.dim_clientes(client_id, cpf_cnpj);

-- dim_fornecedores: ensure unique on (client_id, cnpj)
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_fornecedores_client_cnpj
    ON analytics_v2.dim_fornecedores(client_id, cnpj);

-- dim_produtos: ensure unique on (client_id, nome)
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_produtos_client_nome
    ON analytics_v2.dim_produtos(client_id, nome);

-- dim_datas: ensure unique on (data) date column
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_datas_data
    ON analytics_v2.dim_datas(data);

-- =============================================================================
-- PHASE 2: Seed dim_tipo_transacao with default entries
-- =============================================================================

INSERT INTO analytics_v2.dim_tipo_transacao (codigo, descricao, categoria, natureza_operacional, impacto_caixa)
VALUES
    ('venda', 'Venda de produtos/serviços', 'entrada', 'operacional', true),
    ('compra', 'Compra de produtos/serviços', 'saida', 'operacional', true)
ON CONFLICT (codigo) DO NOTHING;

-- =============================================================================
-- PHASE 3: Helper - get source column name for a canonical name from mapping
-- The column_mapping has format: {"source_col": "canonical_col", ...}
-- This function inverts it: given a canonical name, return the source column.
-- =============================================================================

CREATE OR REPLACE FUNCTION analytics_v2.get_mapped_source(
    p_mapping JSONB,
    p_canonical TEXT
) RETURNS TEXT
LANGUAGE sql IMMUTABLE STRICT
AS $$
    SELECT key FROM jsonb_each_text(p_mapping) WHERE value = p_canonical LIMIT 1;
$$;

-- =============================================================================
-- PHASE 4: Helper - populate dim_datas for a date range
-- Ensures all dates in a range have entries in dim_datas.
-- Uses the convention: data_id = YYYYMMDD integer (e.g., 20260101)
-- =============================================================================

CREATE OR REPLACE FUNCTION analytics_v2.ensure_datas_exist(p_dates date[])
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'pg_catalog', 'analytics_v2'
AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_d DATE;
BEGIN
    FOREACH v_d IN ARRAY p_dates LOOP
        INSERT INTO analytics_v2.dim_datas (
            data_id, data, ano, ano_iso, trimestre, nome_trimestre,
            mes, nome_mes, dia, dia_do_ano, semana_do_ano,
            dia_da_semana, nome_dia, e_fim_de_semana,
            primeiro_dia_mes, ultimo_dia_mes,
            e_inicio_mes, e_fim_mes,
            e_inicio_trimestre, e_fim_trimestre,
            e_inicio_ano, e_fim_ano
        )
        VALUES (
            (EXTRACT(YEAR FROM v_d) * 10000 + EXTRACT(MONTH FROM v_d) * 100 + EXTRACT(DAY FROM v_d))::integer,
            v_d,
            EXTRACT(YEAR FROM v_d)::integer,
            EXTRACT(ISOYEAR FROM v_d)::integer,
            EXTRACT(QUARTER FROM v_d)::integer,
            'Q' || EXTRACT(QUARTER FROM v_d)::text,
            EXTRACT(MONTH FROM v_d)::integer,
            to_char(v_d, 'TMMonth'),
            EXTRACT(DAY FROM v_d)::integer,
            EXTRACT(DOY FROM v_d)::integer,
            EXTRACT(WEEK FROM v_d)::integer,
            EXTRACT(ISODOW FROM v_d)::integer,
            to_char(v_d, 'TMDay'),
            EXTRACT(ISODOW FROM v_d) IN (6, 7),
            date_trunc('month', v_d)::date,
            (date_trunc('month', v_d) + interval '1 month - 1 day')::date,
            v_d = date_trunc('month', v_d)::date,
            v_d = (date_trunc('month', v_d) + interval '1 month - 1 day')::date,
            v_d = date_trunc('quarter', v_d)::date,
            v_d = (date_trunc('quarter', v_d) + interval '3 months - 1 day')::date,
            v_d = date_trunc('year', v_d)::date,
            v_d = (date_trunc('year', v_d) + interval '1 year - 1 day')::date
        )
        ON CONFLICT (data_id) DO NOTHING;
    END LOOP;

    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    RETURN v_inserted;
END;
$$;

-- =============================================================================
-- PHASE 5: Rewrite sincronizar_dados_cliente
-- Reads from FDW foreign table → upserts dimensions → inserts fato_transacoes
-- =============================================================================

CREATE OR REPLACE FUNCTION public.sincronizar_dados_cliente(
    p_client_id TEXT,
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
    v_sync_id BIGINT;
    v_rows_inserted INTEGER := 0;
    v_start_time TIMESTAMPTZ := now();
    v_select_clause TEXT := '';
    v_src TEXT;
    -- Canonical column list for building the aliased SELECT
    v_canonical_cols TEXT[] := ARRAY[
        'pedido_id', 'data_transacao', 'status',
        'fornecedor_nome', 'fornecedor_cnpj', 'fornecedor_telefone', 'fornecedor_uf', 'fornecedor_cidade',
        'cliente_nome', 'cliente_cpf_cnpj', 'cliente_telefone',
        'cliente_rua', 'cliente_numero', 'cliente_bairro', 'cliente_cidade', 'cliente_uf', 'cliente_cep',
        'produto_descricao',
        'quantidade', 'valor_unitario', 'valor_total'
    ];
    v_col TEXT;
    v_tipo_venda_id INTEGER;
    v_dates DATE[];
    v_aggregate_result JSONB;
BEGIN
    -- 1. Get data source configuration
    SELECT
        cds.id,
        cds.storage_location,
        cds.column_mapping
    INTO v_data_source
    FROM public.client_data_sources cds
    WHERE cds.client_id = p_client_id
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

    IF v_column_mapping IS NULL OR v_column_mapping = '{}'::jsonb THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'column_mapping is empty - run column matching first'
        );
    END IF;

    -- 2. Get default tipo_id for 'venda'
    SELECT tipo_id INTO v_tipo_venda_id
    FROM analytics_v2.dim_tipo_transacao
    WHERE codigo = 'venda'
    LIMIT 1;

    IF v_tipo_venda_id IS NULL THEN
        v_tipo_venda_id := 1; -- fallback
    END IF;

    -- 3. Create sync history record
    INSERT INTO public.connector_sync_history (
        client_id, cliente_vizu_id, credential_id,
        status, sync_started_at, sync_mode,
        target_table, mapping_id
    ) VALUES (
        p_client_id::uuid, p_client_id::uuid, p_credential_id,
        'running', v_start_time, 'full',
        'analytics_v2.fato_transacoes', v_data_source.id
    )
    RETURNING id INTO v_sync_id;

    -- 4. Build SELECT clause: for each canonical column, use mapped source or NULL
    FOREACH v_col IN ARRAY v_canonical_cols LOOP
        v_src := analytics_v2.get_mapped_source(v_column_mapping, v_col);
        IF v_src IS NOT NULL THEN
            v_select_clause := v_select_clause || quote_ident(v_src) || ' AS ' || quote_ident(v_col) || ', ';
        ELSE
            v_select_clause := v_select_clause || 'NULL AS ' || quote_ident(v_col) || ', ';
        END IF;
    END LOOP;
    -- Remove trailing comma+space
    v_select_clause := rtrim(v_select_clause, ', ');

    -- 5. Create temp table with canonical column names from FDW foreign table
    EXECUTE format(
        'CREATE TEMP TABLE _sync_data ON COMMIT DROP AS SELECT %s FROM %s',
        v_select_clause, v_foreign_table
    );

    -- 6. Clear existing data if full sync
    IF p_force_full_sync THEN
        DELETE FROM analytics_v2.fato_transacoes WHERE client_id = p_client_id;
    END IF;

    -- 7. UPSERT dim_clientes from temp table
    INSERT INTO analytics_v2.dim_clientes (
        client_id, cpf_cnpj, nome, telefone,
        endereco_rua, endereco_numero, endereco_bairro,
        endereco_cidade, endereco_uf, endereco_cep
    )
    SELECT DISTINCT ON (cliente_cpf_cnpj)
        p_client_id,
        cliente_cpf_cnpj::text,
        cliente_nome::text,
        cliente_telefone::text,
        cliente_rua::text,
        cliente_numero::text,
        cliente_bairro::text,
        cliente_cidade::text,
        cliente_uf::text,
        cliente_cep::text
    FROM _sync_data
    WHERE cliente_cpf_cnpj IS NOT NULL
      AND trim(cliente_cpf_cnpj::text) <> ''
    ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
        nome = COALESCE(NULLIF(EXCLUDED.nome, ''), analytics_v2.dim_clientes.nome),
        telefone = COALESCE(NULLIF(EXCLUDED.telefone, ''), analytics_v2.dim_clientes.telefone),
        endereco_rua = COALESCE(NULLIF(EXCLUDED.endereco_rua, ''), analytics_v2.dim_clientes.endereco_rua),
        endereco_numero = COALESCE(NULLIF(EXCLUDED.endereco_numero, ''), analytics_v2.dim_clientes.endereco_numero),
        endereco_bairro = COALESCE(NULLIF(EXCLUDED.endereco_bairro, ''), analytics_v2.dim_clientes.endereco_bairro),
        endereco_cidade = COALESCE(NULLIF(EXCLUDED.endereco_cidade, ''), analytics_v2.dim_clientes.endereco_cidade),
        endereco_uf = COALESCE(NULLIF(EXCLUDED.endereco_uf, ''), analytics_v2.dim_clientes.endereco_uf),
        endereco_cep = COALESCE(NULLIF(EXCLUDED.endereco_cep, ''), analytics_v2.dim_clientes.endereco_cep),
        atualizado_em = now();

    -- 8. UPSERT dim_fornecedores from temp table
    INSERT INTO analytics_v2.dim_fornecedores (
        client_id, cnpj, nome, telefone,
        endereco_cidade, endereco_uf
    )
    SELECT DISTINCT ON (fornecedor_cnpj)
        p_client_id,
        fornecedor_cnpj::text,
        fornecedor_nome::text,
        fornecedor_telefone::text,
        fornecedor_cidade::text,
        fornecedor_uf::text
    FROM _sync_data
    WHERE fornecedor_cnpj IS NOT NULL
      AND trim(fornecedor_cnpj::text) <> ''
    ON CONFLICT (client_id, cnpj) DO UPDATE SET
        nome = COALESCE(NULLIF(EXCLUDED.nome, ''), analytics_v2.dim_fornecedores.nome),
        telefone = COALESCE(NULLIF(EXCLUDED.telefone, ''), analytics_v2.dim_fornecedores.telefone),
        endereco_cidade = COALESCE(NULLIF(EXCLUDED.endereco_cidade, ''), analytics_v2.dim_fornecedores.endereco_cidade),
        endereco_uf = COALESCE(NULLIF(EXCLUDED.endereco_uf, ''), analytics_v2.dim_fornecedores.endereco_uf),
        atualizado_em = now();

    -- 9. UPSERT dim_produtos from temp table
    INSERT INTO analytics_v2.dim_produtos (client_id, nome)
    SELECT DISTINCT p_client_id, produto_descricao::text
    FROM _sync_data
    WHERE produto_descricao IS NOT NULL
      AND trim(produto_descricao::text) <> ''
    ON CONFLICT (client_id, nome) DO NOTHING;

    -- 10. Populate dim_datas for all transaction dates
    SELECT array_agg(DISTINCT data_transacao::date)
    INTO v_dates
    FROM _sync_data
    WHERE data_transacao IS NOT NULL;

    IF v_dates IS NOT NULL THEN
        PERFORM analytics_v2.ensure_datas_exist(v_dates);
    END IF;

    -- 11. INSERT into fato_transacoes with FK resolution via JOINs
    INSERT INTO analytics_v2.fato_transacoes (
        client_id,
        data_competencia_id,
        tipo_id,
        cliente_id,
        fornecedor_id,
        produto_id,
        documento,
        quantidade,
        valor_unitario,
        valor,
        status,
        origem_tabela
    )
    SELECT
        p_client_id,
        dd.data_id,
        v_tipo_venda_id,
        dc.cliente_id,
        df.fornecedor_id,
        dp.produto_id,
        s.pedido_id::text,
        s.quantidade::numeric,
        s.valor_unitario::numeric,
        COALESCE(s.valor_total::numeric, s.quantidade::numeric * s.valor_unitario::numeric),
        s.status::text,
        'fdw_sync'
    FROM _sync_data s
    LEFT JOIN analytics_v2.dim_datas dd
        ON dd.data = s.data_transacao::date
    LEFT JOIN analytics_v2.dim_clientes dc
        ON dc.cpf_cnpj = s.cliente_cpf_cnpj::text
        AND dc.client_id = p_client_id
    LEFT JOIN analytics_v2.dim_fornecedores df
        ON df.cnpj = s.fornecedor_cnpj::text
        AND df.client_id = p_client_id
    LEFT JOIN analytics_v2.dim_produtos dp
        ON dp.nome = s.produto_descricao::text
        AND dp.client_id = p_client_id;

    GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;

    -- 12. Refresh dimension aggregates
    v_aggregate_result := analytics_v2.atualizar_agregados(p_client_id);

    -- 13. Update sync history with success
    UPDATE public.connector_sync_history
    SET status = 'completed',
        sync_completed_at = now(),
        duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time))::integer,
        records_inserted = v_rows_inserted,
        records_processed = v_rows_inserted,
        progress_percent = 100
    WHERE id = v_sync_id;

    -- 14. Update data source last_synced_at
    UPDATE public.client_data_sources
    SET last_synced_at = now(),
        sync_status = 'completed'
    WHERE id = v_data_source.id;

    RETURN jsonb_build_object(
        'success', true,
        'sync_id', v_sync_id,
        'rows_inserted', v_rows_inserted,
        'aggregates', v_aggregate_result,
        'duration_seconds', EXTRACT(EPOCH FROM (now() - v_start_time))::integer
    );

EXCEPTION
    WHEN OTHERS THEN
        -- Update sync history with error
        IF v_sync_id IS NOT NULL THEN
            UPDATE public.connector_sync_history
            SET status = 'failed',
                sync_completed_at = now(),
                duration_seconds = EXTRACT(EPOCH FROM (now() - v_start_time))::integer,
                error_message = SQLERRM,
                error_details = jsonb_build_object('sqlstate', SQLSTATE, 'message', SQLERRM)
            WHERE id = v_sync_id;
        END IF;

        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'sync_id', v_sync_id
        );
END;
$function$;

COMMENT ON FUNCTION public.sincronizar_dados_cliente IS 'Pipeline V2: FDW foreign table → dimensions → fato_transacoes → refresh aggregates';

-- =============================================================================
-- PHASE 6: Rewrite atualizar_agregados for fato_transacoes
-- =============================================================================

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_agregados(
    p_client_id TEXT
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
BEGIN
    -- ==========================================================================
    -- UPDATE dim_clientes from fato_transacoes
    -- ==========================================================================
    WITH transacoes_por_cliente AS (
        SELECT
            ft.cliente_id,
            COUNT(DISTINCT ft.documento) AS total_pedidos,
            SUM(ft.valor) AS receita_total,
            AVG(ft.valor) AS ticket_medio,
            SUM(ft.quantidade) AS quantidade_total,
            COUNT(DISTINCT ft.documento)
                FILTER (WHERE dd.data >= (now() - interval '30 days')::date)
                AS pedidos_ultimos_30_dias,
            MIN(dd.data) AS data_primeira_compra,
            MAX(dd.data) AS data_ultima_compra,
            EXTRACT(DAY FROM now() - MAX(dd.data))::integer AS dias_recencia
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
        WHERE ft.client_id = p_client_id
          AND ft.cliente_id IS NOT NULL
        GROUP BY ft.cliente_id
    ),
    meses_ativos AS (
        SELECT
            ft.cliente_id,
            COUNT(DISTINCT date_trunc('month', dd.data)) AS meses
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
        WHERE ft.client_id = p_client_id
          AND ft.cliente_id IS NOT NULL
        GROUP BY ft.cliente_id
    )
    UPDATE analytics_v2.dim_clientes c
    SET
        total_pedidos = tpc.total_pedidos,
        receita_total = tpc.receita_total,
        ticket_medio = tpc.ticket_medio,
        quantidade_total = tpc.quantidade_total,
        pedidos_ultimos_30_dias = tpc.pedidos_ultimos_30_dias,
        data_primeira_compra = tpc.data_primeira_compra,
        data_ultima_compra = tpc.data_ultima_compra,
        dias_recencia = tpc.dias_recencia,
        frequencia_mensal = CASE WHEN ma.meses > 0 THEN tpc.total_pedidos::numeric / ma.meses ELSE 0 END,
        atualizado_em = now()
    FROM transacoes_por_cliente tpc
    LEFT JOIN meses_ativos ma ON tpc.cliente_id = ma.cliente_id
    WHERE c.cliente_id = tpc.cliente_id
      AND c.client_id = p_client_id;

    GET DIAGNOSTICS v_clientes_updated = ROW_COUNT;

    -- ==========================================================================
    -- UPDATE dim_fornecedores from fato_transacoes
    -- ==========================================================================
    WITH transacoes_por_fornecedor AS (
        SELECT
            ft.fornecedor_id,
            COUNT(DISTINCT ft.documento) AS total_pedidos_recebidos,
            SUM(ft.valor) AS receita_total,
            AVG(ft.valor) AS ticket_medio,
            COUNT(DISTINCT ft.produto_id) AS total_produtos_fornecidos,
            MIN(dd.data) AS data_primeira_transacao,
            MAX(dd.data) AS data_ultima_transacao,
            EXTRACT(DAY FROM now() - MAX(dd.data))::integer AS dias_recencia
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
        WHERE ft.client_id = p_client_id
          AND ft.fornecedor_id IS NOT NULL
        GROUP BY ft.fornecedor_id
    ),
    meses_ativos_fornecedor AS (
        SELECT
            ft.fornecedor_id,
            COUNT(DISTINCT date_trunc('month', dd.data)) AS meses
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
        WHERE ft.client_id = p_client_id
          AND ft.fornecedor_id IS NOT NULL
        GROUP BY ft.fornecedor_id
    )
    UPDATE analytics_v2.dim_fornecedores f
    SET
        total_pedidos_recebidos = tpf.total_pedidos_recebidos,
        receita_total = tpf.receita_total,
        ticket_medio = tpf.ticket_medio,
        total_produtos_fornecidos = tpf.total_produtos_fornecidos,
        data_primeira_transacao = tpf.data_primeira_transacao,
        data_ultima_transacao = tpf.data_ultima_transacao,
        dias_recencia = tpf.dias_recencia,
        frequencia_mensal = CASE WHEN maf.meses > 0 THEN tpf.total_pedidos_recebidos::numeric / maf.meses ELSE 0 END,
        atualizado_em = now()
    FROM transacoes_por_fornecedor tpf
    LEFT JOIN meses_ativos_fornecedor maf ON tpf.fornecedor_id = maf.fornecedor_id
    WHERE f.fornecedor_id = tpf.fornecedor_id
      AND f.client_id = p_client_id;

    GET DIAGNOSTICS v_fornecedores_updated = ROW_COUNT;

    -- ==========================================================================
    -- UPDATE dim_produtos from fato_transacoes
    -- ==========================================================================
    WITH transacoes_por_produto AS (
        SELECT
            ft.produto_id,
            SUM(ft.quantidade) AS quantidade_total_vendida,
            SUM(ft.valor) AS receita_total,
            AVG(ft.valor_unitario) AS preco_medio,
            COUNT(DISTINCT ft.documento) AS total_pedidos,
            AVG(ft.quantidade) AS quantidade_media_por_pedido,
            MAX(dd.data) AS data_ultima_venda,
            EXTRACT(DAY FROM now() - MAX(dd.data))::integer AS dias_recencia
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
        WHERE ft.client_id = p_client_id
          AND ft.produto_id IS NOT NULL
        GROUP BY ft.produto_id
    ),
    meses_ativos_produto AS (
        SELECT
            ft.produto_id,
            COUNT(DISTINCT date_trunc('month', dd.data)) AS meses
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
        WHERE ft.client_id = p_client_id
          AND ft.produto_id IS NOT NULL
        GROUP BY ft.produto_id
    )
    UPDATE analytics_v2.dim_produtos p
    SET
        quantidade_total_vendida = tpp.quantidade_total_vendida,
        receita_total = tpp.receita_total,
        preco_medio = tpp.preco_medio,
        total_pedidos = tpp.total_pedidos,
        quantidade_media_por_pedido = tpp.quantidade_media_por_pedido,
        data_ultima_venda = tpp.data_ultima_venda,
        dias_recencia = tpp.dias_recencia,
        frequencia_mensal = CASE WHEN map.meses > 0 THEN tpp.total_pedidos::numeric / map.meses ELSE 0 END,
        atualizado_em = now()
    FROM transacoes_por_produto tpp
    LEFT JOIN meses_ativos_produto map ON tpp.produto_id = map.produto_id
    WHERE p.produto_id = tpp.produto_id
      AND p.client_id = p_client_id;

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

COMMENT ON FUNCTION analytics_v2.atualizar_agregados IS 'Refreshes dimension aggregates from fato_transacoes';

-- =============================================================================
-- PHASE 7: Grant permissions
-- =============================================================================

GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente TO authenticated;
GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente TO service_role;
GRANT EXECUTE ON FUNCTION analytics_v2.atualizar_agregados TO authenticated;
GRANT EXECUTE ON FUNCTION analytics_v2.atualizar_agregados TO service_role;
GRANT EXECUTE ON FUNCTION analytics_v2.get_mapped_source TO authenticated;
GRANT EXECUTE ON FUNCTION analytics_v2.get_mapped_source TO service_role;
GRANT EXECUTE ON FUNCTION analytics_v2.ensure_datas_exist TO authenticated;
GRANT EXECUTE ON FUNCTION analytics_v2.ensure_datas_exist TO service_role;

COMMIT;
