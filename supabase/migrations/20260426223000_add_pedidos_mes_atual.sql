BEGIN;

DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_dashboard CASCADE;

CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard AS
WITH current_month AS (
  SELECT ft.client_id,
    sum(ft.valor) AS receita,
    sum(ft.quantidade) AS quantidade,
    count(DISTINCT ft.cliente_id) AS clientes_unicos,
    count(DISTINCT ft.produto_id) AS produtos_unicos,
    count(DISTINCT ft.fornecedor_id) AS fornecedores_unicos,
    count(DISTINCT ft.documento) AS pedidos
  FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= date_trunc('month'::text, CURRENT_DATE::timestamp with time zone)::date
    AND dd.data < (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) + '1 mon'::interval)::date
  GROUP BY ft.client_id
), previous_month AS (
  SELECT ft.client_id,
    sum(ft.valor) AS receita,
    sum(ft.quantidade) AS quantidade,
    count(DISTINCT ft.cliente_id) AS clientes_unicos,
    count(DISTINCT ft.produto_id) AS produtos_unicos,
    count(DISTINCT ft.documento) AS pedidos
  FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= (date_trunc('month'::text, CURRENT_DATE::timestamp with time zone) - '1 mon'::interval)::date
    AND dd.data < date_trunc('month'::text, CURRENT_DATE::timestamp with time zone)::date
  GROUP BY ft.client_id
), client_agg AS (
  SELECT c.client_id,
    count(*) AS total_clientes,
    count(*) FILTER (WHERE c.dias_recencia <= 90) AS clientes_ativos,
    count(*) FILTER (WHERE c.total_pedidos = 1) AS clientes_novos,
    count(DISTINCT c.endereco_uf) FILTER (WHERE c.endereco_uf IS NOT NULL) AS total_regioes
  FROM analytics_v2.dim_clientes c
  GROUP BY c.client_id
), fornecedor_agg AS (
  SELECT f.client_id,
    count(*) AS total_fornecedores,
    COALESCE(avg(f.frequencia_mensal), 0::numeric) AS frequencia_media_fornecedores
  FROM analytics_v2.dim_fornecedores f
  GROUP BY f.client_id
), inventory_agg AS (
  SELECT i.client_id,
    count(*) AS total_produtos,
    COALESCE(sum(i.quantidade_total_vendida), 0::numeric) AS quantidade_total_vendida
  FROM analytics_v2.dim_inventory i
  GROUP BY i.client_id
), fact_agg AS (
  SELECT ft.client_id,
    count(DISTINCT ft.documento) AS total_pedidos,
    COALESCE(sum(ft.valor), 0::numeric) AS receita_total,
    CASE
      WHEN count(DISTINCT ft.documento) > 0 THEN (sum(ft.valor) / count(DISTINCT ft.documento)::numeric)::numeric(15,2)
      ELSE 0::numeric
    END AS ticket_medio
  FROM analytics_v2.fato_transacoes ft
  GROUP BY ft.client_id
)
SELECT cl.client_id,
  COALESCE(ca.total_clientes, 0::bigint) AS total_clientes,
  COALESCE(fa2.total_fornecedores, 0::bigint) AS total_fornecedores,
  COALESCE(ia.total_produtos, 0::bigint) AS total_produtos,
  COALESCE(fa.total_pedidos, 0::bigint) AS total_pedidos,
  COALESCE(fa.receita_total, 0::numeric) AS receita_total,
  COALESCE(fa.ticket_medio, 0::numeric) AS ticket_medio,
  COALESCE(ia.quantidade_total_vendida, 0::numeric) AS quantidade_total_vendida,
  COALESCE(cm.receita, 0::numeric) AS receita_mes_atual,
  COALESCE(cm.quantidade, 0::numeric) AS quantidade_mes_atual,
  COALESCE(cm.clientes_unicos, 0::bigint) AS clientes_mes_atual,
  COALESCE(cm.produtos_unicos, 0::bigint) AS produtos_mes_atual,
  COALESCE(cm.fornecedores_unicos, 0::bigint) AS fornecedores_mes_atual,
  COALESCE(cm.pedidos, 0::bigint) AS pedidos_mes_atual,
  CASE
    WHEN COALESCE(pm.receita, 0::numeric) > 0::numeric THEN ((COALESCE(cm.receita, 0::numeric) - pm.receita) / pm.receita * 100::numeric)::numeric(10,2)
    ELSE NULL::numeric
  END AS crescimento_receita,
  CASE
    WHEN COALESCE(pm.clientes_unicos, 0::bigint) > 0 THEN ((COALESCE(cm.clientes_unicos, 0::bigint)::numeric - pm.clientes_unicos::numeric) / pm.clientes_unicos::numeric * 100::numeric)::numeric(10,2)
    ELSE NULL::numeric
  END AS crescimento_clientes,
  CASE
    WHEN COALESCE(pm.produtos_unicos, 0::bigint) > 0 THEN ((COALESCE(cm.produtos_unicos, 0::bigint)::numeric - pm.produtos_unicos::numeric) / pm.produtos_unicos::numeric * 100::numeric)::numeric(10,2)
    ELSE NULL::numeric
  END AS crescimento_produtos,
  CASE
    WHEN COALESCE(pm.quantidade, 0::numeric) > 0::numeric THEN ((COALESCE(cm.quantidade, 0::numeric) - pm.quantidade) / pm.quantidade * 100::numeric)::numeric(10,2)
    ELSE NULL::numeric
  END AS crescimento_quantidade,
  CASE
    WHEN COALESCE(pm.pedidos, 0::bigint) > 0 THEN ((COALESCE(cm.pedidos, 0::bigint)::numeric - pm.pedidos::numeric) / pm.pedidos::numeric * 100::numeric)::numeric(10,2)
    ELSE NULL::numeric
  END AS crescimento_pedidos,
  COALESCE(fa2.frequencia_media_fornecedores, 0::numeric) AS frequencia_media_fornecedores,
  COALESCE(ca.total_regioes, 0::bigint) AS total_regioes,
  to_char(CURRENT_DATE::timestamp with time zone, 'YYYY-MM'::text) AS ultimo_mes,
  COALESCE(ca.clientes_ativos, 0::bigint) AS clientes_ativos,
  COALESCE(ca.clientes_novos, 0::bigint) AS clientes_novos,
  now() AS gerado_em
FROM (SELECT DISTINCT ft.client_id FROM analytics_v2.fato_transacoes ft) cl
  LEFT JOIN current_month cm ON cm.client_id = cl.client_id
  LEFT JOIN previous_month pm ON pm.client_id = cl.client_id
  LEFT JOIN client_agg ca ON ca.client_id = cl.client_id
  LEFT JOIN fornecedor_agg fa2 ON fa2.client_id = cl.client_id
  LEFT JOIN inventory_agg ia ON ia.client_id = cl.client_id
  LEFT JOIN fact_agg fa ON fa.client_id = cl.client_id;

CREATE UNIQUE INDEX ux_mv_resumo_dashboard_client ON analytics_v2.mv_resumo_dashboard (client_id);

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
  pedidos_mes_atual,
  crescimento_receita,
  crescimento_clientes,
  crescimento_produtos,
  crescimento_quantidade,
  crescimento_pedidos,
  frequencia_media_fornecedores,
  total_regioes,
  ultimo_mes,
  clientes_ativos,
  clientes_novos,
  gerado_em
FROM analytics_v2.mv_resumo_dashboard
WHERE client_id = public.get_my_client_id();

GRANT SELECT ON analytics_v2.v_resumo_dashboard TO authenticated;
GRANT SELECT ON analytics_v2.mv_resumo_dashboard TO authenticated;

REFRESH MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard;

COMMIT;

SELECT client_id, total_pedidos, pedidos_mes_atual, crescimento_pedidos
FROM analytics_v2.mv_resumo_dashboard;
