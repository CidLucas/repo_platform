-- =============================================================================
-- FASE 3: KPI Functions usando tipo_transacao (v2 — corrigido)
-- =============================================================================

-- -------------------------------------------------------
-- 1. get_finance_indicators — receita, custo, margens
-- -------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics_v2.get_finance_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE(
  receita_liquida          numeric,
  custo_total              numeric,
  margem_bruta_perc        numeric,
  margem_operacional_perc  numeric,
  ticket_medio             numeric,
  receita_yoy_perc         numeric,
  crescimento_receita_perc numeric,
  total_pedidos            bigint,
  dso_dias                 numeric,
  dpo_dias                 numeric,
  ccc_dias                 numeric,
  working_capital_ratio    numeric,
  burn_rate_mensal         numeric,
  runway_meses             numeric,
  cash_flow_30d            numeric,
  period                   text
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'analytics_v2', 'public', 'pg_catalog'
AS $$
DECLARE
  v_client_id   uuid    := public.get_my_client_id();
  v_start       date;
  v_prev_start  date;
  v_prev_end    date;
  v_receita     numeric := 0;
  v_custo       numeric := 0;
  v_pedidos     bigint  := 0;
  v_prev_rev    numeric := 0;
  v_yoy_rev     numeric := 0;
  v_margem_bruta numeric;
  v_cash_30d    numeric := 0;
  v_burn        numeric := 0;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end
  INTO   v_start, v_prev_start, v_prev_end
  FROM   analytics_v2._period_range(p_period) r;

  -- Receita líquida (vendas) + contagem de pedidos
  SELECT
    COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda' THEN ft.valor ELSE 0 END), 0),
    COUNT(DISTINCT CASE WHEN ft.tipo_transacao = 'venda' THEN ft.transacao_id ELSE NULL END)
  INTO v_receita, v_pedidos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_start AND dd.data < CURRENT_DATE;

  -- Custo total (compras no período)
  SELECT COALESCE(SUM(ft.valor), 0)
  INTO v_custo
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND ft.tipo_transacao = 'compra'
    AND dd.data >= v_start AND dd.data < CURRENT_DATE;

  -- Cash flow 30d fixo: vendas - compras
  SELECT
    COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda'  THEN ft.valor ELSE 0 END), 0)
  - COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'compra' THEN ft.valor ELSE 0 END), 0)
  INTO v_cash_30d
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= (CURRENT_DATE - INTERVAL '30 days')::date
    AND dd.data < CURRENT_DATE;

  -- Burn rate mensal = média de compras dos últimos 90 dias / 3
  SELECT COALESCE(SUM(ft.valor), 0) / 3.0
  INTO v_burn
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND ft.tipo_transacao = 'compra'
    AND dd.data >= (CURRENT_DATE - INTERVAL '90 days')::date
    AND dd.data < CURRENT_DATE;

  -- Receita período anterior
  SELECT COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda' THEN ft.valor ELSE 0 END), 0)
  INTO v_prev_rev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_prev_start AND dd.data < v_prev_end;

  -- Receita YoY
  SELECT COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda' THEN ft.valor ELSE 0 END), 0)
  INTO v_yoy_rev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= (v_start - INTERVAL '1 year')::date
    AND dd.data <  (CURRENT_DATE - INTERVAL '1 year')::date;

  v_margem_bruta := CASE WHEN v_receita > 0
    THEN ROUND((v_receita - v_custo) / v_receita * 100, 1)
    ELSE NULL END;

  RETURN QUERY SELECT
    v_receita,
    v_custo,
    v_margem_bruta,
    v_margem_bruta,  -- margem_operacional = bruta (sem OPEX separado ainda)
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
$$;

-- -------------------------------------------------------
-- 2. get_commercial_indicators — vendas filtradas por tipo
-- -------------------------------------------------------
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
  -- séries mensais (variáveis individuais por compatibilidade plpgsql)
  v_m1 numeric := 0; v_m2 numeric := 0; v_m3 numeric := 0;
  v_m4 numeric := 0; v_m5 numeric := 0; v_m6 numeric := 0;
BEGIN
  SELECT r.start_date, r.prev_start, r.prev_end
  INTO v_start, v_prev_start, v_prev_end
  FROM analytics_v2._period_range(p_period) r;

  -- Pedidos e receita: APENAS vendas
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

  -- Clientes novos: compraram no período mas NÃO antes
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

  -- Recência média (dias desde última venda)
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

  -- Frequência média mensal
  v_frequencia := CASE WHEN v_clientes_unicos > 0
    THEN ROUND(v_pedidos::numeric / v_clientes_unicos
         / GREATEST((CURRENT_DATE - v_start)::numeric / 30.0, 1), 2)
    ELSE 0 END;

  -- Churn 60d
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

  -- Receita período anterior
  SELECT COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda' THEN ft.valor ELSE 0 END), 0)
  INTO v_prev_rev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_prev_start AND dd.data < v_prev_end;

  -- Séries mensais: receita de venda por mês (últimos 6 meses)
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

-- -------------------------------------------------------
-- 3. Patch get_supply_indicators — adicionar filtro tipo_transacao = 'compra'
--    Mantém assinatura original (não muda RETURNS TABLE)
-- -------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics_v2.get_supply_indicators(p_period text DEFAULT '30d')
RETURNS TABLE(
  rfqs_abertas              bigint,
  rfqs_enviadas             bigint,
  rfqs_respondidas          bigint,
  taxa_resposta_perc        numeric,
  tempo_resposta_medio_h    numeric,
  pos_aprovadas             bigint,
  pos_pendentes_aprovacao   bigint,
  spend_periodo             numeric,
  fornecedores_ativos       bigint,
  concentracao_top_perc     numeric,
  cycle_time_medio_h        numeric,
  cost_savings_perc         numeric,
  ppv                       numeric,
  otif_perc                 numeric,
  lead_time_medio_dias      numeric,
  maverick_spend_perc       numeric,
  spend_under_management_perc numeric,
  period                    text
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'analytics_v2', 'public', 'pg_catalog'
AS $$
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
  WITH period_forn AS (
    SELECT
      ft.fornecedor_id,
      SUM(ft.valor) AS spend
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.client_id = v_client_id
      AND ft.tipo_transacao = 'compra'   -- ← FILTRO ADICIONADO
      AND dd.data >= v_start AND dd.data < CURRENT_DATE
    GROUP BY ft.fornecedor_id
  ),
  total_spend AS (
    SELECT COALESCE(SUM(spend), 0) AS total FROM period_forn
  ),
  top_supplier AS (
    SELECT COALESCE(MAX(spend), 0) AS top FROM period_forn
  ),
  rfqs AS (
    SELECT
      COUNT(*) FILTER (WHERE status = 'pending')                              AS abertas,
      COUNT(*) FILTER (WHERE status IN ('pending','approved','rejected'))      AS enviadas,
      COUNT(*) FILTER (WHERE status IN ('approved','rejected'))                AS respondidas,
      COUNT(*) FILTER (WHERE status = 'approved')                             AS aprovadas,
      ROUND(AVG(EXTRACT(epoch FROM (decided_at - created_at)) / 3600)
            FILTER (WHERE decided_at IS NOT NULL)::numeric, 1)               AS tempo_resp_h,
      ROUND(AVG(EXTRACT(epoch FROM (decided_at - created_at)) / 3600)
            FILTER (WHERE status = 'approved' AND decided_at IS NOT NULL)::numeric, 1) AS cycle_h
    FROM public.approval_requests
    WHERE client_id = v_client_id
      AND created_at >= v_start
  )
  SELECT
    rfqs.abertas,
    rfqs.enviadas,
    rfqs.respondidas,
    CASE WHEN rfqs.enviadas > 0 THEN ROUND(rfqs.respondidas::numeric / rfqs.enviadas * 100, 1) ELSE NULL END,
    rfqs.tempo_resp_h,
    rfqs.aprovadas,
    rfqs.abertas,
    (SELECT total FROM total_spend),
    (SELECT COUNT(DISTINCT fornecedor_id) FROM period_forn),
    CASE WHEN (SELECT total FROM total_spend) > 0
         THEN ROUND((SELECT top FROM top_supplier) / (SELECT total FROM total_spend) * 100, 1)
         ELSE NULL END,
    rfqs.cycle_h,
    NULL::numeric,  -- cost_savings_perc (requer preço de referência)
    NULL::numeric,  -- ppv
    NULL::numeric,  -- otif_perc (requer data de entrega prometida)
    NULL::numeric,  -- lead_time_medio_dias
    NULL::numeric,  -- maverick_spend_perc
    NULL::numeric,  -- spend_under_management_perc
    p_period
  FROM rfqs;
END;
$$;

-- -------------------------------------------------------
-- 4. get_kpi_mtd_comparison — cards principais do painel
-- -------------------------------------------------------
CREATE OR REPLACE FUNCTION analytics_v2.get_kpi_mtd_comparison()
RETURNS TABLE(
  kpi            text,
  valor_atual    numeric,
  valor_anterior numeric,
  variacao_pct   numeric,
  tendencia      text
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path TO 'analytics_v2', 'public', 'pg_catalog'
AS $$
DECLARE
  v_client_id  uuid := public.get_my_client_id();
  v_mtd_start  date := DATE_TRUNC('month', CURRENT_DATE)::date;
  v_prev_start date := (DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month')::date;
  v_prev_end   date := DATE_TRUNC('month', CURRENT_DATE)::date;
  -- MTD
  v_receita_mtd numeric := 0; v_custo_mtd  numeric := 0;
  -- Prev month
  v_receita_prev numeric := 0; v_custo_prev numeric := 0;
BEGIN
  SELECT
    COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda'  THEN ft.valor ELSE 0 END), 0),
    COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'compra' THEN ft.valor ELSE 0 END), 0)
  INTO v_receita_mtd, v_custo_mtd
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_mtd_start AND dd.data < CURRENT_DATE;

  SELECT
    COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'venda'  THEN ft.valor ELSE 0 END), 0),
    COALESCE(SUM(CASE WHEN ft.tipo_transacao = 'compra' THEN ft.valor ELSE 0 END), 0)
  INTO v_receita_prev, v_custo_prev
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = v_client_id
    AND dd.data >= v_prev_start AND dd.data < v_prev_end;

  RETURN QUERY
  WITH kpis(kpi, atual, anterior) AS (VALUES
    ('receita_liquida',   v_receita_mtd,  v_receita_prev),
    ('custo_mercadorias', v_custo_mtd,    v_custo_prev),
    ('margem_bruta',
      CASE WHEN v_receita_mtd  > 0 THEN ROUND((v_receita_mtd  - v_custo_mtd)  / v_receita_mtd  * 100, 1) ELSE 0::numeric END,
      CASE WHEN v_receita_prev > 0 THEN ROUND((v_receita_prev - v_custo_prev) / v_receita_prev * 100, 1) ELSE 0::numeric END),
    ('fluxo_caixa',
      v_receita_mtd  - v_custo_mtd,
      v_receita_prev - v_custo_prev)
  )
  SELECT
    k.kpi,
    k.atual,
    k.anterior,
    CASE WHEN k.anterior <> 0 THEN ROUND((k.atual - k.anterior) / ABS(k.anterior) * 100, 1) ELSE NULL END,
    CASE
      WHEN k.anterior = 0 THEN 'neutral'
      WHEN k.atual > k.anterior THEN 'up'
      WHEN k.atual < k.anterior THEN 'down'
      ELSE 'neutral'
    END
  FROM kpis k;
END;
$$;

COMMENT ON FUNCTION analytics_v2.get_finance_indicators IS
  'KPIs financeiros por tipo_transacao (venda=receita, compra=custo).
   dso/dpo/ccc/working_capital requerem contas a pagar/receber (futuro).';

COMMENT ON FUNCTION analytics_v2.get_kpi_mtd_comparison IS
  'Cards de KPI MTD vs mês anterior: receita_liquida, custo_mercadorias, margem_bruta, fluxo_caixa.';
