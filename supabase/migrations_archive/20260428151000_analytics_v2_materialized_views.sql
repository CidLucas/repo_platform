-- Migration: Create analytics_v2 materialized views and refresh function
-- Purpose: Build aggregation layer for dashboard analytics
-- Created: 2026-04-28

-- ============================================================================
-- MATERIALIZED VIEW: mv_resumo_dashboard
-- ============================================================================
-- Single-row summary per client with all key metrics for dashboard scorecards

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard AS
SELECT
  ft.client_id,
  -- Totals from dimension tables (count of unique entities)
  COUNT(DISTINCT dc.client_id)::INTEGER AS total_clientes,
  COUNT(DISTINCT df.fornecedor_id)::INTEGER AS total_fornecedores,
  COUNT(DISTINCT di.inventory_id)::INTEGER AS total_produtos,
  COUNT(DISTINCT ft.transacao_id)::INTEGER AS total_pedidos,

  -- Revenue and quantity totals from fact table
  COALESCE(SUM(ft.total_value), 0)::NUMERIC AS receita_total,
  COALESCE(SUM(ft.quantity), 0)::NUMERIC AS quantidade_total_vendida,

  -- Average values
  CASE
    WHEN COUNT(DISTINCT ft.transacao_id) > 0
    THEN (COALESCE(SUM(ft.total_value), 0) / COUNT(DISTINCT ft.transacao_id))::NUMERIC
    ELSE 0::NUMERIC
  END AS ticket_medio,

  -- Current month metrics (competencia = current month)
  COALESCE(SUM(CASE WHEN DATE_TRUNC('month', dd.data)::DATE = DATE_TRUNC('month', CURRENT_DATE)::DATE THEN ft.total_value ELSE 0 END), 0)::NUMERIC AS receita_mes_atual,
  COALESCE(SUM(CASE WHEN DATE_TRUNC('month', dd.data)::DATE = DATE_TRUNC('month', CURRENT_DATE)::DATE THEN ft.quantity ELSE 0 END), 0)::NUMERIC AS quantidade_mes_atual,
  COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = DATE_TRUNC('month', CURRENT_DATE)::DATE THEN dc.client_id ELSE NULL END)::INTEGER AS clientes_mes_atual,
  COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = DATE_TRUNC('month', CURRENT_DATE)::DATE THEN di.inventory_id ELSE NULL END)::INTEGER AS produtos_mes_atual,
  COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = DATE_TRUNC('month', CURRENT_DATE)::DATE THEN df.fornecedor_id ELSE NULL END)::INTEGER AS fornecedores_mes_atual,

  -- Growth rates (current month vs previous month)
  CASE
    WHEN COALESCE(SUM(CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN ft.total_value ELSE 0 END), 0) > 0
    THEN ((COALESCE(SUM(CASE WHEN DATE_TRUNC('month', dd.data)::DATE = DATE_TRUNC('month', CURRENT_DATE)::DATE THEN ft.total_value ELSE 0 END), 0) -
           COALESCE(SUM(CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN ft.total_value ELSE 0 END), 0)) /
          COALESCE(SUM(CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN ft.total_value ELSE 0 END), 0) * 100)::NUMERIC
    ELSE 0::NUMERIC
  END AS crescimento_receita,

  CASE
    WHEN COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN dc.client_id ELSE NULL END) > 0
    THEN ((COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = DATE_TRUNC('month', CURRENT_DATE)::DATE THEN dc.client_id ELSE NULL END) -
           COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN dc.client_id ELSE NULL END)) /
          COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN dc.client_id ELSE NULL END) * 100)::NUMERIC
    ELSE 0::NUMERIC
  END AS crescimento_clientes,

  CASE
    WHEN COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN di.inventory_id ELSE NULL END) > 0
    THEN ((COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = DATE_TRUNC('month', CURRENT_DATE)::DATE THEN di.inventory_id ELSE NULL END) -
           COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN di.inventory_id ELSE NULL END)) /
          COUNT(DISTINCT CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN di.inventory_id ELSE NULL END) * 100)::NUMERIC
    ELSE 0::NUMERIC
  END AS crescimento_produtos,

  CASE
    WHEN COALESCE(SUM(CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN ft.quantity ELSE 0 END), 0) > 0
    THEN ((COALESCE(SUM(CASE WHEN DATE_TRUNC('month', dd.data)::DATE = DATE_TRUNC('month', CURRENT_DATE)::DATE THEN ft.quantity ELSE 0 END), 0) -
           COALESCE(SUM(CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN ft.quantity ELSE 0 END), 0)) /
          COALESCE(SUM(CASE WHEN DATE_TRUNC('month', dd.data)::DATE = (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::DATE THEN ft.quantity ELSE 0 END), 0) * 100)::NUMERIC
    ELSE 0::NUMERIC
  END AS crescimento_quantidade,

  -- Supplier frequency (average orders per supplier)
  CASE
    WHEN COUNT(DISTINCT df.fornecedor_id) > 0
    THEN (COUNT(DISTINCT ft.transacao_id)::NUMERIC / COUNT(DISTINCT df.fornecedor_id))
    ELSE 0::NUMERIC
  END AS frequencia_media_fornecedores,

  -- Geographic diversity (count distinct states)
  COUNT(DISTINCT dc.endereco_uf)::INTEGER AS total_regioes,

  -- Last month name
  TO_CHAR(CURRENT_DATE - INTERVAL '1 month', 'Mon/YYYY') AS ultimo_mes,

  -- Active customers (those with transactions in last 30 days)
  COUNT(DISTINCT CASE WHEN dd.data >= CURRENT_DATE - INTERVAL '30 days' THEN dc.client_id ELSE NULL END)::INTEGER AS clientes_ativos,

  -- New customers (first transaction in current month)
  COUNT(DISTINCT CASE
    WHEN DATE_TRUNC('month', dd.data)::DATE = DATE_TRUNC('month', CURRENT_DATE)::DATE
    AND ft.transacao_id NOT IN (
      SELECT ft2.transacao_id FROM analytics_v2.fato_transacoes ft2
      JOIN analytics_v2.dim_datas dd2 ON ft2.data_competencia_id = dd2.data_id
      WHERE dd2.data < DATE_TRUNC('month', CURRENT_DATE)::DATE
    )
    THEN dc.client_id ELSE NULL END)::INTEGER AS clientes_novos,

  -- Generation timestamp
  CURRENT_TIMESTAMP AS gerado_em

FROM analytics_v2.fato_transacoes ft
LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
LEFT JOIN analytics_v2.dim_clientes dc ON ft.client_id = dc.client_id AND dc.client_id = ft.client_id
LEFT JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id AND df.client_id = ft.client_id
LEFT JOIN analytics_v2.dim_inventory di ON ft.produto_id = di.inventory_id AND di.client_id = ft.client_id
GROUP BY ft.client_id;

CREATE INDEX idx_mv_resumo_dashboard_client_id ON analytics_v2.mv_resumo_dashboard(client_id);

-- ============================================================================
-- MATERIALIZED VIEW: mv_series_temporal
-- ============================================================================
-- Time-series data grouped by period, type, and dimension

CREATE MATERIALIZED VIEW analytics_v2.mv_series_temporal AS
SELECT
  ft.client_id,
  TO_CHAR(dd.data, 'YYYY-MM') AS periodo,
  dd.data AS data_periodo,

  -- Type of metric
  CASE
    WHEN SUM(ft.total_value) IS NOT NULL THEN 'receita'
    ELSE 'receita'
  END AS tipo_grafico,

  -- Dimension/breakout
  'total' AS dimensao,

  -- Aggregated values
  COALESCE(SUM(ft.total_value), 0)::NUMERIC AS total,
  COALESCE(SUM(SUM(ft.total_value)) OVER (PARTITION BY ft.client_id ORDER BY dd.data), 0)::NUMERIC AS total_cumulativo

FROM analytics_v2.fato_transacoes ft
LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, dd.data

UNION ALL

-- Revenue by client (clientes tipo_grafico)
SELECT
  ft.client_id,
  TO_CHAR(dd.data, 'YYYY-MM') AS periodo,
  dd.data AS data_periodo,
  'clientes'::TEXT AS tipo_grafico,
  'total'::TEXT AS dimensao,
  COUNT(DISTINCT dc.client_id)::NUMERIC AS total,
  COALESCE(COUNT(DISTINCT dc.client_id) OVER (PARTITION BY ft.client_id ORDER BY dd.data), 0)::NUMERIC AS total_cumulativo

FROM analytics_v2.fato_transacoes ft
LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
LEFT JOIN analytics_v2.dim_clientes dc ON ft.client_id = dc.client_id AND dc.client_id = ft.client_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, dd.data

UNION ALL

-- By suppliers
SELECT
  ft.client_id,
  TO_CHAR(dd.data, 'YYYY-MM') AS periodo,
  dd.data AS data_periodo,
  'fornecedores'::TEXT AS tipo_grafico,
  'total'::TEXT AS dimensao,
  COUNT(DISTINCT df.fornecedor_id)::NUMERIC AS total,
  COALESCE(COUNT(DISTINCT df.fornecedor_id) OVER (PARTITION BY ft.client_id ORDER BY dd.data), 0)::NUMERIC AS total_cumulativo

FROM analytics_v2.fato_transacoes ft
LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
LEFT JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id AND df.client_id = ft.client_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, dd.data

UNION ALL

-- By products
SELECT
  ft.client_id,
  TO_CHAR(dd.data, 'YYYY-MM') AS periodo,
  dd.data AS data_periodo,
  'produtos'::TEXT AS tipo_grafico,
  'total'::TEXT AS dimensao,
  COUNT(DISTINCT di.inventory_id)::NUMERIC AS total,
  COALESCE(COUNT(DISTINCT di.inventory_id) OVER (PARTITION BY ft.client_id ORDER BY dd.data), 0)::NUMERIC AS total_cumulativo

FROM analytics_v2.fato_transacoes ft
LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
LEFT JOIN analytics_v2.dim_inventory di ON ft.produto_id = di.inventory_id AND di.client_id = ft.client_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, dd.data

UNION ALL

-- By orders/pedidos
SELECT
  ft.client_id,
  TO_CHAR(dd.data, 'YYYY-MM') AS periodo,
  dd.data AS data_periodo,
  'pedidos'::TEXT AS tipo_grafico,
  'total'::TEXT AS dimensao,
  COUNT(DISTINCT ft.transacao_id)::NUMERIC AS total,
  COALESCE(COUNT(DISTINCT ft.transacao_id) OVER (PARTITION BY ft.client_id ORDER BY dd.data), 0)::NUMERIC AS total_cumulativo

FROM analytics_v2.fato_transacoes ft
LEFT JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL
GROUP BY ft.client_id, dd.data;

CREATE INDEX idx_mv_series_temporal_client_id ON analytics_v2.mv_series_temporal(client_id);
CREATE INDEX idx_mv_series_temporal_tipo_grafico ON analytics_v2.mv_series_temporal(tipo_grafico);
CREATE INDEX idx_mv_series_temporal_data_periodo ON analytics_v2.mv_series_temporal(data_periodo DESC);

-- ============================================================================
-- MATERIALIZED VIEW: mv_ultimos_pedidos
-- ============================================================================
-- Recent orders per client

CREATE MATERIALIZED VIEW analytics_v2.mv_ultimos_pedidos AS
SELECT
  ft.client_id,
  ft.transacao_id AS pedido_id,
  dc.cpf_cnpj AS cliente_cpf_cnpj,
  ft.total_value AS valor_pedido,
  ft.quantity AS qtd_produtos,
  ROW_NUMBER() OVER (PARTITION BY ft.client_id ORDER BY ft.created_at DESC) AS ordem

FROM analytics_v2.fato_transacoes ft
LEFT JOIN analytics_v2.dim_clientes dc ON ft.client_id = dc.client_id AND dc.client_id = ft.client_id
WHERE ft.created_at IS NOT NULL
ORDER BY ft.client_id, ft.created_at DESC;

CREATE INDEX idx_mv_ultimos_pedidos_client_id ON analytics_v2.mv_ultimos_pedidos(client_id);
CREATE INDEX idx_mv_ultimos_pedidos_ordem ON analytics_v2.mv_ultimos_pedidos(client_id, ordem);

-- ============================================================================
-- MATERIALIZED VIEW: mv_distribuicao_regional
-- ============================================================================
-- Geographic aggregation by state and city

CREATE MATERIALIZED VIEW analytics_v2.mv_distribuicao_regional AS
SELECT
  dc.client_id,
  dc.endereco_uf,
  dc.endereco_cidade,
  COALESCE(SUM(ft.total_value), 0)::NUMERIC AS receita_total,
  COUNT(DISTINCT dc.client_id)::INTEGER AS total_clientes,
  COUNT(DISTINCT ft.transacao_id)::INTEGER AS total_pedidos

FROM analytics_v2.dim_clientes dc
LEFT JOIN analytics_v2.fato_transacoes ft ON dc.client_id = ft.client_id AND dc.client_id = ft.client_id
GROUP BY dc.client_id, dc.endereco_uf, dc.endereco_cidade;

CREATE INDEX idx_mv_distribuicao_regional_client_id ON analytics_v2.mv_distribuicao_regional(client_id);
CREATE INDEX idx_mv_distribuicao_regional_uf ON analytics_v2.mv_distribuicao_regional(endereco_uf);

-- ============================================================================
-- SECURITY-INVOKER VIEWS (wrapping materialized views with RLS)
-- ============================================================================

DROP VIEW IF EXISTS analytics_v2.v_resumo_dashboard CASCADE;
CREATE VIEW analytics_v2.v_resumo_dashboard WITH (security_invoker=on) AS
SELECT * FROM analytics_v2.mv_resumo_dashboard
WHERE client_id = public.get_my_client_id();

DROP VIEW IF EXISTS analytics_v2.v_series_temporal CASCADE;
CREATE VIEW analytics_v2.v_series_temporal WITH (security_invoker=on) AS
SELECT * FROM analytics_v2.mv_series_temporal
WHERE client_id = public.get_my_client_id();

DROP VIEW IF EXISTS analytics_v2.v_ultimos_pedidos CASCADE;
CREATE VIEW analytics_v2.v_ultimos_pedidos WITH (security_invoker=on) AS
SELECT * FROM analytics_v2.mv_ultimos_pedidos
WHERE client_id = public.get_my_client_id();

DROP VIEW IF EXISTS analytics_v2.v_distribuicao_regional CASCADE;
CREATE VIEW analytics_v2.v_distribuicao_regional WITH (security_invoker=on) AS
SELECT * FROM analytics_v2.mv_distribuicao_regional
WHERE client_id = public.get_my_client_id();

-- ============================================================================
-- REFRESH FUNCTION: atualizar_agregados
-- ============================================================================
-- Manually refresh materialized views for a specific client

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_agregados(p_client_id TEXT DEFAULT NULL)
RETURNS TABLE(status TEXT, message TEXT, mv_name TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'analytics_v2'
AS $$
DECLARE
  v_client_id TEXT;
  v_start_time TIMESTAMPTZ;
  v_end_time TIMESTAMPTZ;
  v_duration INTERVAL;
BEGIN
  v_start_time := CURRENT_TIMESTAMP;

  -- If no client_id provided, use current JWT client
  IF p_client_id IS NULL THEN
    v_client_id := public.get_my_client_id()::TEXT;
  ELSE
    v_client_id := p_client_id;
  END IF;

  -- Refresh mv_resumo_dashboard
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_dashboard;
  v_end_time := CURRENT_TIMESTAMP;
  v_duration := v_end_time - v_start_time;
  RETURN QUERY SELECT 'success'::TEXT, 'Refreshed'::TEXT || ' in ' || v_duration::TEXT, 'mv_resumo_dashboard'::TEXT;

  -- Refresh mv_series_temporal
  v_start_time := CURRENT_TIMESTAMP;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_series_temporal;
  v_end_time := CURRENT_TIMESTAMP;
  v_duration := v_end_time - v_start_time;
  RETURN QUERY SELECT 'success'::TEXT, 'Refreshed'::TEXT || ' in ' || v_duration::TEXT, 'mv_series_temporal'::TEXT;

  -- Refresh mv_ultimos_pedidos
  v_start_time := CURRENT_TIMESTAMP;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_ultimos_pedidos;
  v_end_time := CURRENT_TIMESTAMP;
  v_duration := v_end_time - v_start_time;
  RETURN QUERY SELECT 'success'::TEXT, 'Refreshed'::TEXT || ' in ' || v_duration::TEXT, 'mv_ultimos_pedidos'::TEXT;

  -- Refresh mv_distribuicao_regional
  v_start_time := CURRENT_TIMESTAMP;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_distribuicao_regional;
  v_end_time := CURRENT_TIMESTAMP;
  v_duration := v_end_time - v_start_time;
  RETURN QUERY SELECT 'success'::TEXT, 'Refreshed'::TEXT || ' in ' || v_duration::TEXT, 'mv_distribuicao_regional'::TEXT;

EXCEPTION WHEN OTHERS THEN
  RETURN QUERY SELECT 'error'::TEXT, SQLERRM, 'analytics_v2.atualizar_agregados'::TEXT;
END;
$$;

-- Grant access to authenticated users
GRANT EXECUTE ON FUNCTION analytics_v2.atualizar_agregados(TEXT) TO authenticated;

-- ============================================================================
-- SCHEDULED REFRESH VIA pg_cron (if available)
-- ============================================================================
-- Refresh all MVs every hour as a failsafe

-- Check if pg_cron extension exists, if not this will be skipped
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron') THEN
    -- Schedule hourly refresh (run at :00 of each hour)
    PERFORM cron.schedule(
      'refresh_analytics_mvs',
      '0 * * * *',
      'SELECT analytics_v2.atualizar_agregados();'
    );
  END IF;
EXCEPTION WHEN OTHERS THEN
  -- pg_cron not available, skip scheduling
  NULL;
END $$;

-- ============================================================================
-- GRANT PostgREST ACCESS
-- ============================================================================
-- Allow authenticated users to query the views

GRANT SELECT ON analytics_v2.v_resumo_dashboard TO authenticated;
GRANT SELECT ON analytics_v2.v_series_temporal TO authenticated;
GRANT SELECT ON analytics_v2.v_ultimos_pedidos TO authenticated;
GRANT SELECT ON analytics_v2.v_distribuicao_regional TO authenticated;

-- Grant access to underlying materialized views
GRANT SELECT ON analytics_v2.mv_resumo_dashboard TO authenticated;
GRANT SELECT ON analytics_v2.mv_series_temporal TO authenticated;
GRANT SELECT ON analytics_v2.mv_ultimos_pedidos TO authenticated;
GRANT SELECT ON analytics_v2.mv_distribuicao_regional TO authenticated;
