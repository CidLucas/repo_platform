-- Fix: DATE_PART('day', date - date) não funciona em PG pois date-date retorna integer, não interval.
-- Substituído por (date - date)::numeric que já é em dias.

CREATE OR REPLACE FUNCTION analytics_v2.get_commercial_indicators(p_period text)
RETURNS TABLE(
  total_pedidos           bigint,
  receita                 numeric,
  ticket_medio            numeric,
  clientes_unicos         bigint,
  clientes_novos          bigint,
  clientes_recorrentes    bigint,
  recencia_media_dias     numeric,
  frequencia_media_mensal numeric,
  churn_60d_perc          numeric,
  crescimento_receita_pct numeric,
  n1 numeric, n2 numeric, n3 numeric, n4 numeric, n5 numeric, n6 numeric,
  periodo text
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'analytics_v2', 'public'
AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_start date; v_prev_start date; v_prev_end date;
  v_pedidos bigint := 0; v_receita numeric := 0; v_prev_rev numeric := 0;
  v_clientes_unicos bigint := 0; v_clientes_novos bigint := 0;
  v_recencia numeric := 0; v_frequencia numeric := 0;
  v_churn numeric := 0;
  v_m1 numeric := 0; v_m2 numeric := 0; v_m3 numeric := 0;
  v_m4 numeric := 0; v_m5 numeric := 0; v_m6 numeric := 0;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end
  INTO v_start, v_prev_start, v_prev_end
  FROM analytics_v2._period_range(p_period) r;

  SELECT
    COUNT(DISTINCT ft.transacao_id),
    COALESCE(SUM(ft.valor), 0),
    COUNT(DISTINCT ft.customer_id)
  INTO v_pedidos, v_receita, v_clientes_unicos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND ft.tipo_transacao = 'venda'
    AND ft.customer_id IS NOT NULL
    AND dd.data >= v_start AND dd.data < CURRENT_DATE;

  SELECT COUNT(DISTINCT ft.customer_id)
  INTO v_clientes_novos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND ft.tipo_transacao = 'venda'
    AND ft.customer_id IS NOT NULL
    AND dd.data >= v_start AND dd.data < CURRENT_DATE
    AND NOT EXISTS (
      SELECT 1 FROM analytics_v2.fato_transacoes ft2
      JOIN analytics_v2.dim_datas dd2 ON ft2.data_competencia_id = dd2.data_id
      WHERE ft2.client_id = v_client_id
        AND ft2.tipo_transacao = 'venda'
        AND ft2.customer_id = ft.customer_id
        AND dd2.data < v_start
    );

  SELECT COALESCE(AVG(CURRENT_DATE - last_date), 0)
  INTO v_recencia
  FROM (
    SELECT ft.customer_id, MAX(dd.data) AS last_date
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id AND ft.tipo_transacao = 'venda'
      AND ft.customer_id IS NOT NULL
    GROUP BY ft.customer_id
  ) sub;

  -- FIX: (date - date) retorna integer em PG — cast para numeric direto, sem DATE_PART
  v_frequencia := CASE WHEN v_clientes_unicos > 0
    THEN ROUND(v_pedidos::numeric / v_clientes_unicos
         / GREATEST((CURRENT_DATE - v_start)::numeric / 30.0, 1), 2)
    ELSE 0 END;

  WITH active_prev AS (
    SELECT DISTINCT ft.customer_id
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id AND ft.tipo_transacao = 'venda'
      AND ft.customer_id IS NOT NULL
      AND dd.data >= (CURRENT_DATE - INTERVAL '120 days')::date
      AND dd.data <  (CURRENT_DATE - INTERVAL '60 days')::date
  ),
  active_recent AS (
    SELECT DISTINCT ft.customer_id
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id AND ft.tipo_transacao = 'venda'
      AND ft.customer_id IS NOT NULL
      AND dd.data >= (CURRENT_DATE - INTERVAL '60 days')::date
      AND dd.data < CURRENT_DATE
  )
  SELECT ROUND(
    100.0 * COUNT(p.customer_id) FILTER (WHERE r.customer_id IS NULL)
    / NULLIF(COUNT(p.customer_id), 0), 1)
  INTO v_churn
  FROM active_prev p LEFT JOIN active_recent r USING (customer_id);

  SELECT COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda' THEN ft.valor ELSE 0 END), 0)
  INTO v_prev_rev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_prev_start AND dd.data < v_prev_end;

  SELECT
    COALESCE(SUM(CASE WHEN dd.data >= DATE_TRUNC('month', CURRENT_DATE)::date THEN ft.valor END), 0),
    COALESCE(SUM(CASE WHEN dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date
                       AND dd.data <   DATE_TRUNC('month', CURRENT_DATE)::date THEN ft.valor END), 0),
    COALESCE(SUM(CASE WHEN dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '2 months')::date
                       AND dd.data <  (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date THEN ft.valor END), 0),
    COALESCE(SUM(CASE WHEN dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '3 months')::date
                       AND dd.data <  (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '2 months')::date THEN ft.valor END), 0),
    COALESCE(SUM(CASE WHEN dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '4 months')::date
                       AND dd.data <  (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '3 months')::date THEN ft.valor END), 0),
    COALESCE(SUM(CASE WHEN dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '5 months')::date
                       AND dd.data <  (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '4 months')::date THEN ft.valor END), 0)
  INTO v_m1, v_m2, v_m3, v_m4, v_m5, v_m6
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND ft.tipo_transacao = 'venda'
    AND dd.data >= (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '5 months')::date
    AND dd.data < CURRENT_DATE;

  RETURN QUERY SELECT
    v_pedidos,
    ROUND(v_receita, 2),
    CASE WHEN v_pedidos > 0 THEN ROUND(v_receita / v_pedidos, 2) ELSE 0 END,
    v_clientes_unicos,
    v_clientes_novos,
    v_clientes_unicos - v_clientes_novos,
    ROUND(v_recencia, 0),
    v_frequencia,
    v_churn,
    CASE WHEN v_prev_rev > 0 THEN ROUND((v_receita - v_prev_rev) / v_prev_rev * 100, 1) ELSE NULL END,
    v_m1, v_m2, v_m3, v_m4, v_m5, v_m6,
    p_period;
END;
$$;
