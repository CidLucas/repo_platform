-- Migration: analytics_v2 RPCs powering the Pedidos dashboard page
-- Date: 2026-04-23
-- Phase: Dashboard mocks → live data, Phase 1
--
-- Adds three SECURITY INVOKER RPCs that read the slim analytics_v2.fato_transacoes
-- (13-col schema) and are scoped via public.get_my_client_id():
--   * get_order_indicators(period)         — total, revenue, avg_order_value, growth_rate
--   * get_order_status_breakdown(period)   — first real read of fato_transacoes.status
--   * get_pedidos_overview_scorecards()    — qtd média / recorrência / recência

-- ─────────────────────────────────────────────────────────────────────
-- Helper: map a period code to an interval (week/month/quarter/year)
-- Inlined as CASE expressions inside each RPC to keep things STABLE.
-- ─────────────────────────────────────────────────────────────────────

-- ── 1. get_order_indicators ──────────────────────────────────────────
CREATE OR REPLACE FUNCTION analytics_v2.get_order_indicators(
  p_period text DEFAULT 'month'
)
RETURNS TABLE (
  total            bigint,
  revenue          numeric,
  avg_order_value  numeric,
  growth_rate      numeric,
  period           text
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
      COUNT(DISTINCT ft.documento)::bigint AS total,
      COALESCE(SUM(ft.valor), 0)::numeric  AS revenue
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    CROSS JOIN params p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= (now()::date - p.window_size)
  ),
  previous_window AS (
    SELECT
      COALESCE(SUM(ft.valor), 0)::numeric AS revenue
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    CROSS JOIN params p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= (now()::date - (p.window_size * 2))
      AND dd.data <  (now()::date - p.window_size)
  )
  SELECT
    cw.total,
    cw.revenue,
    CASE WHEN cw.total > 0 THEN ROUND(cw.revenue / cw.total, 2) ELSE 0 END AS avg_order_value,
    CASE
      WHEN pw.revenue > 0 THEN ROUND(((cw.revenue - pw.revenue) / pw.revenue) * 100, 2)
      ELSE 0
    END AS growth_rate,
    (SELECT period_code FROM params) AS period
  FROM current_window cw CROSS JOIN previous_window pw;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.get_order_indicators(text) TO authenticated;

-- ── 2. get_order_status_breakdown ────────────────────────────────────
CREATE OR REPLACE FUNCTION analytics_v2.get_order_status_breakdown(
  p_period text DEFAULT 'month'
)
RETURNS TABLE (
  status text,
  count  bigint
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH params AS (
    SELECT
      CASE lower(p_period)
        WHEN 'week'    THEN interval '7 days'
        WHEN 'month'   THEN interval '30 days'
        WHEN 'quarter' THEN interval '90 days'
        WHEN 'year'    THEN interval '365 days'
        ELSE interval '30 days'
      END AS window_size
  )
  SELECT
    COALESCE(NULLIF(trim(ft.status), ''), 'unknown') AS status,
    COUNT(DISTINCT ft.documento)::bigint              AS count
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  CROSS JOIN params p
  WHERE ft.client_id = public.get_my_client_id()
    AND dd.data >= (now()::date - p.window_size)
  GROUP BY 1
  ORDER BY 2 DESC;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.get_order_status_breakdown(text) TO authenticated;

-- ── 3. get_pedidos_overview_scorecards ───────────────────────────────
-- Returns a single row with three scorecards used at the top of PedidosPage.
--   * qtd_media_produtos_por_pedido — distinct produto_id per documento, avg
--   * taxa_recorrencia_clientes_perc — % of customers with > 1 order
--   * recencia_media_entre_pedidos_dias — median day-diff between consecutive
--     orders per customer (using lag()), averaged across customers.
CREATE OR REPLACE FUNCTION analytics_v2.get_pedidos_overview_scorecards()
RETURNS TABLE (
  qtd_media_produtos_por_pedido      numeric,
  taxa_recorrencia_clientes_perc     numeric,
  recencia_media_entre_pedidos_dias  numeric
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH base AS (
    SELECT
      ft.cliente_id,
      ft.documento,
      ft.produto_id,
      dd.data
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = public.get_my_client_id()
      AND ft.documento IS NOT NULL
  ),
  produtos_por_pedido AS (
    SELECT documento,
           COUNT(DISTINCT produto_id) FILTER (WHERE produto_id IS NOT NULL) AS qtd
    FROM base
    GROUP BY documento
  ),
  qtd_media AS (
    SELECT ROUND(COALESCE(AVG(qtd), 0)::numeric, 2) AS v
    FROM produtos_por_pedido
  ),
  pedidos_por_cliente AS (
    SELECT cliente_id, COUNT(DISTINCT documento) AS pedidos
    FROM base
    WHERE cliente_id IS NOT NULL
    GROUP BY cliente_id
  ),
  recorrencia AS (
    SELECT ROUND(
             COALESCE(
               100.0 * (COUNT(*) FILTER (WHERE pedidos > 1))::numeric
                       / NULLIF(COUNT(*), 0),
               0
             ),
             2
           ) AS v
    FROM pedidos_por_cliente
  ),
  ordered_orders AS (
    SELECT cliente_id, documento, MIN(data) AS data_pedido
    FROM base
    WHERE cliente_id IS NOT NULL
    GROUP BY cliente_id, documento
  ),
  diffs AS (
    SELECT (data_pedido - LAG(data_pedido) OVER (PARTITION BY cliente_id ORDER BY data_pedido)) AS gap_days
    FROM ordered_orders
  ),
  recencia AS (
    SELECT ROUND(COALESCE(AVG(gap_days), 0)::numeric, 1) AS v
    FROM diffs
    WHERE gap_days IS NOT NULL
  )
  SELECT
    (SELECT v FROM qtd_media)   AS qtd_media_produtos_por_pedido,
    (SELECT v FROM recorrencia) AS taxa_recorrencia_clientes_perc,
    COALESCE((SELECT v FROM recencia), 0) AS recencia_media_entre_pedidos_dias;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.get_pedidos_overview_scorecards() TO authenticated;

COMMENT ON FUNCTION analytics_v2.get_order_indicators(text) IS
  'Dashboard PedidosPage scorecards. Period: week|month|quarter|year. RLS-scoped via public.get_my_client_id().';
COMMENT ON FUNCTION analytics_v2.get_order_status_breakdown(text) IS
  'Dashboard PedidosPage status header. Reads fato_transacoes.status. RLS-scoped.';
COMMENT ON FUNCTION analytics_v2.get_pedidos_overview_scorecards() IS
  'Dashboard PedidosPage overview KPIs (qtd média / recorrência / recência). RLS-scoped.';
