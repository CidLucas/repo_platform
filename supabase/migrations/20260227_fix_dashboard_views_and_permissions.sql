-- =============================================================================
-- Migration: Fix dashboard views, permissions, and dim_produtos → dim_inventory
-- Date: 2026-02-27
-- Purpose:
--   1. Add missing aggregate columns to dim_inventory
--   2. Add unique constraint for upserts
--   3. Recreate all dashboard views using dim_inventory instead of dim_produtos
--   4. Fix pipeline functions (sincronizar_dados_cliente, atualizar_agregados)
--   5. Add missing GRANTs for authenticated role
-- =============================================================================

BEGIN;

-- =============================================================================
-- PHASE 1: Add missing columns to dim_inventory
-- =============================================================================

ALTER TABLE analytics_v2.dim_inventory
  ADD COLUMN IF NOT EXISTS quantidade_media_por_pedido numeric DEFAULT 0,
  ADD COLUMN IF NOT EXISTS dias_recencia integer DEFAULT 0,
  ADD COLUMN IF NOT EXISTS data_ultima_venda date,
  ADD COLUMN IF NOT EXISTS frequencia_mensal numeric DEFAULT 0,
  ADD COLUMN IF NOT EXISTS pontuacao_cluster numeric,
  ADD COLUMN IF NOT EXISTS nivel_cluster varchar;

-- Unique constraint for upsert (ON CONFLICT) in sync pipeline
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_inventory_client_nome
    ON analytics_v2.dim_inventory(client_id, nome);

-- =============================================================================
-- PHASE 2: Recreate dashboard views
-- =============================================================================

-- v_resumo_dashboard: Dashboard summary scorecards
DROP VIEW IF EXISTS analytics_v2.v_resumo_dashboard CASCADE;
CREATE VIEW analytics_v2.v_resumo_dashboard AS
SELECT
    public.get_my_client_id() AS client_id,
    (SELECT count(*) FROM analytics_v2.dim_clientes
     WHERE client_id = public.get_my_client_id()) AS total_clientes,
    (SELECT count(*) FROM analytics_v2.dim_fornecedores
     WHERE client_id = public.get_my_client_id()) AS total_fornecedores,
    (SELECT count(*) FROM analytics_v2.dim_inventory
     WHERE client_id = public.get_my_client_id()) AS total_produtos,
    (SELECT count(DISTINCT documento) FROM analytics_v2.fato_transacoes
     WHERE client_id = public.get_my_client_id()) AS total_pedidos,
    (SELECT COALESCE(sum(valor), 0) FROM analytics_v2.fato_transacoes
     WHERE client_id = public.get_my_client_id()) AS receita_total,
    (SELECT COALESCE(avg(valor), 0) FROM analytics_v2.fato_transacoes
     WHERE client_id = public.get_my_client_id()) AS ticket_medio,
    now() AS gerado_em;

-- v_series_temporal: Time series charts
DROP VIEW IF EXISTS analytics_v2.v_series_temporal CASCADE;
CREATE VIEW analytics_v2.v_series_temporal AS
-- Fornecedores over time
SELECT ft.client_id,
    'fornecedores_no_tempo'::text AS tipo_grafico,
    'fornecedores'::text AS dimensao,
    to_char(dd.data, 'YYYY-MM') AS periodo,
    date_trunc('month', dd.data)::date AS data_periodo,
    count(DISTINCT ft.fornecedor_id) AS total
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL

-- Clientes over time
SELECT ft.client_id,
    'clientes_no_tempo'::text AS tipo_grafico,
    'clientes'::text AS dimensao,
    to_char(dd.data, 'YYYY-MM') AS periodo,
    date_trunc('month', dd.data)::date AS data_periodo,
    count(DISTINCT ft.cliente_id) AS total
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL

-- Produtos over time (using inventory_id)
SELECT ft.client_id,
    'produtos_no_tempo'::text AS tipo_grafico,
    'produtos'::text AS dimensao,
    to_char(dd.data, 'YYYY-MM') AS periodo,
    date_trunc('month', dd.data)::date AS data_periodo,
    count(DISTINCT ft.inventory_id) AS total
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL

-- Pedidos over time
SELECT ft.client_id,
    'pedidos_no_tempo'::text AS tipo_grafico,
    'pedidos'::text AS dimensao,
    to_char(dd.data, 'YYYY-MM') AS periodo,
    date_trunc('month', dd.data)::date AS data_periodo,
    count(DISTINCT ft.documento) AS total
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL

-- Receita over time
SELECT ft.client_id,
    'receita_no_tempo'::text AS tipo_grafico,
    'receita'::text AS dimensao,
    to_char(dd.data, 'YYYY-MM') AS periodo,
    date_trunc('month', dd.data)::date AS data_periodo,
    COALESCE(sum(ft.valor), 0)::bigint AS total
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date;

-- v_ultimos_pedidos: Last 100 orders per client
DROP VIEW IF EXISTS analytics_v2.v_ultimos_pedidos CASCADE;
CREATE VIEW analytics_v2.v_ultimos_pedidos AS
WITH resumo_pedido AS (
    SELECT ft.client_id,
        ft.documento AS pedido_id,
        dd.data AS data_transacao,
        dc.cpf_cnpj AS cliente_cpf_cnpj,
        max(dc.nome) AS nome_cliente,
        sum(ft.valor) AS valor_pedido,
        count(*) AS qtd_produtos,
        row_number() OVER (
            PARTITION BY ft.client_id
            ORDER BY max(dd.data) DESC, ft.documento DESC
        ) AS ordem
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
    WHERE dd.data IS NOT NULL
    GROUP BY ft.client_id, ft.documento, dd.data, dc.cpf_cnpj
)
SELECT client_id,
    pedido_id,
    data_transacao,
    cliente_cpf_cnpj,
    nome_cliente,
    valor_pedido,
    qtd_produtos,
    ordem
FROM resumo_pedido
WHERE ordem <= 100;

-- v_produtos_por_cliente: Customer-product relationships (using dim_inventory)
DROP VIEW IF EXISTS analytics_v2.v_produtos_por_cliente CASCADE;
CREATE VIEW analytics_v2.v_produtos_por_cliente AS
SELECT ft.client_id,
    dc.cpf_cnpj AS cliente_cpf_cnpj,
    dc.nome AS nome_cliente,
    di.nome AS nome_produto,
    sum(ft.quantidade) AS quantidade_total,
    sum(ft.valor) AS valor_total,
    count(DISTINCT ft.documento) AS num_compras,
    max(dd.data) AS ultima_compra
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
LEFT JOIN analytics_v2.dim_inventory di ON ft.inventory_id = di.inventory_id
WHERE ft.cliente_id IS NOT NULL AND ft.inventory_id IS NOT NULL
GROUP BY ft.client_id, dc.cpf_cnpj, dc.nome, di.nome;

-- v_distribuicao_regional: Regional distribution
DROP VIEW IF EXISTS analytics_v2.v_distribuicao_regional CASCADE;
CREATE VIEW analytics_v2.v_distribuicao_regional AS
WITH estado_para_regiao AS (
    SELECT mapping.sigla_estado, mapping.nome_regiao
    FROM (VALUES
        ('AC','Norte'), ('AM','Norte'), ('AP','Norte'), ('PA','Norte'),
        ('RO','Norte'), ('RR','Norte'), ('TO','Norte'),
        ('AL','Nordeste'), ('BA','Nordeste'), ('CE','Nordeste'), ('MA','Nordeste'),
        ('PB','Nordeste'), ('PE','Nordeste'), ('PI','Nordeste'), ('RN','Nordeste'), ('SE','Nordeste'),
        ('DF','Centro-Oeste'), ('GO','Centro-Oeste'), ('MT','Centro-Oeste'), ('MS','Centro-Oeste'),
        ('ES','Sudeste'), ('MG','Sudeste'), ('RJ','Sudeste'), ('SP','Sudeste'),
        ('PR','Sul'), ('RS','Sul'), ('SC','Sul')
    ) AS mapping(sigla_estado, nome_regiao)
),
totais_regionais AS (
    SELECT ft.client_id,
        COALESCE(dc.endereco_uf, 'Não informado') AS estado,
        COALESCE(sr.nome_regiao, 'Não informado') AS regiao,
        count(DISTINCT ft.documento) AS total
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
    LEFT JOIN estado_para_regiao sr ON dc.endereco_uf = sr.sigla_estado
    GROUP BY ft.client_id, dc.endereco_uf, sr.nome_regiao
),
totais_cliente AS (
    SELECT client_id, sum(total) AS total_geral
    FROM totais_regionais
    GROUP BY client_id
)
SELECT tr.client_id,
    'pedidos_por_regiao'::text AS tipo_grafico,
    'pedidos'::text AS dimensao,
    tr.estado,
    tr.regiao,
    tr.total,
    CASE WHEN tc.total_geral > 0
        THEN (tr.total::numeric / tc.total_geral) * 100
        ELSE 0
    END AS percentual
FROM totais_regionais tr
JOIN totais_cliente tc ON tr.client_id = tc.client_id;

-- =============================================================================
-- PHASE 3: Fix sincronizar_dados_cliente — use dim_inventory instead of dim_produtos
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
        v_tipo_venda_id := 1;
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

    -- 4. Build SELECT clause
    FOREACH v_col IN ARRAY v_canonical_cols LOOP
        v_src := analytics_v2.get_mapped_source(v_column_mapping, v_col);
        IF v_src IS NOT NULL THEN
            v_select_clause := v_select_clause || quote_ident(v_src) || ' AS ' || quote_ident(v_col) || ', ';
        ELSE
            v_select_clause := v_select_clause || 'NULL AS ' || quote_ident(v_col) || ', ';
        END IF;
    END LOOP;
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

    -- 9. UPSERT dim_inventory from temp table (was dim_produtos)
    INSERT INTO analytics_v2.dim_inventory (client_id, nome)
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
    --     Uses inventory_id (FK to dim_inventory) instead of produto_id
    INSERT INTO analytics_v2.fato_transacoes (
        client_id,
        data_competencia_id,
        tipo_id,
        cliente_id,
        fornecedor_id,
        inventory_id,
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
        di.inventory_id,
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
    LEFT JOIN analytics_v2.dim_inventory di
        ON di.nome = s.produto_descricao::text
        AND di.client_id = p_client_id;

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
-- PHASE 4: Fix atualizar_agregados — use dim_inventory instead of dim_produtos
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
    -- UPDATE dim_clientes from fato_transacoes
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

    -- UPDATE dim_fornecedores from fato_transacoes
    WITH transacoes_por_fornecedor AS (
        SELECT
            ft.fornecedor_id,
            COUNT(DISTINCT ft.documento) AS total_pedidos_recebidos,
            SUM(ft.valor) AS receita_total,
            AVG(ft.valor) AS ticket_medio,
            COUNT(DISTINCT ft.inventory_id) AS total_produtos_fornecidos,
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

    -- UPDATE dim_inventory from fato_transacoes (was dim_produtos)
    WITH transacoes_por_produto AS (
        SELECT
            ft.inventory_id,
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
          AND ft.inventory_id IS NOT NULL
        GROUP BY ft.inventory_id
    ),
    meses_ativos_produto AS (
        SELECT
            ft.inventory_id,
            COUNT(DISTINCT date_trunc('month', dd.data)) AS meses
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
        WHERE ft.client_id = p_client_id
          AND ft.inventory_id IS NOT NULL
        GROUP BY ft.inventory_id
    )
    UPDATE analytics_v2.dim_inventory p
    SET
        quantidade_total_vendida = tpp.quantidade_total_vendida,
        receita_total = tpp.receita_total,
        preco_medio = tpp.preco_medio,
        total_pedidos = tpp.total_pedidos,
        quantidade_media_por_pedido = tpp.quantidade_media_por_pedido,
        data_ultima_venda = tpp.data_ultima_venda,
        dias_recencia = tpp.dias_recencia,
        frequencia_mensal = CASE WHEN map.meses > 0 THEN tpp.total_pedidos::numeric / map.meses ELSE 0 END,
        updated_at = now()
    FROM transacoes_por_produto tpp
    LEFT JOIN meses_ativos_produto map ON tpp.inventory_id = map.inventory_id
    WHERE p.inventory_id = tpp.inventory_id
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
-- PHASE 5: Grant permissions
-- =============================================================================

-- Tables
GRANT SELECT ON analytics_v2.fato_transacoes TO authenticated;
GRANT ALL ON analytics_v2.fato_transacoes TO service_role;
GRANT SELECT ON analytics_v2.dim_inventory TO authenticated;
GRANT ALL ON analytics_v2.dim_inventory TO service_role;

-- Views
GRANT SELECT ON analytics_v2.v_resumo_dashboard TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_series_temporal TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_ultimos_pedidos TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_produtos_por_cliente TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_distribuicao_regional TO authenticated, service_role;

-- Functions
GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente TO authenticated;
GRANT EXECUTE ON FUNCTION public.sincronizar_dados_cliente TO service_role;
GRANT EXECUTE ON FUNCTION analytics_v2.atualizar_agregados TO authenticated;
GRANT EXECUTE ON FUNCTION analytics_v2.atualizar_agregados TO service_role;

-- Default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics_v2
  GRANT SELECT ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics_v2
  GRANT ALL ON TABLES TO service_role;

COMMIT;
