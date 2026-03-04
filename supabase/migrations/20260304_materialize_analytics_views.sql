-- =============================================================================
-- Analytics V2 — Materialized Views + Wrapper Views + Daily Refresh
-- =============================================================================
-- Architecture:
--   mv_*  = MATERIALIZED VIEW — pre-computed for ALL clients (refreshed daily)
--   v_*   = thin VIEW wrapper — filters by get_my_client_id() for RLS
--
-- The frontend keeps querying v_* (no code change). Performance comes from the
-- MV; security comes from the wrapper view.
--
-- Includes:
--   1. mv_series_temporal          + v_series_temporal
--   2. mv_resumo_dashboard         + v_resumo_dashboard
--   3. mv_distribuicao_regional    + v_distribuicao_regional
--   4. mv_resumo_produtos          + v_resumo_produtos
--   5. mv_resumo_clientes          + v_resumo_clientes
--   6. mv_resumo_fornecedores      + v_resumo_fornecedores
--   7. 8 detail-page RPCs
--   8. refresh_all_materialized_views() + pg_cron daily job
-- =============================================================================

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 0. EXTENSIONS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. DROP old objects (views, then MVs — order matters for CASCADE)
-- ─────────────────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS analytics_v2.v_series_temporal CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_resumo_dashboard CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_distribuicao_regional CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_resumo_produtos CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_resumo_clientes CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_resumo_fornecedores CASCADE;

DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_series_temporal CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_dashboard CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_distribuicao_regional CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_produtos CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_clientes CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_fornecedores CASCADE;


-- ═════════════════════════════════════════════════════════════════════════════
-- 2. MATERIALIZED VIEWS
-- ═════════════════════════════════════════════════════════════════════════════

-- ── 2a. mv_series_temporal ──────────────────────────────────────────────────
-- 11 UNION legs: 3 per entity (contagem/receita/quantidade) + 2 global
-- Frontend filters by: .eq('tipo_grafico', '{entity}')

CREATE MATERIALIZED VIEW analytics_v2.mv_series_temporal AS

-- Produtos — contagem
SELECT ft.client_id,
       'produtos'::text AS tipo_grafico,
       'contagem'::text AS dimensao,
       to_char(dd.data, 'YYYY-MM') AS periodo,
       date_trunc('month', dd.data)::date AS data_periodo,
       count(DISTINCT ft.inventory_id)::bigint AS total
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL
-- Produtos — receita
SELECT ft.client_id, 'produtos', 'receita',
       to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date,
       COALESCE(sum(ft.valor), 0)::bigint
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL
-- Produtos — quantidade
SELECT ft.client_id, 'produtos', 'quantidade',
       to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date,
       COALESCE(sum(ft.quantidade), 0)::bigint
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL
-- Clientes — contagem
SELECT ft.client_id, 'clientes', 'contagem',
       to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date,
       count(DISTINCT ft.cliente_id)::bigint
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL
-- Clientes — receita
SELECT ft.client_id, 'clientes', 'receita',
       to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date,
       COALESCE(sum(ft.valor), 0)::bigint
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL
-- Clientes — quantidade
SELECT ft.client_id, 'clientes', 'quantidade',
       to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date,
       COALESCE(sum(ft.quantidade), 0)::bigint
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL
-- Fornecedores — contagem
SELECT ft.client_id, 'fornecedores', 'contagem',
       to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date,
       count(DISTINCT ft.fornecedor_id)::bigint
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL
-- Fornecedores — receita
SELECT ft.client_id, 'fornecedores', 'receita',
       to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date,
       COALESCE(sum(ft.valor), 0)::bigint
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL
-- Fornecedores — quantidade
SELECT ft.client_id, 'fornecedores', 'quantidade',
       to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date,
       COALESCE(sum(ft.quantidade), 0)::bigint
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL
-- Pedidos (global)
SELECT ft.client_id, 'pedidos', 'total',
       to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date,
       count(DISTINCT ft.documento)::bigint
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date

UNION ALL
-- Receita (global — for HomePage)
SELECT ft.client_id, 'receita', 'receita',
       to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date,
       COALESCE(sum(ft.valor), 0)::bigint
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM'), date_trunc('month', dd.data)::date
WITH NO DATA;  -- populated by initial REFRESH below


-- ── 2b. mv_resumo_dashboard ────────────────────────────────────────────────
-- One row per client with totals + growth (last 2 months comparison)

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard AS
WITH monthly_revenue AS (
    SELECT
        ft.client_id,
        to_char(dd.data, 'YYYY-MM') AS periodo,
        SUM(ft.valor) AS receita,
        COUNT(DISTINCT ft.cliente_id) AS clientes_unicos,
        COUNT(DISTINCT ft.inventory_id) AS produtos_unicos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE dd.data IS NOT NULL
    GROUP BY ft.client_id, to_char(dd.data, 'YYYY-MM')
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY periodo DESC) AS rn
    FROM monthly_revenue
),
client_agg AS (
    SELECT client_id,
           count(*) AS total_clientes,
           count(*) FILTER (WHERE dias_recencia <= 90) AS clientes_ativos,
           count(*) FILTER (WHERE total_pedidos = 1) AS clientes_novos,
           count(DISTINCT endereco_uf) FILTER (WHERE endereco_uf IS NOT NULL) AS total_regioes
    FROM analytics_v2.dim_clientes
    GROUP BY client_id
),
fornecedor_agg AS (
    SELECT client_id,
           count(*) AS total_fornecedores,
           COALESCE(AVG(frequencia_mensal), 0) AS frequencia_media_fornecedores
    FROM analytics_v2.dim_fornecedores
    GROUP BY client_id
),
inventory_agg AS (
    SELECT client_id,
           count(*) AS total_produtos,
           COALESCE(sum(quantidade_total_vendida), 0) AS quantidade_total_vendida
    FROM analytics_v2.dim_inventory
    GROUP BY client_id
),
fact_agg AS (
    SELECT client_id,
           count(DISTINCT documento) AS total_pedidos,
           COALESCE(sum(valor), 0) AS receita_total,
           COALESCE(avg(valor), 0) AS ticket_medio
    FROM analytics_v2.fato_transacoes
    GROUP BY client_id
)
SELECT
    cl.client_id,
    COALESCE(ca.total_clientes, 0)                   AS total_clientes,
    COALESCE(fa2.total_fornecedores, 0)               AS total_fornecedores,
    COALESCE(ia.total_produtos, 0)                    AS total_produtos,
    COALESCE(fa.total_pedidos, 0)                     AS total_pedidos,
    COALESCE(fa.receita_total, 0)                     AS receita_total,
    COALESCE(fa.ticket_medio, 0)                      AS ticket_medio,
    COALESCE(r1.receita, 0)                           AS receita_mes_atual,
    -- Growth: receita
    CASE WHEN COALESCE(r2.receita, 0) > 0
         THEN ((r1.receita - r2.receita) / r2.receita * 100)::numeric(10,2)
         ELSE NULL
    END AS crescimento_receita,
    -- Growth: clientes
    CASE WHEN COALESCE(r2.clientes_unicos, 0) > 0
         THEN ((r1.clientes_unicos::numeric - r2.clientes_unicos::numeric)
               / r2.clientes_unicos::numeric * 100)::numeric(10,2)
         ELSE NULL
    END AS crescimento_clientes,
    -- Growth: produtos
    CASE WHEN COALESCE(r2.produtos_unicos, 0) > 0
         THEN ((r1.produtos_unicos::numeric - r2.produtos_unicos::numeric)
               / r2.produtos_unicos::numeric * 100)::numeric(10,2)
         ELSE NULL
    END AS crescimento_produtos,
    COALESCE(fa2.frequencia_media_fornecedores, 0)    AS frequencia_media_fornecedores,
    COALESCE(ca.total_regioes, 0)                     AS total_regioes,
    r1.periodo                                        AS ultimo_mes,
    COALESCE(ca.clientes_ativos, 0)                   AS clientes_ativos,
    COALESCE(ca.clientes_novos, 0)                    AS clientes_novos,
    COALESCE(ia.quantidade_total_vendida, 0)           AS quantidade_total_vendida,
    now()                                             AS gerado_em
FROM (SELECT DISTINCT client_id FROM analytics_v2.fato_transacoes) cl
LEFT JOIN ranked r1          ON r1.client_id = cl.client_id AND r1.rn = 1
LEFT JOIN ranked r2          ON r2.client_id = cl.client_id AND r2.rn = 2
LEFT JOIN client_agg ca      ON ca.client_id = cl.client_id
LEFT JOIN fornecedor_agg fa2 ON fa2.client_id = cl.client_id
LEFT JOIN inventory_agg ia   ON ia.client_id = cl.client_id
LEFT JOIN fact_agg fa        ON fa.client_id = cl.client_id
WITH NO DATA;


-- ── 2c. mv_distribuicao_regional ───────────────────────────────────────────

CREATE MATERIALIZED VIEW analytics_v2.mv_distribuicao_regional AS
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
           COUNT(DISTINCT ft.documento) AS total
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id AND ft.client_id = dc.client_id
    LEFT JOIN estado_para_regiao sr ON dc.endereco_uf = sr.sigla_estado
    GROUP BY ft.client_id, dc.endereco_uf, sr.nome_regiao
),
totais_cliente AS (
    SELECT client_id, SUM(total) AS total_geral
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
JOIN totais_cliente tc ON tr.client_id = tc.client_id
WITH NO DATA;


-- ── 2d. mv_resumo_produtos ─────────────────────────────────────────────────

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_produtos AS
SELECT
    client_id,
    count(*) AS total_produtos,
    COALESCE(sum(receita_total), 0) AS receita_total,
    COALESCE(sum(quantidade_total_vendida), 0) AS quantidade_total,
    CASE WHEN sum(quantidade_total_vendida) > 0
         THEN (sum(receita_total) / sum(quantidade_total_vendida))::numeric(15,2)
         ELSE 0 END AS ticket_medio,
    COALESCE(avg(frequencia_mensal), 0) AS frequencia_media,
    COALESCE(avg(dias_recencia), 0)::integer AS recencia_media_dias,
    -- Tier A
    count(*) FILTER (WHERE upper(nivel_cluster) = 'A') AS tier_a_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'A'), 0) AS tier_a_receita,
    COALESCE(sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'A'), 0) AS tier_a_quantidade,
    CASE WHEN sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'A') > 0
         THEN (sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'A')
               / sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'A'))::numeric(15,2)
         ELSE 0 END AS tier_a_ticket_medio,
    -- Tier B
    count(*) FILTER (WHERE upper(nivel_cluster) = 'B') AS tier_b_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'B'), 0) AS tier_b_receita,
    COALESCE(sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'B'), 0) AS tier_b_quantidade,
    CASE WHEN sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'B') > 0
         THEN (sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'B')
               / sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'B'))::numeric(15,2)
         ELSE 0 END AS tier_b_ticket_medio,
    -- Tier C
    count(*) FILTER (WHERE upper(nivel_cluster) = 'C') AS tier_c_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'C'), 0) AS tier_c_receita,
    COALESCE(sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'C'), 0) AS tier_c_quantidade,
    CASE WHEN sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'C') > 0
         THEN (sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'C')
               / sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'C'))::numeric(15,2)
         ELSE 0 END AS tier_c_ticket_medio,
    -- Tier D
    count(*) FILTER (WHERE upper(nivel_cluster) = 'D') AS tier_d_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'D'), 0) AS tier_d_receita,
    COALESCE(sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'D'), 0) AS tier_d_quantidade,
    CASE WHEN sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'D') > 0
         THEN (sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'D')
               / sum(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster) = 'D'))::numeric(15,2)
         ELSE 0 END AS tier_d_ticket_medio
FROM analytics_v2.dim_inventory
GROUP BY client_id
WITH NO DATA;


-- ── 2e. mv_resumo_clientes ─────────────────────────────────────────────────

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_clientes AS
SELECT
    client_id,
    count(*) AS total_clientes,
    COALESCE(sum(receita_total), 0) AS receita_total,
    COALESCE(sum(quantidade_total), 0) AS quantidade_total,
    COALESCE(avg(ticket_medio), 0) AS ticket_medio_geral,
    COALESCE(avg(frequencia_mensal), 0) AS frequencia_media,
    COALESCE(avg(dias_recencia), 0)::integer AS recencia_media_dias,
    count(*) FILTER (WHERE dias_recencia <= 90) AS clientes_ativos,
    count(*) FILTER (WHERE total_pedidos = 1) AS clientes_novos,
    count(*) FILTER (WHERE dias_recencia <= 30) AS novos_ultimos_30_dias,
    -- Tier A
    count(*) FILTER (WHERE upper(nivel_cluster) = 'A') AS tier_a_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'A'), 0) AS tier_a_receita,
    COALESCE(sum(quantidade_total) FILTER (WHERE upper(nivel_cluster) = 'A'), 0) AS tier_a_quantidade,
    COALESCE(avg(ticket_medio) FILTER (WHERE upper(nivel_cluster) = 'A'), 0) AS tier_a_ticket_medio,
    -- Tier B
    count(*) FILTER (WHERE upper(nivel_cluster) = 'B') AS tier_b_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'B'), 0) AS tier_b_receita,
    COALESCE(sum(quantidade_total) FILTER (WHERE upper(nivel_cluster) = 'B'), 0) AS tier_b_quantidade,
    COALESCE(avg(ticket_medio) FILTER (WHERE upper(nivel_cluster) = 'B'), 0) AS tier_b_ticket_medio,
    -- Tier C
    count(*) FILTER (WHERE upper(nivel_cluster) = 'C') AS tier_c_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'C'), 0) AS tier_c_receita,
    COALESCE(sum(quantidade_total) FILTER (WHERE upper(nivel_cluster) = 'C'), 0) AS tier_c_quantidade,
    COALESCE(avg(ticket_medio) FILTER (WHERE upper(nivel_cluster) = 'C'), 0) AS tier_c_ticket_medio,
    -- Tier D
    count(*) FILTER (WHERE upper(nivel_cluster) = 'D') AS tier_d_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'D'), 0) AS tier_d_receita,
    COALESCE(sum(quantidade_total) FILTER (WHERE upper(nivel_cluster) = 'D'), 0) AS tier_d_quantidade,
    COALESCE(avg(ticket_medio) FILTER (WHERE upper(nivel_cluster) = 'D'), 0) AS tier_d_ticket_medio
FROM analytics_v2.dim_clientes
GROUP BY client_id
WITH NO DATA;


-- ── 2f. mv_resumo_fornecedores ─────────────────────────────────────────────

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_fornecedores AS
SELECT
    client_id,
    count(*) AS total_fornecedores,
    COALESCE(sum(receita_total), 0) AS receita_total,
    COALESCE(sum(total_produtos_fornecidos), 0) AS total_produtos_fornecidos,
    COALESCE(avg(ticket_medio), 0) AS ticket_medio_geral,
    COALESCE(avg(frequencia_mensal), 0) AS frequencia_media,
    COALESCE(avg(dias_recencia), 0)::integer AS recencia_media_dias,
    count(*) FILTER (WHERE dias_recencia <= 30) AS novos_ultimos_30_dias,
    -- Tier A
    count(*) FILTER (WHERE upper(nivel_cluster) = 'A') AS tier_a_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'A'), 0) AS tier_a_receita,
    COALESCE(sum(total_produtos_fornecidos) FILTER (WHERE upper(nivel_cluster) = 'A'), 0) AS tier_a_produtos,
    COALESCE(avg(ticket_medio) FILTER (WHERE upper(nivel_cluster) = 'A'), 0) AS tier_a_ticket_medio,
    -- Tier B
    count(*) FILTER (WHERE upper(nivel_cluster) = 'B') AS tier_b_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'B'), 0) AS tier_b_receita,
    COALESCE(sum(total_produtos_fornecidos) FILTER (WHERE upper(nivel_cluster) = 'B'), 0) AS tier_b_produtos,
    COALESCE(avg(ticket_medio) FILTER (WHERE upper(nivel_cluster) = 'B'), 0) AS tier_b_ticket_medio,
    -- Tier C
    count(*) FILTER (WHERE upper(nivel_cluster) = 'C') AS tier_c_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'C'), 0) AS tier_c_receita,
    COALESCE(sum(total_produtos_fornecidos) FILTER (WHERE upper(nivel_cluster) = 'C'), 0) AS tier_c_produtos,
    COALESCE(avg(ticket_medio) FILTER (WHERE upper(nivel_cluster) = 'C'), 0) AS tier_c_ticket_medio,
    -- Tier D
    count(*) FILTER (WHERE upper(nivel_cluster) = 'D') AS tier_d_count,
    COALESCE(sum(receita_total) FILTER (WHERE upper(nivel_cluster) = 'D'), 0) AS tier_d_receita,
    COALESCE(sum(total_produtos_fornecidos) FILTER (WHERE upper(nivel_cluster) = 'D'), 0) AS tier_d_produtos,
    COALESCE(avg(ticket_medio) FILTER (WHERE upper(nivel_cluster) = 'D'), 0) AS tier_d_ticket_medio
FROM analytics_v2.dim_fornecedores
GROUP BY client_id
WITH NO DATA;


-- ═════════════════════════════════════════════════════════════════════════════
-- 3. UNIQUE INDEXES (required for REFRESH … CONCURRENTLY)
-- ═════════════════════════════════════════════════════════════════════════════

CREATE UNIQUE INDEX ux_mv_series_temporal
    ON analytics_v2.mv_series_temporal (client_id, tipo_grafico, dimensao, data_periodo);

CREATE UNIQUE INDEX ux_mv_resumo_dashboard
    ON analytics_v2.mv_resumo_dashboard (client_id);

CREATE UNIQUE INDEX ux_mv_distribuicao_regional
    ON analytics_v2.mv_distribuicao_regional (client_id, tipo_grafico, dimensao, estado, regiao);

CREATE UNIQUE INDEX ux_mv_resumo_produtos
    ON analytics_v2.mv_resumo_produtos (client_id);

CREATE UNIQUE INDEX ux_mv_resumo_clientes
    ON analytics_v2.mv_resumo_clientes (client_id);

CREATE UNIQUE INDEX ux_mv_resumo_fornecedores
    ON analytics_v2.mv_resumo_fornecedores (client_id);

-- Additional filter indexes for wrapper-view WHERE clauses (already covered by unique,
-- but explicit for clarity)
CREATE INDEX ix_mv_series_temporal_client
    ON analytics_v2.mv_series_temporal (client_id);
CREATE INDEX ix_mv_distribuicao_regional_client
    ON analytics_v2.mv_distribuicao_regional (client_id);


-- ═════════════════════════════════════════════════════════════════════════════
-- 4. INITIAL POPULATION
-- ═════════════════════════════════════════════════════════════════════════════
-- First refresh must be non-concurrent (MVs created WITH NO DATA)

REFRESH MATERIALIZED VIEW analytics_v2.mv_series_temporal;
REFRESH MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard;
REFRESH MATERIALIZED VIEW analytics_v2.mv_distribuicao_regional;
REFRESH MATERIALIZED VIEW analytics_v2.mv_resumo_produtos;
REFRESH MATERIALIZED VIEW analytics_v2.mv_resumo_clientes;
REFRESH MATERIALIZED VIEW analytics_v2.mv_resumo_fornecedores;


-- ═════════════════════════════════════════════════════════════════════════════
-- 5. WRAPPER VIEWS (thin — filter by authenticated user's client_id)
-- ═════════════════════════════════════════════════════════════════════════════
-- These are standard views owned by postgres. By default, PostgreSQL views
-- execute with the OWNER's privileges (≈ security definer), so the
-- authenticated user can read through the view even if not granted direct
-- access to the underlying MVs.

CREATE VIEW analytics_v2.v_series_temporal AS
SELECT client_id, tipo_grafico, dimensao, periodo, data_periodo, total
FROM analytics_v2.mv_series_temporal
WHERE client_id = public.get_my_client_id();

CREATE VIEW analytics_v2.v_resumo_dashboard AS
SELECT *
FROM analytics_v2.mv_resumo_dashboard
WHERE client_id = public.get_my_client_id();

CREATE VIEW analytics_v2.v_distribuicao_regional AS
SELECT client_id, tipo_grafico, dimensao, estado, regiao, total, percentual
FROM analytics_v2.mv_distribuicao_regional
WHERE client_id = public.get_my_client_id();

CREATE VIEW analytics_v2.v_resumo_produtos AS
SELECT *
FROM analytics_v2.mv_resumo_produtos
WHERE client_id = public.get_my_client_id();

CREATE VIEW analytics_v2.v_resumo_clientes AS
SELECT *
FROM analytics_v2.mv_resumo_clientes
WHERE client_id = public.get_my_client_id();

CREATE VIEW analytics_v2.v_resumo_fornecedores AS
SELECT *
FROM analytics_v2.mv_resumo_fornecedores
WHERE client_id = public.get_my_client_id();

-- Grant on wrapper views only (NOT on MVs)
GRANT SELECT ON analytics_v2.v_series_temporal       TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_resumo_dashboard      TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_distribuicao_regional  TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_resumo_produtos       TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_resumo_clientes       TO authenticated, service_role;
GRANT SELECT ON analytics_v2.v_resumo_fornecedores   TO authenticated, service_role;


-- ═════════════════════════════════════════════════════════════════════════════
-- 6. DETAIL-PAGE RPCs
-- ═════════════════════════════════════════════════════════════════════════════

-- 6a. get_product_top_clients
CREATE OR REPLACE FUNCTION analytics_v2.get_product_top_clients(p_product_name TEXT)
RETURNS TABLE(nome TEXT, receita_total NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
    SELECT dc.nome, SUM(ft.valor) AS receita_total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_inventory di ON ft.inventory_id = di.inventory_id
    JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
    WHERE di.nome = p_product_name AND ft.client_id = public.get_my_client_id()
    GROUP BY dc.nome ORDER BY receita_total DESC LIMIT 10;
$$;
GRANT EXECUTE ON FUNCTION analytics_v2.get_product_top_clients(TEXT) TO authenticated, service_role;

-- 6b. get_product_top_regions
CREATE OR REPLACE FUNCTION analytics_v2.get_product_top_regions(p_product_name TEXT)
RETURNS TABLE(regiao TEXT, receita_total NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
    SELECT COALESCE(dc.endereco_uf, 'Não informado') AS regiao, SUM(ft.valor) AS receita_total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_inventory di ON ft.inventory_id = di.inventory_id
    LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
    WHERE di.nome = p_product_name AND ft.client_id = public.get_my_client_id()
    GROUP BY dc.endereco_uf ORDER BY receita_total DESC LIMIT 10;
$$;
GRANT EXECUTE ON FUNCTION analytics_v2.get_product_top_regions(TEXT) TO authenticated, service_role;

-- 6c. get_product_revenue_series
CREATE OR REPLACE FUNCTION analytics_v2.get_product_revenue_series(p_product_name TEXT)
RETURNS TABLE(periodo TEXT, total NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
    SELECT to_char(dd.data, 'YYYY-MM') AS periodo, COALESCE(SUM(ft.valor), 0) AS total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    JOIN analytics_v2.dim_inventory di ON ft.inventory_id = di.inventory_id
    WHERE di.nome = p_product_name AND ft.client_id = public.get_my_client_id() AND dd.data IS NOT NULL
    GROUP BY to_char(dd.data, 'YYYY-MM') ORDER BY periodo ASC;
$$;
GRANT EXECUTE ON FUNCTION analytics_v2.get_product_revenue_series(TEXT) TO authenticated, service_role;

-- 6d. get_client_top_products
CREATE OR REPLACE FUNCTION analytics_v2.get_client_top_products(p_client_name TEXT)
RETURNS TABLE(nome TEXT, receita_total NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
    SELECT di.nome, SUM(ft.valor) AS receita_total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
    JOIN analytics_v2.dim_inventory di ON ft.inventory_id = di.inventory_id
    WHERE dc.nome = p_client_name AND ft.client_id = public.get_my_client_id()
    GROUP BY di.nome ORDER BY receita_total DESC LIMIT 10;
$$;
GRANT EXECUTE ON FUNCTION analytics_v2.get_client_top_products(TEXT) TO authenticated, service_role;

-- 6e. get_supplier_top_clients
CREATE OR REPLACE FUNCTION analytics_v2.get_supplier_top_clients(p_supplier_name TEXT)
RETURNS TABLE(nome TEXT, receita_total NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
    SELECT dc.nome, SUM(ft.valor) AS receita_total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id
    JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
    WHERE df.nome = p_supplier_name AND ft.client_id = public.get_my_client_id()
    GROUP BY dc.nome ORDER BY receita_total DESC LIMIT 10;
$$;
GRANT EXECUTE ON FUNCTION analytics_v2.get_supplier_top_clients(TEXT) TO authenticated, service_role;

-- 6f. get_supplier_top_products
CREATE OR REPLACE FUNCTION analytics_v2.get_supplier_top_products(p_supplier_name TEXT)
RETURNS TABLE(nome TEXT, receita_total NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
    SELECT di.nome, SUM(ft.valor) AS receita_total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id
    JOIN analytics_v2.dim_inventory di ON ft.inventory_id = di.inventory_id
    WHERE df.nome = p_supplier_name AND ft.client_id = public.get_my_client_id()
    GROUP BY di.nome ORDER BY receita_total DESC LIMIT 10;
$$;
GRANT EXECUTE ON FUNCTION analytics_v2.get_supplier_top_products(TEXT) TO authenticated, service_role;

-- 6g. get_supplier_top_regions
CREATE OR REPLACE FUNCTION analytics_v2.get_supplier_top_regions(p_supplier_name TEXT)
RETURNS TABLE(regiao TEXT, receita_total NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
    SELECT COALESCE(dc.endereco_uf, 'Não informado') AS regiao, SUM(ft.valor) AS receita_total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id
    LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
    WHERE df.nome = p_supplier_name AND ft.client_id = public.get_my_client_id()
    GROUP BY dc.endereco_uf ORDER BY receita_total DESC LIMIT 10;
$$;
GRANT EXECUTE ON FUNCTION analytics_v2.get_supplier_top_regions(TEXT) TO authenticated, service_role;

-- 6h. get_supplier_revenue_series
CREATE OR REPLACE FUNCTION analytics_v2.get_supplier_revenue_series(p_supplier_name TEXT)
RETURNS TABLE(periodo TEXT, total NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
    SELECT to_char(dd.data, 'YYYY-MM') AS periodo, COALESCE(SUM(ft.valor), 0) AS total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id
    WHERE df.nome = p_supplier_name AND ft.client_id = public.get_my_client_id() AND dd.data IS NOT NULL
    GROUP BY to_char(dd.data, 'YYYY-MM') ORDER BY periodo ASC;
$$;
GRANT EXECUTE ON FUNCTION analytics_v2.get_supplier_revenue_series(TEXT) TO authenticated, service_role;


-- ═════════════════════════════════════════════════════════════════════════════
-- 7. REFRESH FUNCTION
-- ═════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION analytics_v2.refresh_all_materialized_views()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics_v2
AS $$
BEGIN
    RAISE LOG '[analytics_v2] Starting daily MV refresh …';

    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_series_temporal;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_dashboard;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_distribuicao_regional;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_produtos;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_clientes;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_fornecedores;

    RAISE LOG '[analytics_v2] Daily MV refresh complete.';
END;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.refresh_all_materialized_views() TO service_role;


-- ═════════════════════════════════════════════════════════════════════════════
-- 8. DAILY CRON JOB (3 AM UTC)
-- ═════════════════════════════════════════════════════════════════════════════
-- pg_cron runs as superuser so it can refresh MVs.
-- Unschedule first in case this migration is re-applied.

SELECT cron.unschedule('refresh-analytics-mvs-daily')
WHERE EXISTS (
    SELECT 1 FROM cron.job WHERE jobname = 'refresh-analytics-mvs-daily'
);

SELECT cron.schedule(
    'refresh-analytics-mvs-daily',
    '0 3 * * *',
    $$SELECT analytics_v2.refresh_all_materialized_views()$$
);

COMMIT;
