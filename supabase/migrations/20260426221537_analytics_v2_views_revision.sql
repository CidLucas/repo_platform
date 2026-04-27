-- Migration: analytics_v2 views/MVs revision
-- Date: 2026-04-26
--
-- Fixes discovered in Phase 1 audit (see /memories/session/plan.md):
--   1. mv_resumo_dashboard had no UNIQUE index → REFRESH CONCURRENTLY
--      failed nightly since 2026-04-24, leaving every downstream MV stale.
--   2. v_resumo_dashboard was missing the RLS WHERE clause that the other
--      three v_* views all carry — multi-tenant leakage.
--   3. ticket_medio was avg(valor) over fato lines (~R$9k) instead of
--      per-order (~R$19k); UI label "Ticket Médio" is per-order.
--   4. receita_mes_atual / crescimento_* used a rolling 30-day window;
--      UI label is "mês atual" → switch to calendar-month-vs-previous.
--   5. anon role had SELECT on the 4 v_* views; dashboard requires login.
--
-- Adds analytics_v2.get_dashboard_indicators(p_period) for the period
-- toggle on HomePage (rolling-window KPIs), mirroring the existing
-- get_order_indicators(p_period) RPC pattern.

BEGIN;

-- ─────────────────────────────────────────────────────────────────────
-- 1. Recreate mv_resumo_dashboard with correct semantics + UNIQUE index
-- ─────────────────────────────────────────────────────────────────────

DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_dashboard CASCADE;

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard AS
WITH current_month AS (
  SELECT
    ft.client_id,
    sum(ft.valor)                            AS receita,
    sum(ft.quantidade)                       AS quantidade,
    count(DISTINCT ft.cliente_id)            AS clientes_unicos,
    count(DISTINCT ft.produto_id)            AS produtos_unicos,
    count(DISTINCT ft.fornecedor_id)         AS fornecedores_unicos,
    count(DISTINCT ft.documento)             AS pedidos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= date_trunc('month', CURRENT_DATE)::date
    AND dd.data <  (date_trunc('month', CURRENT_DATE) + interval '1 month')::date
  GROUP BY ft.client_id
),
previous_month AS (
  SELECT
    ft.client_id,
    sum(ft.valor)                            AS receita,
    sum(ft.quantidade)                       AS quantidade,
    count(DISTINCT ft.cliente_id)            AS clientes_unicos,
    count(DISTINCT ft.produto_id)            AS produtos_unicos,
    count(DISTINCT ft.documento)             AS pedidos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= (date_trunc('month', CURRENT_DATE) - interval '1 month')::date
    AND dd.data <  date_trunc('month', CURRENT_DATE)::date
  GROUP BY ft.client_id
),
client_agg AS (
  SELECT
    c.client_id,
    count(*)                                                              AS total_clientes,
    count(*) FILTER (WHERE c.dias_recencia <= 90)                         AS clientes_ativos,
    count(*) FILTER (WHERE c.total_pedidos = 1)                           AS clientes_novos,
    count(DISTINCT c.endereco_uf) FILTER (WHERE c.endereco_uf IS NOT NULL) AS total_regioes
  FROM analytics_v2.dim_clientes c
  GROUP BY c.client_id
),
fornecedor_agg AS (
  SELECT
    f.client_id,
    count(*)                                          AS total_fornecedores,
    COALESCE(avg(f.frequencia_mensal), 0)::numeric    AS frequencia_media_fornecedores
  FROM analytics_v2.dim_fornecedores f
  GROUP BY f.client_id
),
inventory_agg AS (
  SELECT
    i.client_id,
    count(*)                                                AS total_produtos,
    COALESCE(sum(i.quantidade_total_vendida), 0)::numeric   AS quantidade_total_vendida
  FROM analytics_v2.dim_inventory i
  GROUP BY i.client_id
),
fact_agg AS (
  SELECT
    ft.client_id,
    count(DISTINCT ft.documento)                                                              AS total_pedidos,
    COALESCE(sum(ft.valor), 0)::numeric                                                       AS receita_total,
    -- Per-order ticket: sum(valor) / count(distinct documento). Replaces the
    -- previous avg(valor) which averaged transaction LINES, not orders.
    CASE
      WHEN count(DISTINCT ft.documento) > 0
      THEN (sum(ft.valor) / count(DISTINCT ft.documento))::numeric(15, 2)
      ELSE 0::numeric
    END                                                                                       AS ticket_medio
  FROM analytics_v2.fato_transacoes ft
  GROUP BY ft.client_id
)
SELECT
  cl.client_id,
  COALESCE(ca.total_clientes,             0)::bigint   AS total_clientes,
  COALESCE(fa2.total_fornecedores,        0)::bigint   AS total_fornecedores,
  COALESCE(ia.total_produtos,             0)::bigint   AS total_produtos,
  COALESCE(fa.total_pedidos,              0)::bigint   AS total_pedidos,
  COALESCE(fa.receita_total,              0)::numeric  AS receita_total,
  COALESCE(fa.ticket_medio,               0)::numeric  AS ticket_medio,
  COALESCE(ia.quantidade_total_vendida,   0)::numeric  AS quantidade_total_vendida,
  COALESCE(cm.receita,                    0)::numeric  AS receita_mes_atual,
  COALESCE(cm.quantidade,                 0)::numeric  AS quantidade_mes_atual,
  COALESCE(cm.clientes_unicos,            0)::bigint   AS clientes_mes_atual,
  COALESCE(cm.produtos_unicos,            0)::bigint   AS produtos_mes_atual,
  COALESCE(cm.fornecedores_unicos,        0)::bigint   AS fornecedores_mes_atual,
  CASE
    WHEN COALESCE(pm.receita, 0)         > 0
    THEN (((COALESCE(cm.receita, 0)         - pm.receita)         / pm.receita)         * 100)::numeric(10, 2)
    ELSE NULL::numeric
  END AS crescimento_receita,
  CASE
    WHEN COALESCE(pm.clientes_unicos, 0) > 0
    THEN (((COALESCE(cm.clientes_unicos, 0)::numeric - pm.clientes_unicos::numeric) / pm.clientes_unicos::numeric) * 100)::numeric(10, 2)
    ELSE NULL::numeric
  END AS crescimento_clientes,
  CASE
    WHEN COALESCE(pm.produtos_unicos, 0) > 0
    THEN (((COALESCE(cm.produtos_unicos, 0)::numeric - pm.produtos_unicos::numeric) / pm.produtos_unicos::numeric) * 100)::numeric(10, 2)
    ELSE NULL::numeric
  END AS crescimento_produtos,
  CASE
    WHEN COALESCE(pm.quantidade, 0)      > 0
    THEN (((COALESCE(cm.quantidade, 0)      - pm.quantidade)      / pm.quantidade)      * 100)::numeric(10, 2)
    ELSE NULL::numeric
  END AS crescimento_quantidade,
  COALESCE(fa2.frequencia_media_fornecedores, 0)::numeric AS frequencia_media_fornecedores,
  COALESCE(ca.total_regioes,              0)::bigint   AS total_regioes,
  to_char(CURRENT_DATE::timestamptz, 'YYYY-MM')        AS ultimo_mes,
  COALESCE(ca.clientes_ativos,            0)::bigint   AS clientes_ativos,
  COALESCE(ca.clientes_novos,             0)::bigint   AS clientes_novos,
  now()                                                AS gerado_em
FROM (SELECT DISTINCT ft.client_id FROM analytics_v2.fato_transacoes ft) cl
LEFT JOIN current_month   cm  ON cm.client_id  = cl.client_id
LEFT JOIN previous_month  pm  ON pm.client_id  = cl.client_id
LEFT JOIN client_agg      ca  ON ca.client_id  = cl.client_id
LEFT JOIN fornecedor_agg  fa2 ON fa2.client_id = cl.client_id
LEFT JOIN inventory_agg   ia  ON ia.client_id  = cl.client_id
LEFT JOIN fact_agg        fa  ON fa.client_id  = cl.client_id;

-- UNIQUE index — required for REFRESH MATERIALIZED VIEW CONCURRENTLY.
CREATE UNIQUE INDEX ux_mv_resumo_dashboard_client
  ON analytics_v2.mv_resumo_dashboard (client_id);

-- ─────────────────────────────────────────────────────────────────────
-- 2. Recreate v_resumo_dashboard WITH the missing RLS WHERE clause
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW analytics_v2.v_resumo_dashboard
  WITH (security_invoker = true) AS
SELECT
  client_id,
  total_clientes,
  total_fornecedores,
  total_produtos,
  total_pedidos,
  receita_total,
  ticket_medio,
  quantidade_total_vendida,
  receita_mes_atual,
  quantidade_mes_atual,
  clientes_mes_atual,
  produtos_mes_atual,
  fornecedores_mes_atual,
  crescimento_receita,
  crescimento_clientes,
  crescimento_produtos,
  crescimento_quantidade,
  frequencia_media_fornecedores,
  total_regioes,
  ultimo_mes,
  clientes_ativos,
  clientes_novos,
  gerado_em
FROM analytics_v2.mv_resumo_dashboard
WHERE client_id = public.get_my_client_id();

-- ─────────────────────────────────────────────────────────────────────
-- 3. GRANTs — authenticated only; revoke anon (dashboard requires login)
-- ─────────────────────────────────────────────────────────────────────

REVOKE SELECT ON analytics_v2.v_resumo_dashboard      FROM anon;
REVOKE SELECT ON analytics_v2.v_series_temporal       FROM anon;
REVOKE SELECT ON analytics_v2.v_distribuicao_regional FROM anon;
REVOKE SELECT ON analytics_v2.v_ultimos_pedidos       FROM anon;

GRANT  SELECT ON analytics_v2.v_resumo_dashboard      TO authenticated;
GRANT  SELECT ON analytics_v2.v_series_temporal       TO authenticated;
GRANT  SELECT ON analytics_v2.v_distribuicao_regional TO authenticated;
GRANT  SELECT ON analytics_v2.v_ultimos_pedidos       TO authenticated;

-- security_invoker views need underlying-MV access for the caller.
GRANT SELECT ON analytics_v2.mv_resumo_dashboard      TO authenticated;
GRANT SELECT ON analytics_v2.mv_series_temporal       TO authenticated;
GRANT SELECT ON analytics_v2.mv_distribuicao_regional TO authenticated;

-- ─────────────────────────────────────────────────────────────────────
-- 4. Period-toggle RPC for HomePage — rolling-window KPIs
--    Mirrors analytics_v2.get_order_indicators(p_period) (2026-04-23).
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.get_dashboard_indicators(
  p_period text DEFAULT 'month'
)
RETURNS TABLE (
  total_pedidos          bigint,
  receita                numeric,
  ticket_medio           numeric,
  quantidade             numeric,
  clientes_unicos        bigint,
  produtos_unicos        bigint,
  fornecedores_unicos    bigint,
  crescimento_receita    numeric,
  crescimento_pedidos    numeric,
  crescimento_clientes   numeric,
  period                 text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH params AS (
    SELECT
      p_period AS period_code,
      CASE lower(p_period)
        WHEN 'week'    THEN interval '7 days'
        WHEN 'month'   THEN interval '30 days'
        WHEN 'quarter' THEN interval '90 days'
        WHEN 'year'    THEN interval '365 days'
        ELSE interval '30 days'
      END AS window_size
  ),
  current_window AS (
    SELECT
      count(DISTINCT ft.documento)::bigint               AS total_pedidos,
      COALESCE(sum(ft.valor),       0)::numeric          AS receita,
      COALESCE(sum(ft.quantidade),  0)::numeric          AS quantidade,
      count(DISTINCT ft.cliente_id)::bigint              AS clientes_unicos,
      count(DISTINCT ft.produto_id)::bigint              AS produtos_unicos,
      count(DISTINCT ft.fornecedor_id)::bigint           AS fornecedores_unicos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    CROSS JOIN params p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= (now()::date - p.window_size)
  ),
  previous_window AS (
    SELECT
      count(DISTINCT ft.documento)::bigint     AS total_pedidos,
      COALESCE(sum(ft.valor), 0)::numeric      AS receita,
      count(DISTINCT ft.cliente_id)::bigint    AS clientes_unicos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    CROSS JOIN params p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= (now()::date - (p.window_size * 2))
      AND dd.data <  (now()::date - p.window_size)
  )
  SELECT
    cw.total_pedidos,
    cw.receita,
    CASE WHEN cw.total_pedidos > 0
         THEN (cw.receita / cw.total_pedidos)::numeric(15, 2)
         ELSE 0::numeric END                        AS ticket_medio,
    cw.quantidade,
    cw.clientes_unicos,
    cw.produtos_unicos,
    cw.fornecedores_unicos,
    CASE WHEN pw.receita > 0
         THEN round(((cw.receita - pw.receita) / pw.receita) * 100, 2)
         ELSE NULL::numeric END                     AS crescimento_receita,
    CASE WHEN pw.total_pedidos > 0
         THEN round(((cw.total_pedidos - pw.total_pedidos)::numeric / pw.total_pedidos) * 100, 2)
         ELSE NULL::numeric END                     AS crescimento_pedidos,
    CASE WHEN pw.clientes_unicos > 0
         THEN round(((cw.clientes_unicos - pw.clientes_unicos)::numeric / pw.clientes_unicos) * 100, 2)
         ELSE NULL::numeric END                     AS crescimento_clientes,
    (SELECT period_code FROM params)                AS period
  FROM current_window cw CROSS JOIN previous_window pw;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.get_dashboard_indicators(text) TO authenticated;

COMMENT ON FUNCTION analytics_v2.get_dashboard_indicators(text) IS
  'Home dashboard period-toggle KPIs over a rolling window (week|month|quarter|year). Returns current-window aggregates plus growth vs the prior equal-length window. Scoped to public.get_my_client_id().';

-- ─────────────────────────────────────────────────────────────────────
-- 5. Refresh the now-fixed MV chain so production data is current
-- ─────────────────────────────────────────────────────────────────────

REFRESH MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard;
SELECT analytics_v2.refresh_all_materialized_views();

COMMIT;
