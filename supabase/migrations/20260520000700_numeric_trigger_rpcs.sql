-- ─────────────────────────────────────────────────────────────────────────────
-- Migration: 20260520000700_numeric_trigger_rpcs.sql
--
-- Adds 4 RPC functions used by the numeric trigger engine in routines.py.
-- Each function follows the same contract:
--   (current_month_X, avg_monthly_X) → trigger fires when current < threshold * avg
--
-- All use fato_transacoes + dim_datas for monthly grouping.
-- dim_clientes columns (receita_total, ticket_medio, total_pedidos) are used
-- as fallback when the fact table has insufficient history.
--
-- Security: SECURITY DEFINER, accessible only to service_role.
-- ─────────────────────────────────────────────────────────────────────────────


-- ── 1. get_revenue_monthly_rate() ────────────────────────────────────────────
--
-- Returns gross revenue for the current calendar month and the average over
-- the previous p_window_months months (excluding the current month).
-- Uses fato_transacoes.valor grouped by dim_datas.ano/mes.
--
-- current_month_revenue : sum of valor in the current anno-mes
-- avg_monthly_revenue   : avg of monthly totals in the prior window
--
-- Aliased as "faturamento" in Python — same function, two names.

CREATE OR REPLACE FUNCTION public.get_revenue_monthly_rate(
  p_client_id     uuid,
  p_window_months integer DEFAULT 1
)
RETURNS TABLE(current_month_revenue numeric, avg_monthly_revenue numeric)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_current numeric;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  -- Current calendar month revenue
  SELECT COALESCE(SUM(ft.valor), 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND dd.ano  = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes  = EXTRACT(MONTH FROM v_now)::integer;

  -- Average monthly revenue over the previous p_window_months months
  -- (month ranges: [now - window, now - 1 month], i.e. excluding current month)
  SELECT COALESCE(AVG(monthly_total), 0)
    INTO v_avg
    FROM (
      SELECT dd.ano, dd.mes, SUM(ft.valor) AS monthly_total
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_month_revenue := v_current;
  avg_monthly_revenue   := ROUND(COALESCE(v_avg, 0), 2);

  RETURN NEXT;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.get_revenue_monthly_rate(uuid, integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.get_revenue_monthly_rate(uuid, integer) FROM anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.get_revenue_monthly_rate(uuid, integer) TO service_role;


-- ── 2. get_ticket_medio_monthly_rate() ───────────────────────────────────────
--
-- Returns average ticket (valor / count of distinct transacao_id) for the
-- current month vs the rolling average over prior p_window_months months.
--
-- current_ticket : avg ticket this month
-- avg_ticket     : avg of per-month avg_tickets over the window

CREATE OR REPLACE FUNCTION public.get_ticket_medio_monthly_rate(
  p_client_id     uuid,
  p_window_months integer DEFAULT 1
)
RETURNS TABLE(current_ticket numeric, avg_ticket numeric)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_current numeric;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  -- Current month average ticket
  SELECT COALESCE(
           CASE WHEN COUNT(DISTINCT ft.transacao_id) = 0 THEN 0
                ELSE SUM(ft.valor) / COUNT(DISTINCT ft.transacao_id)
           END, 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND dd.ano = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_now)::integer;

  -- Average of monthly avg tickets over prior window
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
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_ticket := ROUND(COALESCE(v_current, 0), 2);
  avg_ticket     := ROUND(COALESCE(v_avg,     0), 2);

  RETURN NEXT;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.get_ticket_medio_monthly_rate(uuid, integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.get_ticket_medio_monthly_rate(uuid, integer) FROM anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.get_ticket_medio_monthly_rate(uuid, integer) TO service_role;


-- ── 3. get_pedidos_monthly_rate() ─────────────────────────────────────────────
--
-- Returns count of distinct orders (transacao_id) in the current month vs
-- the rolling average over prior p_window_months months.
--
-- current_pedidos : count of distinct transacao_id this month
-- avg_pedidos     : avg of monthly order counts over the window

CREATE OR REPLACE FUNCTION public.get_pedidos_monthly_rate(
  p_client_id     uuid,
  p_window_months integer DEFAULT 1
)
RETURNS TABLE(current_pedidos numeric, avg_pedidos numeric)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_current bigint;
  v_avg     numeric;
  v_now     date := date_trunc('month', now())::date;
BEGIN
  -- Current month order count
  SELECT COALESCE(COUNT(DISTINCT ft.transacao_id), 0)
    INTO v_current
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND dd.ano = EXTRACT(YEAR  FROM v_now)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_now)::integer;

  -- Average monthly order count over prior window
  SELECT COALESCE(AVG(monthly_count), 0)
    INTO v_avg
    FROM (
      SELECT dd.ano, dd.mes, COUNT(DISTINCT ft.transacao_id) AS monthly_count
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND dd.data >= (v_now - (p_window_months || ' months')::interval)::date
         AND dd.data <  v_now
       GROUP BY dd.ano, dd.mes
    ) monthly_buckets;

  current_pedidos := v_current::numeric;
  avg_pedidos     := ROUND(COALESCE(v_avg, 0), 2);

  RETURN NEXT;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.get_pedidos_monthly_rate(uuid, integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.get_pedidos_monthly_rate(uuid, integer) FROM anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.get_pedidos_monthly_rate(uuid, integer) TO service_role;


-- ── 4. get_churn_rate_monthly() ───────────────────────────────────────────────
--
-- Estimates churn as the fraction of customers who were active in the previous
-- month but placed no orders in the current month.
--
-- "Active last month"  = distinct cpf_cnpj with a transaction in prior month
-- "Churned this month" = those who had NO transaction this month
--
-- current_churn_rate : fraction [0–1] of last-month buyers who didn't buy this month
-- avg_churn_rate     : avg of the monthly churn rates over the prior window
--
-- NOTE: For spike detection set threshold > 1 (e.g. 1.5 = fire when churn is
-- 50% above the historical avg). The engine always evaluates:
--   current < threshold * baseline → fires
-- So for churn spikes configure threshold = 1/expected_spike_ratio or use a
-- dedicated spike trigger type in a future iteration.

CREATE OR REPLACE FUNCTION public.get_churn_rate_monthly(
  p_client_id     uuid,
  p_window_months integer DEFAULT 1
)
RETURNS TABLE(current_churn_rate numeric, avg_churn_rate numeric)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, analytics_v2
AS $$
DECLARE
  v_current_rate numeric;
  v_avg_rate     numeric;
  v_now          date := date_trunc('month', now())::date;
  v_prev_month   date := (v_now - interval '1 month')::date;

  v_active_last_month  bigint;
  v_churned_this_month bigint;
BEGIN
  -- Customers active last month
  SELECT COUNT(DISTINCT ft.transacao_id)
    INTO v_active_last_month
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
   WHERE ft.client_id = p_client_id
     AND dd.ano = EXTRACT(YEAR  FROM v_prev_month)::integer
     AND dd.mes = EXTRACT(MONTH FROM v_prev_month)::integer;

  IF v_active_last_month = 0 THEN
    -- No historical base — no churn to report
    current_churn_rate := 0;
    avg_churn_rate     := 0;
    RETURN NEXT;
    RETURN;
  END IF;

  -- Customers from last month who did NOT transact this month
  SELECT COUNT(DISTINCT prev_buyers.transacao_id)
    INTO v_churned_this_month
    FROM (
      SELECT DISTINCT ft.transacao_id
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_datas       dd ON dd.data_id = ft.data_competencia_id
       WHERE ft.client_id = p_client_id
         AND dd.ano = EXTRACT(YEAR  FROM v_prev_month)::integer
         AND dd.mes = EXTRACT(MONTH FROM v_prev_month)::integer
    ) prev_buyers
   WHERE prev_buyers.transacao_id NOT IN (
      SELECT DISTINCT ft2.transacao_id
        FROM analytics_v2.fato_transacoes ft2
        JOIN analytics_v2.dim_datas        dd2 ON dd2.data_id = ft2.data_competencia_id
       WHERE ft2.client_id = p_client_id
         AND dd2.ano = EXTRACT(YEAR  FROM v_now)::integer
         AND dd2.mes = EXTRACT(MONTH FROM v_now)::integer
   );

  v_current_rate := ROUND(v_churned_this_month::numeric / v_active_last_month, 4);

  -- Rolling average churn over prior p_window_months month-pairs
  -- For each month M in [now-window, now-1], compute churn(M-1→M) and average.
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
          SELECT COUNT(DISTINCT prev_t.transacao_id)
            FROM analytics_v2.fato_transacoes prev_t
            JOIN analytics_v2.dim_datas        prev_dd ON prev_dd.data_id = prev_t.data_competencia_id
           WHERE prev_t.client_id = p_client_id
             AND prev_dd.ano = EXTRACT(YEAR  FROM mp.m_prev)::integer
             AND prev_dd.mes = EXTRACT(MONTH FROM mp.m_prev)::integer
        ), 0) AS base_count,
      COALESCE(
        (
          SELECT COUNT(DISTINCT prev_t.transacao_id)
            FROM analytics_v2.fato_transacoes prev_t
            JOIN analytics_v2.dim_datas        prev_dd ON prev_dd.data_id = prev_t.data_competencia_id
           WHERE prev_t.client_id = p_client_id
             AND prev_dd.ano = EXTRACT(YEAR  FROM mp.m_prev)::integer
             AND prev_dd.mes = EXTRACT(MONTH FROM mp.m_prev)::integer
             AND prev_t.transacao_id NOT IN (
               SELECT DISTINCT cur_t.transacao_id
                 FROM analytics_v2.fato_transacoes cur_t
                 JOIN analytics_v2.dim_datas        cur_dd ON cur_dd.data_id = cur_t.data_competencia_id
                WHERE cur_t.client_id = p_client_id
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
$$;

REVOKE EXECUTE ON FUNCTION public.get_churn_rate_monthly(uuid, integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.get_churn_rate_monthly(uuid, integer) FROM anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.get_churn_rate_monthly(uuid, integer) TO service_role;


-- ─────────────────────────────────────────────────────────────────────────────
-- COMMENTS — for Supabase Studio and future devs
-- ─────────────────────────────────────────────────────────────────────────────

COMMENT ON FUNCTION public.get_revenue_monthly_rate(uuid, integer) IS
  'Numeric trigger metric: returns (current_month_revenue, avg_monthly_revenue). '
  'Fires when current < threshold * avg (e.g. threshold=0.85 → queda > 15%).';

COMMENT ON FUNCTION public.get_ticket_medio_monthly_rate(uuid, integer) IS
  'Numeric trigger metric: returns (current_ticket, avg_ticket). '
  'Ticket = total revenue / distinct orders in the month.';

COMMENT ON FUNCTION public.get_pedidos_monthly_rate(uuid, integer) IS
  'Numeric trigger metric: returns (current_pedidos, avg_pedidos). '
  'Counts distinct transacao_id per calendar month.';

COMMENT ON FUNCTION public.get_churn_rate_monthly(uuid, integer) IS
  'Numeric trigger metric: returns (current_churn_rate, avg_churn_rate) as fractions [0-1]. '
  'Churn = buyers in month M-1 who did not buy in month M. '
  'For spike detection set threshold > 1 (e.g. 1.5 = fires when churn is 50% above avg).';
