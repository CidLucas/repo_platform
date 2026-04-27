-- Analytics V2 Cleanup — Phase C
-- Slim dim_clientes, dim_fornecedores, dim_inventory, dim_datas.
-- Snapshot each into analytics_v2_legacy before dropping columns.
-- Recreates affected MVs against slim schema.
--
-- Reference: docs/plans/archive/2026-04-22-analytics-v2-minimal-schema-cleanup.md (Phase C)

BEGIN;

SET LOCAL statement_timeout = '10min';
SET LOCAL lock_timeout       = '2min';

-- ── 1. Snapshot full dim rows before drops ─────────────────────────
CREATE TABLE analytics_v2_legacy.dim_clientes_full      AS TABLE analytics_v2.dim_clientes;
CREATE TABLE analytics_v2_legacy.dim_fornecedores_full  AS TABLE analytics_v2.dim_fornecedores;
CREATE TABLE analytics_v2_legacy.dim_inventory_full     AS TABLE analytics_v2.dim_inventory;
CREATE TABLE analytics_v2_legacy.dim_datas_full         AS TABLE analytics_v2.dim_datas;
REVOKE ALL ON analytics_v2_legacy.dim_clientes_full,
              analytics_v2_legacy.dim_fornecedores_full,
              analytics_v2_legacy.dim_inventory_full,
              analytics_v2_legacy.dim_datas_full
  FROM anon, authenticated;
GRANT SELECT ON analytics_v2_legacy.dim_clientes_full,
                analytics_v2_legacy.dim_fornecedores_full,
                analytics_v2_legacy.dim_inventory_full,
                analytics_v2_legacy.dim_datas_full
  TO service_role;

-- ── 2. Drop dependent MVs + views ──────────────────────────────────
DROP VIEW IF EXISTS analytics_v2.v_resumo_dashboard       CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_series_temporal        CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_distribuicao_regional  CASCADE;
DROP VIEW IF EXISTS analytics_v2.v_ultimos_pedidos        CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_dashboard      CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_clientes       CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_fornecedores   CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_produtos       CASCADE;

-- ── 3. Drop unused columns ─────────────────────────────────────────
ALTER TABLE analytics_v2.dim_clientes
  DROP COLUMN IF EXISTS endereco_rua,
  DROP COLUMN IF EXISTS endereco_numero,
  DROP COLUMN IF EXISTS endereco_bairro,
  DROP COLUMN IF EXISTS endereco_cep,
  DROP COLUMN IF EXISTS pedidos_ultimos_30_dias,
  DROP COLUMN IF EXISTS criado_em,
  DROP COLUMN IF EXISTS nome_fantasia,
  DROP COLUMN IF EXISTS cnae;

ALTER TABLE analytics_v2.dim_fornecedores
  DROP COLUMN IF EXISTS endereco_rua,
  DROP COLUMN IF EXISTS endereco_numero,
  DROP COLUMN IF EXISTS endereco_bairro,
  DROP COLUMN IF EXISTS endereco_cep,
  DROP COLUMN IF EXISTS criado_em,
  DROP COLUMN IF EXISTS nome_fantasia,
  DROP COLUMN IF EXISTS cnae,
  -- total_produtos_fornecidos kept: aggregated in mv_resumo_fornecedores
  DROP COLUMN IF EXISTS company_id;

ALTER TABLE analytics_v2.dim_inventory
  DROP COLUMN IF EXISTS inventory_type,
  DROP COLUMN IF EXISTS tracking_method,
  DROP COLUMN IF EXISTS current_stock,
  DROP COLUMN IF EXISTS minimum_stock,
  DROP COLUMN IF EXISTS location,
  DROP COLUMN IF EXISTS ncm,
  DROP COLUMN IF EXISTS unidade_comercial,
  DROP COLUMN IF EXISTS external_id,
  DROP COLUMN IF EXISTS category_id;

ALTER TABLE analytics_v2.dim_datas
  DROP COLUMN IF EXISTS ano_iso,
  DROP COLUMN IF EXISTS nome_trimestre,
  DROP COLUMN IF EXISTS dia_do_ano,
  DROP COLUMN IF EXISTS nome_dia,
  DROP COLUMN IF EXISTS e_fim_de_semana,
  DROP COLUMN IF EXISTS primeiro_dia_mes,
  DROP COLUMN IF EXISTS ultimo_dia_mes,
  DROP COLUMN IF EXISTS e_inicio_mes,
  DROP COLUMN IF EXISTS e_fim_mes,
  DROP COLUMN IF EXISTS e_inicio_trimestre,
  DROP COLUMN IF EXISTS e_fim_trimestre,
  DROP COLUMN IF EXISTS e_inicio_ano,
  DROP COLUMN IF EXISTS e_fim_ano;

-- ── 4. Recreate materialized views against slim dims ───────────────

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard AS
 WITH last_30_days AS (
         SELECT ft.client_id,
            sum(ft.valor) AS receita,
            sum(ft.quantidade) AS quantidade,
            count(DISTINCT ft.cliente_id) AS clientes_unicos,
            count(DISTINCT ft.produto_id) AS produtos_unicos,
            count(DISTINCT ft.fornecedor_id) AS fornecedores_unicos
           FROM (analytics_v2.fato_transacoes ft
             JOIN analytics_v2.dim_datas dd ON ((ft.data_competencia_id = dd.data_id)))
          WHERE ((dd.data >= (CURRENT_DATE - '30 days'::interval)) AND (dd.data IS NOT NULL))
          GROUP BY ft.client_id
        ), previous_30_days AS (
         SELECT ft.client_id,
            sum(ft.valor) AS receita,
            sum(ft.quantidade) AS quantidade,
            count(DISTINCT ft.cliente_id) AS clientes_unicos,
            count(DISTINCT ft.produto_id) AS produtos_unicos,
            count(DISTINCT ft.fornecedor_id) AS fornecedores_unicos
           FROM (analytics_v2.fato_transacoes ft
             JOIN analytics_v2.dim_datas dd ON ((ft.data_competencia_id = dd.data_id)))
          WHERE ((dd.data >= (CURRENT_DATE - '60 days'::interval)) AND (dd.data < (CURRENT_DATE - '30 days'::interval)) AND (dd.data IS NOT NULL))
          GROUP BY ft.client_id
        ), client_agg AS (
         SELECT c.client_id,
            count(*) AS total_clientes,
            count(*) FILTER (WHERE (c.dias_recencia <= 90)) AS clientes_ativos,
            count(*) FILTER (WHERE (c.total_pedidos = 1)) AS clientes_novos,
            count(DISTINCT c.endereco_uf) FILTER (WHERE (c.endereco_uf IS NOT NULL)) AS total_regioes
           FROM analytics_v2.dim_clientes c
          GROUP BY c.client_id
        ), fornecedor_agg AS (
         SELECT f.client_id,
            count(*) AS total_fornecedores,
            COALESCE(avg(f.frequencia_mensal), (0)::numeric) AS frequencia_media_fornecedores
           FROM analytics_v2.dim_fornecedores f
          GROUP BY f.client_id
        ), inventory_agg AS (
         SELECT i.client_id,
            count(*) AS total_produtos,
            COALESCE(sum(i.quantidade_total_vendida), (0)::numeric) AS quantidade_total_vendida
           FROM analytics_v2.dim_inventory i
          GROUP BY i.client_id
        ), fact_agg AS (
         SELECT ft.client_id,
            count(DISTINCT ft.documento) AS total_pedidos,
            COALESCE(sum(ft.valor), (0)::numeric) AS receita_total,
            COALESCE(avg(ft.valor), (0)::numeric) AS ticket_medio
           FROM analytics_v2.fato_transacoes ft
          GROUP BY ft.client_id
        )
 SELECT cl.client_id,
    COALESCE(ca.total_clientes, (0)::bigint) AS total_clientes,
    COALESCE(fa2.total_fornecedores, (0)::bigint) AS total_fornecedores,
    COALESCE(ia.total_produtos, (0)::bigint) AS total_produtos,
    COALESCE(fa.total_pedidos, (0)::bigint) AS total_pedidos,
    COALESCE(fa.receita_total, (0)::numeric) AS receita_total,
    COALESCE(fa.ticket_medio, (0)::numeric) AS ticket_medio,
    COALESCE(ia.quantidade_total_vendida, (0)::numeric) AS quantidade_total_vendida,
    COALESCE(l30.receita, (0)::numeric) AS receita_mes_atual,
    COALESCE(l30.quantidade, (0)::numeric) AS quantidade_mes_atual,
    COALESCE(l30.clientes_unicos, (0)::bigint) AS clientes_mes_atual,
    COALESCE(l30.produtos_unicos, (0)::bigint) AS produtos_mes_atual,
    COALESCE(l30.fornecedores_unicos, (0)::bigint) AS fornecedores_mes_atual,
        CASE
            WHEN (COALESCE(p30.receita, (0)::numeric) > (0)::numeric) THEN ((((COALESCE(l30.receita, (0)::numeric) - p30.receita) / p30.receita) * (100)::numeric))::numeric(10,2)
            ELSE NULL::numeric
        END AS crescimento_receita,
        CASE
            WHEN (COALESCE(p30.clientes_unicos, (0)::bigint) > 0) THEN (((((COALESCE(l30.clientes_unicos, (0)::bigint))::numeric - (p30.clientes_unicos)::numeric) / (p30.clientes_unicos)::numeric) * (100)::numeric))::numeric(10,2)
            ELSE NULL::numeric
        END AS crescimento_clientes,
        CASE
            WHEN (COALESCE(p30.produtos_unicos, (0)::bigint) > 0) THEN (((((COALESCE(l30.produtos_unicos, (0)::bigint))::numeric - (p30.produtos_unicos)::numeric) / (p30.produtos_unicos)::numeric) * (100)::numeric))::numeric(10,2)
            ELSE NULL::numeric
        END AS crescimento_produtos,
        CASE
            WHEN (COALESCE(p30.quantidade, (0)::numeric) > (0)::numeric) THEN ((((COALESCE(l30.quantidade, (0)::numeric) - p30.quantidade) / p30.quantidade) * (100)::numeric))::numeric(10,2)
            ELSE NULL::numeric
        END AS crescimento_quantidade,
    COALESCE(fa2.frequencia_media_fornecedores, (0)::numeric) AS frequencia_media_fornecedores,
    COALESCE(ca.total_regioes, (0)::bigint) AS total_regioes,
    to_char((CURRENT_DATE)::timestamp with time zone, 'YYYY-MM'::text) AS ultimo_mes,
    COALESCE(ca.clientes_ativos, (0)::bigint) AS clientes_ativos,
    COALESCE(ca.clientes_novos, (0)::bigint) AS clientes_novos,
    now() AS gerado_em
   FROM ((((((( SELECT DISTINCT ft.client_id
           FROM analytics_v2.fato_transacoes ft) cl
     LEFT JOIN last_30_days l30 ON ((l30.client_id = cl.client_id)))
     LEFT JOIN previous_30_days p30 ON ((p30.client_id = cl.client_id)))
     LEFT JOIN client_agg ca ON ((ca.client_id = cl.client_id)))
     LEFT JOIN fornecedor_agg fa2 ON ((fa2.client_id = cl.client_id)))
     LEFT JOIN inventory_agg ia ON ((ia.client_id = cl.client_id)))
     LEFT JOIN fact_agg fa ON ((fa.client_id = cl.client_id)));

CREATE INDEX idx_mv_resumo_dashboard_client_id ON analytics_v2.mv_resumo_dashboard(client_id);

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_clientes AS
 WITH transacoes_30_dias AS (
         SELECT ft.client_id,
            ft.cliente_id,
            sum(ft.valor) AS receita_30_dias,
            sum(ft.quantidade) AS quantidade_30_dias,
            count(DISTINCT ft.documento) AS pedidos_30_dias
           FROM (analytics_v2.fato_transacoes ft
             JOIN analytics_v2.dim_datas dd ON ((ft.data_competencia_id = dd.data_id)))
          WHERE (dd.data >= (CURRENT_DATE - '30 days'::interval))
          GROUP BY ft.client_id, ft.cliente_id
        ), transacoes_anteriores AS (
         SELECT ft.client_id,
            ft.cliente_id,
            sum(ft.valor) AS receita_anterior,
            sum(ft.quantidade) AS quantidade_anterior,
            count(DISTINCT ft.documento) AS pedidos_anterior
           FROM (analytics_v2.fato_transacoes ft
             JOIN analytics_v2.dim_datas dd ON ((ft.data_competencia_id = dd.data_id)))
          WHERE ((dd.data >= (CURRENT_DATE - '60 days'::interval)) AND (dd.data < (CURRENT_DATE - '30 days'::interval)))
          GROUP BY ft.client_id, ft.cliente_id
        ), clientes_com_30d AS (
         SELECT c.cliente_id,
            c.client_id,
            c.cpf_cnpj,
            c.nome,
            c.telefone,
            c.endereco_cidade,
            c.endereco_uf,
            c.total_pedidos,
            c.receita_total,
            c.ticket_medio,
            c.quantidade_total,
            c.frequencia_mensal,
            c.dias_recencia,
            c.data_primeira_compra,
            c.data_ultima_compra,
            c.atualizado_em,
            c.pontuacao_cluster,
            c.nivel_cluster,
            COALESCE(t30.receita_30_dias, (0)::numeric) AS receita_30_dias,
            COALESCE(t30.quantidade_30_dias, (0)::numeric) AS quantidade_30_dias,
            COALESCE(t30.pedidos_30_dias, (0)::bigint) AS pedidos_30_dias,
            COALESCE(ta.receita_anterior, (0)::numeric) AS receita_anterior,
            COALESCE(ta.quantidade_anterior, (0)::numeric) AS quantidade_anterior,
            COALESCE(ta.pedidos_anterior, (0)::bigint) AS pedidos_anterior
           FROM ((analytics_v2.dim_clientes c
             LEFT JOIN transacoes_30_dias t30 ON (((c.cliente_id = t30.cliente_id) AND (c.client_id = t30.client_id))))
             LEFT JOIN transacoes_anteriores ta ON (((c.cliente_id = ta.cliente_id) AND (c.client_id = ta.client_id))))
        )
 SELECT client_id,
    count(*) AS total_clientes,
    COALESCE(sum(receita_total), (0)::numeric) AS receita_total,
    COALESCE(sum(quantidade_total), (0)::numeric) AS quantidade_total,
    COALESCE(avg(ticket_medio), (0)::numeric) AS ticket_medio_geral,
    COALESCE(avg(frequencia_mensal), (0)::numeric) AS frequencia_media,
    (COALESCE(avg(dias_recencia), (0)::numeric))::integer AS recencia_media_dias,
    count(*) FILTER (WHERE (dias_recencia <= 90)) AS clientes_ativos,
    count(*) FILTER (WHERE (total_pedidos = 1)) AS clientes_novos,
    count(*) FILTER (WHERE (dias_recencia <= 30)) AS novos_ultimos_30_dias,
    COALESCE(sum(receita_30_dias), (0)::numeric) AS receita_30_dias,
    COALESCE(sum(quantidade_30_dias), (0)::numeric) AS quantidade_30_dias,
    COALESCE(sum(pedidos_30_dias), (0)::numeric) AS pedidos_30_dias,
    count(*) FILTER (WHERE (receita_30_dias > (0)::numeric)) AS clientes_ativos_30_dias,
        CASE
            WHEN (COALESCE(sum(receita_anterior), (0)::numeric) > (0)::numeric) THEN round((((sum(receita_30_dias) - sum(receita_anterior)) / sum(receita_anterior)) * (100)::numeric), 2)
            ELSE NULL::numeric
        END AS crescimento_receita,
        CASE
            WHEN (COALESCE(sum(quantidade_anterior), (0)::numeric) > (0)::numeric) THEN round((((sum(quantidade_30_dias) - sum(quantidade_anterior)) / sum(quantidade_anterior)) * (100)::numeric), 2)
            ELSE NULL::numeric
        END AS crescimento_quantidade,
        CASE
            WHEN (COALESCE(sum(pedidos_anterior), (0)::numeric) > (0)::numeric) THEN round((((sum(pedidos_30_dias) - sum(pedidos_anterior)) / sum(pedidos_anterior)) * (100)::numeric), 2)
            ELSE NULL::numeric
        END AS crescimento_pedidos,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)) AS tier_a_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::numeric) AS tier_a_receita,
    COALESCE(sum(quantidade_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::numeric) AS tier_a_quantidade,
    COALESCE(avg(ticket_medio) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::numeric) AS tier_a_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::numeric) AS tier_a_receita_30_dias,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)) AS tier_b_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::numeric) AS tier_b_receita,
    COALESCE(sum(quantidade_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::numeric) AS tier_b_quantidade,
    COALESCE(avg(ticket_medio) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::numeric) AS tier_b_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::numeric) AS tier_b_receita_30_dias,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)) AS tier_c_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::numeric) AS tier_c_receita,
    COALESCE(sum(quantidade_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::numeric) AS tier_c_quantidade,
    COALESCE(avg(ticket_medio) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::numeric) AS tier_c_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::numeric) AS tier_c_receita_30_dias,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)) AS tier_d_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::numeric) AS tier_d_receita,
    COALESCE(sum(quantidade_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::numeric) AS tier_d_quantidade,
    COALESCE(avg(ticket_medio) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::numeric) AS tier_d_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::numeric) AS tier_d_receita_30_dias
   FROM clientes_com_30d
  GROUP BY client_id;

CREATE UNIQUE INDEX idx_mv_resumo_clientes_client ON analytics_v2.mv_resumo_clientes(client_id);

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_fornecedores AS
 WITH transacoes_30_dias AS (
         SELECT ft.client_id,
            ft.fornecedor_id,
            sum(ft.valor) AS receita_30_dias,
            sum(ft.quantidade) AS quantidade_30_dias,
            count(DISTINCT ft.documento) AS pedidos_30_dias,
            count(DISTINCT ft.produto_id) AS produtos_30_dias
           FROM (analytics_v2.fato_transacoes ft
             JOIN analytics_v2.dim_datas dd ON ((ft.data_competencia_id = dd.data_id)))
          WHERE (dd.data >= (CURRENT_DATE - '30 days'::interval))
          GROUP BY ft.client_id, ft.fornecedor_id
        ), transacoes_anteriores AS (
         SELECT ft.client_id,
            ft.fornecedor_id,
            sum(ft.valor) AS receita_anterior,
            sum(ft.quantidade) AS quantidade_anterior,
            count(DISTINCT ft.documento) AS pedidos_anterior
           FROM (analytics_v2.fato_transacoes ft
             JOIN analytics_v2.dim_datas dd ON ((ft.data_competencia_id = dd.data_id)))
          WHERE ((dd.data >= (CURRENT_DATE - '60 days'::interval)) AND (dd.data < (CURRENT_DATE - '30 days'::interval)))
          GROUP BY ft.client_id, ft.fornecedor_id
        ), fornecedores_com_30d AS (
         SELECT f.fornecedor_id,
            f.client_id,
            f.cnpj,
            f.nome,
            f.telefone,
            f.endereco_cidade,
            f.endereco_uf,
            f.total_pedidos_recebidos,
            f.receita_total,
            f.ticket_medio,
            f.total_produtos_fornecidos,
            f.frequencia_mensal,
            f.dias_recencia,
            f.data_primeira_transacao,
            f.data_ultima_transacao,
            f.atualizado_em,
            f.pontuacao_cluster,
            f.nivel_cluster,
            COALESCE(t30.receita_30_dias, (0)::numeric) AS receita_30_dias,
            COALESCE(t30.quantidade_30_dias, (0)::numeric) AS quantidade_30_dias,
            COALESCE(t30.pedidos_30_dias, (0)::bigint) AS pedidos_30_dias,
            COALESCE(t30.produtos_30_dias, (0)::bigint) AS produtos_30_dias,
            COALESCE(ta.receita_anterior, (0)::numeric) AS receita_anterior,
            COALESCE(ta.quantidade_anterior, (0)::numeric) AS quantidade_anterior,
            COALESCE(ta.pedidos_anterior, (0)::bigint) AS pedidos_anterior
           FROM ((analytics_v2.dim_fornecedores f
             LEFT JOIN transacoes_30_dias t30 ON (((f.fornecedor_id = t30.fornecedor_id) AND (f.client_id = t30.client_id))))
             LEFT JOIN transacoes_anteriores ta ON (((f.fornecedor_id = ta.fornecedor_id) AND (f.client_id = ta.client_id))))
        )
 SELECT client_id,
    count(*) AS total_fornecedores,
    COALESCE(sum(receita_total), (0)::numeric) AS receita_total,
    COALESCE(sum(total_produtos_fornecidos), (0)::bigint) AS total_produtos_fornecidos,
    COALESCE(avg(ticket_medio), (0)::numeric) AS ticket_medio_geral,
    COALESCE(avg(frequencia_mensal), (0)::numeric) AS frequencia_media,
    (COALESCE(avg(dias_recencia), (0)::numeric))::integer AS recencia_media_dias,
    count(*) FILTER (WHERE (dias_recencia <= 30)) AS novos_ultimos_30_dias,
    COALESCE(sum(receita_30_dias), (0)::numeric) AS receita_30_dias,
    COALESCE(sum(quantidade_30_dias), (0)::numeric) AS quantidade_30_dias,
    COALESCE(sum(pedidos_30_dias), (0)::numeric) AS pedidos_30_dias,
    COALESCE(sum(produtos_30_dias), (0)::numeric) AS produtos_30_dias,
    count(*) FILTER (WHERE (receita_30_dias > (0)::numeric)) AS fornecedores_ativos_30_dias,
        CASE
            WHEN (COALESCE(sum(receita_anterior), (0)::numeric) > (0)::numeric) THEN round((((sum(receita_30_dias) - sum(receita_anterior)) / sum(receita_anterior)) * (100)::numeric), 2)
            ELSE NULL::numeric
        END AS crescimento_receita,
        CASE
            WHEN (COALESCE(sum(quantidade_anterior), (0)::numeric) > (0)::numeric) THEN round((((sum(quantidade_30_dias) - sum(quantidade_anterior)) / sum(quantidade_anterior)) * (100)::numeric), 2)
            ELSE NULL::numeric
        END AS crescimento_quantidade,
        CASE
            WHEN (COALESCE(sum(pedidos_anterior), (0)::numeric) > (0)::numeric) THEN round((((sum(pedidos_30_dias) - sum(pedidos_anterior)) / sum(pedidos_anterior)) * (100)::numeric), 2)
            ELSE NULL::numeric
        END AS crescimento_pedidos,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)) AS tier_a_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::numeric) AS tier_a_receita,
    COALESCE(sum(total_produtos_fornecidos) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::bigint) AS tier_a_produtos,
    COALESCE(avg(ticket_medio) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::numeric) AS tier_a_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::numeric) AS tier_a_receita_30_dias,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)) AS tier_b_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::numeric) AS tier_b_receita,
    COALESCE(sum(total_produtos_fornecidos) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::bigint) AS tier_b_produtos,
    COALESCE(avg(ticket_medio) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::numeric) AS tier_b_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::numeric) AS tier_b_receita_30_dias,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)) AS tier_c_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::numeric) AS tier_c_receita,
    COALESCE(sum(total_produtos_fornecidos) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::bigint) AS tier_c_produtos,
    COALESCE(avg(ticket_medio) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::numeric) AS tier_c_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::numeric) AS tier_c_receita_30_dias,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)) AS tier_d_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::numeric) AS tier_d_receita,
    COALESCE(sum(total_produtos_fornecidos) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::bigint) AS tier_d_produtos,
    COALESCE(avg(ticket_medio) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::numeric) AS tier_d_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::numeric) AS tier_d_receita_30_dias
   FROM fornecedores_com_30d
  GROUP BY client_id;

CREATE UNIQUE INDEX idx_mv_resumo_fornecedores_client ON analytics_v2.mv_resumo_fornecedores(client_id);

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_produtos AS
 WITH transacoes_30_dias AS (
         SELECT ft.client_id,
            ft.produto_id AS inventory_id,
            sum(ft.valor) AS receita_30_dias,
            sum(ft.quantidade) AS quantidade_30_dias,
            count(DISTINCT ft.documento) AS pedidos_30_dias
           FROM (analytics_v2.fato_transacoes ft
             JOIN analytics_v2.dim_datas dd ON ((ft.data_competencia_id = dd.data_id)))
          WHERE (dd.data >= (CURRENT_DATE - '30 days'::interval))
          GROUP BY ft.client_id, ft.produto_id
        ), transacoes_anteriores AS (
         SELECT ft.client_id,
            ft.produto_id AS inventory_id,
            sum(ft.valor) AS receita_anterior,
            sum(ft.quantidade) AS quantidade_anterior,
            count(DISTINCT ft.documento) AS pedidos_anterior
           FROM (analytics_v2.fato_transacoes ft
             JOIN analytics_v2.dim_datas dd ON ((ft.data_competencia_id = dd.data_id)))
          WHERE ((dd.data >= (CURRENT_DATE - '60 days'::interval)) AND (dd.data < (CURRENT_DATE - '30 days'::interval)))
          GROUP BY ft.client_id, ft.produto_id
        ), produtos_com_30d AS (
         SELECT p.inventory_id,
            p.client_id,
            p.sku,
            p.nome,
            p.quantidade_total_vendida,
            p.receita_total,
            p.preco_medio,
            p.total_pedidos,
            p.created_at,
            p.updated_at,
            p.nivel_cluster,
            p.pontuacao_cluster,
            p.quantidade_media_por_pedido,
            p.frequencia_mensal,
            p.dias_recencia,
            p.data_ultima_venda,
            COALESCE(t30.receita_30_dias, (0)::numeric) AS receita_30_dias,
            COALESCE(t30.quantidade_30_dias, (0)::numeric) AS quantidade_30_dias,
            COALESCE(t30.pedidos_30_dias, (0)::bigint) AS pedidos_30_dias,
            COALESCE(ta.receita_anterior, (0)::numeric) AS receita_anterior,
            COALESCE(ta.quantidade_anterior, (0)::numeric) AS quantidade_anterior,
            COALESCE(ta.pedidos_anterior, (0)::bigint) AS pedidos_anterior
           FROM ((analytics_v2.dim_inventory p
             LEFT JOIN transacoes_30_dias t30 ON (((p.inventory_id = t30.inventory_id) AND (p.client_id = t30.client_id))))
             LEFT JOIN transacoes_anteriores ta ON (((p.inventory_id = ta.inventory_id) AND (p.client_id = ta.client_id))))
        )
 SELECT client_id,
    count(*) AS total_produtos,
    COALESCE(sum(receita_total), (0)::numeric) AS receita_total,
    COALESCE(sum(quantidade_total_vendida), (0)::numeric) AS quantidade_total,
        CASE
            WHEN (sum(quantidade_total_vendida) > (0)::numeric) THEN ((sum(receita_total) / sum(quantidade_total_vendida)))::numeric(15,2)
            ELSE (0)::numeric
        END AS ticket_medio,
    COALESCE(avg(frequencia_mensal), (0)::numeric) AS frequencia_media,
    (COALESCE(avg(dias_recencia), (0)::numeric))::integer AS recencia_media_dias,
    COALESCE(sum(receita_30_dias), (0)::numeric) AS receita_30_dias,
    COALESCE(sum(quantidade_30_dias), (0)::numeric) AS quantidade_30_dias,
    COALESCE(sum(pedidos_30_dias), (0)::numeric) AS pedidos_30_dias,
    count(*) FILTER (WHERE (receita_30_dias > (0)::numeric)) AS produtos_ativos_30_dias,
        CASE
            WHEN (sum(quantidade_30_dias) > (0)::numeric) THEN ((sum(receita_30_dias) / sum(quantidade_30_dias)))::numeric(15,2)
            ELSE (0)::numeric
        END AS ticket_medio_30_dias,
        CASE
            WHEN (COALESCE(sum(receita_anterior), (0)::numeric) > (0)::numeric) THEN round((((sum(receita_30_dias) - sum(receita_anterior)) / sum(receita_anterior)) * (100)::numeric), 2)
            ELSE NULL::numeric
        END AS crescimento_receita,
        CASE
            WHEN (COALESCE(sum(quantidade_anterior), (0)::numeric) > (0)::numeric) THEN round((((sum(quantidade_30_dias) - sum(quantidade_anterior)) / sum(quantidade_anterior)) * (100)::numeric), 2)
            ELSE NULL::numeric
        END AS crescimento_quantidade,
        CASE
            WHEN (COALESCE(sum(pedidos_anterior), (0)::numeric) > (0)::numeric) THEN round((((sum(pedidos_30_dias) - sum(pedidos_anterior)) / sum(pedidos_anterior)) * (100)::numeric), 2)
            ELSE NULL::numeric
        END AS crescimento_pedidos,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)) AS tier_a_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::numeric) AS tier_a_receita,
    COALESCE(sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::numeric) AS tier_a_quantidade,
        CASE
            WHEN (sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)) > (0)::numeric) THEN ((sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)) / sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text))))::numeric(15,2)
            ELSE (0)::numeric
        END AS tier_a_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'A'::text)), (0)::numeric) AS tier_a_receita_30_dias,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)) AS tier_b_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::numeric) AS tier_b_receita,
    COALESCE(sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::numeric) AS tier_b_quantidade,
        CASE
            WHEN (sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)) > (0)::numeric) THEN ((sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)) / sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text))))::numeric(15,2)
            ELSE (0)::numeric
        END AS tier_b_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'B'::text)), (0)::numeric) AS tier_b_receita_30_dias,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)) AS tier_c_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::numeric) AS tier_c_receita,
    COALESCE(sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::numeric) AS tier_c_quantidade,
        CASE
            WHEN (sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)) > (0)::numeric) THEN ((sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)) / sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text))))::numeric(15,2)
            ELSE (0)::numeric
        END AS tier_c_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'C'::text)), (0)::numeric) AS tier_c_receita_30_dias,
    count(*) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)) AS tier_d_count,
    COALESCE(sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::numeric) AS tier_d_receita,
    COALESCE(sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::numeric) AS tier_d_quantidade,
        CASE
            WHEN (sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)) > (0)::numeric) THEN ((sum(receita_total) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)) / sum(quantidade_total_vendida) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text))))::numeric(15,2)
            ELSE (0)::numeric
        END AS tier_d_ticket_medio,
    COALESCE(sum(receita_30_dias) FILTER (WHERE (upper((nivel_cluster)::text) = 'D'::text)), (0)::numeric) AS tier_d_receita_30_dias
   FROM produtos_com_30d
  GROUP BY client_id;

CREATE UNIQUE INDEX idx_mv_resumo_produtos_client ON analytics_v2.mv_resumo_produtos(client_id);

-- ── 5. Recreate client-facing views over the MVs ───────────────────
CREATE OR REPLACE VIEW analytics_v2.v_resumo_dashboard
  WITH (security_invoker = true) AS
SELECT * FROM analytics_v2.mv_resumo_dashboard;

CREATE OR REPLACE VIEW analytics_v2.v_series_temporal
  WITH (security_invoker = true) AS
SELECT client_id, tipo_grafico, dimensao, periodo, data_periodo, total
FROM analytics_v2.mv_series_temporal
WHERE client_id = public.get_my_client_id();

CREATE OR REPLACE VIEW analytics_v2.v_distribuicao_regional
  WITH (security_invoker = true) AS
SELECT client_id, tipo_grafico, dimensao, estado, regiao, total, percentual
FROM analytics_v2.mv_distribuicao_regional
WHERE client_id = public.get_my_client_id();

CREATE OR REPLACE VIEW analytics_v2.v_ultimos_pedidos
  WITH (security_invoker = true) AS
WITH my_cid AS (SELECT public.get_my_client_id() AS cid)
SELECT ft.client_id,
       ft.documento                                 AS pedido_id,
       dd.data                                      AS data_transacao,
       dc.cpf_cnpj                                  AS cliente_cpf_cnpj,
       dc.nome                                      AS cliente_nome,
       SUM(ft.valor)::text                          AS valor_pedido,
       COUNT(*)                                     AS qtd_produtos,
       ROW_NUMBER() OVER (ORDER BY dd.data DESC, ft.documento DESC) AS ordem
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas    dd ON dd.data_id    = ft.data_competencia_id
LEFT JOIN analytics_v2.dim_clientes dc ON dc.cliente_id = ft.cliente_id
CROSS JOIN my_cid m
WHERE ft.client_id = m.cid
GROUP BY ft.client_id, ft.documento, dd.data, dc.cpf_cnpj, dc.nome;

GRANT SELECT ON analytics_v2.v_resumo_dashboard,
                analytics_v2.v_series_temporal,
                analytics_v2.v_distribuicao_regional,
                analytics_v2.v_ultimos_pedidos,
                analytics_v2.mv_resumo_clientes,
                analytics_v2.mv_resumo_fornecedores,
                analytics_v2.mv_resumo_produtos
  TO authenticated;

COMMIT;
