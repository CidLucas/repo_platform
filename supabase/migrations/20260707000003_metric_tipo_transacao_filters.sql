-- Migration: Filter analytics metrics by tipo_transacao
-- Problem: revenue/order/ticket metrics summed ALL rows of fato_transacoes
-- (venda + compra + despesa + banking), inflating receita_total and friends.
-- Semantics applied everywhere:
--   receita / pedidos / ticket / quantidade / clientes  -> tipo_transacao = 'venda'
--   fornecedores / spend / custo                        -> tipo_transacao = 'compra'
--   despesas (new despesas_total in finance indicators) -> tipo_transacao = 'despesa'
-- Also fixes get_churn_rate_monthly (counted transacao_id instead of customer_id,
-- so churn was always 100%) and public.get_commercial_revenue_by_channel
-- (referenced nonexistent columns channel/valor_total/data_transacao).
-- NOTE: prod is applied via psql (schema drift — DB is source of truth);
-- record version 20260707000003 in supabase_migrations.schema_migrations manually.

BEGIN;

-- ============================================================================
-- 1. DIM ETL FUNCTIONS (feed dim_clientes/dim_fornecedores/dim_inventory
--    aggregates used by get_customer_segments / get_top_customers / inventory)
-- ============================================================================

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_dim_clientes(p_client_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'analytics_v2'
AS $function$
BEGIN
  WITH agg AS (
    SELECT ft.customer_id,
      COUNT(DISTINCT ft.transacao_id) AS total_pedidos,
      COALESCE(SUM(ft.valor), 0) AS receita_total,
      CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
           THEN COALESCE(SUM(ft.valor), 0) / COUNT(DISTINCT ft.transacao_id)
           ELSE 0 END AS ticket_medio,
      COALESCE(SUM(ft.quantidade), 0) AS quantidade_total,
      MIN(dd.data) AS data_primeira_compra,
      MAX(dd.data) AS data_ultima_compra,
      (CURRENT_DATE - MAX(dd.data)) AS dias_recencia,
      CASE WHEN MIN(dd.data) IS NOT NULL AND MIN(dd.data) < MAX(dd.data)
        THEN COUNT(DISTINCT ft.transacao_id)::numeric / GREATEST(1,
               EXTRACT(YEAR FROM AGE(MAX(dd.data), MIN(dd.data))) * 12 +
               EXTRACT(MONTH FROM AGE(MAX(dd.data), MIN(dd.data))))
        ELSE COUNT(DISTINCT ft.transacao_id)::numeric
      END AS frequencia_mensal
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = p_client_id
      AND ft.customer_id IS NOT NULL
      AND ft.tipo_transacao = 'venda'
    GROUP BY ft.customer_id
  ),
  scored AS (
    SELECT *,
      NTILE(3) OVER (ORDER BY dias_recencia    DESC NULLS LAST) AS r_score,
      NTILE(3) OVER (ORDER BY frequencia_mensal ASC  NULLS LAST) AS f_score,
      NTILE(3) OVER (ORDER BY receita_total     ASC  NULLS LAST) AS m_score
    FROM agg
  )
  UPDATE analytics_v2.dim_clientes dc SET
    total_pedidos = s.total_pedidos, receita_total = s.receita_total,
    ticket_medio = s.ticket_medio, quantidade_total = s.quantidade_total,
    data_primeira_compra = s.data_primeira_compra, data_ultima_compra = s.data_ultima_compra,
    dias_recencia = s.dias_recencia, frequencia_mensal = s.frequencia_mensal,
    pontuacao_cluster = (s.r_score + s.f_score + s.m_score)::numeric,
    nivel_cluster = CASE WHEN s.r_score + s.f_score + s.m_score >= 7 THEN 'Alto'
                         WHEN s.r_score + s.f_score + s.m_score >= 4 THEN 'Médio'
                         ELSE 'Baixo' END,
    atualizado_em = clock_timestamp()
  FROM scored s
  WHERE dc.client_id = p_client_id AND dc.customer_id = s.customer_id;
  RAISE NOTICE '[atualizar_dim_clientes] client=%: done', p_client_id;
END; $function$;

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_dim_fornecedores(p_client_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'analytics_v2'
AS $function$
BEGIN
  WITH agg AS (
    SELECT
      ft.fornecedor_id,
      COUNT(DISTINCT ft.transacao_id)                                     AS total_pedidos_recebidos,
      COALESCE(SUM(ft.valor), 0)                                          AS receita_total,
      CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
           THEN COALESCE(SUM(ft.valor), 0) / COUNT(DISTINCT ft.transacao_id)
           ELSE 0 END                                                     AS ticket_medio,
      COUNT(DISTINCT ft.produto_id)                                       AS total_produtos_fornecidos,
      MIN(dd.data)                                                        AS data_primeira_transacao,
      MAX(dd.data)                                                        AS data_ultima_transacao,
      (CURRENT_DATE - MAX(dd.data))                                       AS dias_recencia,
      CASE
        WHEN MIN(dd.data) IS NOT NULL AND MIN(dd.data) < MAX(dd.data)
        THEN COUNT(DISTINCT ft.transacao_id)::numeric
             / GREATEST(1,
                 EXTRACT(YEAR  FROM AGE(MAX(dd.data), MIN(dd.data))) * 12 +
                 EXTRACT(MONTH FROM AGE(MAX(dd.data), MIN(dd.data))))
        ELSE COUNT(DISTINCT ft.transacao_id)::numeric
      END                                                                 AS frequencia_mensal
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id     = p_client_id
      AND ft.fornecedor_id IS NOT NULL
      AND ft.tipo_transacao = 'compra'
    GROUP BY ft.fornecedor_id
  ),
  scored AS (
    SELECT *,
      NTILE(3) OVER (ORDER BY dias_recencia     DESC NULLS LAST) AS r_score,
      NTILE(3) OVER (ORDER BY frequencia_mensal  ASC NULLS LAST) AS f_score,
      NTILE(3) OVER (ORDER BY receita_total      ASC NULLS LAST) AS m_score
    FROM agg
  )
  UPDATE analytics_v2.dim_fornecedores df
  SET
    total_pedidos_recebidos   = s.total_pedidos_recebidos,
    receita_total             = s.receita_total,
    ticket_medio              = s.ticket_medio,
    total_produtos_fornecidos = s.total_produtos_fornecidos,
    data_primeira_transacao   = s.data_primeira_transacao,
    data_ultima_transacao     = s.data_ultima_transacao,
    dias_recencia             = s.dias_recencia,
    frequencia_mensal         = s.frequencia_mensal,
    pontuacao_cluster         = (s.r_score + s.f_score + s.m_score)::numeric,
    nivel_cluster             = CASE
                                  WHEN s.r_score + s.f_score + s.m_score >= 7 THEN 'Alto'
                                  WHEN s.r_score + s.f_score + s.m_score >= 4 THEN 'Médio'
                                  ELSE 'Baixo'
                                END,
    atualizado_em             = clock_timestamp()
  FROM scored s
  WHERE df.client_id     = p_client_id
    AND df.fornecedor_id = s.fornecedor_id;

  RAISE NOTICE '[atualizar_dim_fornecedores] client=%: done', p_client_id;
END;
$function$;

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_dim_inventory(p_client_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public', 'analytics_v2'
AS $function$
BEGIN
  WITH agg AS (
    SELECT
      ft.produto_id,
      COUNT(DISTINCT ft.transacao_id)                                     AS total_pedidos,
      COALESCE(SUM(ft.quantidade), 0)                                     AS quantidade_total_vendida,
      COALESCE(SUM(ft.valor), 0)                                          AS receita_total,
      CASE WHEN COALESCE(SUM(ft.quantidade), 0) > 0
           THEN COALESCE(SUM(ft.valor), 0) / SUM(ft.quantidade)
           ELSE 0 END                                                     AS preco_medio,
      CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
           THEN COALESCE(SUM(ft.quantidade), 0) / COUNT(DISTINCT ft.transacao_id)
           ELSE 0 END                                                     AS quantidade_media_por_pedido,
      MAX(dd.data)                                                        AS data_ultima_venda,
      (CURRENT_DATE - MAX(dd.data))                                       AS dias_recencia,
      CASE
        WHEN MIN(dd.data) IS NOT NULL AND MIN(dd.data) < MAX(dd.data)
        THEN COUNT(DISTINCT ft.transacao_id)::numeric
             / GREATEST(1,
                 EXTRACT(YEAR  FROM AGE(MAX(dd.data), MIN(dd.data))) * 12 +
                 EXTRACT(MONTH FROM AGE(MAX(dd.data), MIN(dd.data))))
        ELSE COUNT(DISTINCT ft.transacao_id)::numeric
      END                                                                 AS frequencia_mensal
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = p_client_id
      AND ft.produto_id IS NOT NULL
      AND ft.tipo_transacao = 'venda'
    GROUP BY ft.produto_id
  ),
  scored AS (
    SELECT *,
      NTILE(3) OVER (ORDER BY dias_recencia     DESC NULLS LAST) AS r_score,
      NTILE(3) OVER (ORDER BY frequencia_mensal  ASC NULLS LAST) AS f_score,
      NTILE(3) OVER (ORDER BY receita_total      ASC NULLS LAST) AS m_score
    FROM agg
  )
  UPDATE analytics_v2.dim_inventory di
  SET
    quantidade_total_vendida    = s.quantidade_total_vendida,
    receita_total               = s.receita_total,
    preco_medio                 = s.preco_medio,
    total_pedidos               = s.total_pedidos,
    quantidade_media_por_pedido = s.quantidade_media_por_pedido,
    data_ultima_venda           = s.data_ultima_venda,
    dias_recencia               = s.dias_recencia,
    frequencia_mensal           = s.frequencia_mensal,
    pontuacao_cluster           = (s.r_score + s.f_score + s.m_score)::numeric,
    nivel_cluster               = CASE
                                    WHEN s.r_score + s.f_score + s.m_score >= 7 THEN 'Alto'
                                    WHEN s.r_score + s.f_score + s.m_score >= 4 THEN 'Médio'
                                    ELSE 'Baixo'
                                  END,
    updated_at                  = clock_timestamp()
  FROM scored s
  WHERE di.client_id   = p_client_id
    AND di.inventory_id = s.produto_id;

  RAISE NOTICE '[atualizar_dim_inventory] client=%: done', p_client_id;
END;
$function$;

-- ============================================================================
-- 2. MATERIALIZED VIEWS (drop cascades the v_* security-invoker wrappers)
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_dashboard CASCADE;
CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard AS
WITH base AS (
  SELECT ft.client_id,
    (COUNT(DISTINCT dc.customer_id)  FILTER (WHERE ft.tipo_transacao = 'venda'))::integer  AS total_clientes,
    (COUNT(DISTINCT df.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra'))::integer AS total_fornecedores,
    (COUNT(DISTINCT di.inventory_id)  FILTER (WHERE ft.tipo_transacao = 'venda'))::integer  AS total_produtos,
    (COUNT(DISTINCT ft.transacao_id)  FILTER (WHERE ft.tipo_transacao = 'venda'))::integer  AS total_pedidos,
    COALESCE(SUM(ft.valor)      FILTER (WHERE ft.tipo_transacao = 'venda'), 0)::numeric AS receita_total,
    COALESCE(SUM(ft.quantidade) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)::numeric AS quantidade_total_vendida,
    CASE
      WHEN COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
      THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
           / (COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric
      ELSE 0::numeric
    END AS ticket_medio,
    (COUNT(DISTINCT dc.endereco_uf) FILTER (WHERE ft.tipo_transacao = 'venda'))::integer AS total_regioes,
    CASE
      WHEN COUNT(DISTINCT df.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra') > 0
      THEN (COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'compra'))::numeric
           / (COUNT(DISTINCT df.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra'))::numeric
      ELSE 0::numeric
    END AS frequencia_media_fornecedores,
    (COUNT(DISTINCT dc.customer_id) FILTER (
       WHERE ft.tipo_transacao = 'venda' AND dd.data >= (CURRENT_DATE - 30)))::integer AS clientes_ativos,
    COALESCE(SUM(ft.valor) FILTER (
      WHERE ft.tipo_transacao = 'venda'
        AND DATE_TRUNC('month', dd.data)::date = DATE_TRUNC('month', CURRENT_DATE)::date), 0)::numeric AS receita_mes_atual,
    COALESCE(SUM(ft.quantidade) FILTER (
      WHERE ft.tipo_transacao = 'venda'
        AND DATE_TRUNC('month', dd.data)::date = DATE_TRUNC('month', CURRENT_DATE)::date), 0)::numeric AS quantidade_mes_atual,
    (COUNT(DISTINCT dc.customer_id) FILTER (
      WHERE ft.tipo_transacao = 'venda'
        AND DATE_TRUNC('month', dd.data)::date = DATE_TRUNC('month', CURRENT_DATE)::date))::integer AS clientes_mes_atual,
    (COUNT(DISTINCT di.inventory_id) FILTER (
      WHERE ft.tipo_transacao = 'venda'
        AND DATE_TRUNC('month', dd.data)::date = DATE_TRUNC('month', CURRENT_DATE)::date))::integer AS produtos_mes_atual,
    (COUNT(DISTINCT df.fornecedor_id) FILTER (
      WHERE ft.tipo_transacao = 'compra'
        AND DATE_TRUNC('month', dd.data)::date = DATE_TRUNC('month', CURRENT_DATE)::date))::integer AS fornecedores_mes_atual,
    COALESCE(SUM(ft.valor) FILTER (
      WHERE ft.tipo_transacao = 'venda'
        AND DATE_TRUNC('month', dd.data)::date = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date), 0)::numeric AS receita_mes_anterior,
    COALESCE(SUM(ft.quantidade) FILTER (
      WHERE ft.tipo_transacao = 'venda'
        AND DATE_TRUNC('month', dd.data)::date = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date), 0)::numeric AS quantidade_mes_anterior,
    (COUNT(DISTINCT dc.customer_id) FILTER (
      WHERE ft.tipo_transacao = 'venda'
        AND DATE_TRUNC('month', dd.data)::date = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date))::integer AS clientes_mes_anterior,
    (COUNT(DISTINCT di.inventory_id) FILTER (
      WHERE ft.tipo_transacao = 'venda'
        AND DATE_TRUNC('month', dd.data)::date = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date))::integer AS produtos_mes_anterior
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_datas dd        ON ft.data_competencia_id = dd.data_id
  LEFT JOIN analytics_v2.dim_clientes dc     ON ft.customer_id = dc.customer_id   AND dc.client_id = ft.client_id
  LEFT JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id AND df.client_id = ft.client_id
  LEFT JOIN analytics_v2.dim_inventory di    ON ft.produto_id = di.inventory_id   AND di.client_id = ft.client_id
  GROUP BY ft.client_id
),
novos_agg AS (
  SELECT sub.client_id, COUNT(*)::integer AS clientes_novos
  FROM (
    SELECT ft.client_id, ft.customer_id
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.customer_id IS NOT NULL
      AND dd.data IS NOT NULL
      AND ft.tipo_transacao = 'venda'
    GROUP BY ft.client_id, ft.customer_id
    HAVING MIN(dd.data) >= DATE_TRUNC('month', CURRENT_DATE)::date
  ) sub
  GROUP BY sub.client_id
)
SELECT b.client_id,
  b.total_clientes,
  b.total_fornecedores,
  b.total_produtos,
  b.total_pedidos,
  b.receita_total,
  b.quantidade_total_vendida,
  b.ticket_medio,
  b.receita_mes_atual,
  b.quantidade_mes_atual,
  b.clientes_mes_atual,
  b.produtos_mes_atual,
  b.fornecedores_mes_atual,
  CASE WHEN b.receita_mes_anterior > 0
       THEN (b.receita_mes_atual - b.receita_mes_anterior) / b.receita_mes_anterior
       ELSE 0::numeric END AS crescimento_receita,
  CASE WHEN b.clientes_mes_anterior > 0
       THEN (b.clientes_mes_atual - b.clientes_mes_anterior)::numeric / b.clientes_mes_anterior::numeric
       ELSE 0::numeric END AS crescimento_clientes,
  CASE WHEN b.produtos_mes_anterior > 0
       THEN (b.produtos_mes_atual - b.produtos_mes_anterior)::numeric / b.produtos_mes_anterior::numeric
       ELSE 0::numeric END AS crescimento_produtos,
  CASE WHEN b.quantidade_mes_anterior > 0
       THEN (b.quantidade_mes_atual - b.quantidade_mes_anterior) / b.quantidade_mes_anterior
       ELSE 0::numeric END AS crescimento_quantidade,
  b.frequencia_media_fornecedores,
  b.total_regioes,
  TO_CHAR(CURRENT_DATE - INTERVAL '1 month', 'Mon/YYYY') AS ultimo_mes,
  b.clientes_ativos,
  COALESCE(na.clientes_novos, 0) AS clientes_novos,
  CURRENT_TIMESTAMP AS gerado_em
FROM base b
LEFT JOIN novos_agg na ON b.client_id = na.client_id;

CREATE UNIQUE INDEX uidx_mv_resumo_dashboard_client ON analytics_v2.mv_resumo_dashboard(client_id);

DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_series_temporal CASCADE;
CREATE MATERIALIZED VIEW analytics_v2.mv_series_temporal AS
WITH base AS (
  SELECT ft.client_id,
    TO_CHAR(dd.data, 'YYYY-MM') AS periodo,
    dd.data AS data_periodo,
    'receita'::text AS tipo_grafico,
    'total'::text AS dimensao,
    COALESCE(SUM(ft.valor), 0)::numeric AS total
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data IS NOT NULL AND ft.tipo_transacao = 'venda'
  GROUP BY ft.client_id, dd.data

  UNION ALL

  SELECT ft.client_id,
    TO_CHAR(dd.data, 'YYYY-MM'),
    dd.data,
    'clientes'::text,
    'total'::text,
    COUNT(DISTINCT dc.customer_id)::numeric
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  LEFT JOIN analytics_v2.dim_clientes dc ON ft.customer_id = dc.customer_id AND dc.client_id = ft.client_id
  WHERE dd.data IS NOT NULL AND ft.tipo_transacao = 'venda'
  GROUP BY ft.client_id, dd.data

  UNION ALL

  SELECT ft.client_id,
    TO_CHAR(dd.data, 'YYYY-MM'),
    dd.data,
    'fornecedores'::text,
    'total'::text,
    COUNT(DISTINCT df.fornecedor_id)::numeric
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  LEFT JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id AND df.client_id = ft.client_id
  WHERE dd.data IS NOT NULL AND ft.tipo_transacao = 'compra'
  GROUP BY ft.client_id, dd.data

  UNION ALL

  SELECT ft.client_id,
    TO_CHAR(dd.data, 'YYYY-MM'),
    dd.data,
    'produtos'::text,
    'total'::text,
    COUNT(DISTINCT di.inventory_id)::numeric
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  LEFT JOIN analytics_v2.dim_inventory di ON ft.produto_id = di.inventory_id AND di.client_id = ft.client_id
  WHERE dd.data IS NOT NULL AND ft.tipo_transacao = 'venda'
  GROUP BY ft.client_id, dd.data

  UNION ALL

  SELECT ft.client_id,
    TO_CHAR(dd.data, 'YYYY-MM'),
    dd.data,
    'pedidos'::text,
    'total'::text,
    COUNT(DISTINCT ft.transacao_id)::numeric
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data IS NOT NULL AND ft.tipo_transacao = 'venda'
  GROUP BY ft.client_id, dd.data
)
SELECT client_id,
  periodo,
  data_periodo,
  tipo_grafico,
  dimensao,
  total,
  SUM(total) OVER (
    PARTITION BY client_id, tipo_grafico, dimensao
    ORDER BY data_periodo
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS total_cumulativo
FROM base;

CREATE UNIQUE INDEX uidx_mv_series_temporal_pk ON analytics_v2.mv_series_temporal(client_id, data_periodo, tipo_grafico, dimensao);

DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_ultimos_pedidos CASCADE;
CREATE MATERIALIZED VIEW analytics_v2.mv_ultimos_pedidos AS
SELECT ft.client_id,
  ft.transacao_id AS pedido_id,
  dc.cpf_cnpj AS cliente_cpf_cnpj,
  ft.valor AS valor_pedido,
  ft.quantidade AS qtd_produtos,
  ROW_NUMBER() OVER (PARTITION BY ft.client_id ORDER BY ft.created_at DESC) AS ordem
FROM analytics_v2.fato_transacoes ft
LEFT JOIN analytics_v2.dim_clientes dc ON ft.customer_id = dc.customer_id AND dc.client_id = ft.client_id
WHERE ft.created_at IS NOT NULL AND ft.tipo_transacao = 'venda';

CREATE UNIQUE INDEX uidx_mv_ultimos_pedidos_pk ON analytics_v2.mv_ultimos_pedidos(client_id, pedido_id);

DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_distribuicao_regional CASCADE;
CREATE MATERIALIZED VIEW analytics_v2.mv_distribuicao_regional AS
SELECT dc.client_id,
  dc.endereco_uf,
  dc.endereco_cidade,
  COALESCE(SUM(ft.valor), 0)::numeric AS receita_total,
  COUNT(DISTINCT dc.customer_id)::integer AS total_clientes,
  COUNT(DISTINCT ft.transacao_id)::integer AS total_pedidos
FROM analytics_v2.dim_clientes dc
LEFT JOIN analytics_v2.fato_transacoes ft
  ON dc.customer_id = ft.customer_id
 AND dc.client_id = ft.client_id
 AND ft.tipo_transacao = 'venda'
GROUP BY dc.client_id, dc.endereco_uf, dc.endereco_cidade;

CREATE UNIQUE INDEX uidx_mv_distribuicao_regional_pk ON analytics_v2.mv_distribuicao_regional(client_id, endereco_uf, endereco_cidade);

-- Recreate security-invoker wrappers dropped by CASCADE
CREATE VIEW analytics_v2.v_resumo_dashboard WITH (security_invoker=on) AS
SELECT * FROM analytics_v2.mv_resumo_dashboard
WHERE client_id = public.get_my_client_id();

CREATE VIEW analytics_v2.v_series_temporal WITH (security_invoker=on) AS
SELECT * FROM analytics_v2.mv_series_temporal
WHERE client_id = public.get_my_client_id();

CREATE VIEW analytics_v2.v_ultimos_pedidos WITH (security_invoker=on) AS
SELECT * FROM analytics_v2.mv_ultimos_pedidos
WHERE client_id = public.get_my_client_id();

CREATE VIEW analytics_v2.v_distribuicao_regional WITH (security_invoker=on) AS
SELECT * FROM analytics_v2.mv_distribuicao_regional
WHERE client_id = public.get_my_client_id();

GRANT SELECT ON analytics_v2.v_resumo_dashboard,
                analytics_v2.v_series_temporal,
                analytics_v2.v_ultimos_pedidos,
                analytics_v2.v_distribuicao_regional,
                analytics_v2.mv_resumo_dashboard,
                analytics_v2.mv_series_temporal,
                analytics_v2.mv_ultimos_pedidos,
                analytics_v2.mv_distribuicao_regional
TO authenticated;

-- ============================================================================
-- 3. analytics_v2 RPCs — vendas-only revenue, compras-only spend
-- ============================================================================

CREATE OR REPLACE FUNCTION analytics_v2.get_annual_metrics_for_client(p_client_id uuid)
 RETURNS TABLE(ano integer, receita numeric, total_pedidos bigint, clientes_unicos bigint, clientes_novos bigint, ticket_medio numeric, fornecedores_ativos bigint, skus_ativos bigint, quantidade_vendida numeric, is_partial boolean, yoy_receita_pct numeric, receita_anualizada numeric)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public'
AS $function$
WITH years AS (
  SELECT EXTRACT(YEAR FROM dd.data)::integer AS ano,
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)::numeric AS receita,
    COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda') AS total_pedidos,
    COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda') AS clientes_unicos,
    COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra') AS fornecedores_ativos,
    COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda') AS skus_ativos,
    COALESCE(SUM(ft.quantidade) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)::numeric AS quantidade_vendida,
    CASE WHEN COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS ticket_medio
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
  GROUP BY EXTRACT(YEAR FROM dd.data)::integer
),
first_purchases AS (
  SELECT ft.customer_id, EXTRACT(YEAR FROM MIN(dd.data))::integer AS first_year
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND ft.customer_id IS NOT NULL AND dd.data IS NOT NULL
    AND ft.tipo_transacao = 'venda'
  GROUP BY ft.customer_id
),
novos_por_ano AS (SELECT first_year AS ano, COUNT(*)::bigint AS clientes_novos FROM first_purchases GROUP BY first_year),
current_year_months AS (
  SELECT COUNT(DISTINCT date_trunc('month', dd.data)) AS months_with_data
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
    AND ft.tipo_transacao = 'venda'
    AND EXTRACT(YEAR FROM dd.data) = EXTRACT(YEAR FROM CURRENT_DATE)
),
with_yoy AS (
  SELECT y.ano, ROUND(y.receita, 2) AS receita, y.total_pedidos, y.clientes_unicos,
    COALESCE(n.clientes_novos, 0) AS clientes_novos, ROUND(y.ticket_medio, 2) AS ticket_medio,
    y.fornecedores_ativos, y.skus_ativos, y.quantidade_vendida,
    (y.ano = EXTRACT(YEAR FROM CURRENT_DATE)::integer) AS is_partial,
    CASE WHEN LAG(y.receita) OVER (ORDER BY y.ano) > 0
         THEN ROUND((y.receita - LAG(y.receita) OVER (ORDER BY y.ano)) / LAG(y.receita) OVER (ORDER BY y.ano) * 100, 1)
         ELSE NULL END AS yoy_receita_pct,
    y.receita AS raw_receita
  FROM years y LEFT JOIN novos_por_ano n ON n.ano = y.ano
)
SELECT w.ano, w.receita, w.total_pedidos, w.clientes_unicos, w.clientes_novos,
  w.ticket_medio, w.fornecedores_ativos, w.skus_ativos, w.quantidade_vendida, w.is_partial,
  w.yoy_receita_pct,
  CASE WHEN w.is_partial AND m.months_with_data > 0
       THEN ROUND(w.raw_receita / m.months_with_data * 12, 2) ELSE NULL END AS receita_anualizada
FROM with_yoy w CROSS JOIN current_year_months m ORDER BY w.ano DESC;
$function$;

CREATE OR REPLACE FUNCTION analytics_v2.get_inventory_indicators(p_period text DEFAULT '30d'::text)
 RETURNS TABLE(skus_ativos bigint, skus_total bigint, quantidade_vendida_periodo numeric, receita_skus_periodo numeric, giro_estimado numeric, ticket_medio_sku numeric, cobertura_top20_perc numeric, stockout_rate_perc numeric, crescimento_quantidade_perc numeric, dio_dias numeric, cobertura_dias numeric, fill_rate_perc numeric, sell_through_perc numeric, gmroi numeric, acuracidade_perc numeric, period text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public', 'pg_catalog'
AS $function$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start     date;
  v_prev_start date;
  v_prev_end  date;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end
  INTO   v_start, v_prev_start, v_prev_end
  FROM   analytics_v2._period_range(p_period) r;

  RETURN QUERY
  WITH period_data AS (
    SELECT
      ft.produto_id,
      SUM(ft.quantidade) AS qtd,
      SUM(ft.valor)      AS rev
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id
      AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data < CURRENT_DATE
    GROUP BY ft.produto_id
  ),
  prev_data AS (
    SELECT SUM(ft.quantidade) AS qtd
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id
      AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_prev_start AND dd.data < v_prev_end
  ),
  top20_rev AS (
    SELECT SUM(rev) AS top_rev
    FROM (SELECT rev FROM period_data ORDER BY rev DESC LIMIT GREATEST(1, (SELECT COUNT(*) FROM period_data) * 20 / 100)) t
  ),
  agg AS (
    SELECT
      COUNT(*)                    AS skus_ativos,
      COALESCE(SUM(p.qtd), 0)   AS quantidade,
      COALESCE(SUM(p.rev), 0)   AS receita
    FROM period_data p
  )
  SELECT
    agg.skus_ativos,
    (SELECT COUNT(*) FROM analytics_v2.dim_inventory WHERE client_id = v_client_id),
    agg.quantidade,
    agg.receita,
    NULL::numeric, -- giro_estimado
    CASE WHEN agg.skus_ativos > 0 THEN ROUND(agg.receita / agg.skus_ativos, 2) ELSE 0 END,
    CASE WHEN agg.receita > 0 THEN ROUND((SELECT top_rev FROM top20_rev) / agg.receita * 100, 1) ELSE NULL END,
    NULL::numeric, -- stockout_rate_perc
    CASE WHEN (SELECT qtd FROM prev_data) > 0
         THEN ROUND((agg.quantidade - (SELECT qtd FROM prev_data)) / (SELECT qtd FROM prev_data) * 100, 1)
         ELSE NULL END,
    NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric,
    p_period
  FROM agg;
END;
$function$;

CREATE OR REPLACE FUNCTION analytics_v2.get_marketing_indicators(p_period text)
 RETURNS TABLE(clientes_novos bigint, receita_novos_clientes numeric, n1 numeric, n2 numeric, n3 numeric, n4 numeric, n5 numeric, n6 numeric, n7 numeric, n8 numeric, n9 numeric, periodo text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public'
AS $function$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start date; v_prev_start date; v_prev_end date;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end INTO v_start, v_prev_start, v_prev_end
  FROM analytics_v2._period_range(p_period) r;
  RETURN QUERY
  WITH first_purchases AS (
    SELECT ft.customer_id, MIN(dd.data) AS first_date FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id AND ft.customer_id IS NOT NULL
      AND ft.tipo_transacao = 'venda'
    GROUP BY ft.customer_id
  ),
  new_customers AS (
    SELECT fp.customer_id FROM first_purchases fp
    WHERE fp.first_date >= v_start AND fp.first_date < CURRENT_DATE
  ),
  new_customer_rev AS (
    SELECT COALESCE(SUM(ft.valor), 0) AS rev FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    JOIN new_customers nc ON nc.customer_id = ft.customer_id
    WHERE ft.client_id = v_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data < CURRENT_DATE
  )
  SELECT (SELECT COUNT(*) FROM new_customers), (SELECT rev FROM new_customer_rev),
    NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric,
    NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, p_period;
END; $function$;

CREATE OR REPLACE FUNCTION analytics_v2.get_commercial_revenue_by_channel(p_period text DEFAULT '30d'::text)
 RETURNS TABLE(channel text, receita numeric, pedidos bigint, share_perc numeric, period text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public', 'pg_catalog'
AS $function$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start     date;
BEGIN
  SELECT r.start_date INTO v_start FROM analytics_v2._period_range(p_period) r;

  RETURN QUERY
  WITH by_status AS (
    SELECT
      COALESCE(ft.status, 'sem_status')   AS channel,
      COALESCE(SUM(ft.valor), 0)          AS receita,
      COUNT(DISTINCT ft.transacao_id)     AS pedidos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id
      AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data < CURRENT_DATE
    GROUP BY ft.status
  ),
  total AS (SELECT NULLIF(SUM(receita), 0) AS total FROM by_status)
  SELECT
    b.channel,
    b.receita,
    b.pedidos,
    ROUND(b.receita / t.total * 100, 1),
    p_period
  FROM by_status b, total t
  ORDER BY b.receita DESC;
END;
$function$;

CREATE OR REPLACE FUNCTION analytics_v2.get_commercial_top_clients(p_period text, p_limit integer DEFAULT 10)
 RETURNS TABLE(customer_id bigint, nome text, receita numeric, pedidos bigint, participacao_pct numeric, periodo text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public'
AS $function$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start date;
BEGIN
  SELECT r.start_date INTO v_start FROM analytics_v2._period_range(p_period) r;
  RETURN QUERY
  WITH by_customer AS (
    SELECT ft.customer_id, COALESCE(SUM(ft.valor), 0) AS receita,
      COUNT(DISTINCT ft.transacao_id) AS pedidos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id AND dd.data >= v_start AND dd.data < CURRENT_DATE
      AND ft.customer_id IS NOT NULL
      AND ft.tipo_transacao = 'venda'
    GROUP BY ft.customer_id ORDER BY receita DESC LIMIT p_limit
  ),
  total AS (SELECT NULLIF(SUM(receita), 0) AS total FROM by_customer)
  SELECT b.customer_id, dc.nome, b.receita, b.pedidos,
    ROUND(b.receita / t.total * 100, 1), p_period
  FROM by_customer b
  JOIN analytics_v2.dim_clientes dc ON dc.customer_id = b.customer_id AND dc.client_id = v_client_id
  CROSS JOIN total t ORDER BY b.receita DESC;
END; $function$;

CREATE OR REPLACE FUNCTION analytics_v2.get_kpi_mtd_comparison(p_client_id uuid)
 RETURNS TABLE(dimension text, kpi text, label text, unit text, current_value numeric, prev_period_value numeric, avg_3m numeric, mom_pct numeric, vs_3m_avg_pct numeric)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public'
AS $function$
DECLARE
  v_today     date := CURRENT_DATE;
  v_day       int  := EXTRACT(day FROM CURRENT_DATE);
  v_cur_start date := date_trunc('month', CURRENT_DATE)::date;
  v_m1_start date; v_m1_end date;
  v_m2_start date; v_m2_end date;
  v_m3_start date; v_m3_end date;
BEGIN
  v_m1_start := date_trunc('month', v_today - INTERVAL '1 month')::date;
  v_m1_end   := LEAST(v_m1_start + (v_day - 1), (v_m1_start + INTERVAL '1 month - 1 day')::date);
  v_m2_start := date_trunc('month', v_today - INTERVAL '2 months')::date;
  v_m2_end   := LEAST(v_m2_start + (v_day - 1), (v_m2_start + INTERVAL '1 month - 1 day')::date);
  v_m3_start := date_trunc('month', v_today - INTERVAL '3 months')::date;
  v_m3_end   := LEAST(v_m3_start + (v_day - 1), (v_m3_start + INTERVAL '1 month - 1 day')::date);

  RETURN QUERY
  WITH
  periods(tag, d_start, d_end) AS (
    VALUES ('cur'::text, v_cur_start, v_today),
           ('m1', v_m1_start, v_m1_end),
           ('m2', v_m2_start, v_m2_end),
           ('m3', v_m3_start, v_m3_end)
  ),
  raw AS (
    SELECT p.tag,
      COALESCE(SUM(ft.valor), 0)            AS receita,
      COUNT(DISTINCT ft.documento)           AS pedidos,
      COUNT(DISTINCT ft.customer_id)         AS clientes
    FROM periods p
    JOIN dim_datas dd ON dd.data BETWEEN p.d_start AND p.d_end
    JOIN fato_transacoes ft
      ON ft.data_competencia_id = dd.data_id
     AND ft.client_id = p_client_id
     AND ft.tipo_transacao = 'venda'
    GROUP BY p.tag
  ),
  base AS (
    SELECT p.tag,
      COALESCE(r.receita,  0) AS receita,
      COALESCE(r.pedidos,  0) AS pedidos,
      COALESCE(r.clientes, 0) AS clientes
    FROM periods p LEFT JOIN raw r USING (tag)
  ),
  agg AS (
    SELECT
      MAX(receita)  FILTER (WHERE tag='cur') AS cur_receita,
      MAX(pedidos)  FILTER (WHERE tag='cur') AS cur_pedidos,
      MAX(clientes) FILTER (WHERE tag='cur') AS cur_clientes,
      MAX(receita)  FILTER (WHERE tag='m1')  AS m1_receita,
      MAX(pedidos)  FILTER (WHERE tag='m1')  AS m1_pedidos,
      MAX(clientes) FILTER (WHERE tag='m1')  AS m1_clientes,
      ROUND((MAX(receita)  FILTER (WHERE tag='m1') + MAX(receita)  FILTER (WHERE tag='m2') + MAX(receita)  FILTER (WHERE tag='m3')) / 3, 2) AS avg_receita,
      ROUND((MAX(pedidos)  FILTER (WHERE tag='m1') + MAX(pedidos)  FILTER (WHERE tag='m2') + MAX(pedidos)  FILTER (WHERE tag='m3'))::numeric / 3, 1) AS avg_pedidos,
      ROUND((MAX(clientes) FILTER (WHERE tag='m1') + MAX(clientes) FILTER (WHERE tag='m2') + MAX(clientes) FILTER (WHERE tag='m3'))::numeric / 3, 1) AS avg_clientes
    FROM base
  ),
  novos AS (
    SELECT COUNT(*) AS cnt FROM (
      SELECT ft.customer_id FROM fato_transacoes ft
      JOIN dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id
        AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id
      HAVING MIN(dd.data) BETWEEN v_cur_start AND v_today
    ) s
  ),
  recorrentes AS (
    SELECT COUNT(*) AS cnt FROM (
      SELECT ft.customer_id FROM fato_transacoes ft
      JOIN dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id
        AND ft.tipo_transacao = 'venda'
        AND dd.data BETWEEN v_cur_start AND v_today
      GROUP BY ft.customer_id HAVING COUNT(DISTINCT ft.documento) > 1
    ) s
  )
  SELECT 'finance'::text, 'receita_liquida', 'Receita MTD', 'BRL',
    ROUND(a.cur_receita, 2), ROUND(a.m1_receita, 2), a.avg_receita,
    CASE WHEN a.m1_receita > 0 THEN ROUND((a.cur_receita - a.m1_receita) / a.m1_receita * 100, 1) ELSE NULL END,
    CASE WHEN a.avg_receita  > 0 THEN ROUND((a.cur_receita - a.avg_receita)  / a.avg_receita  * 100, 1) ELSE NULL END
  FROM agg a
  UNION ALL
  SELECT 'finance', 'ticket_medio', 'Ticket Médio', 'BRL',
    CASE WHEN a.cur_pedidos > 0 THEN ROUND(a.cur_receita / a.cur_pedidos, 2) ELSE NULL END,
    CASE WHEN a.m1_pedidos  > 0 THEN ROUND(a.m1_receita  / a.m1_pedidos,  2) ELSE NULL END,
    CASE WHEN a.avg_pedidos > 0 THEN ROUND(a.avg_receita / a.avg_pedidos, 2) ELSE NULL END,
    CASE WHEN a.m1_pedidos > 0 AND a.cur_pedidos > 0
         THEN ROUND(((a.cur_receita/a.cur_pedidos) - (a.m1_receita/a.m1_pedidos)) / (a.m1_receita/a.m1_pedidos) * 100, 1)
         ELSE NULL END,
    NULL
  FROM agg a
  UNION ALL
  SELECT 'commercial'::text, 'total_pedidos', 'Pedidos MTD', 'count',
    a.cur_pedidos::numeric, a.m1_pedidos::numeric, a.avg_pedidos,
    CASE WHEN a.m1_pedidos > 0 THEN ROUND((a.cur_pedidos - a.m1_pedidos)::numeric / a.m1_pedidos * 100, 1) ELSE NULL END,
    CASE WHEN a.avg_pedidos > 0 THEN ROUND((a.cur_pedidos - a.avg_pedidos) / a.avg_pedidos * 100, 1) ELSE NULL END
  FROM agg a
  UNION ALL
  SELECT 'commercial', 'clientes_ativos', 'Clientes Ativos MTD', 'count',
    a.cur_clientes::numeric, a.m1_clientes::numeric, a.avg_clientes,
    CASE WHEN a.m1_clientes > 0 THEN ROUND((a.cur_clientes - a.m1_clientes)::numeric / a.m1_clientes * 100, 1) ELSE NULL END,
    CASE WHEN a.avg_clientes > 0 THEN ROUND((a.cur_clientes - a.avg_clientes) / a.avg_clientes * 100, 1) ELSE NULL END
  FROM agg a
  UNION ALL
  SELECT 'commercial', 'novos_clientes', 'Novos Clientes MTD', 'count',
    novos.cnt::numeric, NULL, NULL, NULL, NULL FROM novos
  UNION ALL
  SELECT 'commercial', 'taxa_recorrencia_perc', 'Taxa de Recorrência', '%',
    CASE WHEN a.cur_clientes > 0 THEN ROUND(recorrentes.cnt::numeric / a.cur_clientes * 100, 1) ELSE NULL END,
    NULL, NULL, NULL, NULL
  FROM agg a, recorrentes;
END;
$function$;

-- ----------------------------------------------------------------------------
-- get_context_metrics_for_client(uuid) — monthly KPI series (Estratégia room
-- and context reports). Revenue KPIs -> venda; fornecedor KPIs -> compra spend.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics_v2.get_context_metrics_for_client(p_client_id uuid)
 RETURNS TABLE(dimension text, kpi text, label text, unit text, current_value numeric, prev_month_value numeric, avg_6m numeric, mom_pct numeric, vs_6m_avg_pct numeric, streak_months integer)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public'
AS $function$
WITH
all_monthly AS (
  SELECT date_trunc('month', dd.data)::date AS mes,
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0) AS receita,
    (COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS total_pedidos,
    COALESCE(SUM(ft.quantidade) FILTER (WHERE ft.tipo_transacao = 'venda'), 0) AS quantidade,
    (COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS clientes_unicos,
    (COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra'))::numeric AS fornecedores_ativos,
    (COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS skus_ativos,
    CASE WHEN COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS ticket_medio,
    CASE WHEN COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN (COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric
              / COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS frequencia_media,
    CASE WHEN COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS receita_por_cliente,
    CASE WHEN COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS receita_por_sku,
    CASE WHEN COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'compra'), 0)
              / COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra')
         ELSE 0 END AS receita_por_fornecedor
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
  GROUP BY date_trunc('month', dd.data)::date
),
monthly_buyers AS (
  SELECT DISTINCT date_trunc('month', dd.data)::date AS mes, ft.customer_id
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND ft.customer_id IS NOT NULL AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
    AND ft.tipo_transacao = 'venda'
),
first_purchases AS (
  SELECT ft.customer_id, date_trunc('month', MIN(dd.data))::date AS first_month
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND ft.customer_id IS NOT NULL AND dd.data IS NOT NULL
    AND ft.tipo_transacao = 'venda'
  GROUP BY ft.customer_id
),
novos_por_mes AS (SELECT first_month AS mes, COUNT(*)::numeric AS clientes_novos FROM first_purchases GROUP BY first_month),
recorrentes_por_mes AS (
  SELECT a.mes, COUNT(*)::numeric AS clientes_recorrentes FROM monthly_buyers a
  JOIN monthly_buyers b ON b.customer_id = a.customer_id AND b.mes = (a.mes - INTERVAL '1 month')::date
  GROUP BY a.mes
),
monthly_rev_per_entity AS (
  SELECT date_trunc('month', dd.data)::date AS mes, ft.customer_id, ft.produto_id, ft.fornecedor_id, ft.valor, ft.tipo_transacao
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
),
rev_por_cliente AS (SELECT mes, customer_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE customer_id IS NOT NULL AND tipo_transacao = 'venda' GROUP BY mes, customer_id),
rev_por_produto AS (SELECT mes, produto_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE produto_id IS NOT NULL AND tipo_transacao = 'venda' GROUP BY mes, produto_id),
rev_por_fornecedor AS (SELECT mes, fornecedor_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE fornecedor_id IS NOT NULL AND tipo_transacao = 'compra' GROUP BY mes, fornecedor_id),
concentracao_top3_clientes AS (
  SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev), 0) * 100, 1) AS perc
  FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_cliente) x GROUP BY mes
),
concentracao_top3_produtos AS (
  SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev), 0) * 100, 1) AS perc
  FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_produto) x GROUP BY mes
),
concentracao_top3_fornecedores AS (
  SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev), 0) * 100, 1) AS perc
  FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_fornecedor) x GROUP BY mes
),
top1_clean AS (SELECT mes, ROUND(MAX(rev) / NULLIF(SUM(rev), 0) * 100, 1) AS concentracao_top1_perc FROM rev_por_fornecedor GROUP BY mes),
enriched AS (
  SELECT am.mes, am.receita, am.ticket_medio, am.total_pedidos, am.quantidade,
    am.clientes_unicos, am.frequencia_media, am.receita_por_cliente,
    am.skus_ativos, am.receita_por_sku, am.fornecedores_ativos, am.receita_por_fornecedor,
    COALESCE(np.clientes_novos, 0) AS clientes_novos,
    COALESCE(rp.clientes_recorrentes, 0) AS clientes_recorrentes,
    CASE WHEN COALESCE(am_prev.clientes_unicos, 0) > 0
         THEN ROUND(COALESCE(rp.clientes_recorrentes, 0) / am_prev.clientes_unicos * 100, 1) ELSE 0 END AS taxa_recorrencia_perc,
    COALESCE(t1.concentracao_top1_perc, 0) AS concentracao_top1_fornecedor_perc,
    COALESCE(c3c.perc, 0) AS concentracao_top3_clientes_perc,
    COALESCE(c3p.perc, 0) AS concentracao_top3_produtos_perc,
    COALESCE(c3s.perc, 0) AS concentracao_top3_fornecedores_perc
  FROM all_monthly am
  LEFT JOIN all_monthly am_prev ON am_prev.mes = (am.mes - INTERVAL '1 month')::date
  LEFT JOIN novos_por_mes np ON np.mes = am.mes
  LEFT JOIN recorrentes_por_mes rp ON rp.mes = am.mes
  LEFT JOIN top1_clean t1 ON t1.mes = am.mes
  LEFT JOIN concentracao_top3_clientes c3c ON c3c.mes = am.mes
  LEFT JOIN concentracao_top3_produtos c3p ON c3p.mes = am.mes
  LEFT JOIN concentracao_top3_fornecedores c3s ON c3s.mes = am.mes
),
ref_month AS (
  SELECT COALESCE(
    (SELECT mes FROM enriched WHERE mes = date_trunc('month', CURRENT_DATE)::date LIMIT 1),
    (SELECT mes FROM enriched WHERE mes < date_trunc('month', CURRENT_DATE)::date ORDER BY mes DESC LIMIT 1)
  ) AS mes
),
complete_months AS (SELECT e.* FROM enriched e, ref_month r WHERE e.mes < r.mes),
current_month AS (SELECT e.* FROM enriched e, ref_month r WHERE e.mes = r.mes),
long_complete AS (
  SELECT mes, 'receita_liquida' AS kpi, receita AS val FROM complete_months UNION ALL
  SELECT mes, 'ticket_medio', ticket_medio FROM complete_months UNION ALL
  SELECT mes, 'total_pedidos', total_pedidos FROM complete_months UNION ALL
  SELECT mes, 'quantidade_vendida', quantidade FROM complete_months UNION ALL
  SELECT mes, 'clientes_unicos', clientes_unicos FROM complete_months UNION ALL
  SELECT mes, 'clientes_novos', clientes_novos FROM complete_months UNION ALL
  SELECT mes, 'clientes_recorrentes', clientes_recorrentes FROM complete_months UNION ALL
  SELECT mes, 'taxa_recorrencia_perc', taxa_recorrencia_perc FROM complete_months UNION ALL
  SELECT mes, 'receita_por_cliente', receita_por_cliente FROM complete_months UNION ALL
  SELECT mes, 'frequencia_media', frequencia_media FROM complete_months UNION ALL
  SELECT mes, 'skus_ativos', skus_ativos FROM complete_months UNION ALL
  SELECT mes, 'receita_por_sku', receita_por_sku FROM complete_months UNION ALL
  SELECT mes, 'fornecedores_ativos', fornecedores_ativos FROM complete_months UNION ALL
  SELECT mes, 'receita_por_fornecedor', receita_por_fornecedor FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top1_fornecedor_perc', concentracao_top1_fornecedor_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_clientes_perc', concentracao_top3_clientes_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_produtos_perc', concentracao_top3_produtos_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_fornecedores_perc', concentracao_top3_fornecedores_perc FROM complete_months
),
long_current AS (
  SELECT 'receita_liquida' AS kpi, receita AS val FROM current_month UNION ALL
  SELECT 'ticket_medio', ticket_medio FROM current_month UNION ALL
  SELECT 'total_pedidos', total_pedidos FROM current_month UNION ALL
  SELECT 'quantidade_vendida', quantidade FROM current_month UNION ALL
  SELECT 'clientes_unicos', clientes_unicos FROM current_month UNION ALL
  SELECT 'clientes_novos', clientes_novos FROM current_month UNION ALL
  SELECT 'clientes_recorrentes', clientes_recorrentes FROM current_month UNION ALL
  SELECT 'taxa_recorrencia_perc', taxa_recorrencia_perc FROM current_month UNION ALL
  SELECT 'receita_por_cliente', receita_por_cliente FROM current_month UNION ALL
  SELECT 'frequencia_media', frequencia_media FROM current_month UNION ALL
  SELECT 'skus_ativos', skus_ativos FROM current_month UNION ALL
  SELECT 'receita_por_sku', receita_por_sku FROM current_month UNION ALL
  SELECT 'fornecedores_ativos', fornecedores_ativos FROM current_month UNION ALL
  SELECT 'receita_por_fornecedor', receita_por_fornecedor FROM current_month UNION ALL
  SELECT 'concentracao_top1_fornecedor_perc', concentracao_top1_fornecedor_perc FROM current_month UNION ALL
  SELECT 'concentracao_top3_clientes_perc', concentracao_top3_clientes_perc FROM current_month UNION ALL
  SELECT 'concentracao_top3_produtos_perc', concentracao_top3_produtos_perc FROM current_month UNION ALL
  SELECT 'concentracao_top3_fornecedores_perc', concentracao_top3_fornecedores_perc FROM current_month
),
ranked AS (SELECT kpi, mes, val, ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC) AS rn FROM long_complete),
prev_month AS (SELECT kpi, val AS prev_val FROM ranked WHERE rn = 1),
avg_6m AS (SELECT kpi, ROUND(AVG(val), 2) AS avg_val FROM ranked WHERE rn BETWEEN 1 AND 6 GROUP BY kpi),
with_dir AS (SELECT kpi, mes, val, SIGN(val - LAG(val) OVER (PARTITION BY kpi ORDER BY mes)) AS dir, ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC) AS rn FROM long_complete),
latest_dir AS (SELECT kpi, dir FROM with_dir WHERE rn = 1 AND dir IS NOT NULL),
streak_tagged AS (
  SELECT w.kpi, l.dir AS streak_dir,
    SUM(CASE WHEN w.dir != l.dir THEN 1 ELSE 0 END) OVER (PARTITION BY w.kpi ORDER BY w.rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS breaks
  FROM with_dir w JOIN latest_dir l USING (kpi) WHERE w.dir IS NOT NULL
),
streak AS (SELECT kpi, (MAX(streak_dir) * COUNT(*))::integer AS streak_months FROM streak_tagged WHERE breaks = 0 GROUP BY kpi),
assembled AS (
  SELECT lc.kpi, ROUND(lc.val, 2) AS current_value, ROUND(pm.prev_val, 2) AS prev_month_value,
    a6.avg_val AS avg_6m,
    CASE WHEN COALESCE(pm.prev_val, 0) <> 0 THEN ROUND((lc.val - pm.prev_val) / pm.prev_val * 100, 1) ELSE NULL END AS mom_pct,
    CASE WHEN COALESCE(a6.avg_val, 0) <> 0 THEN ROUND((lc.val - a6.avg_val) / a6.avg_val * 100, 1) ELSE NULL END AS vs_6m_avg_pct,
    COALESCE(st.streak_months, 0) AS streak_months
  FROM long_current lc LEFT JOIN prev_month pm USING (kpi) LEFT JOIN avg_6m a6 USING (kpi) LEFT JOIN streak st USING (kpi)
)
SELECT m.dimension, m.kpi, m.label, m.unit,
       a.current_value, a.prev_month_value, a.avg_6m, a.mom_pct, a.vs_6m_avg_pct, a.streak_months
FROM assembled a
JOIN (VALUES
  ('receita_liquida','finance','Receita Líquida','BRL'),('ticket_medio','finance','Ticket Médio','BRL'),
  ('total_pedidos','finance','Total de Pedidos','count'),('clientes_unicos','commercial','Clientes Únicos','count'),
  ('clientes_novos','commercial','Clientes Novos','count'),('clientes_recorrentes','commercial','Clientes Recorrentes','count'),
  ('taxa_recorrencia_perc','commercial','Taxa de Recorrência','%'),('receita_por_cliente','commercial','Receita por Cliente','BRL'),
  ('frequencia_media','commercial','Frequência Média de Compra','count'),('concentracao_top3_clientes_perc','commercial','Concentração Top 3 Clientes','%'),
  ('skus_ativos','inventory','SKUs Ativos no Mês','count'),('quantidade_vendida','inventory','Quantidade Vendida','count'),
  ('receita_por_sku','inventory','Receita por SKU Ativo','BRL'),('concentracao_top3_produtos_perc','inventory','Concentração Top 3 Produtos','%'),
  ('fornecedores_ativos','supply','Fornecedores Ativos','count'),('receita_por_fornecedor','supply','Receita por Fornecedor','BRL'),
  ('concentracao_top1_fornecedor_perc','supply','Concentração Top Fornecedor','%'),('concentracao_top3_fornecedores_perc','supply','Concentração Top 3 Fornecedores','%')
) AS m(kpi, dimension, label, unit) ON m.kpi = a.kpi
UNION ALL SELECT 'finance','receita_ytd','Receita Acumulada (YTD)','BRL',ROUND(COALESCE(SUM(ft.valor),0)::numeric,2),NULL,NULL,NULL,NULL,0
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
  AND EXTRACT(YEAR FROM dd.data) = EXTRACT(YEAR FROM CURRENT_DATE) AND dd.data < CURRENT_DATE
UNION ALL SELECT 'inventory','skus_total','Total de SKUs (catálogo)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_inventory WHERE client_id = p_client_id
UNION ALL SELECT 'commercial','clientes_base_total','Total de Clientes (base)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id
UNION ALL SELECT 'commercial','clientes_ativos_90d','Clientes Ativos (últimos 90 dias)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id AND dias_recencia IS NOT NULL AND dias_recencia <= 90
UNION ALL SELECT 'commercial','recencia_media_dias','Recência Média da Base (dias)','days',ROUND(AVG(dias_recencia)::numeric,0),NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id AND dias_recencia IS NOT NULL
ORDER BY dimension, kpi;
$function$;

-- ----------------------------------------------------------------------------
-- get_context_metrics_for_client(uuid, text) — period-window overload
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics_v2.get_context_metrics_for_client(p_client_id uuid, p_period text)
 RETURNS TABLE(dimension text, kpi text, label text, unit text, current_value numeric, prev_month_value numeric, avg_6m numeric, mom_pct numeric, vs_6m_avg_pct numeric, streak_months integer)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public'
AS $function$
WITH
all_monthly AS (
  SELECT date_trunc('month', dd.data)::date AS mes,
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0) AS receita,
    (COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS total_pedidos,
    COALESCE(SUM(ft.quantidade) FILTER (WHERE ft.tipo_transacao = 'venda'), 0) AS quantidade,
    (COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS clientes_unicos,
    (COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra'))::numeric AS fornecedores_ativos,
    (COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric AS skus_ativos,
    CASE WHEN COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS ticket_medio,
    CASE WHEN COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN (COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda'))::numeric
              / COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS frequencia_media,
    CASE WHEN COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.customer_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS receita_por_cliente,
    CASE WHEN COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
              / COUNT(DISTINCT ft.produto_id) FILTER (WHERE ft.tipo_transacao = 'venda')
         ELSE 0 END AS receita_por_sku,
    CASE WHEN COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra') > 0
         THEN COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'compra'), 0)
              / COUNT(DISTINCT ft.fornecedor_id) FILTER (WHERE ft.tipo_transacao = 'compra')
         ELSE 0 END AS receita_por_fornecedor
  FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
  GROUP BY date_trunc('month', dd.data)::date
),
monthly_buyers AS (
  SELECT DISTINCT date_trunc('month', dd.data)::date AS mes, ft.customer_id
  FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND ft.customer_id IS NOT NULL AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
    AND ft.tipo_transacao = 'venda'
),
first_purchases AS (
  SELECT ft.customer_id, date_trunc('month', MIN(dd.data))::date AS first_month
  FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND ft.customer_id IS NOT NULL AND dd.data IS NOT NULL
    AND ft.tipo_transacao = 'venda'
  GROUP BY ft.customer_id
),
novos_por_mes AS (SELECT first_month AS mes, COUNT(*)::numeric AS clientes_novos FROM first_purchases GROUP BY first_month),
recorrentes_por_mes AS (
  SELECT a.mes, COUNT(*)::numeric AS clientes_recorrentes FROM monthly_buyers a
  JOIN monthly_buyers b ON b.customer_id = a.customer_id AND b.mes = (a.mes - INTERVAL '1 month')::date GROUP BY a.mes
),
monthly_rev_per_entity AS (
  SELECT date_trunc('month', dd.data)::date AS mes, ft.customer_id, ft.produto_id, ft.fornecedor_id, ft.valor, ft.tipo_transacao
  FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id AND dd.data IS NOT NULL AND dd.data < CURRENT_DATE
),
rev_por_cliente AS (SELECT mes, customer_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE customer_id IS NOT NULL AND tipo_transacao = 'venda' GROUP BY mes, customer_id),
rev_por_produto AS (SELECT mes, produto_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE produto_id IS NOT NULL AND tipo_transacao = 'venda' GROUP BY mes, produto_id),
rev_por_fornecedor AS (SELECT mes, fornecedor_id AS entity_id, SUM(valor) AS rev FROM monthly_rev_per_entity WHERE fornecedor_id IS NOT NULL AND tipo_transacao = 'compra' GROUP BY mes, fornecedor_id),
concentracao_top3_clientes AS (SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev),0)*100,1) AS perc FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_cliente) x GROUP BY mes),
concentracao_top3_produtos AS (SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev),0)*100,1) AS perc FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_produto) x GROUP BY mes),
concentracao_top3_fornecedores AS (SELECT mes, ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev),0)*100,1) AS perc FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk FROM rev_por_fornecedor) x GROUP BY mes),
top1_clean AS (SELECT mes, ROUND(MAX(rev) / NULLIF(SUM(rev),0)*100,1) AS concentracao_top1_perc FROM rev_por_fornecedor GROUP BY mes),
enriched AS (
  SELECT am.mes, am.receita, am.ticket_medio, am.total_pedidos, am.quantidade,
    am.clientes_unicos, am.frequencia_media, am.receita_por_cliente,
    am.skus_ativos, am.receita_por_sku, am.fornecedores_ativos, am.receita_por_fornecedor,
    COALESCE(np.clientes_novos, 0) AS clientes_novos, COALESCE(rp.clientes_recorrentes, 0) AS clientes_recorrentes,
    CASE WHEN COALESCE(am_prev.clientes_unicos,0) > 0 THEN ROUND(COALESCE(rp.clientes_recorrentes,0)/am_prev.clientes_unicos*100,1) ELSE 0 END AS taxa_recorrencia_perc,
    COALESCE(t1.concentracao_top1_perc,0) AS concentracao_top1_fornecedor_perc,
    COALESCE(c3c.perc,0) AS concentracao_top3_clientes_perc, COALESCE(c3p.perc,0) AS concentracao_top3_produtos_perc, COALESCE(c3s.perc,0) AS concentracao_top3_fornecedores_perc
  FROM all_monthly am
  LEFT JOIN all_monthly am_prev ON am_prev.mes = (am.mes - INTERVAL '1 month')::date
  LEFT JOIN novos_por_mes np ON np.mes = am.mes LEFT JOIN recorrentes_por_mes rp ON rp.mes = am.mes
  LEFT JOIN top1_clean t1 ON t1.mes = am.mes LEFT JOIN concentracao_top3_clientes c3c ON c3c.mes = am.mes
  LEFT JOIN concentracao_top3_produtos c3p ON c3p.mes = am.mes LEFT JOIN concentracao_top3_fornecedores c3s ON c3s.mes = am.mes
),
ref_month AS (SELECT COALESCE((SELECT mes FROM enriched WHERE mes = date_trunc('month', CURRENT_DATE)::date LIMIT 1),(SELECT mes FROM enriched WHERE mes < date_trunc('month', CURRENT_DATE)::date ORDER BY mes DESC LIMIT 1)) AS mes),
period_months AS (SELECT CASE p_period WHEN '90d' THEN 3 WHEN '1y' THEN 12 ELSE 1 END AS n),
current_window AS (SELECT e.* FROM enriched e, ref_month r, period_months pm WHERE e.mes <= r.mes AND e.mes > (r.mes - (pm.n || ' months')::interval)::date),
prev_window AS (SELECT e.* FROM enriched e, ref_month r, period_months pm WHERE e.mes <= (r.mes - (pm.n || ' months')::interval)::date AND e.mes > (r.mes - (pm.n*2 || ' months')::interval)::date),
current_latest AS (SELECT * FROM current_window ORDER BY mes DESC LIMIT 1),
prev_latest AS (SELECT * FROM prev_window ORDER BY mes DESC LIMIT 1),
long_current AS (
  SELECT 'receita_liquida' AS kpi, SUM(receita) AS val FROM current_window UNION ALL SELECT 'total_pedidos', SUM(total_pedidos) FROM current_window UNION ALL
  SELECT 'quantidade_vendida', SUM(quantidade) FROM current_window UNION ALL SELECT 'clientes_novos', SUM(clientes_novos) FROM current_window UNION ALL
  SELECT 'clientes_recorrentes', SUM(clientes_recorrentes) FROM current_window UNION ALL SELECT 'clientes_unicos', clientes_unicos FROM current_latest UNION ALL
  SELECT 'skus_ativos', skus_ativos FROM current_latest UNION ALL SELECT 'fornecedores_ativos', fornecedores_ativos FROM current_latest UNION ALL
  SELECT 'ticket_medio', CASE WHEN SUM(total_pedidos) > 0 THEN SUM(receita)/SUM(total_pedidos) ELSE 0 END FROM current_window UNION ALL
  SELECT 'frequencia_media', CASE WHEN MAX(clientes_unicos) > 0 THEN SUM(total_pedidos)::numeric/MAX(clientes_unicos) ELSE 0 END FROM current_window UNION ALL
  SELECT 'receita_por_cliente', CASE WHEN MAX(clientes_unicos) > 0 THEN SUM(receita)/MAX(clientes_unicos) ELSE 0 END FROM current_window UNION ALL
  SELECT 'receita_por_sku', CASE WHEN MAX(skus_ativos) > 0 THEN SUM(receita)/MAX(skus_ativos) ELSE 0 END FROM current_window UNION ALL
  SELECT 'receita_por_fornecedor', CASE WHEN MAX(fornecedores_ativos) > 0 THEN SUM(receita_por_fornecedor * fornecedores_ativos)/MAX(fornecedores_ativos) ELSE 0 END FROM current_window UNION ALL
  SELECT 'taxa_recorrencia_perc', AVG(taxa_recorrencia_perc) FROM current_window UNION ALL
  SELECT 'concentracao_top3_clientes_perc', AVG(concentracao_top3_clientes_perc) FROM current_window UNION ALL
  SELECT 'concentracao_top3_produtos_perc', AVG(concentracao_top3_produtos_perc) FROM current_window UNION ALL
  SELECT 'concentracao_top1_fornecedor_perc', AVG(concentracao_top1_fornecedor_perc) FROM current_window UNION ALL
  SELECT 'concentracao_top3_fornecedores_perc', AVG(concentracao_top3_fornecedores_perc) FROM current_window
),
long_prev AS (
  SELECT 'receita_liquida' AS kpi, SUM(receita) AS val FROM prev_window UNION ALL SELECT 'total_pedidos', SUM(total_pedidos) FROM prev_window UNION ALL
  SELECT 'quantidade_vendida', SUM(quantidade) FROM prev_window UNION ALL SELECT 'clientes_novos', SUM(clientes_novos) FROM prev_window UNION ALL
  SELECT 'clientes_recorrentes', SUM(clientes_recorrentes) FROM prev_window UNION ALL SELECT 'clientes_unicos', clientes_unicos FROM prev_latest UNION ALL
  SELECT 'skus_ativos', skus_ativos FROM prev_latest UNION ALL SELECT 'fornecedores_ativos', fornecedores_ativos FROM prev_latest UNION ALL
  SELECT 'ticket_medio', CASE WHEN SUM(total_pedidos) > 0 THEN SUM(receita)/SUM(total_pedidos) ELSE 0 END FROM prev_window UNION ALL
  SELECT 'frequencia_media', CASE WHEN MAX(clientes_unicos) > 0 THEN SUM(total_pedidos)::numeric/MAX(clientes_unicos) ELSE 0 END FROM prev_window UNION ALL
  SELECT 'receita_por_cliente', CASE WHEN MAX(clientes_unicos) > 0 THEN SUM(receita)/MAX(clientes_unicos) ELSE 0 END FROM prev_window UNION ALL
  SELECT 'receita_por_sku', CASE WHEN MAX(skus_ativos) > 0 THEN SUM(receita)/MAX(skus_ativos) ELSE 0 END FROM prev_window UNION ALL
  SELECT 'receita_por_fornecedor', CASE WHEN MAX(fornecedores_ativos) > 0 THEN SUM(receita_por_fornecedor * fornecedores_ativos)/MAX(fornecedores_ativos) ELSE 0 END FROM prev_window UNION ALL
  SELECT 'taxa_recorrencia_perc', AVG(taxa_recorrencia_perc) FROM prev_window UNION ALL
  SELECT 'concentracao_top3_clientes_perc', AVG(concentracao_top3_clientes_perc) FROM prev_window UNION ALL
  SELECT 'concentracao_top3_produtos_perc', AVG(concentracao_top3_produtos_perc) FROM prev_window UNION ALL
  SELECT 'concentracao_top1_fornecedor_perc', AVG(concentracao_top1_fornecedor_perc) FROM prev_window UNION ALL
  SELECT 'concentracao_top3_fornecedores_perc', AVG(concentracao_top3_fornecedores_perc) FROM prev_window
),
complete_months AS (SELECT e.* FROM enriched e, ref_month r WHERE e.mes < r.mes),
long_complete AS (
  SELECT mes, 'receita_liquida' AS kpi, receita AS val FROM complete_months UNION ALL SELECT mes, 'ticket_medio', ticket_medio FROM complete_months UNION ALL
  SELECT mes, 'total_pedidos', total_pedidos FROM complete_months UNION ALL SELECT mes, 'quantidade_vendida', quantidade FROM complete_months UNION ALL
  SELECT mes, 'clientes_unicos', clientes_unicos FROM complete_months UNION ALL SELECT mes, 'clientes_novos', clientes_novos FROM complete_months UNION ALL
  SELECT mes, 'clientes_recorrentes', clientes_recorrentes FROM complete_months UNION ALL SELECT mes, 'taxa_recorrencia_perc', taxa_recorrencia_perc FROM complete_months UNION ALL
  SELECT mes, 'receita_por_cliente', receita_por_cliente FROM complete_months UNION ALL SELECT mes, 'frequencia_media', frequencia_media FROM complete_months UNION ALL
  SELECT mes, 'skus_ativos', skus_ativos FROM complete_months UNION ALL SELECT mes, 'receita_por_sku', receita_por_sku FROM complete_months UNION ALL
  SELECT mes, 'fornecedores_ativos', fornecedores_ativos FROM complete_months UNION ALL SELECT mes, 'receita_por_fornecedor', receita_por_fornecedor FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top1_fornecedor_perc', concentracao_top1_fornecedor_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_clientes_perc', concentracao_top3_clientes_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_produtos_perc', concentracao_top3_produtos_perc FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_fornecedores_perc', concentracao_top3_fornecedores_perc FROM complete_months
),
ranked AS (SELECT kpi, mes, val, ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC) AS rn FROM long_complete),
avg_6m AS (SELECT kpi, ROUND(AVG(val),2) AS avg_val FROM ranked WHERE rn BETWEEN 1 AND 6 GROUP BY kpi),
with_dir AS (SELECT kpi, mes, val, SIGN(val - LAG(val) OVER (PARTITION BY kpi ORDER BY mes)) AS dir, ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC) AS rn FROM long_complete),
latest_dir AS (SELECT kpi, dir FROM with_dir WHERE rn = 1 AND dir IS NOT NULL),
streak_tagged AS (SELECT w.kpi, l.dir AS streak_dir, SUM(CASE WHEN w.dir != l.dir THEN 1 ELSE 0 END) OVER (PARTITION BY w.kpi ORDER BY w.rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS breaks FROM with_dir w JOIN latest_dir l USING (kpi) WHERE w.dir IS NOT NULL),
streak AS (SELECT kpi, (MAX(streak_dir)*COUNT(*))::integer AS streak_months FROM streak_tagged WHERE breaks = 0 GROUP BY kpi),
assembled AS (
  SELECT lc.kpi, ROUND(lc.val,2) AS current_value, ROUND(lp.val,2) AS prev_month_value, a6.avg_val AS avg_6m,
    CASE WHEN COALESCE(lp.val,0) <> 0 THEN ROUND((lc.val-lp.val)/lp.val*100,1) ELSE NULL END AS mom_pct,
    CASE WHEN COALESCE(a6.avg_val,0) <> 0 THEN ROUND((lc.val-a6.avg_val)/a6.avg_val*100,1) ELSE NULL END AS vs_6m_avg_pct,
    COALESCE(st.streak_months,0) AS streak_months
  FROM long_current lc LEFT JOIN long_prev lp USING (kpi) LEFT JOIN avg_6m a6 USING (kpi) LEFT JOIN streak st USING (kpi)
)
SELECT m.dimension, m.kpi, m.label, m.unit, a.current_value, a.prev_month_value, a.avg_6m, a.mom_pct, a.vs_6m_avg_pct, a.streak_months
FROM assembled a
JOIN (VALUES
  ('receita_liquida','finance','Receita Líquida','BRL'),('ticket_medio','finance','Ticket Médio','BRL'),
  ('total_pedidos','finance','Total de Pedidos','count'),('clientes_unicos','commercial','Clientes Únicos','count'),
  ('clientes_novos','commercial','Clientes Novos','count'),('clientes_recorrentes','commercial','Clientes Recorrentes','count'),
  ('taxa_recorrencia_perc','commercial','Taxa de Recorrência','%'),('receita_por_cliente','commercial','Receita por Cliente','BRL'),
  ('frequencia_media','commercial','Frequência Média de Compra','count'),('concentracao_top3_clientes_perc','commercial','Concentração Top 3 Clientes','%'),
  ('skus_ativos','inventory','SKUs Ativos no Mês','count'),('quantidade_vendida','inventory','Quantidade Vendida','count'),
  ('receita_por_sku','inventory','Receita por SKU Ativo','BRL'),('concentracao_top3_produtos_perc','inventory','Concentração Top 3 Produtos','%'),
  ('fornecedores_ativos','supply','Fornecedores Ativos','count'),('receita_por_fornecedor','supply','Receita por Fornecedor','BRL'),
  ('concentracao_top1_fornecedor_perc','supply','Concentração Top Fornecedor','%'),('concentracao_top3_fornecedores_perc','supply','Concentração Top 3 Fornecedores','%')
) AS m(kpi, dimension, label, unit) ON m.kpi = a.kpi
UNION ALL SELECT 'finance','receita_ytd','Receita Acumulada (YTD)','BRL',ROUND(COALESCE(SUM(ft.valor),0)::numeric,2),NULL,NULL,NULL,NULL,0
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
  AND EXTRACT(YEAR FROM dd.data) = EXTRACT(YEAR FROM CURRENT_DATE) AND dd.data < CURRENT_DATE
UNION ALL SELECT 'inventory','skus_total','Total de SKUs (catálogo)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_inventory WHERE client_id = p_client_id
UNION ALL SELECT 'commercial','clientes_base_total','Total de Clientes (base)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id
UNION ALL SELECT 'commercial','clientes_ativos_90d','Clientes Ativos (últimos 90 dias)','count',COUNT(*)::numeric,NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id AND dias_recencia IS NOT NULL AND dias_recencia <= 90
UNION ALL SELECT 'commercial','recencia_media_dias','Recência Média da Base (dias)','days',ROUND(AVG(dias_recencia)::numeric,0),NULL,NULL,NULL,NULL,0 FROM analytics_v2.dim_clientes WHERE client_id = p_client_id AND dias_recencia IS NOT NULL
ORDER BY dimension, kpi;
$function$;

-- ----------------------------------------------------------------------------
-- get_indicators_for_client — both overloads (agent/routine consumption)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics_v2.get_indicators_for_client(p_client_id uuid, p_dimension text, p_period text DEFAULT '30d'::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public'
AS $function$
DECLARE
  v_days int; v_start date; v_prev_start date; v_result jsonb := '{}'::jsonb;
  v_receita numeric; v_prev_receita numeric; v_pedidos bigint; v_ticket numeric;
  v_clientes_ativos bigint; v_novos_clientes bigint; v_recorrentes bigint;
  v_skus_ativos bigint; v_giro numeric; v_rfqs bigint; v_pos_aprovadas bigint;
BEGIN
  v_days := regexp_replace(p_period, '[^0-9]', '', 'g')::int;
  v_start := CURRENT_DATE - (v_days * INTERVAL '1 day')::interval;
  v_prev_start := v_start - (v_days * INTERVAL '1 day')::interval;

  IF p_dimension = 'finance' THEN
    SELECT COALESCE(SUM(ft.valor), 0), NULLIF(COUNT(DISTINCT ft.documento), 0)
    INTO v_receita, v_pedidos FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda' AND dd.data >= v_start;
    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;
    SELECT COALESCE(SUM(ft.valor), 0) INTO v_prev_receita FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_prev_start AND dd.data < v_start;
    v_result := jsonb_build_object('receita_liquida', v_receita, 'custo_total', NULL,
      'margem_bruta_perc', NULL, 'ticket_medio', v_ticket,
      'crescimento_receita_perc', CASE WHEN v_prev_receita > 0
        THEN ROUND(((v_receita - v_prev_receita) / v_prev_receita * 100)::numeric, 2) ELSE NULL END);

  ELSIF p_dimension = 'commercial' THEN
    SELECT COUNT(DISTINCT ft.documento), NULLIF(SUM(ft.valor), 0), COUNT(DISTINCT ft.customer_id)
    INTO v_pedidos, v_receita, v_clientes_ativos FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda' AND dd.data >= v_start;
    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;
    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id HAVING MIN(dd.data) >= v_start
    ) sub;
    SELECT COUNT(*) INTO v_recorrentes FROM (
      SELECT ft.customer_id FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda' AND dd.data >= v_start
      GROUP BY ft.customer_id HAVING COUNT(DISTINCT ft.documento) > 1
    ) sub;
    v_result := jsonb_build_object('total_pedidos', v_pedidos, 'ticket_medio', v_ticket,
      'novos_clientes', v_novos_clientes, 'clientes_ativos', v_clientes_ativos,
      'taxa_recorrencia_perc', CASE WHEN v_clientes_ativos > 0
        THEN ROUND((v_recorrentes::numeric / v_clientes_ativos * 100), 2) ELSE NULL END);

  ELSIF p_dimension = 'inventory' THEN
    SELECT COUNT(*), ROUND(AVG(frequencia_mensal), 2) INTO v_skus_ativos, v_giro
    FROM analytics_v2.dim_inventory WHERE client_id = p_client_id AND dias_recencia <= 90;
    v_result := jsonb_build_object('skus_ativos', v_skus_ativos, 'skus_sem_estoque', NULL,
      'stockout_rate_perc', NULL, 'giro_estoque', v_giro, 'dias_cobertura', NULL);

  ELSIF p_dimension = 'supply' THEN
    SELECT COUNT(DISTINCT fc.documento), COUNT(DISTINCT fc.documento) FILTER (WHERE fc.status = 'aprovado')
    INTO v_rfqs, v_pos_aprovadas FROM analytics_v2.fato_compras fc
    JOIN analytics_v2.dim_datas dd ON dd.data_id = fc.data_competencia_id
    WHERE fc.client_id = p_client_id AND dd.data >= v_start;
    v_result := jsonb_build_object('rfqs_abertas', v_rfqs, 'taxa_resposta_rfq_perc', NULL,
      'tempo_medio_resposta_h', NULL, 'pos_aprovadas', v_pos_aprovadas);

  ELSIF p_dimension = 'marketing' THEN
    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id HAVING MIN(dd.data) >= v_start
    ) sub;
    v_result := jsonb_build_object('novos_clientes', v_novos_clientes);
  END IF;
  RETURN v_result;
END; $function$;

CREATE OR REPLACE FUNCTION analytics_v2.get_indicators_for_client(p_client_id uuid, p_dimension text, p_period text DEFAULT '30d'::text, p_offset_days integer DEFAULT 0)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public'
AS $function$
DECLARE
  v_days      int;
  v_end       date;
  v_start     date;
  v_prev_start date;
  v_result    jsonb := '{}'::jsonb;

  v_receita       numeric;
  v_prev_receita  numeric;
  v_pedidos       bigint;
  v_ticket        numeric;
  v_clientes_ativos bigint;
  v_novos_clientes  bigint;
  v_recorrentes     bigint;
  v_skus_ativos   bigint;
  v_giro          numeric;
  v_rfqs          bigint;
  v_pos_aprovadas bigint;
BEGIN
  v_days       := regexp_replace(p_period, '[^0-9]', '', 'g')::int;
  v_end        := CURRENT_DATE - (p_offset_days * INTERVAL '1 day')::interval;
  v_start      := v_end      - (v_days        * INTERVAL '1 day')::interval;
  v_prev_start := v_start    - (v_days        * INTERVAL '1 day')::interval;

  IF p_dimension = 'finance' THEN
    SELECT COALESCE(SUM(ft.valor), 0), NULLIF(COUNT(DISTINCT ft.documento), 0)
    INTO v_receita, v_pedidos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data <= v_end;

    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;

    SELECT COALESCE(SUM(ft.valor), 0) INTO v_prev_receita
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_prev_start AND dd.data < v_start;

    v_result := jsonb_build_object(
      'receita_liquida',         v_receita,
      'custo_total',             NULL,
      'margem_bruta_perc',       NULL,
      'ticket_medio',            v_ticket,
      'crescimento_receita_perc', CASE WHEN v_prev_receita > 0
        THEN ROUND(((v_receita - v_prev_receita) / v_prev_receita * 100)::numeric, 2)
        ELSE NULL END
    );

  ELSIF p_dimension = 'commercial' THEN
    SELECT COUNT(DISTINCT ft.documento), NULLIF(SUM(ft.valor), 0), COUNT(DISTINCT ft.customer_id)
    INTO v_pedidos, v_receita, v_clientes_ativos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      AND dd.data >= v_start AND dd.data <= v_end;

    v_ticket := CASE WHEN v_pedidos > 0 THEN v_receita / v_pedidos ELSE NULL END;

    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id
      FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id
      HAVING MIN(dd.data) >= v_start AND MIN(dd.data) <= v_end
    ) sub;

    SELECT COUNT(*) INTO v_recorrentes FROM (
      SELECT ft.customer_id
      FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
        AND dd.data >= v_start AND dd.data <= v_end
      GROUP BY ft.customer_id
      HAVING COUNT(DISTINCT ft.documento) > 1
    ) sub;

    v_result := jsonb_build_object(
      'total_pedidos',        v_pedidos,
      'ticket_medio',         v_ticket,
      'novos_clientes',       v_novos_clientes,
      'clientes_ativos',      v_clientes_ativos,
      'taxa_recorrencia_perc', CASE WHEN v_clientes_ativos > 0
        THEN ROUND((v_recorrentes::numeric / v_clientes_ativos * 100), 2) ELSE NULL END
    );

  ELSIF p_dimension = 'inventory' THEN
    -- dim_inventory is a current-state snapshot (no time-series), offset has no effect
    SELECT COUNT(*), ROUND(AVG(frequencia_mensal), 2)
    INTO v_skus_ativos, v_giro
    FROM analytics_v2.dim_inventory
    WHERE client_id = p_client_id AND dias_recencia <= 90;

    v_result := jsonb_build_object(
      'skus_ativos',       v_skus_ativos,
      'skus_sem_estoque',  NULL,
      'stockout_rate_perc', NULL,
      'giro_estoque',      v_giro,
      'dias_cobertura',    NULL
    );

  ELSIF p_dimension = 'supply' THEN
    SELECT
      COUNT(DISTINCT fc.documento),
      COUNT(DISTINCT fc.documento) FILTER (WHERE fc.status = 'aprovado')
    INTO v_rfqs, v_pos_aprovadas
    FROM analytics_v2.fato_compras fc
    JOIN analytics_v2.dim_datas dd ON dd.data_id = fc.data_competencia_id
    WHERE fc.client_id = p_client_id
      AND dd.data >= v_start AND dd.data <= v_end;

    v_result := jsonb_build_object(
      'rfqs_abertas',           v_rfqs,
      'taxa_resposta_rfq_perc', NULL,
      'tempo_medio_resposta_h', NULL,
      'pos_aprovadas',          v_pos_aprovadas
    );

  ELSIF p_dimension = 'marketing' THEN
    SELECT COUNT(*) INTO v_novos_clientes FROM (
      SELECT ft.customer_id
      FROM analytics_v2.fato_transacoes ft
      JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
      WHERE ft.client_id = p_client_id AND ft.tipo_transacao = 'venda'
      GROUP BY ft.customer_id
      HAVING MIN(dd.data) >= v_start AND MIN(dd.data) <= v_end
    ) sub;

    v_result := jsonb_build_object('novos_clientes', v_novos_clientes);
  END IF;

  RETURN v_result;
END;
$function$;

-- ============================================================================
-- 4. get_finance_indicators — adds despesas_total (tipo_transacao = 'despesa').
--    "Despesas" in the Financeiro room previously showed custo_total (compras).
--    margem_operacional now = (receita - custo - despesas) / receita.
--    Return type changes -> DROP + CREATE (both analytics_v2 and public wrapper).
-- ============================================================================

DROP FUNCTION IF EXISTS public.get_finance_indicators(text);
DROP FUNCTION IF EXISTS analytics_v2.get_finance_indicators(text);

CREATE FUNCTION analytics_v2.get_finance_indicators(p_period text DEFAULT '30d'::text)
 RETURNS TABLE(receita_liquida numeric, custo_total numeric, despesas_total numeric, margem_bruta_perc numeric, margem_operacional_perc numeric, ticket_medio numeric, receita_yoy_perc numeric, crescimento_receita_perc numeric, total_pedidos bigint, dso_dias numeric, dpo_dias numeric, ccc_dias numeric, working_capital_ratio numeric, burn_rate_mensal numeric, runway_meses numeric, cash_flow_30d numeric, period text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'analytics_v2', 'public', 'pg_catalog'
AS $function$
DECLARE
  v_client_id   uuid    := public.get_my_client_id();
  v_start       date;
  v_prev_start  date;
  v_prev_end    date;
  v_receita     numeric := 0;
  v_custo       numeric := 0;
  v_despesas    numeric := 0;
  v_pedidos     bigint  := 0;
  v_prev_rev    numeric := 0;
  v_yoy_rev     numeric := 0;
  v_margem_bruta numeric;
  v_margem_oper  numeric;
  v_cash_30d    numeric := 0;
  v_burn        numeric := 0;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end
  INTO   v_start, v_prev_start, v_prev_end
  FROM   analytics_v2._period_range(p_period) r;

  -- Receita líquida (vendas), custo (compras), despesas + contagem de pedidos
  SELECT
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0),
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'compra'), 0),
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'despesa'), 0),
    COUNT(DISTINCT ft.transacao_id) FILTER (WHERE ft.tipo_transacao = 'venda')
  INTO v_receita, v_custo, v_despesas, v_pedidos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_start AND dd.data < CURRENT_DATE;

  -- Cash flow 30d fixo: vendas - compras - despesas
  SELECT
    COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
  - COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'compra'), 0)
  - COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'despesa'), 0)
  INTO v_cash_30d
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= (CURRENT_DATE - INTERVAL '30 days')::date
    AND dd.data < CURRENT_DATE;

  -- Burn rate mensal = média de saídas (compras + despesas) dos últimos 90 dias / 3
  SELECT COALESCE(SUM(ft.valor), 0) / 3.0
  INTO v_burn
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND ft.tipo_transacao IN ('compra', 'despesa')
    AND dd.data >= (CURRENT_DATE - INTERVAL '90 days')::date
    AND dd.data < CURRENT_DATE;

  -- Receita período anterior
  SELECT COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
  INTO v_prev_rev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_prev_start AND dd.data < v_prev_end;

  -- Receita YoY
  SELECT COALESCE(SUM(ft.valor) FILTER (WHERE ft.tipo_transacao = 'venda'), 0)
  INTO v_yoy_rev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= (v_start - INTERVAL '1 year')::date
    AND dd.data <  (CURRENT_DATE - INTERVAL '1 year')::date;

  v_margem_bruta := CASE WHEN v_receita > 0
    THEN ROUND((v_receita - v_custo) / v_receita * 100, 1)
    ELSE NULL END;

  v_margem_oper := CASE WHEN v_receita > 0
    THEN ROUND((v_receita - v_custo - v_despesas) / v_receita * 100, 1)
    ELSE NULL END;

  RETURN QUERY SELECT
    v_receita,
    v_custo,
    v_despesas,
    v_margem_bruta,
    v_margem_oper,
    CASE WHEN v_pedidos > 0 THEN ROUND(v_receita / v_pedidos, 2) ELSE 0 END,
    CASE WHEN v_yoy_rev  > 0 THEN ROUND((v_receita - v_yoy_rev)  / v_yoy_rev  * 100, 1) ELSE NULL END,
    CASE WHEN v_prev_rev > 0 THEN ROUND((v_receita - v_prev_rev) / v_prev_rev * 100, 1) ELSE NULL END,
    v_pedidos,
    NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric,
    ROUND(v_burn, 2),
    CASE WHEN v_burn > 0 THEN ROUND(v_cash_30d / v_burn, 1) ELSE NULL END,
    ROUND(v_cash_30d, 2),
    p_period;
END;
$function$;

CREATE FUNCTION public.get_finance_indicators(p_period text DEFAULT '30d'::text)
 RETURNS TABLE(receita_liquida numeric, custo_total numeric, despesas_total numeric, margem_bruta_perc numeric, margem_operacional_perc numeric, ticket_medio numeric, receita_yoy_perc numeric, crescimento_receita_perc numeric, total_pedidos bigint, dso_dias numeric, dpo_dias numeric, ccc_dias numeric, working_capital_ratio numeric, burn_rate_mensal numeric, runway_meses numeric, cash_flow_30d numeric, period text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public', 'analytics_v2'
AS $function$
  SELECT * FROM analytics_v2.get_finance_indicators(p_period);
$function$;

GRANT EXECUTE ON FUNCTION analytics_v2.get_finance_indicators(text) TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.get_finance_indicators(text)       TO anon, authenticated, service_role;

-- ============================================================================
-- 5. public helper functions (routines/agents)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_revenue_monthly_rate(p_client_id uuid, p_window_months integer DEFAULT 1)
 RETURNS TABLE(current_month_revenue numeric, avg_monthly_revenue numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'analytics_v2'
AS $function$
DECLARE
  v_current numeric;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  SELECT COALESCE(SUM(ft.valor), 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND ft.tipo_transacao = 'venda'
     AND dd.ano  = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes  = EXTRACT(MONTH FROM v_now)::integer;

  SELECT COALESCE(AVG(monthly_total), 0)
    INTO v_avg
    FROM (
      SELECT dd.ano, dd.mes, SUM(ft.valor) AS monthly_total
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND ft.tipo_transacao = 'venda'
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_month_revenue := v_current;
  avg_monthly_revenue   := ROUND(COALESCE(v_avg, 0), 2);

  RETURN NEXT;
END;
$function$;

CREATE OR REPLACE FUNCTION public.get_ticket_medio_monthly_rate(p_client_id uuid, p_window_months integer DEFAULT 1)
 RETURNS TABLE(current_ticket numeric, avg_ticket numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'analytics_v2'
AS $function$
DECLARE
  v_current numeric;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  SELECT COALESCE(
           CASE WHEN COUNT(DISTINCT ft.transacao_id) = 0 THEN 0
                ELSE SUM(ft.valor) / COUNT(DISTINCT ft.transacao_id)
           END, 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND ft.tipo_transacao = 'venda'
     AND dd.ano = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_now)::integer;

  SELECT COALESCE(AVG(monthly_ticket), 0)
    INTO v_avg
    FROM (
      SELECT dd.ano, dd.mes,
             CASE WHEN COUNT(DISTINCT ft.transacao_id) = 0 THEN 0
                  ELSE SUM(ft.valor) / COUNT(DISTINCT ft.transacao_id)
             END AS monthly_ticket
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND ft.tipo_transacao = 'venda'
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_ticket := ROUND(COALESCE(v_current, 0), 2);
  avg_ticket     := ROUND(COALESCE(v_avg,     0), 2);

  RETURN NEXT;
END;
$function$;

-- Churn: previously counted transacao_id (transaction IDs never repeat across
-- months, so churn was always 100%). Now tracks customer_id on vendas.
CREATE OR REPLACE FUNCTION public.get_churn_rate_monthly(p_client_id uuid, p_window_months integer DEFAULT 1)
 RETURNS TABLE(current_churn_rate numeric, avg_churn_rate numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'analytics_v2'
AS $function$
DECLARE
  v_current_rate numeric;
  v_avg_rate     numeric;
  v_now          date := date_trunc('month', now())::date;
  v_prev_month   date := (v_now - interval '1 month')::date;

  v_active_last_month  bigint;
  v_churned_this_month bigint;
BEGIN
  SELECT COUNT(DISTINCT ft.customer_id)
    INTO v_active_last_month
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND ft.tipo_transacao = 'venda'
     AND ft.customer_id IS NOT NULL
     AND dd.ano = EXTRACT(YEAR  FROM v_prev_month)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_prev_month)::integer;

  IF v_active_last_month = 0 THEN
    current_churn_rate := 0;
    avg_churn_rate     := 0;
    RETURN NEXT;
    RETURN;
  END IF;

  SELECT COUNT(DISTINCT prev_buyers.customer_id)
    INTO v_churned_this_month
    FROM (
      SELECT DISTINCT ft.customer_id
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND ft.tipo_transacao = 'venda'
         AND ft.customer_id IS NOT NULL
         AND dd.ano = EXTRACT(YEAR  FROM v_prev_month)::integer
         AND dd.mes = EXTRACT(MONTH FROM v_prev_month)::integer
    ) prev_buyers
   WHERE prev_buyers.customer_id NOT IN (
      SELECT DISTINCT ft2.customer_id
        FROM analytics_v2.fato_transacoes ft2
        JOIN analytics_v2.dim_datas        dd2 ON dd2.data_id = ft2.data_competencia_id
       WHERE ft2.client_id = p_client_id
         AND ft2.tipo_transacao = 'venda'
         AND ft2.customer_id IS NOT NULL
         AND dd2.ano = EXTRACT(YEAR  FROM v_now)::integer
         AND dd2.mes = EXTRACT(MONTH FROM v_now)::integer
   );

  v_current_rate := ROUND(v_churned_this_month::numeric / v_active_last_month, 4);

  WITH month_series AS (
    SELECT generate_series(1, p_window_months) AS offset_n
  ),
  month_pairs AS (
    SELECT
      (v_now - (offset_n       || ' months')::interval)::date AS m_current,
      (v_now - ((offset_n + 1) || ' months')::interval)::date AS m_prev
    FROM month_series
  ),
  monthly_churn AS (
    SELECT
      mp.m_current,
      mp.m_prev,
      COALESCE(
        (
          SELECT COUNT(DISTINCT prev_t.customer_id)
            FROM analytics_v2.fato_transacoes prev_t
            JOIN analytics_v2.dim_datas        prev_dd ON prev_dd.data_id = prev_t.data_competencia_id
           WHERE prev_t.client_id = p_client_id
             AND prev_t.tipo_transacao = 'venda'
             AND prev_t.customer_id IS NOT NULL
             AND prev_dd.ano = EXTRACT(YEAR  FROM mp.m_prev)::integer
             AND prev_dd.mes = EXTRACT(MONTH FROM mp.m_prev)::integer
        ), 0) AS base_count,
      COALESCE(
        (
          SELECT COUNT(DISTINCT prev_t.customer_id)
            FROM analytics_v2.fato_transacoes prev_t
            JOIN analytics_v2.dim_datas        prev_dd ON prev_dd.data_id = prev_t.data_competencia_id
           WHERE prev_t.client_id = p_client_id
             AND prev_t.tipo_transacao = 'venda'
             AND prev_t.customer_id IS NOT NULL
             AND prev_dd.ano = EXTRACT(YEAR  FROM mp.m_prev)::integer
             AND prev_dd.mes = EXTRACT(MONTH FROM mp.m_prev)::integer
             AND prev_t.customer_id NOT IN (
               SELECT DISTINCT cur_t.customer_id
                 FROM analytics_v2.fato_transacoes cur_t
                 JOIN analytics_v2.dim_datas        cur_dd ON cur_dd.data_id = cur_t.data_competencia_id
                WHERE cur_t.client_id = p_client_id
                  AND cur_t.tipo_transacao = 'venda'
                  AND cur_t.customer_id IS NOT NULL
                  AND cur_dd.ano = EXTRACT(YEAR  FROM mp.m_current)::integer
                  AND cur_dd.mes = EXTRACT(MONTH FROM mp.m_current)::integer
             )
        ), 0) AS churned_count
    FROM month_pairs mp
  )
  SELECT COALESCE(AVG(
    CASE WHEN base_count = 0 THEN 0
         ELSE churned_count::numeric / base_count
    END), 0)
    INTO v_avg_rate
    FROM monthly_churn;

  current_churn_rate := v_current_rate;
  avg_churn_rate     := ROUND(COALESCE(v_avg_rate, 0), 4);

  RETURN NEXT;
END;
$function$;

CREATE OR REPLACE FUNCTION public.get_commercial_top_clients()
 RETURNS TABLE(client_id bigint, cliente_nome text, total_volume numeric, total_revenue numeric, last_purchase timestamp with time zone)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  RETURN QUERY
  SELECT
    dc.customer_id,
    dc.nome::TEXT,
    COUNT(ft.transacao_id)::NUMERIC AS total_volume,
    SUM(ft.valor)::NUMERIC          AS total_revenue,
    MAX(ft.created_at)              AS last_purchase
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_clientes dc
    ON ft.customer_id = dc.customer_id
   AND ft.client_id   = dc.client_id
  WHERE ft.client_id = public.get_my_client_id()
    AND ft.tipo_transacao = 'venda'
  GROUP BY dc.customer_id, dc.nome
  ORDER BY total_revenue DESC
  LIMIT 10;
END;
$function$;

-- Previously referenced nonexistent columns (channel/valor_total/data_transacao)
-- and errored at runtime. Rebuilt on real columns: status as channel, vendas only.
CREATE OR REPLACE FUNCTION public.get_commercial_revenue_by_channel()
 RETURNS TABLE(channel text, total_revenue numeric, transaction_count integer, avg_transaction_value numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
BEGIN
  RETURN QUERY
  SELECT
    COALESCE(ft.status, 'sem_status')::TEXT AS channel,
    SUM(ft.valor)::NUMERIC                  AS total_revenue,
    COUNT(*)::INT                           AS transaction_count,
    AVG(ft.valor)::NUMERIC                  AS avg_transaction_value
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
  WHERE ft.client_id = public.get_my_client_id()
    AND ft.tipo_transacao = 'venda'
    AND dd.data >= (CURRENT_DATE - INTERVAL '90 days')::date
  GROUP BY ft.status
  ORDER BY total_revenue DESC;
END;
$function$;

CREATE OR REPLACE FUNCTION public.get_recent_transactions(p_client_id uuid, p_limit integer DEFAULT 10)
 RETURNS TABLE(id text, customer_id bigint, nome text, descricao text, valor numeric, data timestamp with time zone, status text)
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'public', 'analytics_v2'
AS $function$
  SELECT
    ft.transacao_id,
    ft.customer_id,
    COALESCE(dc.nome, 'Cliente')        AS nome,
    COALESCE(ft.documento, 'Transação') AS descricao,
    ft.valor,
    ft.created_at                       AS data,
    ft.status
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_clientes dc
    ON dc.customer_id = ft.customer_id
   AND dc.client_id   = ft.client_id
  WHERE ft.client_id = p_client_id
    AND ft.tipo_transacao = 'venda'
  ORDER BY ft.created_at DESC
  LIMIT p_limit;
$function$;

-- ============================================================================
-- 6. Reprocess dim aggregates for every client and refresh the MVs
-- ============================================================================

DO $$
DECLARE
  v_client uuid;
BEGIN
  FOR v_client IN SELECT DISTINCT ft.client_id FROM analytics_v2.fato_transacoes ft LOOP
    PERFORM analytics_v2.atualizar_dim_clientes(v_client);
    PERFORM analytics_v2.atualizar_dim_fornecedores(v_client);
    PERFORM analytics_v2.atualizar_dim_inventory(v_client);
  END LOOP;
END $$;

REFRESH MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard;
REFRESH MATERIALIZED VIEW analytics_v2.mv_series_temporal;
REFRESH MATERIALIZED VIEW analytics_v2.mv_ultimos_pedidos;
REFRESH MATERIALIZED VIEW analytics_v2.mv_distribuicao_regional;

COMMIT;
