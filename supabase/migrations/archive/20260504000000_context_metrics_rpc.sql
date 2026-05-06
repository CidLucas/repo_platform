-- ─────────────────────────────────────────────────────────────────────────────
-- analytics_v2.get_context_metrics_for_client  (REPLACE v1 — 5 KPIs → 15)
--
-- Computes every KPI derivable from fato_transacoes + dimension tables.
-- Returns one row per KPI enriched with:
--
--   current_value    — MTD total for the current calendar month (excludes today)
--   prev_month_value — most recent complete-month total
--   avg_6m           — trailing 6-complete-month average
--   mom_pct          — (current - prev) / prev × 100
--   vs_6m_avg_pct    — (current - avg_6m) / avg_6m × 100
--   streak_months    — consecutive complete months trending in same direction
--                      (+N = rising, -N = falling, 0 = flat/insufficient data)
--
-- KPIs (15 total):
--   Finance    (3): receita_liquida, ticket_medio, total_pedidos
--   Commercial (6): clientes_unicos, clientes_novos, clientes_recorrentes,
--                   taxa_recorrencia_perc, receita_por_cliente, frequencia_media
--   Inventory  (3): skus_ativos, quantidade_vendida, receita_por_sku
--   Supply     (3): fornecedores_ativos, receita_por_fornecedor,
--                   concentracao_top1_fornecedor_perc
--
-- SECURITY DEFINER — service_role only. Bypasses RLS intentionally.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION analytics_v2.get_context_metrics_for_client(
  p_client_id uuid
)
RETURNS TABLE (
  dimension        text,
  kpi              text,
  label            text,
  unit             text,
  current_value    numeric,
  prev_month_value numeric,
  avg_6m           numeric,
  mom_pct          numeric,
  vs_6m_avg_pct    numeric,
  streak_months    integer
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = analytics_v2, public
AS $$
WITH

-- ── 1. Single scan of fato_transacoes, grouped by month.
--       Excludes today (partial day) so current MTD is clean.
--       Includes current month (filtered later into complete vs. current).
all_monthly AS (
  SELECT
    date_trunc('month', dd.data)::date               AS mes,
    COALESCE(SUM(ft.valor),                    0)    AS receita,
    COUNT(DISTINCT ft.transacao_id)::numeric          AS total_pedidos,
    COALESCE(SUM(ft.quantidade),               0)    AS quantidade,
    COUNT(DISTINCT ft.cliente_id)::numeric            AS clientes_unicos,
    COUNT(DISTINCT ft.fornecedor_id)::numeric         AS fornecedores_ativos,
    COUNT(DISTINCT ft.produto_id)::numeric            AS skus_ativos,
    CASE
      WHEN COUNT(DISTINCT ft.transacao_id) > 0
        THEN SUM(ft.valor) / COUNT(DISTINCT ft.transacao_id)
      ELSE 0
    END                                               AS ticket_medio,
    CASE
      WHEN COUNT(DISTINCT ft.cliente_id) > 0
        THEN COUNT(DISTINCT ft.transacao_id)::numeric
             / COUNT(DISTINCT ft.cliente_id)
      ELSE 0
    END                                               AS frequencia_media,
    CASE
      WHEN COUNT(DISTINCT ft.cliente_id) > 0
        THEN SUM(ft.valor) / COUNT(DISTINCT ft.cliente_id)
      ELSE 0
    END                                               AS receita_por_cliente,
    CASE
      WHEN COUNT(DISTINCT ft.produto_id) > 0
        THEN SUM(ft.valor) / COUNT(DISTINCT ft.produto_id)
      ELSE 0
    END                                               AS receita_por_sku,
    CASE
      WHEN COUNT(DISTINCT ft.fornecedor_id) > 0
        THEN SUM(ft.valor) / COUNT(DISTINCT ft.fornecedor_id)
      ELSE 0
    END                                               AS receita_por_fornecedor
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas       dd
    ON  ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id
    AND dd.data IS NOT NULL
    AND dd.data  < CURRENT_DATE             -- exclude today (partial)
  GROUP BY date_trunc('month', dd.data)::date
),

-- ── 2. (mes, cliente_id) used to compute novos and recorrentes.
--       Covers all months including current.
monthly_buyers AS (
  SELECT DISTINCT
    date_trunc('month', dd.data)::date AS mes,
    ft.cliente_id
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas       dd
    ON  ft.data_competencia_id = dd.data_id
  WHERE ft.client_id     = p_client_id
    AND ft.cliente_id    IS NOT NULL
    AND dd.data          IS NOT NULL
    AND dd.data           < CURRENT_DATE
),

-- ── 3. First purchase month per customer → used for clientes_novos.
first_purchases AS (
  SELECT
    ft.cliente_id,
    date_trunc('month', MIN(dd.data))::date AS first_month
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas       dd
    ON  ft.data_competencia_id = dd.data_id
  WHERE ft.client_id  = p_client_id
    AND ft.cliente_id IS NOT NULL
    AND dd.data       IS NOT NULL
  GROUP BY ft.cliente_id
),

-- ── 4. Count novos per month.
novos_por_mes AS (
  SELECT first_month AS mes, COUNT(*)::numeric AS clientes_novos
  FROM   first_purchases
  GROUP  BY first_month
),

-- ── 5. Clientes recorrentes per month: bought in M AND in M-1.
recorrentes_por_mes AS (
  SELECT
    a.mes,
    COUNT(*)::numeric AS clientes_recorrentes
  FROM monthly_buyers a
  JOIN monthly_buyers b
    ON  b.cliente_id = a.cliente_id
    AND b.mes = (a.mes - INTERVAL '1 month')::date
  GROUP BY a.mes
),

-- ── 6. Top-1 supplier revenue concentration per month.
top1_clean AS (
  SELECT
    mes,
    ROUND(MAX(rev_forn) / NULLIF(SUM(rev_forn), 0) * 100, 1) AS concentracao_top1_perc
  FROM (
    SELECT
      date_trunc('month', dd.data)::date AS mes,
      ft.fornecedor_id,
      SUM(ft.valor)                       AS rev_forn
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas       dd
      ON  ft.data_competencia_id = dd.data_id
    WHERE ft.client_id      = p_client_id
      AND ft.fornecedor_id  IS NOT NULL
      AND dd.data           IS NOT NULL
      AND dd.data            < CURRENT_DATE
    GROUP BY date_trunc('month', dd.data)::date, ft.fornecedor_id
  ) s
  GROUP BY mes
),

-- ── 7. Enrich all_monthly with derived metrics.
--       Self-join on (mes - 1 month) to get prev clientes_unicos for recorrência.
enriched AS (
  SELECT
    am.mes,
    am.receita,
    am.ticket_medio,
    am.total_pedidos,
    am.quantidade,
    am.clientes_unicos,
    am.frequencia_media,
    am.receita_por_cliente,
    am.skus_ativos,
    am.receita_por_sku,
    am.fornecedores_ativos,
    am.receita_por_fornecedor,
    COALESCE(np.clientes_novos,        0)  AS clientes_novos,
    COALESCE(rp.clientes_recorrentes,  0)  AS clientes_recorrentes,
    CASE
      WHEN COALESCE(am_prev.clientes_unicos, 0) > 0
        THEN ROUND(
          COALESCE(rp.clientes_recorrentes, 0) / am_prev.clientes_unicos * 100,
        1)
      ELSE 0
    END                                    AS taxa_recorrencia_perc,
    COALESCE(t1.concentracao_top1_perc, 0) AS concentracao_top1_fornecedor_perc
  FROM all_monthly am
  LEFT JOIN all_monthly        am_prev ON am_prev.mes = (am.mes - INTERVAL '1 month')::date
  LEFT JOIN novos_por_mes      np      ON np.mes  = am.mes
  LEFT JOIN recorrentes_por_mes rp     ON rp.mes  = am.mes
  LEFT JOIN top1_clean         t1      ON t1.mes  = am.mes
),

-- ── 8a. Determine the reference month:
--        Use the current calendar month (MTD) if it has any rows.
--        Fall back to the most recent complete month otherwise.
--        This prevents an empty result when no transactions have been
--        ingested yet for the current month (e.g., data lags a few days).
ref_month AS (
  SELECT COALESCE(
    (SELECT mes FROM enriched
     WHERE mes = date_trunc('month', CURRENT_DATE)::date
     LIMIT 1),
    (SELECT mes FROM enriched
     WHERE mes < date_trunc('month', CURRENT_DATE)::date
     ORDER BY mes DESC LIMIT 1)
  ) AS mes
),

-- ── 8b. Split enriched rows into:
--        current_month  — the reference month (MTD or most recent complete)
--        complete_months — every month strictly before the reference month
--        This means prev_month / avg_6m / streak are always relative to
--        whatever month we're treating as "current".
complete_months AS (
  SELECT e.* FROM enriched e, ref_month r
  WHERE e.mes < r.mes
),

current_month AS (
  SELECT e.* FROM enriched e, ref_month r
  WHERE e.mes = r.mes
),

-- ── 9. Unpivot complete months → long format (kpi, mes, val).
--       One row per KPI per month — window functions applied uniformly below.
long_complete AS (
  SELECT mes, 'receita_liquida'                   AS kpi, receita                          AS val FROM complete_months
  UNION ALL
  SELECT mes, 'ticket_medio',                              ticket_medio                          FROM complete_months
  UNION ALL
  SELECT mes, 'total_pedidos',                             total_pedidos                         FROM complete_months
  UNION ALL
  SELECT mes, 'quantidade_vendida',                        quantidade                            FROM complete_months
  UNION ALL
  SELECT mes, 'clientes_unicos',                           clientes_unicos                       FROM complete_months
  UNION ALL
  SELECT mes, 'clientes_novos',                            clientes_novos                        FROM complete_months
  UNION ALL
  SELECT mes, 'clientes_recorrentes',                      clientes_recorrentes                  FROM complete_months
  UNION ALL
  SELECT mes, 'taxa_recorrencia_perc',                     taxa_recorrencia_perc                 FROM complete_months
  UNION ALL
  SELECT mes, 'receita_por_cliente',                       receita_por_cliente                   FROM complete_months
  UNION ALL
  SELECT mes, 'frequencia_media',                          frequencia_media                      FROM complete_months
  UNION ALL
  SELECT mes, 'skus_ativos',                               skus_ativos                           FROM complete_months
  UNION ALL
  SELECT mes, 'receita_por_sku',                           receita_por_sku                       FROM complete_months
  UNION ALL
  SELECT mes, 'fornecedores_ativos',                       fornecedores_ativos                   FROM complete_months
  UNION ALL
  SELECT mes, 'receita_por_fornecedor',                    receita_por_fornecedor                FROM complete_months
  UNION ALL
  SELECT mes, 'concentracao_top1_fornecedor_perc',         concentracao_top1_fornecedor_perc     FROM complete_months
),

-- ── 10. Unpivot current month → long format.
long_current AS (
  SELECT 'receita_liquida'                   AS kpi, receita                          AS val FROM current_month
  UNION ALL
  SELECT 'ticket_medio',                              ticket_medio                          FROM current_month
  UNION ALL
  SELECT 'total_pedidos',                             total_pedidos                         FROM current_month
  UNION ALL
  SELECT 'quantidade_vendida',                        quantidade                            FROM current_month
  UNION ALL
  SELECT 'clientes_unicos',                           clientes_unicos                       FROM current_month
  UNION ALL
  SELECT 'clientes_novos',                            clientes_novos                        FROM current_month
  UNION ALL
  SELECT 'clientes_recorrentes',                      clientes_recorrentes                  FROM current_month
  UNION ALL
  SELECT 'taxa_recorrencia_perc',                     taxa_recorrencia_perc                 FROM current_month
  UNION ALL
  SELECT 'receita_por_cliente',                       receita_por_cliente                   FROM current_month
  UNION ALL
  SELECT 'frequencia_media',                          frequencia_media                      FROM current_month
  UNION ALL
  SELECT 'skus_ativos',                               skus_ativos                           FROM current_month
  UNION ALL
  SELECT 'receita_por_sku',                           receita_por_sku                       FROM current_month
  UNION ALL
  SELECT 'fornecedores_ativos',                       fornecedores_ativos                   FROM current_month
  UNION ALL
  SELECT 'receita_por_fornecedor',                    receita_por_fornecedor                FROM current_month
  UNION ALL
  SELECT 'concentracao_top1_fornecedor_perc',         concentracao_top1_fornecedor_perc     FROM current_month
),

-- ── 11. Rank complete months by recency for each KPI (rn=1 → most recent).
ranked AS (
  SELECT
    kpi, mes, val,
    ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC) AS rn
  FROM long_complete
),

-- ── 12. Previous month value (most recent complete month).
prev_month AS (
  SELECT kpi, val AS prev_val
  FROM   ranked
  WHERE  rn = 1
),

-- ── 13. Trailing 6-month average.
avg_6m AS (
  SELECT
    kpi,
    ROUND(AVG(val), 2) AS avg_val
  FROM   ranked
  WHERE  rn BETWEEN 1 AND 6
  GROUP  BY kpi
),

-- ── 14. MoM direction per month, most-recent first.
with_dir AS (
  SELECT
    kpi, mes, val,
    SIGN(val - LAG(val) OVER (PARTITION BY kpi ORDER BY mes)) AS dir,
    ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC)     AS rn
  FROM long_complete
),

-- ── 15. Direction of the most recent complete month.
latest_dir AS (
  SELECT kpi, dir
  FROM   with_dir
  WHERE  rn = 1
    AND  dir IS NOT NULL     -- NULL when only one month exists
),

-- ── 16. Tag each row: how many direction breaks since the most recent month?
--        rows with breaks = 0 → belong to the current consecutive streak.
streak_tagged AS (
  SELECT
    w.kpi,
    l.dir                                                       AS streak_dir,
    SUM(CASE WHEN w.dir != l.dir THEN 1 ELSE 0 END)
      OVER (
        PARTITION BY w.kpi
        ORDER BY     w.rn        -- rn=1 first (most recent → oldest)
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
      )                                                         AS breaks
  FROM   with_dir   w
  JOIN   latest_dir l USING (kpi)
  WHERE  w.dir IS NOT NULL
),

-- ── 17. Streak length, signed by direction.
streak AS (
  SELECT
    kpi,
    (MAX(streak_dir) * COUNT(*))::integer AS streak_months
  FROM   streak_tagged
  WHERE  breaks = 0
  GROUP  BY kpi
),

-- ── 18. Assemble: current value + comparison fields per KPI.
assembled AS (
  SELECT
    lc.kpi,
    ROUND(lc.val,                              2)  AS current_value,
    ROUND(pm.prev_val,                         2)  AS prev_month_value,
    a6.avg_val                                      AS avg_6m,
    CASE
      WHEN COALESCE(pm.prev_val, 0) <> 0
        THEN ROUND((lc.val - pm.prev_val) / pm.prev_val * 100, 1)
      ELSE NULL
    END                                             AS mom_pct,
    CASE
      WHEN COALESCE(a6.avg_val, 0) <> 0
        THEN ROUND((lc.val - a6.avg_val) / a6.avg_val * 100, 1)
      ELSE NULL
    END                                             AS vs_6m_avg_pct,
    COALESCE(st.streak_months, 0)                   AS streak_months
  FROM      long_current lc
  LEFT JOIN prev_month   pm USING (kpi)
  LEFT JOIN avg_6m       a6 USING (kpi)
  LEFT JOIN streak       st USING (kpi)
)

-- ── 19. Map kpi → dimension / label / unit and return.
SELECT
  m.dimension,
  m.kpi,
  m.label,
  m.unit,
  a.current_value,
  a.prev_month_value,
  a.avg_6m,
  a.mom_pct,
  a.vs_6m_avg_pct,
  a.streak_months
FROM assembled a
JOIN (VALUES
  -- Finance
  ('receita_liquida',                 'finance',     'Receita Líquida',               'BRL'  ),
  ('ticket_medio',                    'finance',     'Ticket Médio',                  'BRL'  ),
  ('total_pedidos',                   'finance',     'Total de Pedidos',              'count'),
  -- Commercial
  ('clientes_unicos',                 'commercial',  'Clientes Únicos',               'count'),
  ('clientes_novos',                  'commercial',  'Clientes Novos',                'count'),
  ('clientes_recorrentes',            'commercial',  'Clientes Recorrentes',          'count'),
  ('taxa_recorrencia_perc',           'commercial',  'Taxa de Recorrência',           '%'    ),
  ('receita_por_cliente',             'commercial',  'Receita por Cliente',           'BRL'  ),
  ('frequencia_media',                'commercial',  'Frequência Média de Compra',    'count'),
  -- Inventory
  ('skus_ativos',                     'inventory',   'SKUs Ativos',                   'count'),
  ('quantidade_vendida',              'inventory',   'Quantidade Vendida',            'count'),
  ('receita_por_sku',                 'inventory',   'Receita por SKU Ativo',         'BRL'  ),
  -- Supply
  ('fornecedores_ativos',             'supply',      'Fornecedores Ativos',           'count'),
  ('receita_por_fornecedor',          'supply',      'Receita por Fornecedor',        'BRL'  ),
  ('concentracao_top1_fornecedor_perc', 'supply',    'Concentração Top Fornecedor',   '%'    )
) AS m(kpi, dimension, label, unit)
  ON m.kpi = a.kpi
ORDER BY m.dimension, m.kpi;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.get_context_metrics_for_client(uuid)
  TO service_role;

REVOKE EXECUTE ON FUNCTION analytics_v2.get_context_metrics_for_client(uuid)
  FROM authenticated;
