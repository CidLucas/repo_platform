-- =============================================================================
-- Migration: Update analytics views for fato_transacoes
-- Date: 2026-02-26
-- Purpose: Recreate all dashboard views to query fato_transacoes with
--   proper JOINs to dimension tables instead of the old vendas table.
--   View output columns are kept compatible with analyticsService.ts.
-- =============================================================================

BEGIN;

-- =============================================================================
-- Drop existing views
-- =============================================================================

DROP VIEW IF EXISTS analytics_v2.v_series_temporal CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_ultimos_pedidos CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_produtos_por_cliente CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_distribuicao_regional CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_resumo_dashboard CASCADE;

-- =============================================================================
-- v_series_temporal: Time series charts for dashboard
-- Output columns: client_id, tipo_grafico, dimensao, periodo, data_periodo, total
-- =============================================================================

CREATE OR REPLACE VIEW analytics_v2.v_series_temporal AS
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

-- Produtos over time
SELECT ft.client_id,
    'produtos_no_tempo'::text AS tipo_grafico,
    'produtos'::text AS dimensao,
    to_char(dd.data, 'YYYY-MM') AS periodo,
    date_trunc('month', dd.data)::date AS data_periodo,
    count(DISTINCT ft.produto_id) AS total
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

-- =============================================================================
-- v_ultimos_pedidos: Last 100 orders per client
-- Output columns kept compatible: client_id, pedido_id, data_transacao,
--   cliente_cpf_cnpj, nome_cliente, valor_pedido, qtd_produtos, ordem
-- =============================================================================

CREATE OR REPLACE VIEW analytics_v2.v_ultimos_pedidos AS
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

-- =============================================================================
-- v_produtos_por_cliente: Customer-product relationships
-- =============================================================================

CREATE OR REPLACE VIEW analytics_v2.v_produtos_por_cliente AS
SELECT ft.client_id,
    dc.cpf_cnpj AS cliente_cpf_cnpj,
    dc.nome AS nome_cliente,
    dp.nome AS nome_produto,
    sum(ft.quantidade) AS quantidade_total,
    sum(ft.valor) AS valor_total,
    count(DISTINCT ft.documento) AS num_compras,
    max(dd.data) AS ultima_compra
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
LEFT JOIN analytics_v2.dim_produtos dp ON ft.produto_id = dp.produto_id
WHERE ft.cliente_id IS NOT NULL AND ft.produto_id IS NOT NULL
GROUP BY ft.client_id, dc.cpf_cnpj, dc.nome, dp.nome;

-- =============================================================================
-- v_distribuicao_regional: Regional distribution
-- Output columns: client_id, tipo_grafico, dimensao, estado, regiao, total, percentual
-- =============================================================================

CREATE OR REPLACE VIEW analytics_v2.v_distribuicao_regional AS
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
-- v_resumo_dashboard: Dashboard summary scorecards
-- Output columns: client_id, total_clientes, total_fornecedores, total_produtos,
--   total_pedidos, receita_total, ticket_medio, gerado_em
-- =============================================================================

CREATE OR REPLACE VIEW analytics_v2.v_resumo_dashboard AS
SELECT
    public.get_my_client_id() AS client_id,
    (SELECT count(*) FROM analytics_v2.dim_clientes
     WHERE client_id = public.get_my_client_id()) AS total_clientes,
    (SELECT count(*) FROM analytics_v2.dim_fornecedores
     WHERE client_id = public.get_my_client_id()) AS total_fornecedores,
    (SELECT count(*) FROM analytics_v2.dim_produtos
     WHERE client_id = public.get_my_client_id()) AS total_produtos,
    (SELECT count(DISTINCT documento) FROM analytics_v2.fato_transacoes
     WHERE client_id = public.get_my_client_id()) AS total_pedidos,
    (SELECT COALESCE(sum(valor), 0) FROM analytics_v2.fato_transacoes
     WHERE client_id = public.get_my_client_id()) AS receita_total,
    (SELECT COALESCE(avg(valor), 0) FROM analytics_v2.fato_transacoes
     WHERE client_id = public.get_my_client_id()) AS ticket_medio,
    now() AS gerado_em;

-- =============================================================================
-- Grant permissions on views
-- =============================================================================

GRANT SELECT ON analytics_v2.v_series_temporal TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_ultimos_pedidos TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_produtos_por_cliente TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_distribuicao_regional TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_resumo_dashboard TO authenticated, service_role;

COMMIT;
