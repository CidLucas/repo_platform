-- Migration: Phase 1 — per-dimension KPI RPCs
-- Date: 2026-04-26
--
-- Implements BLU-MVP-010..014 (K1.2 in 2026-04-26-blu-mvp-roadmap.md):
-- Adds five `security_invoker` RPCs returning the KPI rows defined in §6
-- of the roadmap, parameterized by `p_period`. All callable by
-- `authenticated` and scoped via `public.get_my_client_id()` (RLS).
--
--   analytics_v2.get_finance_indicators(p_period)
--   analytics_v2.get_commercial_indicators(p_period)
--   analytics_v2.get_inventory_indicators(p_period)
--   analytics_v2.get_supply_indicators(p_period)
--   analytics_v2.get_marketing_indicators(p_period)
--
-- Period vocabulary (K1.4): supports the standardized
--   '7d' | '30d' | '90d' | 'mtd' | 'ytd' | 'custom'
-- alongside the legacy 'week' | 'month' | 'quarter' | 'year' aliases.
-- 'custom' falls back to 30d when no explicit window is supplied
-- (custom-range RPC variant deferred to Phase 1 follow-up).
--
-- Notes:
--   • Marketing KPIs are gated PRO/ENTERPRISE in the catalog. The RPC ships
--     today returning NULLs for KPIs that depend on data sources we have
--     not wired yet (ad spend, attribution). It still respects RLS so the
--     frontend can render placeholders without leaking other tenants.
--   • Each RPC returns exactly one row, mirroring get_dashboard_indicators.

BEGIN;

-- ─────────────────────────────────────────────────────────────────────
-- 0. Helper: resolve period code → (window_start, window_end, prev_start, prev_end)
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2._resolve_period(p_period text)
RETURNS TABLE (
  period_code  text,
  window_start date,
  window_end   date,
  prev_start   date,
  prev_end     date
)
LANGUAGE plpgsql IMMUTABLE
AS $$
DECLARE
  code  text := lower(coalesce(p_period, '30d'));
  today date := CURRENT_DATE;
  win_size interval;
  ws date;
  we date;
BEGIN
  -- Calendar-anchored windows
  IF code IN ('mtd') THEN
    ws := date_trunc('month', today)::date;
    we := today + 1;  -- exclusive upper bound
    period_code := code;
    window_start := ws;
    window_end   := we;
    prev_start   := (date_trunc('month', today) - interval '1 month')::date;
    prev_end     := date_trunc('month', today)::date;
    RETURN NEXT;
    RETURN;
  ELSIF code IN ('ytd') THEN
    ws := date_trunc('year', today)::date;
    we := today + 1;
    period_code := code;
    window_start := ws;
    window_end   := we;
    prev_start   := (date_trunc('year', today) - interval '1 year')::date;
    prev_end     := (date_trunc('year', today))::date;
    RETURN NEXT;
    RETURN;
  END IF;

  -- Rolling windows
  win_size := CASE code
    WHEN '7d'      THEN interval '7 days'
    WHEN 'week'    THEN interval '7 days'
    WHEN '30d'     THEN interval '30 days'
    WHEN 'month'   THEN interval '30 days'
    WHEN '90d'     THEN interval '90 days'
    WHEN 'quarter' THEN interval '90 days'
    WHEN 'year'    THEN interval '365 days'
    WHEN 'custom'  THEN interval '30 days'  -- fallback; explicit-range RPC TBD
    ELSE interval '30 days'
  END;

  ws := (today - win_size)::date;
  we := today + 1;
  period_code  := code;
  window_start := ws;
  window_end   := we;
  prev_start   := (today - (win_size * 2))::date;
  prev_end     := ws;
  RETURN NEXT;
END;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2._resolve_period(text) TO authenticated;

-- ─────────────────────────────────────────────────────────────────────
-- 1. Finance — receita, COGS, margens, ticket, growth (per §6.1)
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.get_finance_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  receita_liquida          numeric,
  custo_total              numeric,
  margem_bruta_perc        numeric,
  margem_operacional_perc  numeric,
  ticket_medio             numeric,
  receita_yoy_perc         numeric,
  crescimento_receita_perc numeric,
  total_pedidos            bigint,
  period                   text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  cur AS (
    SELECT
      COALESCE(SUM(ft.valor) FILTER (
        WHERE COALESCE(tt.categoria, '') NOT IN ('despesa','custo','fiscal_saida')
          AND COALESCE(ft.status, '') NOT IN ('cancelled','invalid')
      ), 0)::numeric AS receita,
      COALESCE(SUM(ft.valor) FILTER (
        WHERE COALESCE(tt.categoria, '') IN ('despesa','custo')
      ), 0)::numeric AS custos,
      COUNT(DISTINCT ft.documento) FILTER (
        WHERE COALESCE(tt.categoria, '') NOT IN ('despesa','custo','fiscal_saida')
      )::bigint AS pedidos
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_tipo_transacao tt ON tt.tipo_id = ft.tipo_id
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
  ),
  prev AS (
    SELECT
      COALESCE(SUM(ft.valor) FILTER (
        WHERE COALESCE(tt.categoria, '') NOT IN ('despesa','custo','fiscal_saida')
          AND COALESCE(ft.status, '') NOT IN ('cancelled','invalid')
      ), 0)::numeric AS receita
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_tipo_transacao tt ON tt.tipo_id = ft.tipo_id
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.prev_start
      AND dd.data <  p.prev_end
  ),
  yoy AS (
    SELECT
      COALESCE(SUM(ft.valor) FILTER (
        WHERE COALESCE(tt.categoria, '') NOT IN ('despesa','custo','fiscal_saida')
          AND COALESCE(ft.status, '') NOT IN ('cancelled','invalid')
      ), 0)::numeric AS receita
    FROM analytics_v2.fato_transacoes ft
    LEFT JOIN analytics_v2.dim_tipo_transacao tt ON tt.tipo_id = ft.tipo_id
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= (p.window_start - interval '1 year')::date
      AND dd.data <  (p.window_end   - interval '1 year')::date
  )
  SELECT
    cur.receita                                               AS receita_liquida,
    cur.custos                                                AS custo_total,
    CASE WHEN cur.receita > 0
         THEN round(((cur.receita - cur.custos) / cur.receita) * 100, 2)
         ELSE NULL END                                        AS margem_bruta_perc,
    CASE WHEN cur.receita > 0
         THEN round(((cur.receita - cur.custos) / cur.receita) * 100, 2)
         ELSE NULL END                                        AS margem_operacional_perc,
    CASE WHEN cur.pedidos > 0
         THEN round(cur.receita / cur.pedidos, 2)
         ELSE 0::numeric END                                  AS ticket_medio,
    CASE WHEN yoy.receita > 0
         THEN round(((cur.receita - yoy.receita) / yoy.receita) * 100, 2)
         ELSE NULL END                                        AS receita_yoy_perc,
    CASE WHEN prev.receita > 0
         THEN round(((cur.receita - prev.receita) / prev.receita) * 100, 2)
         ELSE NULL END                                        AS crescimento_receita_perc,
    cur.pedidos                                               AS total_pedidos,
    (SELECT period_code FROM p)                               AS period
  FROM cur, prev, yoy;
$$;

COMMENT ON FUNCTION analytics_v2.get_finance_indicators(text) IS
  'Finance dimension KPIs (§6.1): receita_liquida, custo_total, margens, ticket_medio, receita_yoy_perc. Period: 7d|30d|90d|mtd|ytd|year (legacy week|month|quarter|year accepted).';

GRANT EXECUTE ON FUNCTION analytics_v2.get_finance_indicators(text) TO authenticated;

-- ─────────────────────────────────────────────────────────────────────
-- 2. Commercial — vendas, AOV, top clientes, recência (per §6.2)
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.get_commercial_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  pedidos_periodo            bigint,
  receita_periodo            numeric,
  ticket_medio               numeric,
  clientes_unicos            bigint,
  clientes_novos             bigint,
  clientes_recorrentes       bigint,
  recencia_media_dias        numeric,
  frequencia_media_mensal    numeric,
  churn_60d_perc             numeric,
  crescimento_receita_perc   numeric,
  period                     text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  cur AS (
    SELECT
      COUNT(DISTINCT ft.documento)::bigint                  AS pedidos,
      COALESCE(SUM(ft.valor), 0)::numeric                   AS receita,
      COUNT(DISTINCT ft.cliente_id)::bigint                 AS clientes_unicos
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
  ),
  prev AS (
    SELECT COALESCE(SUM(ft.valor), 0)::numeric AS receita
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.prev_start
      AND dd.data <  p.prev_end
  ),
  cli_agg AS (
    SELECT
      COUNT(*) FILTER (WHERE c.total_pedidos = 1)::bigint                   AS novos,
      COUNT(*) FILTER (WHERE c.total_pedidos > 1)::bigint                   AS recorrentes,
      COALESCE(AVG(c.dias_recencia)::numeric, 0)                             AS recencia,
      COALESCE(AVG(c.frequencia_mensal)::numeric, 0)                         AS frequencia,
      COUNT(*) FILTER (WHERE c.dias_recencia > 60)::numeric                  AS inativos_60d,
      NULLIF(COUNT(*)::numeric, 0)                                           AS total_clientes
    FROM analytics_v2.dim_clientes c
    WHERE c.client_id = public.get_my_client_id()
  )
  SELECT
    cur.pedidos,
    cur.receita,
    CASE WHEN cur.pedidos > 0
         THEN round(cur.receita / cur.pedidos, 2)
         ELSE 0::numeric END                                AS ticket_medio,
    cur.clientes_unicos,
    cli_agg.novos                                           AS clientes_novos,
    cli_agg.recorrentes                                     AS clientes_recorrentes,
    round(cli_agg.recencia, 1)                              AS recencia_media_dias,
    round(cli_agg.frequencia, 2)                            AS frequencia_media_mensal,
    CASE WHEN cli_agg.total_clientes IS NOT NULL
         THEN round((cli_agg.inativos_60d / cli_agg.total_clientes) * 100, 2)
         ELSE NULL END                                      AS churn_60d_perc,
    CASE WHEN prev.receita > 0
         THEN round(((cur.receita - prev.receita) / prev.receita) * 100, 2)
         ELSE NULL END                                      AS crescimento_receita_perc,
    (SELECT period_code FROM p)                             AS period
  FROM cur, prev, cli_agg;
$$;

COMMENT ON FUNCTION analytics_v2.get_commercial_indicators(text) IS
  'Commercial dimension KPIs (§6.2): pedidos, receita, AOV, clientes únicos/novos/recorrentes, recência, frequência, churn 60d.';

GRANT EXECUTE ON FUNCTION analytics_v2.get_commercial_indicators(text) TO authenticated;

-- ─────────────────────────────────────────────────────────────────────
-- 3. Inventory — SKUs, giro, cobertura (per §6.3)
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.get_inventory_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  skus_ativos                  bigint,
  skus_total                   bigint,
  quantidade_vendida_periodo   numeric,
  receita_skus_periodo         numeric,
  giro_estimado                numeric,
  ticket_medio_sku             numeric,
  cobertura_top20_perc         numeric,
  stockout_rate_perc           numeric,
  crescimento_quantidade_perc  numeric,
  period                       text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  cur AS (
    SELECT
      COUNT(DISTINCT ft.produto_id)::bigint                   AS skus_movimentados,
      COALESCE(SUM(ft.quantidade), 0)::numeric                AS qtd,
      COALESCE(SUM(ft.valor), 0)::numeric                     AS receita
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
  ),
  prev AS (
    SELECT COALESCE(SUM(ft.quantidade), 0)::numeric AS qtd
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON dd.data_id = ft.data_competencia_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.prev_start
      AND dd.data <  p.prev_end
  ),
  inv AS (
    SELECT
      COUNT(*)::bigint                                                                          AS total_skus,
      COUNT(*) FILTER (WHERE COALESCE(i.quantidade_total_vendida, 0) > 0)::bigint               AS ativos,
      COUNT(*) FILTER (WHERE COALESCE(i.quantidade_total_vendida, 0) = 0)::bigint               AS sem_giro,
      COALESCE(SUM(i.receita_total), 0)::numeric                                                AS receita_total
    FROM analytics_v2.dim_inventory i
    WHERE i.client_id = public.get_my_client_id()
  ),
  pareto AS (
    -- Top 20% SKUs (by receita_total) revenue share — Pareto coverage of class A.
    SELECT
      COALESCE(SUM(i.receita_total) FILTER (
        WHERE i.rn <= GREATEST(1, ceil(i.cnt * 0.20))
      ), 0)::numeric AS top_receita,
      COALESCE(SUM(i.receita_total), 0)::numeric AS total_receita
    FROM (
      SELECT
        i.receita_total,
        ROW_NUMBER() OVER (ORDER BY i.receita_total DESC NULLS LAST) AS rn,
        COUNT(*) OVER ()                                              AS cnt
      FROM analytics_v2.dim_inventory i
      WHERE i.client_id = public.get_my_client_id()
    ) i
  )
  SELECT
    inv.ativos                                                  AS skus_ativos,
    inv.total_skus                                              AS skus_total,
    cur.qtd                                                     AS quantidade_vendida_periodo,
    cur.receita                                                 AS receita_skus_periodo,
    -- Approximate inventory turnover for the period: qty sold / active SKU count
    -- (true turnover requires avg inventory on hand which we do not yet ingest).
    CASE WHEN inv.ativos > 0
         THEN round(cur.qtd / inv.ativos, 2)
         ELSE NULL END                                          AS giro_estimado,
    CASE WHEN cur.skus_movimentados > 0
         THEN round(cur.receita / cur.skus_movimentados, 2)
         ELSE 0::numeric END                                    AS ticket_medio_sku,
    CASE WHEN pareto.total_receita > 0
         THEN round((pareto.top_receita / pareto.total_receita) * 100, 2)
         ELSE NULL END                                          AS cobertura_top20_perc,
    CASE WHEN inv.total_skus > 0
         THEN round((inv.sem_giro::numeric / inv.total_skus) * 100, 2)
         ELSE NULL END                                          AS stockout_rate_perc,
    CASE WHEN prev.qtd > 0
         THEN round(((cur.qtd - prev.qtd) / prev.qtd) * 100, 2)
         ELSE NULL END                                          AS crescimento_quantidade_perc,
    (SELECT period_code FROM p)                                 AS period
  FROM cur, prev, inv, pareto;
$$;

COMMENT ON FUNCTION analytics_v2.get_inventory_indicators(text) IS
  'Inventory KPIs (§6.3): SKUs ativos/total, qtd e receita do período, giro estimado, cobertura Pareto top-20% e stockout rate (proxy via SKUs sem giro).';

GRANT EXECUTE ON FUNCTION analytics_v2.get_inventory_indicators(text) TO authenticated;

-- ─────────────────────────────────────────────────────────────────────
-- 4. Supply / Procurement — RFQ + PO funnel (per §6.4)
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.get_supply_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
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
  period                    text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  rfq_cur AS (
    SELECT
      COUNT(*) FILTER (WHERE r.status IN ('sent','responded'))::bigint                AS abertas,
      COUNT(*) FILTER (WHERE r.status = 'sent')::bigint                               AS enviadas,
      COUNT(*) FILTER (WHERE r.status = 'responded')::bigint                          AS respondidas,
      AVG(EXTRACT(EPOCH FROM (r.updated_at - r.sent_at)) / 3600.0) FILTER (
        WHERE r.status = 'responded' AND r.sent_at IS NOT NULL
      )::numeric                                                                       AS resp_h
    FROM public.rfq_requests r
    CROSS JOIN p
    WHERE r.client_id = public.get_my_client_id()::uuid
      AND r.created_at::date >= p.window_start
      AND r.created_at::date <  p.window_end
  ),
  po_cur AS (
    SELECT
      COUNT(*) FILTER (WHERE po.status = 'approved')::bigint                          AS aprovadas,
      COUNT(*) FILTER (WHERE po.status = 'pending_approval')::bigint                  AS pendentes,
      COALESCE(SUM(po.total_amount) FILTER (WHERE po.status IN ('approved','sent')), 0)::numeric AS spend,
      AVG(EXTRACT(EPOCH FROM (po.approved_at - po.created_at)) / 3600.0) FILTER (
        WHERE po.approved_at IS NOT NULL
      )::numeric                                                                       AS cycle_h
    FROM public.purchase_orders po
    CROSS JOIN p
    WHERE po.client_id = public.get_my_client_id()::uuid
      AND po.created_at::date >= p.window_start
      AND po.created_at::date <  p.window_end
  ),
  forn AS (
    SELECT
      COUNT(*) FILTER (WHERE f.frequencia_mensal IS NOT NULL AND f.frequencia_mensal > 0)::bigint AS ativos,
      COALESCE(SUM(f.receita_total), 0)::numeric                                                  AS spend_total,
      MAX(f.receita_total)                                                                        AS top_receita
    FROM analytics_v2.dim_fornecedores f
    WHERE f.client_id = public.get_my_client_id()
  )
  SELECT
    rfq_cur.abertas,
    rfq_cur.enviadas,
    rfq_cur.respondidas,
    CASE WHEN (rfq_cur.enviadas + rfq_cur.respondidas) > 0
         THEN round((rfq_cur.respondidas::numeric / (rfq_cur.enviadas + rfq_cur.respondidas)) * 100, 2)
         ELSE NULL END                                                                AS taxa_resposta_perc,
    CASE WHEN rfq_cur.resp_h IS NOT NULL THEN round(rfq_cur.resp_h, 2) ELSE NULL END  AS tempo_resposta_medio_h,
    po_cur.aprovadas                                                                  AS pos_aprovadas,
    po_cur.pendentes                                                                  AS pos_pendentes_aprovacao,
    po_cur.spend                                                                      AS spend_periodo,
    forn.ativos                                                                       AS fornecedores_ativos,
    CASE WHEN forn.spend_total > 0 AND forn.top_receita IS NOT NULL
         THEN round((forn.top_receita / forn.spend_total) * 100, 2)
         ELSE NULL END                                                                AS concentracao_top_perc,
    CASE WHEN po_cur.cycle_h IS NOT NULL THEN round(po_cur.cycle_h, 2) ELSE NULL END  AS cycle_time_medio_h,
    (SELECT period_code FROM p)                                                       AS period
  FROM rfq_cur, po_cur, forn;
$$;

COMMENT ON FUNCTION analytics_v2.get_supply_indicators(text) IS
  'Supply/Procurement KPIs (§6.4): RFQ funnel, taxa resposta, POs aprovadas/pendentes, spend, fornecedores ativos, concentração e cycle time.';

GRANT EXECUTE ON FUNCTION analytics_v2.get_supply_indicators(text) TO authenticated;

-- ─────────────────────────────────────────────────────────────────────
-- 5. Marketing (PRO) — best-effort placeholders until ad/web ingest lands (§6.5)
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.get_marketing_indicators(
  p_period text DEFAULT '30d'
)
RETURNS TABLE (
  novos_clientes_periodo    bigint,
  receita_novos_clientes    numeric,
  conversao_campanha_perc   numeric,   -- via audit_log outbound (TODO when EPIC-F lands)
  engajamento_whatsapp_perc numeric,   -- via Twilio webhooks (TODO)
  taxa_optout_perc          numeric,   -- via Twilio webhooks (TODO)
  cac                       numeric,   -- requires ad spend ingest (NULL today)
  ltv_cac_ratio             numeric,   -- derived; NULL until CAC available
  roas                      numeric,   -- requires ad spend ingest (NULL today)
  ctr_perc                  numeric,   -- external sources (NULL today)
  period                    text
)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH p AS (SELECT * FROM analytics_v2._resolve_period(p_period)),
  novos AS (
    SELECT
      COUNT(DISTINCT ft.cliente_id) FILTER (
        WHERE c.total_pedidos = 1
      )::bigint AS qtd,
      COALESCE(SUM(ft.valor) FILTER (
        WHERE c.total_pedidos = 1
      ), 0)::numeric AS receita
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd     ON dd.data_id   = ft.data_competencia_id
    LEFT JOIN analytics_v2.dim_clientes c ON c.cliente_id = ft.cliente_id
                                         AND c.client_id  = ft.client_id
    CROSS JOIN p
    WHERE ft.client_id = public.get_my_client_id()
      AND dd.data >= p.window_start
      AND dd.data <  p.window_end
  )
  SELECT
    novos.qtd                       AS novos_clientes_periodo,
    novos.receita                   AS receita_novos_clientes,
    NULL::numeric                   AS conversao_campanha_perc,
    NULL::numeric                   AS engajamento_whatsapp_perc,
    NULL::numeric                   AS taxa_optout_perc,
    NULL::numeric                   AS cac,
    NULL::numeric                   AS ltv_cac_ratio,
    NULL::numeric                   AS roas,
    NULL::numeric                   AS ctr_perc,
    (SELECT period_code FROM p)     AS period
  FROM novos;
$$;

COMMENT ON FUNCTION analytics_v2.get_marketing_indicators(text) IS
  'Marketing KPIs (§6.5, PRO). Today returns novos clientes do período + NULLs for KPIs that require ad-spend / Twilio webhook ingest (delivered in EPIC-F / EPIC-H).';

GRANT EXECUTE ON FUNCTION analytics_v2.get_marketing_indicators(text) TO authenticated;

COMMIT;
