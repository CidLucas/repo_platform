


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "analytics_v2";


ALTER SCHEMA "analytics_v2" OWNER TO "postgres";


CREATE SCHEMA IF NOT EXISTS "bigquery";


ALTER SCHEMA "bigquery" OWNER TO "postgres";


COMMENT ON SCHEMA "bigquery" IS 'Schema for BigQuery foreign tables via Supabase FDW';



CREATE EXTENSION IF NOT EXISTS "pg_cron" WITH SCHEMA "pg_catalog";






CREATE SCHEMA IF NOT EXISTS "fdw";


ALTER SCHEMA "fdw" OWNER TO "postgres";


CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "extensions";






COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE SCHEMA IF NOT EXISTS "util";


ALTER SCHEMA "util" OWNER TO "postgres";


CREATE SCHEMA IF NOT EXISTS "vector_db";


ALTER SCHEMA "vector_db" OWNER TO "postgres";


CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "wrappers" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "analytics_v2"."atualizar_agregados"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "statement_timeout" TO '0'
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_start timestamptz := clock_timestamp();
BEGIN
  RAISE NOTICE '[atualizar_agregados] client=%: updating dim aggregates', p_client_id;

  PERFORM analytics_v2.atualizar_dim_clientes(p_client_id);
  PERFORM analytics_v2.atualizar_dim_fornecedores(p_client_id);
  PERFORM analytics_v2.atualizar_dim_inventory(p_client_id);

  RAISE NOTICE '[atualizar_agregados] client=%: dims done in %.1fs, refreshing MVs',
    p_client_id, EXTRACT(epoch FROM clock_timestamp() - v_start);

  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_resumo_dashboard;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_series_temporal;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_distribuicao_regional;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_ultimos_pedidos;

  RAISE NOTICE '[atualizar_agregados] client=%: all done in %.1fs',
    p_client_id, EXTRACT(epoch FROM clock_timestamp() - v_start);
END;
$$;


ALTER FUNCTION "analytics_v2"."atualizar_agregados"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."atualizar_dim_clientes"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
BEGIN
  WITH agg AS (
    SELECT
      ft.cliente_id,
      COUNT(DISTINCT ft.transacao_id)                                     AS total_pedidos,
      COALESCE(SUM(ft.valor), 0)                                          AS receita_total,
      CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
           THEN COALESCE(SUM(ft.valor), 0) / COUNT(DISTINCT ft.transacao_id)
           ELSE 0 END                                                     AS ticket_medio,
      COALESCE(SUM(ft.quantidade), 0)                                     AS quantidade_total,
      MIN(dd.data)                                                        AS data_primeira_compra,
      MAX(dd.data)                                                        AS data_ultima_compra,
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
      AND ft.cliente_id IS NOT NULL
    GROUP BY ft.cliente_id
  ),
  scored AS (
    SELECT *,
      NTILE(3) OVER (ORDER BY dias_recencia    DESC NULLS LAST) AS r_score,
      NTILE(3) OVER (ORDER BY frequencia_mensal ASC  NULLS LAST) AS f_score,
      NTILE(3) OVER (ORDER BY receita_total     ASC  NULLS LAST) AS m_score
    FROM agg
  )
  UPDATE analytics_v2.dim_clientes dc
  SET
    total_pedidos        = s.total_pedidos,
    receita_total        = s.receita_total,
    ticket_medio         = s.ticket_medio,
    quantidade_total     = s.quantidade_total,
    data_primeira_compra = s.data_primeira_compra,
    data_ultima_compra   = s.data_ultima_compra,
    dias_recencia        = s.dias_recencia,
    frequencia_mensal    = s.frequencia_mensal,
    pontuacao_cluster    = (s.r_score + s.f_score + s.m_score)::numeric,
    nivel_cluster        = CASE
                             WHEN s.r_score + s.f_score + s.m_score >= 7 THEN 'Alto'
                             WHEN s.r_score + s.f_score + s.m_score >= 4 THEN 'Médio'
                             ELSE 'Baixo'
                           END,
    atualizado_em        = clock_timestamp()
  FROM scored s
  WHERE dc.client_id  = p_client_id
    AND dc.cliente_id = s.cliente_id;

  RAISE NOTICE '[atualizar_dim_clientes] client=%: done', p_client_id;
END;
$$;


ALTER FUNCTION "analytics_v2"."atualizar_dim_clientes"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."atualizar_dim_fornecedores"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
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
$$;


ALTER FUNCTION "analytics_v2"."atualizar_dim_fornecedores"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."atualizar_dim_inventory"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
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
$$;


ALTER FUNCTION "analytics_v2"."atualizar_dim_inventory"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."etl_resource_to_doc_type"("p_resource_type" "text") RETURNS "text"
    LANGUAGE "sql" IMMUTABLE
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
  SELECT CASE lower(trim(p_resource_type))
    WHEN 'orders'           THEN 'historico_pedidos'
    WHEN 'pedidos'          THEN 'historico_pedidos'
    WHEN 'products'         THEN 'catalogo_produtos'
    WHEN 'produtos'         THEN 'catalogo_produtos'
    WHEN 'inventory'        THEN 'controle_inventario'
    WHEN 'estoque'          THEN 'controle_inventario'
    WHEN 'customers'        THEN 'ficha_cliente'
    WHEN 'clientes'         THEN 'ficha_cliente'
    WHEN 'fornecedores'     THEN 'cadastro_fornecedores'
    WHEN 'suppliers'        THEN 'cadastro_fornecedores'
    WHEN 'financial'        THEN 'dre_mensal'
    WHEN 'dre'              THEN 'dre_mensal'
    WHEN 'fluxo_caixa'      THEN 'fluxo_caixa_diario'
    WHEN 'cashflow'         THEN 'fluxo_caixa_diario'
    ELSE NULL
  END;
$$;


ALTER FUNCTION "analytics_v2"."etl_resource_to_doc_type"("p_resource_type" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_annual_metrics_for_client"("p_client_id" "uuid") RETURNS TABLE("ano" integer, "receita" numeric, "total_pedidos" bigint, "clientes_unicos" bigint, "clientes_novos" bigint, "ticket_medio" numeric, "fornecedores_ativos" bigint, "skus_ativos" bigint, "quantidade_vendida" numeric, "is_partial" boolean, "yoy_receita_pct" numeric, "receita_anualizada" numeric)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
WITH

years AS (
  SELECT
    EXTRACT(YEAR FROM dd.data)::integer                            AS ano,
    COALESCE(SUM(ft.valor), 0)::numeric                            AS receita,
    COUNT(DISTINCT ft.transacao_id)                                AS total_pedidos,
    COUNT(DISTINCT ft.cliente_id)                                  AS clientes_unicos,
    COUNT(DISTINCT ft.fornecedor_id)                               AS fornecedores_ativos,
    COUNT(DISTINCT ft.produto_id)                                  AS skus_ativos,
    COALESCE(SUM(ft.quantidade), 0)::numeric                       AS quantidade_vendida,
    CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
         THEN SUM(ft.valor) / COUNT(DISTINCT ft.transacao_id)
         ELSE 0 END                                                AS ticket_medio
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas       dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id
    AND dd.data IS NOT NULL
    AND dd.data  < CURRENT_DATE
  GROUP BY EXTRACT(YEAR FROM dd.data)::integer
),

first_purchases AS (
  SELECT
    ft.cliente_id,
    EXTRACT(YEAR FROM MIN(dd.data))::integer AS first_year
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas       dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id  = p_client_id
    AND ft.cliente_id IS NOT NULL
    AND dd.data IS NOT NULL
  GROUP BY ft.cliente_id
),

novos_por_ano AS (
  SELECT first_year AS ano, COUNT(*)::bigint AS clientes_novos
  FROM   first_purchases
  GROUP  BY first_year
),

current_year_months AS (
  SELECT COUNT(DISTINCT date_trunc('month', dd.data)) AS months_with_data
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas       dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id
    AND dd.data IS NOT NULL
    AND dd.data  < CURRENT_DATE
    AND EXTRACT(YEAR FROM dd.data) = EXTRACT(YEAR FROM CURRENT_DATE)
),

with_yoy AS (
  SELECT
    y.ano,
    ROUND(y.receita, 2)        AS receita,
    y.total_pedidos,
    y.clientes_unicos,
    COALESCE(n.clientes_novos, 0) AS clientes_novos,
    ROUND(y.ticket_medio, 2)   AS ticket_medio,
    y.fornecedores_ativos,
    y.skus_ativos,
    y.quantidade_vendida,
    (y.ano = EXTRACT(YEAR FROM CURRENT_DATE)::integer) AS is_partial,
    CASE WHEN LAG(y.receita) OVER (ORDER BY y.ano) > 0
         THEN ROUND(
               (y.receita - LAG(y.receita) OVER (ORDER BY y.ano))
               / LAG(y.receita) OVER (ORDER BY y.ano) * 100,
             1)
         ELSE NULL END AS yoy_receita_pct,
    y.receita AS raw_receita
  FROM years y
  LEFT JOIN novos_por_ano n ON n.ano = y.ano
)

SELECT
  w.ano,
  w.receita,
  w.total_pedidos,
  w.clientes_unicos,
  w.clientes_novos,
  w.ticket_medio,
  w.fornecedores_ativos,
  w.skus_ativos,
  w.quantidade_vendida,
  w.is_partial,
  w.yoy_receita_pct,
  CASE
    WHEN w.is_partial AND m.months_with_data > 0
    THEN ROUND(w.raw_receita / m.months_with_data * 12, 2)
    ELSE NULL
  END AS receita_anualizada
FROM with_yoy   w
CROSS JOIN current_year_months m
ORDER BY w.ano DESC;
$$;


ALTER FUNCTION "analytics_v2"."get_annual_metrics_for_client"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid") RETURNS TABLE("dimension" "text", "kpi" "text", "label" "text", "unit" "text", "current_value" numeric, "prev_month_value" numeric, "avg_6m" numeric, "mom_pct" numeric, "vs_6m_avg_pct" numeric, "streak_months" integer)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
WITH

all_monthly AS (
  SELECT
    date_trunc('month', dd.data)::date                  AS mes,
    COALESCE(SUM(ft.valor),                       0)    AS receita,
    COUNT(DISTINCT ft.transacao_id)::numeric             AS total_pedidos,
    COALESCE(SUM(ft.quantidade),                  0)    AS quantidade,
    COUNT(DISTINCT ft.cliente_id)::numeric               AS clientes_unicos,
    COUNT(DISTINCT ft.fornecedor_id)::numeric            AS fornecedores_ativos,
    COUNT(DISTINCT ft.produto_id)::numeric               AS skus_ativos,
    CASE WHEN COUNT(DISTINCT ft.transacao_id) > 0
         THEN SUM(ft.valor) / COUNT(DISTINCT ft.transacao_id)
         ELSE 0 END                                      AS ticket_medio,
    CASE WHEN COUNT(DISTINCT ft.cliente_id) > 0
         THEN COUNT(DISTINCT ft.transacao_id)::numeric
              / COUNT(DISTINCT ft.cliente_id)
         ELSE 0 END                                      AS frequencia_media,
    CASE WHEN COUNT(DISTINCT ft.cliente_id) > 0
         THEN SUM(ft.valor) / COUNT(DISTINCT ft.cliente_id)
         ELSE 0 END                                      AS receita_por_cliente,
    CASE WHEN COUNT(DISTINCT ft.produto_id) > 0
         THEN SUM(ft.valor) / COUNT(DISTINCT ft.produto_id)
         ELSE 0 END                                      AS receita_por_sku,
    CASE WHEN COUNT(DISTINCT ft.fornecedor_id) > 0
         THEN SUM(ft.valor) / COUNT(DISTINCT ft.fornecedor_id)
         ELSE 0 END                                      AS receita_por_fornecedor
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas       dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id
    AND dd.data IS NOT NULL
    AND dd.data  < CURRENT_DATE
  GROUP BY date_trunc('month', dd.data)::date
),

monthly_buyers AS (
  SELECT DISTINCT date_trunc('month', dd.data)::date AS mes, ft.cliente_id
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas       dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id  = p_client_id
    AND ft.cliente_id IS NOT NULL
    AND dd.data IS NOT NULL
    AND dd.data        < CURRENT_DATE
),
first_purchases AS (
  SELECT ft.cliente_id, date_trunc('month', MIN(dd.data))::date AS first_month
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas       dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id  = p_client_id
    AND ft.cliente_id IS NOT NULL
    AND dd.data IS NOT NULL
  GROUP BY ft.cliente_id
),
novos_por_mes AS (
  SELECT first_month AS mes, COUNT(*)::numeric AS clientes_novos
  FROM   first_purchases
  GROUP  BY first_month
),
recorrentes_por_mes AS (
  SELECT a.mes, COUNT(*)::numeric AS clientes_recorrentes
  FROM monthly_buyers a
  JOIN monthly_buyers b ON b.cliente_id = a.cliente_id
    AND b.mes = (a.mes - INTERVAL '1 month')::date
  GROUP BY a.mes
),

monthly_rev_per_entity AS (
  SELECT
    date_trunc('month', dd.data)::date AS mes,
    ft.cliente_id,
    ft.produto_id,
    ft.fornecedor_id,
    ft.valor
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas       dd ON ft.data_competencia_id = dd.data_id
  WHERE ft.client_id = p_client_id
    AND dd.data IS NOT NULL
    AND dd.data  < CURRENT_DATE
),
rev_por_cliente AS (
  SELECT mes, cliente_id AS entity_id, SUM(valor) AS rev
  FROM   monthly_rev_per_entity WHERE cliente_id IS NOT NULL
  GROUP  BY mes, cliente_id
),
rev_por_produto AS (
  SELECT mes, produto_id AS entity_id, SUM(valor) AS rev
  FROM   monthly_rev_per_entity WHERE produto_id IS NOT NULL
  GROUP  BY mes, produto_id
),
rev_por_fornecedor AS (
  SELECT mes, fornecedor_id AS entity_id, SUM(valor) AS rev
  FROM   monthly_rev_per_entity WHERE fornecedor_id IS NOT NULL
  GROUP  BY mes, fornecedor_id
),

concentracao_top3_clientes AS (
  SELECT mes,
    ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev), 0) * 100, 1) AS perc
  FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk
        FROM rev_por_cliente) x
  GROUP BY mes
),
concentracao_top3_produtos AS (
  SELECT mes,
    ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev), 0) * 100, 1) AS perc
  FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk
        FROM rev_por_produto) x
  GROUP BY mes
),
concentracao_top3_fornecedores AS (
  SELECT mes,
    ROUND(SUM(rev) FILTER (WHERE rnk <= 3) / NULLIF(SUM(rev), 0) * 100, 1) AS perc
  FROM (SELECT mes, rev, ROW_NUMBER() OVER (PARTITION BY mes ORDER BY rev DESC) AS rnk
        FROM rev_por_fornecedor) x
  GROUP BY mes
),
top1_clean AS (
  SELECT mes, ROUND(MAX(rev) / NULLIF(SUM(rev), 0) * 100, 1) AS concentracao_top1_perc
  FROM   rev_por_fornecedor
  GROUP  BY mes
),

enriched AS (
  SELECT
    am.mes,
    am.receita, am.ticket_medio, am.total_pedidos, am.quantidade,
    am.clientes_unicos, am.frequencia_media, am.receita_por_cliente,
    am.skus_ativos, am.receita_por_sku, am.fornecedores_ativos, am.receita_por_fornecedor,
    COALESCE(np.clientes_novos,       0)  AS clientes_novos,
    COALESCE(rp.clientes_recorrentes, 0)  AS clientes_recorrentes,
    CASE WHEN COALESCE(am_prev.clientes_unicos, 0) > 0
         THEN ROUND(COALESCE(rp.clientes_recorrentes, 0) / am_prev.clientes_unicos * 100, 1)
         ELSE 0 END                       AS taxa_recorrencia_perc,
    COALESCE(t1.concentracao_top1_perc,          0) AS concentracao_top1_fornecedor_perc,
    COALESCE(c3c.perc,                           0) AS concentracao_top3_clientes_perc,
    COALESCE(c3p.perc,                           0) AS concentracao_top3_produtos_perc,
    COALESCE(c3s.perc,                           0) AS concentracao_top3_fornecedores_perc
  FROM all_monthly am
  LEFT JOIN all_monthly             am_prev ON am_prev.mes = (am.mes - INTERVAL '1 month')::date
  LEFT JOIN novos_por_mes           np      ON np.mes   = am.mes
  LEFT JOIN recorrentes_por_mes     rp      ON rp.mes   = am.mes
  LEFT JOIN top1_clean              t1      ON t1.mes   = am.mes
  LEFT JOIN concentracao_top3_clientes   c3c ON c3c.mes = am.mes
  LEFT JOIN concentracao_top3_produtos   c3p ON c3p.mes = am.mes
  LEFT JOIN concentracao_top3_fornecedores c3s ON c3s.mes = am.mes
),

ref_month AS (
  SELECT COALESCE(
    (SELECT mes FROM enriched WHERE mes = date_trunc('month', CURRENT_DATE)::date LIMIT 1),
    (SELECT mes FROM enriched WHERE mes < date_trunc('month', CURRENT_DATE)::date ORDER BY mes DESC LIMIT 1)
  ) AS mes
),
complete_months AS (SELECT e.* FROM enriched e, ref_month r WHERE e.mes < r.mes),
current_month   AS (SELECT e.* FROM enriched e, ref_month r WHERE e.mes = r.mes),

long_complete AS (
  SELECT mes, 'receita_liquida'                   AS kpi, receita                          AS val FROM complete_months UNION ALL
  SELECT mes, 'ticket_medio',                              ticket_medio                          FROM complete_months UNION ALL
  SELECT mes, 'total_pedidos',                             total_pedidos                         FROM complete_months UNION ALL
  SELECT mes, 'quantidade_vendida',                        quantidade                            FROM complete_months UNION ALL
  SELECT mes, 'clientes_unicos',                           clientes_unicos                       FROM complete_months UNION ALL
  SELECT mes, 'clientes_novos',                            clientes_novos                        FROM complete_months UNION ALL
  SELECT mes, 'clientes_recorrentes',                      clientes_recorrentes                  FROM complete_months UNION ALL
  SELECT mes, 'taxa_recorrencia_perc',                     taxa_recorrencia_perc                 FROM complete_months UNION ALL
  SELECT mes, 'receita_por_cliente',                       receita_por_cliente                   FROM complete_months UNION ALL
  SELECT mes, 'frequencia_media',                          frequencia_media                      FROM complete_months UNION ALL
  SELECT mes, 'skus_ativos',                               skus_ativos                           FROM complete_months UNION ALL
  SELECT mes, 'receita_por_sku',                           receita_por_sku                       FROM complete_months UNION ALL
  SELECT mes, 'fornecedores_ativos',                       fornecedores_ativos                   FROM complete_months UNION ALL
  SELECT mes, 'receita_por_fornecedor',                    receita_por_fornecedor                FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top1_fornecedor_perc',         concentracao_top1_fornecedor_perc     FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_clientes_perc',           concentracao_top3_clientes_perc       FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_produtos_perc',           concentracao_top3_produtos_perc       FROM complete_months UNION ALL
  SELECT mes, 'concentracao_top3_fornecedores_perc',       concentracao_top3_fornecedores_perc   FROM complete_months
),
long_current AS (
  SELECT 'receita_liquida'                   AS kpi, receita                          AS val FROM current_month UNION ALL
  SELECT 'ticket_medio',                              ticket_medio                          FROM current_month UNION ALL
  SELECT 'total_pedidos',                             total_pedidos                         FROM current_month UNION ALL
  SELECT 'quantidade_vendida',                        quantidade                            FROM current_month UNION ALL
  SELECT 'clientes_unicos',                           clientes_unicos                       FROM current_month UNION ALL
  SELECT 'clientes_novos',                            clientes_novos                        FROM current_month UNION ALL
  SELECT 'clientes_recorrentes',                      clientes_recorrentes                  FROM current_month UNION ALL
  SELECT 'taxa_recorrencia_perc',                     taxa_recorrencia_perc                 FROM current_month UNION ALL
  SELECT 'receita_por_cliente',                       receita_por_cliente                   FROM current_month UNION ALL
  SELECT 'frequencia_media',                          frequencia_media                      FROM current_month UNION ALL
  SELECT 'skus_ativos',                               skus_ativos                           FROM current_month UNION ALL
  SELECT 'receita_por_sku',                           receita_por_sku                       FROM current_month UNION ALL
  SELECT 'fornecedores_ativos',                       fornecedores_ativos                   FROM current_month UNION ALL
  SELECT 'receita_por_fornecedor',                    receita_por_fornecedor                FROM current_month UNION ALL
  SELECT 'concentracao_top1_fornecedor_perc',         concentracao_top1_fornecedor_perc     FROM current_month UNION ALL
  SELECT 'concentracao_top3_clientes_perc',           concentracao_top3_clientes_perc       FROM current_month UNION ALL
  SELECT 'concentracao_top3_produtos_perc',           concentracao_top3_produtos_perc       FROM current_month UNION ALL
  SELECT 'concentracao_top3_fornecedores_perc',       concentracao_top3_fornecedores_perc   FROM current_month
),

ranked AS (
  SELECT kpi, mes, val, ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC) AS rn
  FROM long_complete
),
prev_month AS (SELECT kpi, val AS prev_val FROM ranked WHERE rn = 1),
avg_6m     AS (SELECT kpi, ROUND(AVG(val), 2) AS avg_val FROM ranked WHERE rn BETWEEN 1 AND 6 GROUP BY kpi),
with_dir   AS (
  SELECT kpi, mes, val,
    SIGN(val - LAG(val) OVER (PARTITION BY kpi ORDER BY mes)) AS dir,
    ROW_NUMBER() OVER (PARTITION BY kpi ORDER BY mes DESC)     AS rn
  FROM long_complete
),
latest_dir AS (SELECT kpi, dir FROM with_dir WHERE rn = 1 AND dir IS NOT NULL),
streak_tagged AS (
  SELECT w.kpi, l.dir AS streak_dir,
    SUM(CASE WHEN w.dir != l.dir THEN 1 ELSE 0 END)
      OVER (PARTITION BY w.kpi ORDER BY w.rn ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS breaks
  FROM with_dir w JOIN latest_dir l USING (kpi)
  WHERE w.dir IS NOT NULL
),
streak AS (
  SELECT kpi, (MAX(streak_dir) * COUNT(*))::integer AS streak_months
  FROM streak_tagged WHERE breaks = 0
  GROUP BY kpi
),

assembled AS (
  SELECT
    lc.kpi,
    ROUND(lc.val,      2) AS current_value,
    ROUND(pm.prev_val, 2) AS prev_month_value,
    a6.avg_val             AS avg_6m,
    CASE WHEN COALESCE(pm.prev_val, 0) <> 0
         THEN ROUND((lc.val - pm.prev_val) / pm.prev_val * 100, 1) ELSE NULL END AS mom_pct,
    CASE WHEN COALESCE(a6.avg_val,  0) <> 0
         THEN ROUND((lc.val - a6.avg_val)  / a6.avg_val  * 100, 1) ELSE NULL END AS vs_6m_avg_pct,
    COALESCE(st.streak_months, 0) AS streak_months
  FROM      long_current lc
  LEFT JOIN prev_month   pm USING (kpi)
  LEFT JOIN avg_6m       a6 USING (kpi)
  LEFT JOIN streak       st USING (kpi)
)

SELECT m.dimension, m.kpi, m.label, m.unit,
       a.current_value, a.prev_month_value, a.avg_6m,
       a.mom_pct, a.vs_6m_avg_pct, a.streak_months
FROM assembled a
JOIN (VALUES
  ('receita_liquida',                   'finance',     'Receita Líquida',                  'BRL'  ),
  ('ticket_medio',                      'finance',     'Ticket Médio',                     'BRL'  ),
  ('total_pedidos',                     'finance',     'Total de Pedidos',                 'count'),
  ('clientes_unicos',                   'commercial',  'Clientes Únicos',                  'count'),
  ('clientes_novos',                    'commercial',  'Clientes Novos',                   'count'),
  ('clientes_recorrentes',              'commercial',  'Clientes Recorrentes',             'count'),
  ('taxa_recorrencia_perc',             'commercial',  'Taxa de Recorrência',              '%'    ),
  ('receita_por_cliente',               'commercial',  'Receita por Cliente',              'BRL'  ),
  ('frequencia_media',                  'commercial',  'Frequência Média de Compra',       'count'),
  ('concentracao_top3_clientes_perc',   'commercial',  'Concentração Top 3 Clientes',      '%'    ),
  ('skus_ativos',                       'inventory',   'SKUs Ativos no Mês',               'count'),
  ('quantidade_vendida',                'inventory',   'Quantidade Vendida',               'count'),
  ('receita_por_sku',                   'inventory',   'Receita por SKU Ativo',            'BRL'  ),
  ('concentracao_top3_produtos_perc',   'inventory',   'Concentração Top 3 Produtos',      '%'    ),
  ('fornecedores_ativos',               'supply',      'Fornecedores Ativos',              'count'),
  ('receita_por_fornecedor',            'supply',      'Receita por Fornecedor',           'BRL'  ),
  ('concentracao_top1_fornecedor_perc', 'supply',      'Concentração Top Fornecedor',      '%'    ),
  ('concentracao_top3_fornecedores_perc','supply',     'Concentração Top 3 Fornecedores',  '%'    )
) AS m(kpi, dimension, label, unit) ON m.kpi = a.kpi

UNION ALL

SELECT 'finance'::text, 'receita_ytd'::text, 'Receita Acumulada (YTD)'::text, 'BRL'::text,
  ROUND(COALESCE(SUM(ft.valor), 0)::numeric, 2),
  NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, 0::integer
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE ft.client_id = p_client_id
  AND EXTRACT(YEAR FROM dd.data) = EXTRACT(YEAR FROM CURRENT_DATE)
  AND dd.data < CURRENT_DATE

UNION ALL

SELECT 'inventory'::text, 'skus_total'::text, 'Total de SKUs (catálogo)'::text, 'count'::text,
  COUNT(*)::numeric,
  NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, 0::integer
FROM analytics_v2.dim_inventory
WHERE client_id = p_client_id

UNION ALL

SELECT 'commercial'::text, 'clientes_base_total'::text, 'Total de Clientes (base)'::text, 'count'::text,
  COUNT(*)::numeric,
  NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, 0::integer
FROM analytics_v2.dim_clientes
WHERE client_id = p_client_id

UNION ALL

SELECT 'commercial'::text, 'clientes_ativos_90d'::text, 'Clientes Ativos (últimos 90 dias)'::text, 'count'::text,
  COUNT(*)::numeric,
  NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, 0::integer
FROM analytics_v2.dim_clientes
WHERE client_id    = p_client_id
  AND dias_recencia IS NOT NULL
  AND dias_recencia <= 90

UNION ALL

SELECT 'commercial'::text, 'recencia_media_dias'::text, 'Recência Média da Base (dias)'::text, 'days'::text,
  ROUND(AVG(dias_recencia)::numeric, 0),
  NULL::numeric, NULL::numeric, NULL::numeric, NULL::numeric, 0::integer
FROM analytics_v2.dim_clientes
WHERE client_id    = p_client_id
  AND dias_recencia IS NOT NULL

ORDER BY dimension, kpi;
$$;


ALTER FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."get_dim_totals_for_client"("p_client_id" "uuid") RETURNS TABLE("entity" "text", "total_receita" numeric)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
  SELECT 'clients'::text,   COALESCE(SUM(receita_total), 0)::numeric
  FROM   analytics_v2.dim_clientes    WHERE client_id = p_client_id
  UNION ALL
  SELECT 'products'::text,  COALESCE(SUM(receita_total), 0)::numeric
  FROM   analytics_v2.dim_inventory   WHERE client_id = p_client_id
  UNION ALL
  SELECT 'suppliers'::text, COALESCE(SUM(receita_total), 0)::numeric
  FROM   analytics_v2.dim_fornecedores WHERE client_id = p_client_id;
$$;


ALTER FUNCTION "analytics_v2"."get_dim_totals_for_client"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."on_etl_job_completed"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
DECLARE
  v_doc_type_id text;
BEGIN
  IF NEW.status <> 'completed' THEN
    RETURN NEW;
  END IF;
  IF OLD.status = 'completed' THEN
    RETURN NEW;
  END IF;
  IF NEW.job_type <> 'bigquery_sync' THEN
    RETURN NEW;
  END IF;
  IF NEW.client_id IS NULL OR NEW.resource_type IS NULL THEN
    RETURN NEW;
  END IF;

  v_doc_type_id := analytics_v2.etl_resource_to_doc_type(NEW.resource_type);

  IF v_doc_type_id IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source, updated_at)
    VALUES
      (NEW.client_id, v_doc_type_id, 'complete', 'erp_sync', now())
    ON CONFLICT (client_id, document_type_id) DO UPDATE
      SET status     = 'complete',
          source     = 'erp_sync',
          updated_at = now()
      WHERE client_knowledge_documents.status <> 'complete';
  END IF;

  RETURN NEW;
EXCEPTION
  WHEN others THEN
    RAISE WARNING '[knowledge] ETL hook failed for job %: %', NEW.job_id, SQLERRM;
    RETURN NEW;
END;
$$;


ALTER FUNCTION "analytics_v2"."on_etl_job_completed"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."process_pending_etl_jobs"() RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "statement_timeout" TO '0'
    SET "search_path" TO 'public', 'analytics_v2'
    AS $$
DECLARE
  v_job_id uuid;
BEGIN
  -- Pick one job: pending jobs first, then failed jobs eligible for retry
  -- (failed < 3 times, last attempt > 5 minutes ago)
  SELECT job_id INTO v_job_id
  FROM analytics_v2.reg_jobs
  WHERE job_type = 'bigquery_sync'
    AND (
      status = 'pending'
      OR (
        status = 'failed'
        AND retry_count < 3
        AND completed_at < now() - interval '5 minutes'
      )
    )
  ORDER BY
    CASE WHEN status = 'pending' THEN 0 ELSE 1 END,
    created_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF v_job_id IS NOT NULL THEN
    -- If this is a retry, reset back to pending and increment counter
    UPDATE analytics_v2.reg_jobs
    SET
      status        = 'pending',
      retry_count   = retry_count + 1,
      error_message = NULL,
      updated_at    = clock_timestamp()
    WHERE job_id = v_job_id AND status = 'failed';

    RAISE NOTICE '[process_pending_etl_jobs] dispatching job %', v_job_id;
    PERFORM analytics_v2.run_etl_job(v_job_id);
  END IF;
END;
$$;


ALTER FUNCTION "analytics_v2"."process_pending_etl_jobs"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."run_etl_job"("p_job_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "statement_timeout" TO '0'
    SET "search_path" TO 'public', 'analytics_v2', 'fdw'
    AS $_$
DECLARE
  v_client_id           uuid;
  v_cred_id             bigint;
  v_mapping             jsonb;
  v_ft_bare             text;
  v_server_name         text;
  v_bq_columns          jsonb;
  v_bare_table          text;
  v_col_defs            text;

  c_documento           text;
  c_data_competencia    text;
  c_quantidade          text;
  c_valor_unitario      text;
  c_valor               text;
  c_status              text;
  c_cliente_cpf_cnpj    text;
  c_cliente_nome        text;
  c_cliente_telefone    text;
  c_cliente_cidade      text;
  c_cliente_uf          text;
  c_fornecedor_cnpj     text;
  c_fornecedor_nome     text;
  c_fornecedor_telefone text;
  c_fornecedor_cidade   text;
  c_fornecedor_uf       text;
  c_produto_sku         text;
  c_produto_nome        text;

  v_select              text;
  v_start               timestamptz := clock_timestamp();
  v_rows                bigint  := 0;
  v_staged              bigint  := 0;
  v_duration            numeric;
BEGIN
  SET LOCAL statement_timeout = 0;

  -- ── Fetch job ─────────────────────────────────────────────────────────────────
  SELECT client_id, (input_params->>'credential_id')::bigint
  INTO v_client_id, v_cred_id
  FROM analytics_v2.reg_jobs
  WHERE job_id = p_job_id AND status = 'pending';

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Job % not found or not in pending state', p_job_id;
  END IF;

  UPDATE analytics_v2.reg_jobs
  SET status = 'running', started_at = clock_timestamp(), progress_pct = 5, updated_at = clock_timestamp()
  WHERE job_id = p_job_id;

  -- ── Fetch column mapping ──────────────────────────────────────────────────────
  SELECT column_mapping INTO v_mapping
  FROM public.client_data_sources
  WHERE client_id = v_client_id::text AND credential_id = v_cred_id
  ORDER BY atualizado_em DESC NULLS LAST
  LIMIT 1;

  IF v_mapping IS NULL OR v_mapping = '{}'::jsonb THEN
    RAISE EXCEPTION 'No column mapping found for client_id=% credential_id=%', v_client_id, v_cred_id;
  END IF;

  -- ── Fetch FDW metadata from registry ─────────────────────────────────────────
  SELECT bft.server_name, bft.columns, bft.table_name
  INTO v_server_name, v_bq_columns, v_bare_table
  FROM public.bigquery_foreign_tables bft
  WHERE bft.client_id = v_client_id::text
  ORDER BY bft.created_at DESC
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RAISE EXCEPTION 'No BigQuery registration found for client_id=%. Connect BigQuery first.', v_client_id;
  END IF;

  IF v_bq_columns IS NULL OR jsonb_array_length(v_bq_columns) = 0 THEN
    RAISE EXCEPTION 'No columns registered for client_id=%. Run column discovery first.', v_client_id;
  END IF;

  -- ── Build and create ephemeral foreign table ──────────────────────────────────
  -- Name is deterministic: one slot per client, no random suffix accumulation
  v_ft_bare  := 'bq_ft_' || SUBSTRING(REPLACE(v_client_id::text, '-', ''), 1, 12);
  v_col_defs := public._bq_col_defs_from_jsonb(v_bq_columns);

  EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I CASCADE', v_ft_bare);
  EXECUTE format(
    'CREATE FOREIGN TABLE fdw.%I (%s) SERVER %I OPTIONS (table %L)',
    v_ft_bare, v_col_defs, v_server_name, v_bare_table
  );

  RAISE NOTICE '[run_etl_job] job=%: created ephemeral FT fdw.%', p_job_id, v_ft_bare;

  -- ── Invert column mapping ─────────────────────────────────────────────────────
  SELECT key INTO c_documento           FROM jsonb_each_text(v_mapping) WHERE value = 'documento'           LIMIT 1;
  SELECT key INTO c_data_competencia    FROM jsonb_each_text(v_mapping) WHERE value = 'data_competencia_id' LIMIT 1;
  SELECT key INTO c_quantidade          FROM jsonb_each_text(v_mapping) WHERE value = 'quantidade'          LIMIT 1;
  SELECT key INTO c_valor_unitario      FROM jsonb_each_text(v_mapping) WHERE value = 'valor_unitario'      LIMIT 1;
  SELECT key INTO c_valor               FROM jsonb_each_text(v_mapping) WHERE value = 'valor'               LIMIT 1;
  SELECT key INTO c_status              FROM jsonb_each_text(v_mapping) WHERE value = 'status'              LIMIT 1;
  SELECT key INTO c_cliente_cpf_cnpj    FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_cpf_cnpj'   LIMIT 1;
  SELECT key INTO c_cliente_nome        FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_nome'        LIMIT 1;
  SELECT key INTO c_cliente_telefone    FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_telefone'    LIMIT 1;
  SELECT key INTO c_cliente_cidade      FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_cidade'      LIMIT 1;
  SELECT key INTO c_cliente_uf          FROM jsonb_each_text(v_mapping) WHERE value = 'cliente_uf'          LIMIT 1;
  SELECT key INTO c_fornecedor_cnpj     FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_cnpj'     LIMIT 1;
  SELECT key INTO c_fornecedor_nome     FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_nome'     LIMIT 1;
  SELECT key INTO c_fornecedor_telefone FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_telefone' LIMIT 1;
  SELECT key INTO c_fornecedor_cidade   FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_cidade'   LIMIT 1;
  SELECT key INTO c_fornecedor_uf       FROM jsonb_each_text(v_mapping) WHERE value = 'fornecedor_uf'       LIMIT 1;
  SELECT key INTO c_produto_sku         FROM jsonb_each_text(v_mapping) WHERE value = 'produto_sku'         LIMIT 1;
  SELECT key INTO c_produto_nome        FROM jsonb_each_text(v_mapping) WHERE value = 'produto_nome'        LIMIT 1;

  IF c_documento IS NULL THEN
    RAISE EXCEPTION 'Column mapping missing required field "documento". Got mapping: %', v_mapping;
  END IF;

  RAISE NOTICE '[run_etl_job] job=%: mapping resolved — documento=%, valor=%, data=%',
    p_job_id, c_documento, c_valor, c_data_competencia;

  -- ── Build SELECT clause ───────────────────────────────────────────────────────
  v_select := format(
    $sel$
      %s::text AS documento,
      %s::text AS data_competencia_raw,
      %s::text AS quantidade_raw,
      %s::text AS valor_unitario_raw,
      %s::text AS valor_raw,
      %s::text AS status,
      %s::text AS cliente_cpf_cnpj,
      %s::text AS cliente_nome,
      %s::text AS cliente_telefone,
      %s::text AS cliente_cidade,
      %s::text AS cliente_uf,
      %s::text AS fornecedor_cnpj,
      %s::text AS fornecedor_nome,
      %s::text AS fornecedor_telefone,
      %s::text AS fornecedor_cidade,
      %s::text AS fornecedor_uf,
      %s::text AS produto_sku,
      %s::text AS produto_nome
    $sel$,
    CASE WHEN c_documento           IS NOT NULL THEN format('%I', c_documento)           ELSE 'NULL' END,
    CASE WHEN c_data_competencia    IS NOT NULL THEN format('%I', c_data_competencia)    ELSE 'NULL' END,
    CASE WHEN c_quantidade          IS NOT NULL THEN format('%I', c_quantidade)          ELSE 'NULL' END,
    CASE WHEN c_valor_unitario      IS NOT NULL THEN format('%I', c_valor_unitario)      ELSE 'NULL' END,
    CASE WHEN c_valor               IS NOT NULL THEN format('%I', c_valor)               ELSE 'NULL' END,
    CASE WHEN c_status              IS NOT NULL THEN format('%I', c_status)              ELSE 'NULL' END,
    CASE WHEN c_cliente_cpf_cnpj    IS NOT NULL THEN format('%I', c_cliente_cpf_cnpj)    ELSE 'NULL' END,
    CASE WHEN c_cliente_nome        IS NOT NULL THEN format('%I', c_cliente_nome)        ELSE 'NULL' END,
    CASE WHEN c_cliente_telefone    IS NOT NULL THEN format('%I', c_cliente_telefone)    ELSE 'NULL' END,
    CASE WHEN c_cliente_cidade      IS NOT NULL THEN format('%I', c_cliente_cidade)      ELSE 'NULL' END,
    CASE WHEN c_cliente_uf          IS NOT NULL THEN format('%I', c_cliente_uf)          ELSE 'NULL' END,
    CASE WHEN c_fornecedor_cnpj     IS NOT NULL THEN format('%I', c_fornecedor_cnpj)     ELSE 'NULL' END,
    CASE WHEN c_fornecedor_nome     IS NOT NULL THEN format('%I', c_fornecedor_nome)     ELSE 'NULL' END,
    CASE WHEN c_fornecedor_telefone IS NOT NULL THEN format('%I', c_fornecedor_telefone) ELSE 'NULL' END,
    CASE WHEN c_fornecedor_cidade   IS NOT NULL THEN format('%I', c_fornecedor_cidade)   ELSE 'NULL' END,
    CASE WHEN c_fornecedor_uf       IS NOT NULL THEN format('%I', c_fornecedor_uf)       ELSE 'NULL' END,
    CASE WHEN c_produto_sku         IS NOT NULL THEN format('%I', c_produto_sku)         ELSE 'NULL' END,
    CASE WHEN c_produto_nome        IS NOT NULL THEN format('%I', c_produto_nome)        ELSE 'NULL' END
  );

  -- ── Clear leftover staging rows ────────────────────────────────────────────────
  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 10, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Single FDW scan → staging ─────────────────────────────────────────────────
  EXECUTE format(
    'INSERT INTO analytics_v2.etl_staging
       (job_id, documento, data_competencia_raw, quantidade_raw, valor_unitario_raw, valor_raw,
        status, cliente_cpf_cnpj, cliente_nome, cliente_telefone, cliente_cidade, cliente_uf,
        fornecedor_cnpj, fornecedor_nome, fornecedor_telefone, fornecedor_cidade, fornecedor_uf,
        produto_sku, produto_nome)
     SELECT %L, %s FROM %I.%I',
    p_job_id, v_select, 'fdw', v_ft_bare
  );
  GET DIAGNOSTICS v_staged = ROW_COUNT;

  -- ── Drop ephemeral FT immediately after scan ──────────────────────────────────
  EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I CASCADE', v_ft_bare);
  RAISE NOTICE '[run_etl_job] job=%: dropped ephemeral FT fdw.%, staged % rows', p_job_id, v_ft_bare, v_staged;

  UPDATE analytics_v2.reg_jobs
  SET progress_pct = 55, rows_inserted = v_staged, updated_at = clock_timestamp()
  WHERE job_id = p_job_id;

  -- ── Upsert dim_clientes ───────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_clientes
    (client_id, cpf_cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
  SELECT DISTINCT ON (COALESCE(cliente_cpf_cnpj, cliente_nome))
    v_client_id,
    COALESCE(cliente_cpf_cnpj, cliente_nome),
    cliente_nome, cliente_telefone, cliente_cidade, cliente_uf,
    clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id AND COALESCE(cliente_cpf_cnpj, cliente_nome) IS NOT NULL
  ORDER BY COALESCE(cliente_cpf_cnpj, cliente_nome)
  ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET
    nome = EXCLUDED.nome, telefone = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade, endereco_uf = EXCLUDED.endereco_uf,
    atualizado_em = EXCLUDED.atualizado_em;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 65, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_fornecedores ───────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_fornecedores
    (client_id, cnpj, nome, telefone, endereco_cidade, endereco_uf, atualizado_em)
  SELECT DISTINCT ON (COALESCE(fornecedor_cnpj, fornecedor_nome))
    v_client_id,
    COALESCE(fornecedor_cnpj, fornecedor_nome),
    fornecedor_nome, fornecedor_telefone, fornecedor_cidade, fornecedor_uf,
    clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id AND COALESCE(fornecedor_cnpj, fornecedor_nome) IS NOT NULL
  ORDER BY COALESCE(fornecedor_cnpj, fornecedor_nome)
  ON CONFLICT (client_id, cnpj) DO UPDATE SET
    nome = EXCLUDED.nome, telefone = EXCLUDED.telefone,
    endereco_cidade = EXCLUDED.endereco_cidade, endereco_uf = EXCLUDED.endereco_uf,
    atualizado_em = EXCLUDED.atualizado_em;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 75, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_inventory ──────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_inventory (client_id, sku, nome, updated_at)
  SELECT DISTINCT ON (COALESCE(produto_sku, produto_nome))
    v_client_id, COALESCE(produto_sku, produto_nome), produto_nome, clock_timestamp()
  FROM analytics_v2.etl_staging
  WHERE job_id = p_job_id AND COALESCE(produto_sku, produto_nome) IS NOT NULL
  ORDER BY COALESCE(produto_sku, produto_nome)
  ON CONFLICT (client_id, sku) DO UPDATE SET
    nome = EXCLUDED.nome, updated_at = EXCLUDED.updated_at;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 82, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert dim_datas ──────────────────────────────────────────────────────────
  INSERT INTO analytics_v2.dim_datas
    (data, ano, mes, dia, numero_dia_semana, numero_semana_ano, numero_semestre, periodo_trimestral)
  SELECT DISTINCT
    d::date,
    EXTRACT(year  FROM d)::int, EXTRACT(month  FROM d)::int, EXTRACT(day FROM d)::int,
    CASE WHEN EXTRACT(dow FROM d) = 0 THEN 7 ELSE EXTRACT(dow FROM d)::int END,
    EXTRACT(week FROM d)::int,
    CASE WHEN EXTRACT(month FROM d) <= 6 THEN 1 ELSE 2 END,
    'Q' || EXTRACT(quarter FROM d)::text
  FROM (
    SELECT data_competencia_raw::timestamptz AS d
    FROM analytics_v2.etl_staging
    WHERE job_id = p_job_id
      AND data_competencia_raw IS NOT NULL
      AND data_competencia_raw ~ '^\d{4}-\d{2}-\d{2}'
  ) t
  ON CONFLICT (data) DO NOTHING;

  UPDATE analytics_v2.reg_jobs SET progress_pct = 88, updated_at = clock_timestamp() WHERE job_id = p_job_id;

  -- ── Upsert fato_transacoes ────────────────────────────────────────────────────
  INSERT INTO analytics_v2.fato_transacoes
    (transacao_id, client_id, data_competencia_id, cliente_id, fornecedor_id, produto_id,
     documento, quantidade, valor_unitario, valor, status)
  SELECT
    md5(v_client_id::text || ':' ||
        COALESCE(s.documento, '')            || ':' ||
        COALESCE(s.data_competencia_raw, '') || ':' ||
        COALESCE(s.produto_sku, ''))         AS transacao_id,
    v_client_id,
    dd.data_id,
    dc.cliente_id,
    df.fornecedor_id,
    di.inventory_id,
    s.documento,
    analytics_v2.safe_to_numeric(s.quantidade_raw),
    analytics_v2.safe_to_numeric(s.valor_unitario_raw),
    analytics_v2.safe_to_numeric(s.valor_raw),
    s.status
  FROM analytics_v2.etl_staging s
  LEFT JOIN analytics_v2.dim_datas dd
    ON dd.data = (
      CASE WHEN s.data_competencia_raw ~ '^\d{4}-\d{2}-\d{2}'
           THEN (s.data_competencia_raw::timestamptz)::date ELSE NULL END
    )
  LEFT JOIN analytics_v2.dim_clientes dc
    ON dc.client_id = v_client_id AND dc.cpf_cnpj = COALESCE(s.cliente_cpf_cnpj, s.cliente_nome)
  LEFT JOIN analytics_v2.dim_fornecedores df
    ON df.client_id = v_client_id AND df.cnpj = COALESCE(s.fornecedor_cnpj, s.fornecedor_nome)
  LEFT JOIN analytics_v2.dim_inventory di
    ON di.client_id = v_client_id AND di.sku = COALESCE(s.produto_sku, s.produto_nome)
  WHERE s.job_id = p_job_id
  ON CONFLICT (transacao_id, client_id) DO UPDATE SET
    data_competencia_id = EXCLUDED.data_competencia_id,
    cliente_id          = EXCLUDED.cliente_id,
    fornecedor_id       = EXCLUDED.fornecedor_id,
    produto_id          = EXCLUDED.produto_id,
    documento           = EXCLUDED.documento,
    quantidade          = EXCLUDED.quantidade,
    valor_unitario      = EXCLUDED.valor_unitario,
    valor               = EXCLUDED.valor,
    status              = EXCLUDED.status;

  GET DIAGNOSTICS v_rows = ROW_COUNT;

  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;

  v_duration := EXTRACT(epoch FROM clock_timestamp() - v_start);
  UPDATE analytics_v2.reg_jobs
  SET
    status           = 'completed',
    completed_at     = clock_timestamp(),
    rows_inserted    = v_rows,
    progress_pct     = 100,
    duration_seconds = v_duration,
    output           = jsonb_build_object(
                         'rows_inserted', v_rows,
                         'rows_staged',   v_staged,
                         'completed_at',  now()::text
                       ),
    updated_at       = clock_timestamp()
  WHERE job_id = p_job_id;

  RAISE NOTICE '[run_etl_job] job=%: DONE — % fato rows from % staged rows in %.1fs',
    p_job_id, v_rows, v_staged, v_duration;

  -- ── Refresh aggregates (non-fatal) ────────────────────────────────────────────
  BEGIN
    PERFORM analytics_v2.atualizar_agregados(v_client_id);
  EXCEPTION WHEN OTHERS THEN
    RAISE WARNING '[run_etl_job] job=%: aggregate refresh failed (non-fatal): %', p_job_id, SQLERRM;
  END;

EXCEPTION WHEN OTHERS THEN
  -- Always drop the ephemeral FT, even on failure
  IF v_ft_bare IS NOT NULL THEN
    EXECUTE format('DROP FOREIGN TABLE IF EXISTS fdw.%I CASCADE', v_ft_bare);
    RAISE NOTICE '[run_etl_job] job=%: dropped ephemeral FT fdw.% after failure', p_job_id, v_ft_bare;
  END IF;
  DELETE FROM analytics_v2.etl_staging WHERE job_id = p_job_id;
  v_duration := EXTRACT(epoch FROM clock_timestamp() - v_start);
  UPDATE analytics_v2.reg_jobs
  SET status = 'failed', completed_at = clock_timestamp(), progress_pct = 0,
      duration_seconds = v_duration, error_message = SQLERRM, updated_at = clock_timestamp()
  WHERE job_id = p_job_id;
  RAISE;
END;
$_$;


ALTER FUNCTION "analytics_v2"."run_etl_job"("p_job_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "analytics_v2"."safe_to_numeric"("p_text" "text") RETURNS numeric
    LANGUAGE "plpgsql" IMMUTABLE
    AS $_$
DECLARE
  v_text text;
BEGIN
  IF p_text IS NULL OR trim(p_text) = '' THEN
    RETURN NULL;
  END IF;
  v_text := trim(p_text);

  -- Direct cast: plain integers and standard decimals (1234, 1234.56, -1234.56)
  BEGIN
    RETURN v_text::numeric;
  EXCEPTION WHEN OTHERS THEN NULL;
  END;

  -- Brazilian format: period = thousands sep, comma = decimal ("1.234,56")
  IF v_text ~ '^-?[\d.]+,\d+$' THEN
    BEGIN
      RETURN replace(replace(v_text, '.', ''), ',', '.')::numeric;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
  END IF;

  -- US format: comma = thousands sep, period = decimal ("1,234.56")
  IF v_text ~ '^-?[\d,]+\.\d+$' THEN
    BEGIN
      RETURN replace(v_text, ',', '')::numeric;
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
  END IF;

  RETURN NULL;
END;
$_$;


ALTER FUNCTION "analytics_v2"."safe_to_numeric"("p_text" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."_bq_canonical_ref"("p_project_id" "text", "p_dataset_id" "text", "p_table_name" "text") RETURNS "text"
    LANGUAGE "sql" IMMUTABLE
    AS $$
  SELECT p_project_id || '.' || p_dataset_id || '.' || p_table_name;
$$;


ALTER FUNCTION "public"."_bq_canonical_ref"("p_project_id" "text", "p_dataset_id" "text", "p_table_name" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."_bq_col_defs_from_jsonb"("p_columns" "jsonb") RETURNS "text"
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
  SELECT string_agg(
    format('%I %s', col->>'name', public._bq_type_to_postgres_type(col->>'type')),
    ', '
    ORDER BY ordinality
  )
  FROM jsonb_array_elements(p_columns) WITH ORDINALITY AS t(col, ordinality);
$$;


ALTER FUNCTION "public"."_bq_col_defs_from_jsonb"("p_columns" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") RETURNS "text"
    LANGUAGE "plpgsql" IMMUTABLE
    AS $$
DECLARE
  v_bq_type_lower TEXT := LOWER(p_bq_type);
BEGIN
  CASE v_bq_type_lower
    -- Numeric types
    WHEN 'int64', 'integer' THEN RETURN 'bigint';
    WHEN 'int32' THEN RETURN 'integer';
    WHEN 'float64', 'float' THEN RETURN 'double precision';
    WHEN 'float32' THEN RETURN 'real';
    WHEN 'numeric', 'decimal' THEN RETURN 'numeric';

    -- String types
    WHEN 'string' THEN RETURN 'text';
    WHEN 'bytes' THEN RETURN 'bytea';

    -- Boolean
    WHEN 'bool', 'boolean' THEN RETURN 'boolean';

    -- Temporal types
    WHEN 'date' THEN RETURN 'date';
    WHEN 'time', 'time64' THEN RETURN 'time';
    WHEN 'datetime', 'timestamp' THEN RETURN 'timestamp with time zone';

    -- Complex types (stored as JSON)
    WHEN 'record', 'struct' THEN RETURN 'jsonb';
    WHEN 'array' THEN RETURN 'jsonb';
    WHEN 'geography', 'bignumeric' THEN RETURN 'jsonb';

    -- Default fallback
    ELSE RETURN 'text';
  END CASE;
END;
$$;


ALTER FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") IS 'Helper function to map BigQuery data types to PostgreSQL equivalents.
Used by async discovery to generate CREATE FOREIGN TABLE DDL.';



CREATE OR REPLACE FUNCTION "public"."bootstrap_knowledge_from_onboarding"("p_client_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'vector_db'
    AS $$
DECLARE
  v_cp        jsonb;
  v_ts        jsonb;
  v_seeded    int := 0;
BEGIN
  SELECT company_profile, team_structure
    INTO v_cp, v_ts
    FROM public.clientes_blu
   WHERE client_id = p_client_id;

  -- ficha_cadastral: partial if any profile identity fields exist
  IF (v_cp->>'legal_name') IS NOT NULL OR (v_cp->>'industry') IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'ficha_cadastral', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- perfil_empresarial: partial if industry + size both set
  IF (v_cp->>'industry') IS NOT NULL AND (v_cp->>'employee_count_range') IS NOT NULL THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'perfil_empresarial', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- posicionamento: partial if website context exists in RAG
  IF EXISTS (
    SELECT 1 FROM vector_db.documents
     WHERE client_id = p_client_id AND source = 'onboarding.website_context'
  ) THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'posicionamento', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- organograma: partial if team contacts are set
  IF jsonb_array_length(COALESCE(v_ts->'key_contacts', '[]'::jsonb)) > 0 THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES (p_client_id, 'organograma', 'partial', 'onboarding')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 1;
  END IF;

  -- ERP/commerce integration → seed commerce + financial docs as partial
  IF EXISTS (
    SELECT 1 FROM public.integration_configs
     WHERE client_id = p_client_id
       AND provider IN ('bling','omie','tiny','shopify','vtex','nuvemshop')
  ) THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES
      (p_client_id, 'historico_pedidos',  'partial', 'erp'),
      (p_client_id, 'catalogo_produtos',  'partial', 'erp'),
      (p_client_id, 'fluxo_caixa_diario', 'partial', 'erp')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 3;
  END IF;

  -- ERP with purchasing features → supplier/inventory docs
  IF EXISTS (
    SELECT 1 FROM public.integration_configs
     WHERE client_id = p_client_id
       AND provider IN ('bling','omie','tiny')
  ) THEN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source)
    VALUES
      (p_client_id, 'cadastro_fornecedores', 'partial', 'erp'),
      (p_client_id, 'controle_inventario',   'partial', 'erp')
    ON CONFLICT (client_id, document_type_id) DO NOTHING;
    v_seeded := v_seeded + 2;
  END IF;

  -- client_data_sources synced → upgrade to complete (never downgrade)
  UPDATE public.client_knowledge_documents ckd
     SET status     = 'complete',
         source     = 'erp_synced',
         updated_at = now()
    FROM public.client_data_sources cds
   WHERE cds.client_id = p_client_id::text
     AND cds.sync_status IN ('ready','success')
     AND ckd.client_id = p_client_id
     AND ckd.document_type_id = CASE cds.resource_type
           WHEN 'orders'       THEN 'historico_pedidos'
           WHEN 'pedidos'      THEN 'historico_pedidos'
           WHEN 'products'     THEN 'catalogo_produtos'
           WHEN 'inventory'    THEN 'controle_inventario'
           WHEN 'estoque'      THEN 'controle_inventario'
           WHEN 'customers'    THEN 'ficha_cliente'
           WHEN 'clientes'     THEN 'ficha_cliente'
           WHEN 'fornecedores' THEN 'cadastro_fornecedores'
           ELSE NULL
         END
     AND ckd.status != 'complete';

  RETURN jsonb_build_object('client_id', p_client_id, 'docs_seeded', v_seeded);
END;
$$;


ALTER FUNCTION "public"."bootstrap_knowledge_from_onboarding"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_credential_id" "uuid", "p_location" "text" DEFAULT 'US'::"text") RETURNS "jsonb"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_temp'
    AS $$
DECLARE
  v_my_client_id   UUID;
  v_data_source_id UUID;
  v_server_name    TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;
  IF p_client_id != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    SELECT server_name INTO v_server_name
    FROM public.bigquery_servers
    WHERE client_id = v_my_client_id::text LIMIT 1;

    IF v_server_name IS NULL THEN
      RAISE EXCEPTION 'BigQuery server not configured for this tenant. Call create_bigquery_server first.';
    END IF;

    INSERT INTO public.bigquery_foreign_tables (
      id, client_id, table_name, bigquery_table, server_name, columns, location, created_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id::text, p_table_name,
      p_bigquery_table, v_server_name, '[]'::jsonb, p_location, NOW()
    )
    ON CONFLICT (client_id, table_name) DO UPDATE SET
      bigquery_table = EXCLUDED.bigquery_table,
      server_name    = EXCLUDED.server_name,
      location       = EXCLUDED.location,
      columns        = '[]'::jsonb;

    INSERT INTO public.client_data_sources (
      id, client_id, credential_id, source_type, resource_type,
      storage_type, storage_location, source_columns, sync_status, created_at, updated_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id::text, p_credential_id,
      'bigquery', 'table', 'bigquery_fdw', p_bigquery_table,
      '[]'::jsonb, 'discovery_pending', NOW(), NOW()
    )
    ON CONFLICT (client_id, source_type, resource_type) DO UPDATE SET
      source_columns = '[]'::jsonb,
      sync_status    = 'discovery_pending',
      credential_id  = EXCLUDED.credential_id,
      updated_at     = NOW()
    RETURNING id INTO v_data_source_id;

    RETURN jsonb_build_object(
      'success',        true,
      'data_source_id', v_data_source_id,
      'sync_status',    'discovery_pending',
      'message',        'Metadata registered. Calling discover-bigquery-columns to create FT with real schema.'
    );

  EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
  END;
END;
$$;


ALTER FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_credential_id" "uuid", "p_location" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_location" "text" DEFAULT 'US'::"text", "p_timeout_ms" integer DEFAULT 300000, "p_credential_id" bigint DEFAULT NULL::bigint) RETURNS "jsonb"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_temp'
    AS $$
DECLARE
  v_my_client_id   UUID;
  v_data_source_id UUID;
  v_server_name    TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;
  IF p_client_id != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    SELECT server_name INTO v_server_name
    FROM public.bigquery_servers
    WHERE client_id = v_my_client_id::text LIMIT 1;

    IF v_server_name IS NULL THEN
      RAISE EXCEPTION 'BigQuery server not configured for this tenant. Call create_bigquery_server first.';
    END IF;

    INSERT INTO public.bigquery_foreign_tables (
      id, client_id, table_name, bigquery_table, server_name, columns, location, created_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id::text, p_table_name,
      p_bigquery_table, v_server_name, '[]'::jsonb, p_location, NOW()
    )
    ON CONFLICT (client_id, table_name) DO UPDATE SET
      bigquery_table = EXCLUDED.bigquery_table,
      server_name    = EXCLUDED.server_name,
      location       = EXCLUDED.location,
      columns        = '[]'::jsonb;

    INSERT INTO public.client_data_sources (
      id, client_id, source_type, resource_type,
      storage_type, storage_location, source_columns, sync_status, created_at, updated_at
    )
    VALUES (
      gen_random_uuid(), v_my_client_id::text,
      'bigquery', 'table', 'bigquery_fdw', p_bigquery_table,
      '[]'::jsonb, 'discovery_pending', NOW(), NOW()
    )
    ON CONFLICT (client_id, source_type, resource_type) DO UPDATE SET
      source_columns = '[]'::jsonb,
      sync_status    = 'discovery_pending',
      updated_at     = NOW()
    RETURNING id INTO v_data_source_id;

    RETURN jsonb_build_object(
      'success',        true,
      'data_source_id', v_data_source_id,
      'sync_status',    'discovery_pending',
      'message',        'Metadata registered. Calling discover-bigquery-columns to create FT with real schema.'
    );

  EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
  END;
END;
$$;


ALTER FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_location" "text", "p_timeout_ms" integer, "p_credential_id" bigint) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_bigquery_foreign_table_from_schema"("p_client_id" "text", "p_columns" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_server_name  TEXT;
  v_project_id   TEXT;
  v_dataset_id   TEXT;
  v_bare_table   TEXT;
  v_col_defs     TEXT;
BEGIN
  SELECT server_name, project_id, dataset_id
  INTO v_server_name, v_project_id, v_dataset_id
  FROM public.bigquery_servers
  WHERE client_id::text = p_client_id::text
  LIMIT 1;

  IF v_server_name IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No BigQuery server found for this client');
  END IF;

  SELECT table_name INTO v_bare_table
  FROM public.bigquery_foreign_tables
  WHERE client_id::text = p_client_id::text
  ORDER BY created_at DESC
  LIMIT 1;

  IF v_bare_table IS NULL THEN
    RETURN jsonb_build_object('success', false, 'error', 'No foreign table metadata found for this client');
  END IF;

  v_col_defs := public._bq_col_defs_from_jsonb(p_columns);
  IF v_col_defs IS NULL OR v_col_defs = '' THEN
    RETURN jsonb_build_object('success', false, 'error', 'p_columns array is empty or contains unmappable types');
  END IF;

  UPDATE public.bigquery_foreign_tables
  SET columns        = p_columns,
      server_name    = v_server_name,
      bigquery_table = public._bq_canonical_ref(v_project_id, v_dataset_id, v_bare_table)
  WHERE client_id::text = p_client_id::text;

  RETURN jsonb_build_object(
    'success',       true,
    'columns_count', jsonb_array_length(p_columns),
    'bigquery_ref',  public._bq_canonical_ref(v_project_id, v_dataset_id, v_bare_table)
  );

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION "public"."create_bigquery_foreign_table_from_schema"("p_client_id" "text", "p_columns" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text" DEFAULT 'US'::"text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_my_client_id UUID;
  v_server_name TEXT;
  v_vault_key_id UUID;
  v_secret_name TEXT;
  v_existing_server_name TEXT;
  v_error_msg TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  IF p_service_account_key IS NULL THEN
    RAISE EXCEPTION 'service_account_key cannot be null';
  END IF;

  IF (p_service_account_key->>'type')::text != 'service_account' THEN
    RAISE EXCEPTION 'Invalid service account key: missing or incorrect type field';
  END IF;

  IF (p_service_account_key->>'project_id')::text IS NULL THEN
    RAISE EXCEPTION 'Invalid service account key: missing project_id field';
  END IF;

  IF (p_service_account_key->>'private_key')::text IS NULL THEN
    RAISE EXCEPTION 'Invalid service account key: missing private_key field';
  END IF;

  BEGIN
    v_server_name := 'bq_server_' || (v_my_client_id::text) || '_' || EXTRACT(EPOCH FROM NOW())::bigint::text;

    SELECT server_name INTO v_existing_server_name
    FROM public.bigquery_servers
    WHERE client_id::text = v_my_client_id::text
    LIMIT 1;

    IF v_existing_server_name IS NOT NULL THEN
      SELECT vault_key_id INTO v_vault_key_id
      FROM public.bigquery_servers
      WHERE client_id::text = v_my_client_id::text;

      RETURN jsonb_build_object(
        'success', true,
        'server_name', v_existing_server_name,
        'vault_key_id', v_vault_key_id,
        'message', 'BigQuery server already exists for this tenant'
      );
    END IF;

    v_vault_key_id := gen_random_uuid();
    v_secret_name := 'bigquery_service_account_' || v_vault_key_id::text;

    INSERT INTO vault.decrypted_secrets (name, decrypted_secret)
    VALUES (v_secret_name, p_service_account_key::text)
    ON CONFLICT (name) DO NOTHING;

    PERFORM 1 FROM vault.decrypted_secrets WHERE name = v_secret_name;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'Failed to store credentials in Vault';
    END IF;

    EXECUTE format('CREATE SERVER IF NOT EXISTS %I FOREIGN DATA WRAPPER bigquery_fdw OPTIONS (project_id %L, dataset_id %L, location %L)',
                   v_server_name, p_project_id, p_dataset_id, p_location);

    EXECUTE format('CREATE USER MAPPING IF NOT EXISTS FOR current_user SERVER %I OPTIONS (service_account_json %L)',
                   v_server_name, p_service_account_key::text);

    INSERT INTO public.bigquery_servers (
      client_id, server_name, project_id, dataset_id,
      vault_key_id, location, created_at, updated_at
    )
    VALUES (
      v_my_client_id::text, v_server_name, p_project_id, p_dataset_id,
      v_vault_key_id, p_location, NOW(), NOW()
    )
    ON CONFLICT (client_id) DO NOTHING;

    RETURN jsonb_build_object(
      'success', true,
      'server_name', v_server_name,
      'vault_key_id', v_vault_key_id
    );

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;

    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN
      NULL;
    END;

    IF v_vault_key_id IS NOT NULL THEN
      BEGIN
        DELETE FROM vault.decrypted_secrets WHERE name = v_secret_name;
      EXCEPTION WHEN OTHERS THEN
        NULL;
      END;
    END IF;

    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$$;


ALTER FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text") IS 'Creates a BigQuery foreign server for a client';



CREATE OR REPLACE FUNCTION "public"."decide_approval"("p_request_id" "uuid", "p_decision" "text", "p_reason" "text" DEFAULT NULL::"text") RETURNS "jsonb"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  UPDATE public.approval_requests
  SET status     = p_decision,
      decided_by = auth.uid()::text,
      decided_at = now(),
      payload    = payload || jsonb_build_object('reason', p_reason)
  WHERE id = p_request_id
    AND client_id = public.get_my_client_id()
    AND status = 'pending';

  IF NOT FOUND THEN
    RETURN jsonb_build_object('success', false, 'error', 'Not found or already decided');
  END IF;
  RETURN jsonb_build_object('success', true, 'status', p_decision);
END;
$$;


ALTER FUNCTION "public"."decide_approval"("p_request_id" "uuid", "p_decision" "text", "p_reason" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."dismiss_insight"("p_insight_id" "uuid") RETURNS "void"
    LANGUAGE "sql"
    AS $$
  UPDATE public.client_insights
  SET dismissed = true, dismissed_at = now()
  WHERE id = p_insight_id
    AND client_id = public.get_my_client_id();
$$;


ALTER FUNCTION "public"."dismiss_insight"("p_insight_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_my_client_id UUID;
  v_server_name  TEXT;
  v_vault_key_id UUID;
  v_secret_name  TEXT;
  v_error_msg    TEXT;
BEGIN
  v_my_client_id := public.get_my_client_id();
  IF v_my_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant context found for current user';
  END IF;

  IF p_client_id::text != v_my_client_id::text THEN
    RAISE EXCEPTION 'Access denied: client_id mismatch';
  END IF;

  BEGIN
    SELECT server_name, vault_key_id
    INTO v_server_name, v_vault_key_id
    FROM public.bigquery_servers
    WHERE client_id::text = v_my_client_id::text
    LIMIT 1;

    IF v_server_name IS NULL THEN
      RETURN jsonb_build_object('success', true, 'message', 'No BigQuery server found for this tenant');
    END IF;

    -- FTs are ephemeral — nothing to DROP here; they only exist during run_etl_job

    BEGIN
      EXECUTE format('DROP USER MAPPING IF EXISTS FOR current_user SERVER %I', v_server_name);
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    BEGIN
      EXECUTE format('DROP SERVER IF EXISTS %I CASCADE', v_server_name);
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    IF v_vault_key_id IS NOT NULL THEN
      v_secret_name := 'bigquery_service_account_' || v_vault_key_id::text;
      BEGIN
        DELETE FROM vault.decrypted_secrets WHERE name = v_secret_name;
      EXCEPTION WHEN OTHERS THEN NULL;
      END;
    END IF;

    DELETE FROM public.client_data_sources
    WHERE client_id::text = v_my_client_id::text AND source_type = 'bigquery';

    DELETE FROM public.bigquery_foreign_tables WHERE server_name = v_server_name;
    DELETE FROM public.bigquery_servers        WHERE server_name = v_server_name;

    RETURN jsonb_build_object('success', true, 'message', 'BigQuery server and registry removed');

  EXCEPTION WHEN OTHERS THEN
    v_error_msg := SQLERRM;
    RETURN jsonb_build_object('success', false, 'error', v_error_msg);
  END;
END;
$$;


ALTER FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") IS 'Drops BigQuery foreign server and all its tables';



CREATE OR REPLACE FUNCTION "public"."enqueue_monthly_close"() RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_last_day date;
  v_today    date := current_date;
  v_enqueued integer := 0;
  v_client_id uuid;
BEGIN
  -- Calculate last day of current month
  v_last_day := (date_trunc('month', now()) + interval '1 month' - interval '1 day')::date;

  IF v_today <> v_last_day THEN
    RETURN 0;  -- not last day of month
  END IF;

  FOR v_client_id IN
    SELECT client_id FROM public.clientes_blu
    WHERE onboarding_completed_at IS NOT NULL
  LOOP
    IF public.enqueue_routine(
      v_client_id,
      'monthly_close',
      'cron',
      jsonb_build_object('month', to_char(now(), 'YYYY-MM')),
      -- Cooldown 25 days so it can't fire twice in one month
      600
    ) IS NOT NULL THEN
      v_enqueued := v_enqueued + 1;
    END IF;
  END LOOP;

  RETURN v_enqueued;
END;
$$;


ALTER FUNCTION "public"."enqueue_monthly_close"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."enqueue_routine"("p_client_id" "uuid", "p_routine_id" "text", "p_triggered_by" "text", "p_trigger_data" "jsonb" DEFAULT '{}'::"jsonb", "p_cooldown_h" integer DEFAULT 24) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_id uuid;
BEGIN
  -- Skip if same routine fired within cooldown window
  IF EXISTS (
    SELECT 1 FROM public.client_routine_executions
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id
      AND created_at > now() - (p_cooldown_h || ' hours')::interval
  ) THEN
    RETURN NULL;
  END IF;

  INSERT INTO public.client_routine_executions
    (client_id, routine_id, triggered_by, trigger_data)
  VALUES
    (p_client_id, p_routine_id, p_triggered_by, p_trigger_data)
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;


ALTER FUNCTION "public"."enqueue_routine"("p_client_id" "uuid", "p_routine_id" "text", "p_triggered_by" "text", "p_trigger_data" "jsonb", "p_cooldown_h" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."ensure_client_approval_stats"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  INSERT INTO public.client_approval_stats (client_id)
  VALUES (NEW.client_id)
  ON CONFLICT (client_id) DO NOTHING;
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."ensure_client_approval_stats"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."ensure_tenant_row"() RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_user_id text := auth.uid()::text;
  v_email   text;
  v_client_id uuid;
  v_api_key text;
BEGIN
  SELECT client_id INTO v_client_id FROM public.clientes_blu
  WHERE external_user_id = v_user_id;
  
  IF v_client_id IS NULL THEN
    SELECT email INTO v_email FROM auth.users WHERE id = auth.uid();
    v_api_key := gen_random_uuid()::text;
    
    INSERT INTO public.clientes_blu (external_user_id, nome_empresa, api_key)
    VALUES (v_user_id, COALESCE(v_email, 'Empresa'), v_api_key)
    ON CONFLICT (external_user_id) DO NOTHING
    RETURNING client_id INTO v_client_id;
  END IF;
  
  -- Ensure api_key exists (fill in for existing rows without one)
  IF v_client_id IS NOT NULL THEN
    UPDATE public.clientes_blu
    SET api_key = COALESCE(api_key, gen_random_uuid()::text)
    WHERE client_id = v_client_id AND api_key IS NULL;
  END IF;
  
  RETURN jsonb_build_object('client_id', v_client_id);
END;
$$;


ALTER FUNCTION "public"."ensure_tenant_row"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."exec_sql"("p_query" "text") RETURNS TABLE("result" "jsonb")
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  -- session_user is the actual calling role, not the definer
  IF session_user NOT IN ('service_role', 'postgres') THEN
    RAISE EXCEPTION 'exec_sql: permission denied for role %', session_user;
  END IF;

  RETURN QUERY EXECUTE format(
    'SELECT to_jsonb(t) FROM (%s) t', p_query
  );
EXCEPTION WHEN OTHERS THEN
  RETURN QUERY SELECT jsonb_build_object('error', SQLERRM, 'detail', SQLSTATE)::JSONB;
END;
$$;


ALTER FUNCTION "public"."exec_sql"("p_query" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."expire_stale_insights"("p_days_old" integer DEFAULT 30) RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  v_count INT;
BEGIN
  UPDATE public.client_insights
  SET dismissed_at = NOW()
  WHERE dismissed_at IS NULL
    AND created_at < NOW() - (p_days_old || ' days')::INTERVAL
    AND severity != 'critical';

  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$;


ALTER FUNCTION "public"."expire_stale_insights"("p_days_old" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_agent_readiness"("p_client_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_result      jsonb;
  v_client_tier text;
BEGIN
  IF auth.role() = 'authenticated' AND p_client_id IS DISTINCT FROM public.get_my_client_id() THEN
    RAISE EXCEPTION 'Unauthorized: cannot read readiness for another client';
  END IF;

  -- Look up client tier; default to FREE if not found or NULL
  SELECT UPPER(COALESCE(tier, 'FREE'))
  INTO v_client_tier
  FROM public.clientes_blu
  WHERE client_id = p_client_id;

  v_client_tier := COALESCE(v_client_tier, 'FREE');

  WITH agent_doc_status AS (
    SELECT
      kar.agent_slug,
      kar.document_type_id,
      kar.requirement_type,
      kar.coverage_threshold,
      kdt.name            AS doc_name,
      kdt.coverage_weight,
      COALESCE(ckd.status, 'missing') AS client_doc_status,
      CASE COALESCE(ckd.status, 'missing')
        WHEN 'complete' THEN 1.0
        WHEN 'partial'  THEN 0.5
        ELSE            0.0
      END AS status_score
    FROM public.knowledge_agent_requirements kar
    JOIN public.knowledge_document_types kdt
      ON  kdt.id = kar.document_type_id
    LEFT JOIN public.client_knowledge_documents ckd
      ON  ckd.document_type_id = kar.document_type_id
      AND ckd.client_id        = p_client_id
  ),
  agent_scores AS (
    SELECT
      agent_slug,
      requirement_type,
      MAX(coverage_threshold) AS coverage_threshold,
      ROUND(
        SUM(status_score * coverage_weight) / NULLIF(SUM(coverage_weight), 0) * 100
      )::int AS weighted_pct,
      array_agg(doc_name ORDER BY doc_name)
        FILTER (WHERE requirement_type = 'minimum' AND client_doc_status = 'missing')
        AS missing_doc_names
    FROM agent_doc_status
    GROUP BY agent_slug, requirement_type
  ),
  agent_summary AS (
    SELECT
      s.agent_slug,
      cat.name          AS agent_name,
      cat.tier_required,
      (cea.enabled_at IS NOT NULL) AS is_enabled,
      MAX(CASE WHEN s.requirement_type = 'minimum'      THEN s.weighted_pct   ELSE 0   END) AS min_pct,
      MAX(CASE WHEN s.requirement_type = 'nice_to_have' THEN s.weighted_pct   ELSE 0   END) AS nice_pct,
      MAX(s.coverage_threshold) AS coverage_threshold,
      array_remove(
        array_agg(DISTINCT elem)
          FILTER (WHERE s.requirement_type = 'minimum'),
        NULL
      ) AS missing_names
    FROM agent_scores s
    CROSS JOIN LATERAL unnest(COALESCE(s.missing_doc_names, ARRAY[]::text[])) AS elem
    JOIN public.agent_catalog cat ON cat.slug = s.agent_slug
    LEFT JOIN public.client_enabled_agents cea
      ON cea.agent_slug = s.agent_slug AND cea.client_id = p_client_id
    GROUP BY s.agent_slug, cat.name, cat.tier_required, cea.enabled_at
  )
  SELECT jsonb_agg(
    jsonb_build_object(
      'agent_slug',       agent_slug,
      'agent_name',       agent_name,
      'tier_required',    tier_required,
      'is_enabled',       is_enabled,
      -- tier_blocked: client's subscription tier is below what this agent requires
      'tier_blocked',     CASE
                            WHEN UPPER(tier_required) = 'PRO'   AND v_client_tier NOT IN ('PRO')          THEN true
                            WHEN UPPER(tier_required) = 'BASIC' AND v_client_tier = 'FREE'                THEN true
                            ELSE false
                          END,
      'status',           CASE
                            -- Tier gate takes priority over document coverage
                            WHEN UPPER(tier_required) = 'PRO'   AND v_client_tier NOT IN ('PRO')          THEN 'blocked'
                            WHEN UPPER(tier_required) = 'BASIC' AND v_client_tier = 'FREE'                THEN 'blocked'
                            WHEN min_pct >= (coverage_threshold * 100)                                    THEN 'ready'
                            WHEN min_pct > 0                                                              THEN 'partial'
                            ELSE                                                                               'blocked'
                          END,
      'capability',       CASE WHEN nice_pct >= 70 THEN 'full' ELSE 'partial' END,
      'min_coverage_pct', min_pct,
      'nice_coverage_pct',nice_pct,
      'missing_docs',     COALESCE(to_jsonb(missing_names), '[]'::jsonb)
    ) ORDER BY agent_slug
  )
  INTO v_result
  FROM agent_summary;

  RETURN COALESCE(v_result, '[]'::jsonb);
END;
$$;


ALTER FUNCTION "public"."get_agent_readiness"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_agent_runs_today"() RETURNS TABLE("total" integer, "by_agent" "jsonb")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'analytics_v2'
    AS $$
SELECT
  COUNT(*)::INT AS total,
  JSONB_OBJECT_AGG(
    COALESCE(resource_type, 'unknown'),
    run_count
  ) AS by_agent
FROM (
  SELECT
    resource_type,
    COUNT(*)::INT AS run_count
  FROM analytics_v2.reg_jobs
  WHERE client_id = public.get_my_client_id()
    AND job_type LIKE '%agent%'
    AND DATE(created_at) = CURRENT_DATE
  GROUP BY resource_type
) subquery;
$$;


ALTER FUNCTION "public"."get_agent_runs_today"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_commercial_revenue_by_channel"() RETURNS TABLE("channel" "text", "total_revenue" numeric, "transaction_count" integer, "avg_transaction_value" numeric)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    f.channel::TEXT,
    SUM(f.valor_total)::NUMERIC as total_revenue,
    COUNT(*)::INT as transaction_count,
    AVG(f.valor_total)::NUMERIC as avg_transaction_value
  FROM analytics_v2.fato_transacoes f
  WHERE f.client_id = public.get_my_client_id()
    AND f.data_transacao >= NOW() - INTERVAL '90 days'
  GROUP BY f.channel
  ORDER BY total_revenue DESC;
END;
$$;


ALTER FUNCTION "public"."get_commercial_revenue_by_channel"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_commercial_top_clients"() RETURNS TABLE("cliente_id" bigint, "cliente_nome" "text", "total_volume" numeric, "total_revenue" numeric, "last_purchase" timestamp with time zone)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.nome::TEXT,
    COUNT(f.pedido_id)::NUMERIC as total_volume,
    SUM(f.valor_total)::NUMERIC as total_revenue,
    MAX(f.data_transacao) as last_purchase
  FROM analytics_v2.fato_transacoes f
  LEFT JOIN analytics_v2.dim_clientes d ON f.cliente_id = d.id
  WHERE f.client_id = public.get_my_client_id()
    AND f.data_transacao >= NOW() - INTERVAL '90 days'
  GROUP BY d.id, d.nome
  ORDER BY total_revenue DESC
  LIMIT 10;
END;
$$;


ALTER FUNCTION "public"."get_commercial_top_clients"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_knowledge_coverage"("p_client_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public', 'vector_db'
    AS $$
DECLARE
  v_result jsonb;
BEGIN
  IF auth.role() = 'authenticated' AND p_client_id IS DISTINCT FROM public.get_my_client_id() THEN
    RAISE EXCEPTION 'Unauthorized: cannot read coverage for another client';
  END IF;

  WITH doc_status AS (
    SELECT
      kdt.id              AS document_type_id,
      kdt.domain_id,
      kdt.subdomain_id,
      kdt.name,
      kdt.type,
      kdt.status          AS doc_status,
      kdt.coverage_weight,
      kdt.tags,
      kdt.consumed_by,
      COALESCE(ckd.status, 'missing') AS client_status
    FROM public.knowledge_document_types kdt
    LEFT JOIN public.client_knowledge_documents ckd
      ON  ckd.document_type_id = kdt.id
      AND ckd.client_id        = p_client_id
  ),
  weighted AS (
    SELECT
      domain_id,
      subdomain_id,
      document_type_id,
      name,
      doc_status,
      client_status,
      tags,
      consumed_by,
      coverage_weight * CASE doc_status
        WHEN 'required'  THEN 1.0
        WHEN 'optional'  THEN 0.6
        WHEN 'generated' THEN 0.8
        ELSE 1.0
      END AS effective_weight,
      coverage_weight * CASE doc_status
        WHEN 'required'  THEN 1.0
        WHEN 'optional'  THEN 0.6
        WHEN 'generated' THEN 0.8
        ELSE 1.0
      END * CASE client_status
        WHEN 'complete' THEN 1.0
        WHEN 'partial'  THEN 0.5
        ELSE            0.0
      END AS earned_weight
    FROM doc_status
  ),
  group_scores AS (
    SELECT
      domain_id,
      subdomain_id,
      ROUND(
        CASE WHEN SUM(effective_weight) = 0 THEN 0
             ELSE SUM(earned_weight) / SUM(effective_weight)
        END * 100
      )::int AS coverage_pct,
      jsonb_agg(
        jsonb_build_object(
          'id',            document_type_id,
          'name',          name,
          'type',          doc_status,
          'client_status', client_status,
          'tags',          tags,
          'consumed_by',   consumed_by
        ) ORDER BY document_type_id
      ) AS documents
    FROM weighted
    GROUP BY domain_id, subdomain_id
  )
  SELECT jsonb_agg(
    jsonb_build_object(
      'domain_id',    domain_id,
      'subdomain_id', subdomain_id,
      'coverage_pct', coverage_pct,
      'is_covered',   (coverage_pct >= 60),
      'documents',    documents
    ) ORDER BY domain_id, COALESCE(subdomain_id, '')
  )
  INTO v_result
  FROM group_scores;

  RETURN COALESCE(v_result, '[]'::jsonb);
END;
$$;


ALTER FUNCTION "public"."get_knowledge_coverage"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_my_client_id"() RETURNS "uuid"
    LANGUAGE "sql" STABLE SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
  SELECT COALESCE(
    -- 1. app_metadata (backend-authoritative)
    (auth.jwt() -> 'app_metadata' ->> 'client_id')::uuid,
    -- 2. user_metadata (social/onboarding path)
    (auth.jwt() -> 'user_metadata' ->> 'client_id')::uuid,
    -- 3. DB lookup (legacy accounts without JWT claim)
    (SELECT client_id
     FROM public.clientes_blu
     WHERE external_user_id = (auth.jwt() ->> 'sub')
     LIMIT 1)
  );
$$;


ALTER FUNCTION "public"."get_my_client_id"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_my_dashboard_kpis"() RETURNS TABLE("dimension" "text", "slot_index" integer, "slug" "text", "label" "text", "unit" "text", "formula" "text", "data_status" "text", "tier_required" "text", "is_enabled" boolean)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
SELECT
  kc.dimension,
  ROW_NUMBER() OVER (PARTITION BY kc.dimension ORDER BY COALESCE(kc.sort_order, 999)) AS slot_index,
  kc.slug,
  kc.label,
  kc.unit,
  kc.formula,
  kc.data_status,
  kc.tier_required,
  COALESCE(ck.slug IS NOT NULL, FALSE) AS is_enabled
FROM public.kpi_catalog kc
LEFT JOIN public.client_dimension_kpis ck
  ON ck.slug = kc.slug
  AND ck.client_id = public.get_my_client_id()
  AND ck.dimension = kc.dimension
ORDER BY kc.dimension, COALESCE(kc.sort_order, 999);
$$;


ALTER FUNCTION "public"."get_my_dashboard_kpis"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_my_insights"("p_limit" integer DEFAULT 5, "p_status" "text" DEFAULT 'active'::"text") RETURNS TABLE("id" "uuid", "run_date" timestamp with time zone, "dimension" "text", "kpi" "text", "severity" "text", "title" "text", "observation" "text", "recommendation" "text", "metric_value" numeric, "baseline_value" numeric, "variance_pct" numeric, "status" "text", "created_at" timestamp with time zone)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
SELECT
  ci.id,
  ci.generated_at::TIMESTAMPTZ AS run_date,
  ci.dimension,
  ''::TEXT AS kpi,
  ci.severity,
  ci.title,
  ci.body::TEXT AS observation,
  ''::TEXT AS recommendation,
  NULL::NUMERIC AS metric_value,
  NULL::NUMERIC AS baseline_value,
  NULL::NUMERIC AS variance_pct,
  CASE WHEN ci.dismissed THEN 'dismissed' ELSE 'active' END AS status,
  ci.generated_at::TIMESTAMPTZ AS created_at
FROM public.client_insights ci
WHERE ci.client_id = public.get_my_client_id()
  AND (
    p_status = 'active'    AND NOT ci.dismissed
    OR p_status = 'dismissed' AND ci.dismissed
    OR p_status NOT IN ('active', 'dismissed')
  )
ORDER BY ci.generated_at DESC
LIMIT p_limit;
$$;


ALTER FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_nps_score"("p_window_days" integer DEFAULT 90) RETURNS TABLE("score" numeric, "total_responses" bigint, "promoters" bigint, "passives" bigint, "detractors" bigint)
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
SELECT
  CASE
    WHEN COUNT(*) > 0
    THEN ROUND(
      ((COALESCE(SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END), 0)::NUMERIC -
        COALESCE(SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END), 0)::NUMERIC) /
       COUNT(*)::NUMERIC * 100), 1)
    ELSE NULL::NUMERIC
  END AS score,
  COUNT(*)::BIGINT AS total_responses,
  COALESCE(SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END), 0)::BIGINT AS promoters,
  COALESCE(SUM(CASE WHEN score >= 7 AND score <= 8 THEN 1 ELSE 0 END), 0)::BIGINT AS passives,
  COALESCE(SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END), 0)::BIGINT AS detractors
FROM public.nps_responses
WHERE client_id = public.get_my_client_id()
  AND created_at >= CURRENT_TIMESTAMP - (p_window_days || ' days')::INTERVAL;
$$;


ALTER FUNCTION "public"."get_nps_score"("p_window_days" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_pendencias"() RETURNS TABLE("kind" "text", "title" "text", "severity" "text", "occurred_at" timestamp with time zone, "target_route" "text")
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'analytics_v2', 'public'
    AS $$
SELECT
  CASE
    WHEN rj.job_type = 'connector_sync' THEN 'connector_error'
    WHEN rj.job_type = 'bigquery_sync'  THEN 'data_source_issue'
    WHEN rj.job_type = 'analytics_etl'  THEN 'rfq_pending'
    ELSE 'rfq_pending'
  END AS kind,
  'Job: ' || rj.job_type || ' - ' || COALESCE(rj.resource_type, 'Unknown') AS title,
  CASE
    WHEN rj.status = 'failed'  THEN 'error'
    WHEN rj.status = 'pending' THEN 'warning'
    ELSE 'info'
  END AS severity,
  rj.created_at AS occurred_at,
  CASE
    WHEN rj.job_type = 'connector_sync' THEN '/dashboard/connectors'
    WHEN rj.job_type = 'bigquery_sync'  THEN '/dashboard/sources'
    ELSE '/dashboard'
  END AS target_route
FROM analytics_v2.reg_jobs rj
WHERE rj.client_id = public.get_my_client_id()
  AND (rj.status IN ('pending', 'failed') OR rj.error_message IS NOT NULL)
ORDER BY rj.created_at DESC;
$$;


ALTER FUNCTION "public"."get_pendencias"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_platform_google_oauth_config"() RETURNS "jsonb"
    LANGUAGE "sql" STABLE SECURITY DEFINER
    AS $$
  SELECT decrypted_secret::jsonb FROM vault.decrypted_secrets
  WHERE name = 'google_oauth_config' LIMIT 1;
$$;


ALTER FUNCTION "public"."get_platform_google_oauth_config"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_recent_activity"("p_limit" integer DEFAULT 10) RETURNS TABLE("kind" "text", "title" "text", "subtitle" "text", "occurred_at" timestamp with time zone, "severity" "text")
    LANGUAGE "sql" STABLE
    SET "search_path" TO 'public'
    AS $$
SELECT
  CASE
    WHEN action = 'CREATE' THEN 'ingestion'
    WHEN action = 'UPDATE' THEN 'agent_session'
    WHEN action = 'DELETE' THEN 'error'
    ELSE 'info'
  END AS kind,
  UPPER(entity_type) || ' ' || action AS title,
  (payload->>'description')::TEXT AS subtitle,
  created_at AS occurred_at,
  CASE
    WHEN action = 'DELETE' THEN 'error'
    WHEN action = 'UPDATE' THEN 'warning'
    ELSE 'info'
  END AS severity
FROM public.audit_log
WHERE client_id = public.get_my_client_id()
ORDER BY created_at DESC
LIMIT p_limit;
$$;


ALTER FUNCTION "public"."get_recent_activity"("p_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_new_auth_user"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_client_id uuid;
  v_api_key text;
BEGIN
  -- Generate a fresh API key
  v_api_key := gen_random_uuid()::text;
  
  -- Insert or update: if row exists (via external_user_id), keep existing api_key
  -- Otherwise create with new api_key
  INSERT INTO public.clientes_blu (
    external_user_id,
    api_key,
    nome_empresa,
    created_at,
    updated_at
  )
  VALUES (
    NEW.id::text,
    v_api_key,
    COALESCE(NEW.email, 'Empresa'),
    now(),
    now()
  )
  ON CONFLICT (external_user_id) DO NOTHING
  RETURNING client_id INTO v_client_id;

  -- If row already existed (conflict), get its client_id
  IF v_client_id IS NULL THEN
    SELECT client_id INTO v_client_id FROM public.clientes_blu
    WHERE external_user_id = NEW.id::text;
  END IF;

  -- Log the creation
  IF v_client_id IS NOT NULL THEN
    INSERT INTO public.audit_log (
      client_id,
      actor_id,
      action,
      entity_type,
      payload
    ) VALUES (
      v_client_id,
      NEW.id::text,
      'tenant_auto_created',
      'clientes_blu',
      jsonb_build_object('email', NEW.email, 'api_key_generated', true)
    );
  END IF;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."handle_new_auth_user"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_due_report_schedules"() RETURNS TABLE("schedule_id" "uuid", "client_id" "uuid", "name" "text", "report_type" "text", "cron_expr" "text")
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.client_id,
    s.name,
    s.report_type,
    s.cron_expr
  FROM public.report_schedules s
  WHERE s.active = TRUE
    AND s.next_run_at <= NOW()
  ORDER BY s.next_run_at ASC;
END;
$$;


ALTER FUNCTION "public"."list_due_report_schedules"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_inbox_threads"("p_limit" integer DEFAULT 50) RETURNS TABLE("id" "uuid", "client_id" "uuid", "created_at" timestamp with time zone, "updated_at" timestamp with time zone, "message_count" integer, "last_message_at" timestamp with time zone)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    c.id,
    c.client_id,
    c.created_at,
    c.updated_at,
    (SELECT COUNT(*)::INT FROM public.messages m WHERE m.session_id = c.id) as message_count,
    (SELECT MAX(m.created_at) FROM public.messages m WHERE m.session_id = c.id) as last_message_at
  FROM public.conversa c
  WHERE c.client_id = public.get_my_client_id()
  ORDER BY c.updated_at DESC
  LIMIT p_limit;
END;
$$;


ALTER FUNCTION "public"."list_inbox_threads"("p_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_kpi_catalog"("p_dimension" "text" DEFAULT NULL::"text", "p_only_enabled" boolean DEFAULT false) RETURNS TABLE("slug" "text", "dimension" "text", "label" "text", "unit" "text", "data_status" "text", "sort_order" integer, "is_default" boolean, "default_dimension_rank" integer, "is_enabled" boolean)
    LANGUAGE "sql" STABLE
    AS $$
  SELECT
    k.slug, k.dimension, k.label, k.unit, k.data_status, k.sort_order,
    false AS is_default,
    NULL::int AS default_dimension_rank,
    (EXISTS (
      SELECT 1 FROM public.client_dimension_kpis ck
      WHERE ck.client_id = public.get_my_client_id()
        AND ck.slug = k.slug
    )) AS is_enabled
  FROM public.kpi_catalog k
  WHERE (p_dimension IS NULL OR k.dimension = p_dimension)
    AND (NOT p_only_enabled OR EXISTS (
      SELECT 1 FROM public.client_dimension_kpis ck
      WHERE ck.client_id = public.get_my_client_id() AND ck.slug = k.slug
    ))
  ORDER BY k.sort_order, k.slug;
$$;


ALTER FUNCTION "public"."list_kpi_catalog"("p_dimension" "text", "p_only_enabled" boolean) OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."approval_requests" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "requested_by" "text",
    "action_type" "text" NOT NULL,
    "payload" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "decided_by" "text",
    "decided_at" timestamp with time zone,
    "expires_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "agent_slug" "text",
    "priority" "text" DEFAULT 'normal'::"text",
    "title" "text",
    "insight_text" "text",
    "snooze_until" timestamp with time zone,
    "snooze_count" integer DEFAULT 0,
    "scheduled_for" timestamp with time zone,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "session_id" "text",
    "tool_call_id" "text",
    CONSTRAINT "approval_requests_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'approved'::"text", 'rejected'::"text", 'cancelled'::"text"])))
);


ALTER TABLE "public"."approval_requests" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_pending_approvals"() RETURNS SETOF "public"."approval_requests"
    LANGUAGE "sql" STABLE
    AS $$
  SELECT * FROM public.approval_requests
  WHERE client_id = public.get_my_client_id()
    AND status = 'pending'
    AND (expires_at IS NULL OR expires_at > now())
  ORDER BY created_at DESC;
$$;


ALTER FUNCTION "public"."list_pending_approvals"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_report_runs"("p_limit" integer DEFAULT 50) RETURNS TABLE("id" "uuid", "schedule_id" "uuid", "status" "text", "output_url" "text", "error" "text", "started_at" timestamp with time zone, "completed_at" timestamp with time zone)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    r.id,
    r.schedule_id,
    r.status,
    r.output_url,
    r.error,
    r.started_at,
    r.completed_at
  FROM public.report_runs r
  WHERE r.client_id = public.get_my_client_id()
  ORDER BY COALESCE(r.started_at, r.completed_at) DESC
  LIMIT p_limit;
END;
$$;


ALTER FUNCTION "public"."list_report_runs"("p_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."list_report_schedules"() RETURNS TABLE("id" "uuid", "name" "text", "report_type" "text", "cron_expr" "text", "active" boolean, "next_run_at" timestamp with time zone, "created_at" timestamp with time zone)
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.name,
    s.report_type,
    s.cron_expr,
    s.active,
    s.next_run_at,
    s.created_at
  FROM public.report_schedules s
  WHERE s.client_id = public.get_my_client_id()
  ORDER BY s.next_run_at ASC;
END;
$$;


ALTER FUNCTION "public"."list_report_schedules"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."merge_onboarding_state"("p_patch" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
  v_result    jsonb;
BEGIN
  UPDATE public.clientes_blu
  SET onboarding_state = onboarding_state || p_patch,
      updated_at       = now()
  WHERE client_id = v_client_id
  RETURNING onboarding_state INTO v_result;
  RETURN v_result;
END;
$$;


ALTER FUNCTION "public"."merge_onboarding_state"("p_patch" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."on_approval_completed"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_doc_type_id text;
  v_client_id   uuid := NEW.client_id;
BEGIN
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  IF v_client_id IS NULL THEN
    RETURN NEW;
  END IF;

  -- Phase 5 routine-dispatched actions carry routine_id in the payload.
  -- Use expected_output directly; no need to map action_type strings.
  IF NEW.payload->>'routine_id' IS NOT NULL THEN
    v_doc_type_id := NEW.payload->>'expected_output';  -- NULL means this step has no output doc
  ELSE
    -- Direct agent actions: map action_type → document_type_id
    v_doc_type_id := CASE NEW.action_type
      WHEN 'create_purchase_order'   THEN 'cotacao_rfq'
      WHEN 'approve_purchase_order'  THEN 'ordem_compra'
      WHEN 'comercial.draft_created' THEN 'proposta_comercial'
      WHEN 'reports.generate'        THEN
        CASE NEW.payload->>'report_type'
          WHEN 'dre'        THEN 'dre_mensal'
          WHEN 'cash_flow'  THEN 'fluxo_caixa_diario'
          WHEN 'margin'     THEN 'relatorio_lucratividade'
          ELSE NULL
        END
      WHEN 'pesquisa_nps'            THEN 'pesquisa_nps'
      WHEN 'send_consumer_reply'     THEN NULL
      ELSE NULL
    END;
  END IF;

  IF v_doc_type_id IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    INSERT INTO public.client_knowledge_documents
      (client_id, document_type_id, status, source, updated_at)
    VALUES
      (v_client_id, v_doc_type_id, 'complete', 'agent_generated', now())
    ON CONFLICT (client_id, document_type_id) DO UPDATE
      SET status     = 'complete',
          source     = 'agent_generated',
          updated_at = now()
    WHERE client_knowledge_documents.status <> 'complete';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_approval_completed] knowledge upsert failed for action_type=%, client=%: %',
      NEW.action_type, v_client_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."on_approval_completed"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."on_knowledge_document_complete"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
BEGIN
  -- Only fire when status transitions to 'complete'
  IF OLD.status = NEW.status OR NEW.status <> 'complete' THEN
    RETURN NEW;
  END IF;

  BEGIN
    -- Enqueue every routine whose trigger_document_id matches this document type
    PERFORM public.enqueue_routine(
      NEW.client_id,
      car.id,
      'document_change',
      jsonb_build_object('document_type_id', NEW.document_type_id)
    )
    FROM public.cross_agent_routines car
    WHERE car.trigger_document_id = NEW.document_type_id;
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_knowledge_document_complete] enqueue failed for doc=%, client=%: %',
      NEW.document_type_id, NEW.client_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."on_knowledge_document_complete"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."onboarding_bootstrap_tx"("p_payload" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public', 'pg_temp'
    AS $$
DECLARE
  v_client_id   uuid := public.get_my_client_id();
  v_agent_slug  text;
  v_routine_id  text;
  v_agents_ct   integer := 0;
  v_routines_ct integer := 0;
  v_notify      text;
BEGIN
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'No tenant row found for current user';
  END IF;

  v_notify := COALESCE(p_payload->>'notify_channel', 'app');

  UPDATE public.clientes_blu SET
    nome_empresa            = COALESCE(p_payload->>'nome_empresa', nome_empresa),
    company_profile         = COALESCE(p_payload->'company_profile', company_profile),
    team_structure          = COALESCE(p_payload->'team_structure', team_structure),
    policies                = COALESCE(p_payload->'policies', policies),
    onboarding_completed_at = COALESCE(onboarding_completed_at, now()),
    updated_at              = now()
  WHERE client_id = v_client_id;

  FOR v_agent_slug IN SELECT jsonb_array_elements_text(p_payload->'agents') LOOP
    INSERT INTO public.client_enabled_agents (client_id, agent_slug)
    VALUES (v_client_id, v_agent_slug)
    ON CONFLICT (client_id, agent_slug) DO NOTHING;
    v_agents_ct := v_agents_ct + 1;
  END LOOP;

  FOR v_routine_id IN SELECT jsonb_array_elements_text(p_payload->'routines') LOOP
    INSERT INTO public.client_routines (client_id, routine_id, notify_channel)
    VALUES (v_client_id, v_routine_id, v_notify)
    ON CONFLICT (client_id, routine_id) DO UPDATE SET notify_channel = EXCLUDED.notify_channel;
    v_routines_ct := v_routines_ct + 1;
  END LOOP;

  RETURN jsonb_build_object(
    'client_id', v_client_id,
    'agents',    v_agents_ct,
    'routines',  v_routines_ct
  );
END;
$$;


ALTER FUNCTION "public"."onboarding_bootstrap_tx"("p_payload" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."process_pending_routine_executions"() RETURNS integer
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_exec    record;
  v_routine record;
  v_step    jsonb;
  v_done    integer := 0;
BEGIN
  FOR v_exec IN
    SELECT cre.*
    FROM public.client_routine_executions cre
    WHERE cre.status = 'pending'
    ORDER BY cre.created_at
    LIMIT 20
  LOOP
    SELECT * INTO v_routine
    FROM public.cross_agent_routines
    WHERE id = v_exec.routine_id;

    IF NOT FOUND THEN
      UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
      CONTINUE;
    END IF;

    BEGIN
      -- Create one approval_request per step
      FOR v_step IN SELECT value FROM jsonb_array_elements(v_routine.steps)
      LOOP
        INSERT INTO public.approval_requests
          (client_id, action_type, agent_slug, payload, expires_at)
        VALUES (
          v_exec.client_id,
          v_step->>'action',
          v_step->>'agent',
          jsonb_build_object(
            'routine_id',       v_exec.routine_id,
            'execution_id',     v_exec.id,
            'step',             (v_step->>'step')::integer,
            'expected_output',  v_step->>'output',
            'routine_name',     v_routine.name
          ),
          now() + interval '7 days'
        );

        -- Pre-mark output document as partial (in-progress)
        IF v_step->>'output' IS NOT NULL THEN
          INSERT INTO public.client_knowledge_documents
            (client_id, document_type_id, status, source, updated_at)
          VALUES
            (v_exec.client_id, v_step->>'output', 'partial', 'agent_generated', now())
          ON CONFLICT (client_id, document_type_id) DO UPDATE
            SET status     = 'partial',
                updated_at = now()
          WHERE client_knowledge_documents.status = 'missing';
        END IF;
      END LOOP;

      UPDATE public.client_routine_executions
        SET status = 'dispatched', dispatched_at = now()
      WHERE id = v_exec.id;

      v_done := v_done + 1;

    EXCEPTION WHEN others THEN
      UPDATE public.client_routine_executions SET status = 'failed' WHERE id = v_exec.id;
      RAISE WARNING '[process_pending_routine_executions] failed for execution %: %', v_exec.id, SQLERRM;
    END;
  END LOOP;

  RETURN v_done;
END;
$$;


ALTER FUNCTION "public"."process_pending_routine_executions"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."record_audit"("p_action" "text", "p_entity_type" "text" DEFAULT NULL::"text", "p_entity_id" "text" DEFAULT NULL::"text", "p_payload" "jsonb" DEFAULT '{}'::"jsonb") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  INSERT INTO public.audit_log (client_id, actor_id, action, entity_type, entity_id, payload)
  VALUES (public.get_my_client_id(), auth.uid()::text, p_action, p_entity_type, p_entity_id, p_payload);
END;
$$;


ALTER FUNCTION "public"."record_audit"("p_action" "text", "p_entity_type" "text", "p_entity_id" "text", "p_payload" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."record_frontend_event"("p_event_name" "text", "p_properties" "jsonb" DEFAULT '{}'::"jsonb") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  INSERT INTO public.frontend_events (client_id, event_name, properties)
  VALUES (public.get_my_client_id(), p_event_name, p_properties);
END;
$$;


ALTER FUNCTION "public"."record_frontend_event"("p_event_name" "text", "p_properties" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."record_insight"("p_title" "text", "p_content" "text", "p_severity" "text" DEFAULT 'info'::"text", "p_data" "jsonb" DEFAULT NULL::"jsonb") RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  v_insight_id UUID;
BEGIN
  INSERT INTO public.client_insights (
    id,
    client_id,
    title,
    content,
    severity,
    metadata,
    created_at,
    dismissed_at
  )
  VALUES (
    gen_random_uuid(),
    public.get_my_client_id(),
    p_title,
    p_content,
    p_severity,
    p_data,
    NOW(),
    NULL
  )
  RETURNING id INTO v_insight_id;

  RETURN v_insight_id;
END;
$$;


ALTER FUNCTION "public"."record_insight"("p_title" "text", "p_content" "text", "p_severity" "text", "p_data" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."request_approval"("p_action_type" "text" DEFAULT NULL::"text", "p_payload" "jsonb" DEFAULT '{}'::"jsonb", "p_expires_at" timestamp with time zone DEFAULT NULL::timestamp with time zone, "p_agent_slug" "text" DEFAULT NULL::"text", "p_action" "text" DEFAULT NULL::"text", "p_session_id" "text" DEFAULT NULL::"text", "p_tool_call_id" "text" DEFAULT NULL::"text", "p_routed_to_role" "text" DEFAULT NULL::"text", "p_sla_hours" integer DEFAULT 72) RETURNS "uuid"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_id          uuid;
  v_action_type text := COALESCE(p_action_type, p_action);
  v_expires_at  timestamp with time zone := COALESCE(
    p_expires_at,
    CASE WHEN p_sla_hours IS NOT NULL THEN now() + (p_sla_hours || ' hours')::interval ELSE NULL END
  );
BEGIN
  IF v_action_type IS NULL THEN
    RAISE EXCEPTION 'request_approval: action_type (or p_action) is required';
  END IF;

  INSERT INTO public.approval_requests
    (client_id, requested_by, action_type, agent_slug, payload, expires_at,
     session_id, tool_call_id)
  VALUES
    (public.get_my_client_id(), auth.uid()::text, v_action_type, p_agent_slug,
     p_payload, v_expires_at, p_session_id, p_tool_call_id)
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;


ALTER FUNCTION "public"."request_approval"("p_action_type" "text", "p_payload" "jsonb", "p_expires_at" timestamp with time zone, "p_agent_slug" "text", "p_action" "text", "p_session_id" "text", "p_tool_call_id" "text", "p_routed_to_role" "text", "p_sla_hours" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_client_dimension_kpis"("p_dimension" "text", "p_slugs" "text"[]) RETURNS "jsonb"
    LANGUAGE "plpgsql"
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_client_id uuid := public.get_my_client_id();
BEGIN
  DELETE FROM public.client_dimension_kpis
  WHERE client_id = v_client_id AND dimension = p_dimension;

  INSERT INTO public.client_dimension_kpis (client_id, dimension, slug)
  SELECT v_client_id, p_dimension, s
  FROM unnest(p_slugs) s
  WHERE EXISTS (SELECT 1 FROM public.kpi_catalog WHERE slug = s)
  ON CONFLICT DO NOTHING;

  RETURN jsonb_build_object('dimension', p_dimension, 'count', array_length(p_slugs, 1));
END;
$$;


ALTER FUNCTION "public"."set_client_dimension_kpis"("p_dimension" "text", "p_slugs" "text"[]) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_current_cliente_id"("p_client_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  PERFORM set_config('app.current_client_id', p_client_id::text, true);
END;
$$;


ALTER FUNCTION "public"."set_current_cliente_id"("p_client_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."set_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."trigger_column_discovery"("p_credential_id" bigint) RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
DECLARE
  v_client_id UUID;
BEGIN
  SELECT client_id INTO v_client_id
  FROM public.credencial_servico_externo
  WHERE id = p_credential_id;

  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Credential not found';
  END IF;

  IF v_client_id != public.get_my_client_id() THEN
    RAISE EXCEPTION 'Access denied';
  END IF;

  UPDATE public.client_data_sources
  SET sync_status = 'discovery_pending'
  WHERE credential_id = p_credential_id;

  RETURN jsonb_build_object(
    'status', 'discovery_queued',
    'credential_id', p_credential_id,
    'queued_at', to_jsonb(NOW())
  );
END;
$$;


ALTER FUNCTION "public"."trigger_column_discovery"("p_credential_id" bigint) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_approval_stats"() RETURNS "trigger"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO public.client_approval_stats (client_id)
    VALUES (NEW.client_id)
    ON CONFLICT (client_id) DO NOTHING;

    IF NEW.status = 'approved' THEN
      UPDATE public.client_approval_stats
        SET total_approved = total_approved + 1, updated_at = now()
        WHERE client_id = NEW.client_id;
    ELSIF NEW.status = 'rejected' THEN
      UPDATE public.client_approval_stats
        SET total_rejected = total_rejected + 1, updated_at = now()
        WHERE client_id = NEW.client_id;
    END IF;

    -- Promote trust level based on total_approved thresholds
    UPDATE public.client_approval_stats
      SET trust_level = CASE
        WHEN total_approved >= 50 THEN 'full_config'
        WHEN total_approved >= 25 THEN 'rules'
        WHEN total_approved >= 10 THEN 'similar_toggle'
        ELSE 'manual'
      END,
      updated_at = now()
      WHERE client_id = NEW.client_id;
  END IF;
  RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_approval_stats"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_bigquery_foreign_table_columns"("p_client_id" "text", "p_columns" "jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_col_defs TEXT;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.bigquery_foreign_tables WHERE client_id::text = p_client_id::text
  ) THEN
    RETURN jsonb_build_object('success', false, 'error', 'No foreign table metadata found for this client');
  END IF;

  v_col_defs := public._bq_col_defs_from_jsonb(p_columns);
  IF v_col_defs IS NULL OR v_col_defs = '' THEN
    RETURN jsonb_build_object('success', false, 'error', 'p_columns array is empty or contains unmappable types');
  END IF;

  UPDATE public.bigquery_foreign_tables
  SET columns = p_columns
  WHERE client_id::text = p_client_id::text;

  RETURN jsonb_build_object('success', true, 'columns_count', jsonb_array_length(p_columns));

EXCEPTION WHEN OTHERS THEN
  RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;


ALTER FUNCTION "public"."update_bigquery_foreign_table_columns"("p_client_id" "text", "p_columns" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_data_source_mappings_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_data_source_mappings_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."upsert_client_document"("p_document_type_id" "text", "p_status" "text" DEFAULT 'complete'::"text", "p_source" "text" DEFAULT 'upload'::"text", "p_field_coverage" "jsonb" DEFAULT '{}'::"jsonb", "p_metadata" "jsonb" DEFAULT '{}'::"jsonb") RETURNS "jsonb"
    LANGUAGE "plpgsql" SECURITY DEFINER
    SET "search_path" TO 'public'
    AS $$
DECLARE
  v_client_id uuid;
  v_result    jsonb;
BEGIN
  v_client_id := public.get_my_client_id();
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'Client not authenticated';
  END IF;

  IF p_status NOT IN ('missing','partial','complete') THEN
    RAISE EXCEPTION 'Invalid status: %. Must be missing | partial | complete', p_status;
  END IF;

  INSERT INTO public.client_knowledge_documents
    (client_id, document_type_id, status, source, field_coverage, metadata, updated_at)
  VALUES
    (v_client_id, p_document_type_id, p_status, p_source, p_field_coverage, p_metadata, now())
  ON CONFLICT (client_id, document_type_id) DO UPDATE SET
    status         = EXCLUDED.status,
    source         = EXCLUDED.source,
    field_coverage = EXCLUDED.field_coverage,
    metadata       = EXCLUDED.metadata,
    updated_at     = now()
  -- Never-downgrade: only update if the new status is >= the existing status.
  -- missing (lowest) → partial → complete (highest); reverse is never allowed.
  WHERE CASE client_knowledge_documents.status
    WHEN 'missing'  THEN true                         -- any status can overwrite missing
    WHEN 'partial'  THEN EXCLUDED.status = 'complete' -- only 'complete' can overwrite partial
    WHEN 'complete' THEN false                        -- nothing overwrites complete
    ELSE true
  END
  RETURNING jsonb_build_object(
    'document_type_id', document_type_id,
    'status',           status,
    'source',           source,
    'updated_at',       updated_at
  ) INTO v_result;

  -- When the WHERE guard prevented the update, RETURNING yields nothing.
  -- Return the current row instead so callers always get a valid response.
  IF v_result IS NULL THEN
    SELECT jsonb_build_object(
      'document_type_id', document_type_id,
      'status',           status,
      'source',           source,
      'updated_at',       updated_at
    ) INTO v_result
    FROM public.client_knowledge_documents
    WHERE client_id = v_client_id AND document_type_id = p_document_type_id;
  END IF;

  RETURN v_result;
END;
$$;


ALTER FUNCTION "public"."upsert_client_document"("p_document_type_id" "text", "p_status" "text", "p_source" "text", "p_field_coverage" "jsonb", "p_metadata" "jsonb") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "vector_db"."hybrid_match_documents"("p_client_id" "uuid", "p_query_embed" "extensions"."halfvec", "p_query_text" "text", "p_match_count" integer DEFAULT 10, "p_theme_filter" "text" DEFAULT NULL::"text") RETURNS TABLE("id" integer, "document_id" "uuid", "content" "text", "metadata" "jsonb", "similarity" double precision)
    LANGUAGE "sql" STABLE SECURITY DEFINER
    AS $$
  WITH semantic AS (
    SELECT
      c.id, c.document_id, c.content, c.metadata,
      1 - (c.embedding <#> p_query_embed) AS sim
    FROM vector_db.document_chunks c
    JOIN vector_db.documents d ON d.id = c.document_id
    WHERE c.client_id = p_client_id
      AND d.source   != 'archived'
      AND (p_theme_filter IS NULL OR c.metadata->>'theme' = p_theme_filter)
    ORDER BY c.embedding <#> p_query_embed
    LIMIT p_match_count * 3
  ),
  fts AS (
    SELECT
      c.id, c.document_id, c.content, c.metadata,
      ts_rank(c.fts, plainto_tsquery('portuguese', p_query_text)) AS rank
    FROM vector_db.document_chunks c
    JOIN vector_db.documents d ON d.id = c.document_id
    WHERE c.client_id = p_client_id
      AND d.source   != 'archived'
      AND c.fts @@ plainto_tsquery('portuguese', p_query_text)
      AND (p_theme_filter IS NULL OR c.metadata->>'theme' = p_theme_filter)
    LIMIT p_match_count * 3
  )
  SELECT DISTINCT ON (COALESCE(s.id, f.id))
    COALESCE(s.id, f.id),
    COALESCE(s.document_id, f.document_id),
    COALESCE(s.content, f.content),
    COALESCE(s.metadata, f.metadata),
    COALESCE(s.sim, 0) * 0.7 + COALESCE(f.rank, 0) * 0.3 AS similarity
  FROM semantic s
  FULL OUTER JOIN fts f USING (id)
  ORDER BY COALESCE(s.id, f.id), similarity DESC
  LIMIT p_match_count;
$$;


ALTER FUNCTION "vector_db"."hybrid_match_documents"("p_client_id" "uuid", "p_query_embed" "extensions"."halfvec", "p_query_text" "text", "p_match_count" integer, "p_theme_filter" "text") OWNER TO "postgres";


CREATE FOREIGN DATA WRAPPER "bigquery_wrapper" HANDLER "extensions"."big_query_fdw_handler" VALIDATOR "extensions"."big_query_fdw_validator";




CREATE SERVER "bigquery_9192bcc1-315b-4f30-af14-3d9cc7c50fbf" FOREIGN DATA WRAPPER "bigquery_wrapper" OPTIONS (
    "dataset_id" 'dataform',
    "location" 'US',
    "project_id" 'analytics-big-query-242119',
    "sa_key_id" '9e2c7259-ebb7-457e-bea5-cf79e7ca795e'
);


ALTER SERVER "bigquery_9192bcc1-315b-4f30-af14-3d9cc7c50fbf" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "analytics_v2"."dim_clientes" (
    "cliente_id" bigint NOT NULL,
    "client_id" "uuid",
    "cpf_cnpj" "text",
    "nome" "text",
    "telefone" "text",
    "endereco_cidade" "text",
    "endereco_uf" "text",
    "total_pedidos" bigint DEFAULT 0,
    "receita_total" numeric(15,2) DEFAULT 0,
    "ticket_medio" numeric(15,2) DEFAULT 0,
    "quantidade_total" numeric DEFAULT 0,
    "frequencia_mensal" numeric,
    "dias_recencia" integer,
    "data_primeira_compra" "date",
    "data_ultima_compra" "date",
    "pontuacao_cluster" numeric,
    "nivel_cluster" "text",
    "atualizado_em" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "analytics_v2"."dim_clientes" OWNER TO "postgres";


ALTER TABLE "analytics_v2"."dim_clientes" ALTER COLUMN "cliente_id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "analytics_v2"."dim_clientes_cliente_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "analytics_v2"."dim_datas" (
    "data_id" bigint NOT NULL,
    "data" "date" NOT NULL,
    "ano" integer NOT NULL,
    "mes" integer NOT NULL,
    "dia" integer NOT NULL,
    "numero_dia_semana" integer,
    "numero_semana_ano" integer,
    "numero_semestre" integer,
    "periodo_trimestral" "text",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "analytics_v2"."dim_datas" OWNER TO "postgres";


ALTER TABLE "analytics_v2"."dim_datas" ALTER COLUMN "data_id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "analytics_v2"."dim_datas_data_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "analytics_v2"."dim_fornecedores" (
    "fornecedor_id" bigint NOT NULL,
    "client_id" "uuid",
    "cnpj" "text",
    "nome" "text",
    "telefone" "text",
    "endereco_cidade" "text",
    "endereco_uf" "text",
    "total_pedidos_recebidos" bigint DEFAULT 0,
    "receita_total" numeric(15,2) DEFAULT 0,
    "ticket_medio" numeric(15,2) DEFAULT 0,
    "total_produtos_fornecidos" bigint DEFAULT 0,
    "frequencia_mensal" numeric,
    "dias_recencia" integer,
    "data_primeira_transacao" "date",
    "data_ultima_transacao" "date",
    "pontuacao_cluster" numeric,
    "nivel_cluster" "text",
    "atualizado_em" timestamp with time zone DEFAULT "now"(),
    "category" "text",
    "tags" "text"[],
    "rating" numeric,
    "performance_summary" "text",
    "contact_email" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    CONSTRAINT "dim_fornecedores_rating_check" CHECK ((("rating" >= (0)::numeric) AND ("rating" <= (5)::numeric)))
);


ALTER TABLE "analytics_v2"."dim_fornecedores" OWNER TO "postgres";


ALTER TABLE "analytics_v2"."dim_fornecedores" ALTER COLUMN "fornecedor_id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "analytics_v2"."dim_fornecedores_fornecedor_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "analytics_v2"."dim_inventory" (
    "inventory_id" bigint NOT NULL,
    "client_id" "uuid",
    "sku" "text",
    "nome" "text",
    "quantidade_total_vendida" numeric DEFAULT 0,
    "receita_total" numeric(15,2) DEFAULT 0,
    "preco_medio" numeric(15,2) DEFAULT 0,
    "total_pedidos" bigint DEFAULT 0,
    "quantidade_media_por_pedido" numeric,
    "frequencia_mensal" numeric,
    "dias_recencia" integer,
    "data_ultima_venda" "date",
    "pontuacao_cluster" numeric,
    "nivel_cluster" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "analytics_v2"."dim_inventory" OWNER TO "postgres";


ALTER TABLE "analytics_v2"."dim_inventory" ALTER COLUMN "inventory_id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "analytics_v2"."dim_inventory_inventory_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "analytics_v2"."fato_transacoes" (
    "transacao_id" "text" NOT NULL,
    "client_id" "uuid" NOT NULL,
    "data_competencia_id" bigint,
    "cliente_id" bigint,
    "fornecedor_id" bigint,
    "produto_id" bigint,
    "documento" "text",
    "quantidade" numeric,
    "valor_unitario" numeric(15,2),
    "valor" numeric(15,2),
    "status" "text",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "analytics_v2"."fato_transacoes" OWNER TO "postgres";


CREATE MATERIALIZED VIEW "analytics_v2"."mv_distribuicao_regional" AS
 SELECT "dc"."client_id",
    "dc"."endereco_uf",
    "dc"."endereco_cidade",
    COALESCE("sum"("ft"."valor"), (0)::numeric) AS "receita_total",
    ("count"(DISTINCT "dc"."cliente_id"))::integer AS "total_clientes",
    ("count"(DISTINCT "ft"."transacao_id"))::integer AS "total_pedidos"
   FROM ("analytics_v2"."dim_clientes" "dc"
     LEFT JOIN "analytics_v2"."fato_transacoes" "ft" ON ((("dc"."cliente_id" = "ft"."cliente_id") AND ("dc"."client_id" = "ft"."client_id"))))
  GROUP BY "dc"."client_id", "dc"."endereco_uf", "dc"."endereco_cidade"
  WITH NO DATA;


ALTER MATERIALIZED VIEW "analytics_v2"."mv_distribuicao_regional" OWNER TO "postgres";


CREATE MATERIALIZED VIEW "analytics_v2"."mv_resumo_dashboard" AS
 WITH "base" AS (
         SELECT "ft"."client_id",
            ("count"(DISTINCT "dc"."cliente_id"))::integer AS "total_clientes",
            ("count"(DISTINCT "df"."fornecedor_id"))::integer AS "total_fornecedores",
            ("count"(DISTINCT "di"."inventory_id"))::integer AS "total_produtos",
            ("count"(DISTINCT "ft"."transacao_id"))::integer AS "total_pedidos",
            COALESCE("sum"("ft"."valor"), (0)::numeric) AS "receita_total",
            COALESCE("sum"("ft"."quantidade"), (0)::numeric) AS "quantidade_total_vendida",
                CASE
                    WHEN ("count"(DISTINCT "ft"."transacao_id") > 0) THEN (COALESCE("sum"("ft"."valor"), (0)::numeric) / ("count"(DISTINCT "ft"."transacao_id"))::numeric)
                    ELSE (0)::numeric
                END AS "ticket_medio",
            ("count"(DISTINCT "dc"."endereco_uf"))::integer AS "total_regioes",
                CASE
                    WHEN ("count"(DISTINCT "df"."fornecedor_id") > 0) THEN (("count"(DISTINCT "ft"."transacao_id"))::numeric / ("count"(DISTINCT "df"."fornecedor_id"))::numeric)
                    ELSE (0)::numeric
                END AS "frequencia_media_fornecedores",
            ("count"(DISTINCT "dc"."cliente_id") FILTER (WHERE ("dd"."data" >= (CURRENT_DATE - 30))))::integer AS "clientes_ativos",
            COALESCE("sum"("ft"."valor") FILTER (WHERE (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date")), (0)::numeric) AS "receita_mes_atual",
            COALESCE("sum"("ft"."quantidade") FILTER (WHERE (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date")), (0)::numeric) AS "quantidade_mes_atual",
            ("count"(DISTINCT "dc"."cliente_id") FILTER (WHERE (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date")))::integer AS "clientes_mes_atual",
            ("count"(DISTINCT "di"."inventory_id") FILTER (WHERE (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date")))::integer AS "produtos_mes_atual",
            ("count"(DISTINCT "df"."fornecedor_id") FILTER (WHERE (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date")))::integer AS "fornecedores_mes_atual",
            COALESCE("sum"("ft"."valor") FILTER (WHERE (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = (("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone) - '1 mon'::interval))::"date")), (0)::numeric) AS "receita_mes_anterior",
            COALESCE("sum"("ft"."quantidade") FILTER (WHERE (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = (("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone) - '1 mon'::interval))::"date")), (0)::numeric) AS "quantidade_mes_anterior",
            ("count"(DISTINCT "dc"."cliente_id") FILTER (WHERE (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = (("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone) - '1 mon'::interval))::"date")))::integer AS "clientes_mes_anterior",
            ("count"(DISTINCT "di"."inventory_id") FILTER (WHERE (("date_trunc"('month'::"text", ("dd"."data")::timestamp with time zone))::"date" = (("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone) - '1 mon'::interval))::"date")))::integer AS "produtos_mes_anterior"
           FROM (((("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
             LEFT JOIN "analytics_v2"."dim_clientes" "dc" ON ((("ft"."cliente_id" = "dc"."cliente_id") AND ("dc"."client_id" = "ft"."client_id"))))
             LEFT JOIN "analytics_v2"."dim_fornecedores" "df" ON ((("ft"."fornecedor_id" = "df"."fornecedor_id") AND ("df"."client_id" = "ft"."client_id"))))
             LEFT JOIN "analytics_v2"."dim_inventory" "di" ON ((("ft"."produto_id" = "di"."inventory_id") AND ("di"."client_id" = "ft"."client_id"))))
          GROUP BY "ft"."client_id"
        ), "novos_agg" AS (
         SELECT "sub"."client_id",
            ("count"(*))::integer AS "clientes_novos"
           FROM ( SELECT "ft"."client_id",
                    "ft"."cliente_id"
                   FROM ("analytics_v2"."fato_transacoes" "ft"
                     JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
                  WHERE (("ft"."cliente_id" IS NOT NULL) AND ("dd"."data" IS NOT NULL))
                  GROUP BY "ft"."client_id", "ft"."cliente_id"
                 HAVING ("min"("dd"."data") >= ("date_trunc"('month'::"text", (CURRENT_DATE)::timestamp with time zone))::"date")) "sub"
          GROUP BY "sub"."client_id"
        )
 SELECT "b"."client_id",
    "b"."total_clientes",
    "b"."total_fornecedores",
    "b"."total_produtos",
    "b"."total_pedidos",
    "b"."receita_total",
    "b"."quantidade_total_vendida",
    "b"."ticket_medio",
    "b"."receita_mes_atual",
    "b"."quantidade_mes_atual",
    "b"."clientes_mes_atual",
    "b"."produtos_mes_atual",
    "b"."fornecedores_mes_atual",
        CASE
            WHEN ("b"."receita_mes_anterior" > (0)::numeric) THEN (("b"."receita_mes_atual" - "b"."receita_mes_anterior") / "b"."receita_mes_anterior")
            ELSE (0)::numeric
        END AS "crescimento_receita",
        CASE
            WHEN ("b"."clientes_mes_anterior" > 0) THEN ((("b"."clientes_mes_atual" - "b"."clientes_mes_anterior"))::numeric / ("b"."clientes_mes_anterior")::numeric)
            ELSE (0)::numeric
        END AS "crescimento_clientes",
        CASE
            WHEN ("b"."produtos_mes_anterior" > 0) THEN ((("b"."produtos_mes_atual" - "b"."produtos_mes_anterior"))::numeric / ("b"."produtos_mes_anterior")::numeric)
            ELSE (0)::numeric
        END AS "crescimento_produtos",
        CASE
            WHEN ("b"."quantidade_mes_anterior" > (0)::numeric) THEN (("b"."quantidade_mes_atual" - "b"."quantidade_mes_anterior") / "b"."quantidade_mes_anterior")
            ELSE (0)::numeric
        END AS "crescimento_quantidade",
    "b"."frequencia_media_fornecedores",
    "b"."total_regioes",
    "to_char"((CURRENT_DATE - '1 mon'::interval), 'Mon/YYYY'::"text") AS "ultimo_mes",
    "b"."clientes_ativos",
    COALESCE("na"."clientes_novos", 0) AS "clientes_novos",
    CURRENT_TIMESTAMP AS "gerado_em"
   FROM ("base" "b"
     LEFT JOIN "novos_agg" "na" ON (("b"."client_id" = "na"."client_id")))
  WITH NO DATA;


ALTER MATERIALIZED VIEW "analytics_v2"."mv_resumo_dashboard" OWNER TO "postgres";


CREATE MATERIALIZED VIEW "analytics_v2"."mv_series_temporal" AS
 WITH "base" AS (
         SELECT "ft"."client_id",
            "to_char"(("dd"."data")::timestamp with time zone, 'YYYY-MM'::"text") AS "periodo",
            "dd"."data" AS "data_periodo",
            'receita'::"text" AS "tipo_grafico",
            'total'::"text" AS "dimensao",
            COALESCE("sum"("ft"."valor"), (0)::numeric) AS "total"
           FROM ("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
          WHERE ("dd"."data" IS NOT NULL)
          GROUP BY "ft"."client_id", "dd"."data"
        UNION ALL
         SELECT "ft"."client_id",
            "to_char"(("dd"."data")::timestamp with time zone, 'YYYY-MM'::"text") AS "to_char",
            "dd"."data",
            'clientes'::"text",
            'total'::"text",
            ("count"(DISTINCT "dc"."cliente_id"))::numeric AS "count"
           FROM (("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
             LEFT JOIN "analytics_v2"."dim_clientes" "dc" ON ((("ft"."cliente_id" = "dc"."cliente_id") AND ("dc"."client_id" = "ft"."client_id"))))
          WHERE ("dd"."data" IS NOT NULL)
          GROUP BY "ft"."client_id", "dd"."data"
        UNION ALL
         SELECT "ft"."client_id",
            "to_char"(("dd"."data")::timestamp with time zone, 'YYYY-MM'::"text") AS "to_char",
            "dd"."data",
            'fornecedores'::"text",
            'total'::"text",
            ("count"(DISTINCT "df"."fornecedor_id"))::numeric AS "count"
           FROM (("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
             LEFT JOIN "analytics_v2"."dim_fornecedores" "df" ON ((("ft"."fornecedor_id" = "df"."fornecedor_id") AND ("df"."client_id" = "ft"."client_id"))))
          WHERE ("dd"."data" IS NOT NULL)
          GROUP BY "ft"."client_id", "dd"."data"
        UNION ALL
         SELECT "ft"."client_id",
            "to_char"(("dd"."data")::timestamp with time zone, 'YYYY-MM'::"text") AS "to_char",
            "dd"."data",
            'produtos'::"text",
            'total'::"text",
            ("count"(DISTINCT "di"."inventory_id"))::numeric AS "count"
           FROM (("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
             LEFT JOIN "analytics_v2"."dim_inventory" "di" ON ((("ft"."produto_id" = "di"."inventory_id") AND ("di"."client_id" = "ft"."client_id"))))
          WHERE ("dd"."data" IS NOT NULL)
          GROUP BY "ft"."client_id", "dd"."data"
        UNION ALL
         SELECT "ft"."client_id",
            "to_char"(("dd"."data")::timestamp with time zone, 'YYYY-MM'::"text") AS "to_char",
            "dd"."data",
            'pedidos'::"text",
            'total'::"text",
            ("count"(DISTINCT "ft"."transacao_id"))::numeric AS "count"
           FROM ("analytics_v2"."fato_transacoes" "ft"
             LEFT JOIN "analytics_v2"."dim_datas" "dd" ON (("ft"."data_competencia_id" = "dd"."data_id")))
          WHERE ("dd"."data" IS NOT NULL)
          GROUP BY "ft"."client_id", "dd"."data"
        )
 SELECT "client_id",
    "periodo",
    "data_periodo",
    "tipo_grafico",
    "dimensao",
    "total",
    "sum"("total") OVER (PARTITION BY "client_id", "tipo_grafico", "dimensao" ORDER BY "data_periodo" ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS "total_cumulativo"
   FROM "base"
  WITH NO DATA;


ALTER MATERIALIZED VIEW "analytics_v2"."mv_series_temporal" OWNER TO "postgres";


CREATE MATERIALIZED VIEW "analytics_v2"."mv_ultimos_pedidos" AS
 SELECT "ft"."client_id",
    "ft"."transacao_id" AS "pedido_id",
    "dc"."cpf_cnpj" AS "cliente_cpf_cnpj",
    "ft"."valor" AS "valor_pedido",
    "ft"."quantidade" AS "qtd_produtos",
    "row_number"() OVER (PARTITION BY "ft"."client_id" ORDER BY "ft"."created_at" DESC) AS "ordem"
   FROM ("analytics_v2"."fato_transacoes" "ft"
     LEFT JOIN "analytics_v2"."dim_clientes" "dc" ON ((("ft"."cliente_id" = "dc"."cliente_id") AND ("dc"."client_id" = "ft"."client_id"))))
  WHERE ("ft"."created_at" IS NOT NULL)
  WITH NO DATA;


ALTER MATERIALIZED VIEW "analytics_v2"."mv_ultimos_pedidos" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "analytics_v2"."reg_jobs" (
    "job_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "job_type" "text" DEFAULT 'bigquery_sync'::"text" NOT NULL,
    "credential_id" bigint,
    "resource_type" "text",
    "sync_mode" "text" DEFAULT 'incremental'::"text",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "input_params" "jsonb" DEFAULT '{}'::"jsonb",
    "output" "jsonb",
    "rows_inserted" bigint DEFAULT 0,
    "progress_pct" integer DEFAULT 0,
    "error_message" "text",
    "started_at" timestamp with time zone,
    "completed_at" timestamp with time zone,
    "duration_seconds" numeric,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "retry_count" integer DEFAULT 0 NOT NULL,
    CONSTRAINT "reg_jobs_job_type_check" CHECK (("job_type" = ANY (ARRAY['bigquery_sync'::"text", 'connector_sync'::"text", 'analytics_etl'::"text", 'custom'::"text"]))),
    CONSTRAINT "reg_jobs_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text", 'cancelled'::"text"]))),
    CONSTRAINT "reg_jobs_sync_mode_check" CHECK (("sync_mode" = ANY (ARRAY['incremental'::"text", 'full'::"text"])))
);


ALTER TABLE "analytics_v2"."reg_jobs" OWNER TO "postgres";


CREATE OR REPLACE VIEW "analytics_v2"."v_distribuicao_regional" WITH ("security_invoker"='on') AS
 SELECT "client_id",
    "endereco_uf",
    "endereco_cidade",
    "receita_total",
    "total_clientes",
    "total_pedidos"
   FROM "analytics_v2"."mv_distribuicao_regional"
  WHERE ("client_id" = "public"."get_my_client_id"());


ALTER VIEW "analytics_v2"."v_distribuicao_regional" OWNER TO "postgres";


CREATE OR REPLACE VIEW "analytics_v2"."v_resumo_dashboard" AS
 SELECT "client_id",
    "total_clientes",
    "total_fornecedores",
    "total_produtos",
    "total_pedidos",
    "receita_total",
    "quantidade_total_vendida",
    "ticket_medio",
    "receita_mes_atual",
    "quantidade_mes_atual",
    "clientes_mes_atual",
    "produtos_mes_atual",
    "fornecedores_mes_atual",
    "crescimento_receita",
    "crescimento_clientes",
    "crescimento_produtos",
    "crescimento_quantidade",
    "frequencia_media_fornecedores",
    "total_regioes",
    "ultimo_mes",
    "clientes_ativos",
    "clientes_novos",
    "gerado_em"
   FROM "analytics_v2"."mv_resumo_dashboard"
  WHERE ("client_id" = "public"."get_my_client_id"());


ALTER VIEW "analytics_v2"."v_resumo_dashboard" OWNER TO "postgres";


CREATE OR REPLACE VIEW "analytics_v2"."v_series_temporal" AS
 SELECT "client_id",
    "periodo",
    "data_periodo",
    "tipo_grafico",
    "dimensao",
    "total",
    "total_cumulativo"
   FROM "analytics_v2"."mv_series_temporal"
  WHERE ("client_id" = "public"."get_my_client_id"());


ALTER VIEW "analytics_v2"."v_series_temporal" OWNER TO "postgres";


CREATE OR REPLACE VIEW "analytics_v2"."v_ultimos_pedidos" WITH ("security_invoker"='on') AS
 SELECT "client_id",
    "pedido_id",
    "cliente_cpf_cnpj",
    "valor_pedido",
    "qtd_produtos",
    "ordem"
   FROM "analytics_v2"."mv_ultimos_pedidos"
  WHERE ("client_id" = "public"."get_my_client_id"());


ALTER VIEW "analytics_v2"."v_ultimos_pedidos" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."agent_catalog" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "slug" "text" NOT NULL,
    "description" "text",
    "category" "text",
    "icon" "text",
    "agent_config" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "prompt_name" "text" NOT NULL,
    "required_context" "jsonb" DEFAULT '[]'::"jsonb",
    "required_files" "jsonb" DEFAULT '{}'::"jsonb",
    "requires_google" boolean DEFAULT false,
    "tier_required" "text" DEFAULT 'BASIC'::"text",
    "landing_slug" "text",
    "workflow_graph" "jsonb",
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."agent_catalog" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."audit_log" (
    "id" bigint NOT NULL,
    "client_id" "uuid",
    "actor_id" "text",
    "action" "text" NOT NULL,
    "entity_type" "text",
    "entity_id" "text",
    "payload" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."audit_log" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."audit_log_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."audit_log_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."audit_log_id_seq" OWNED BY "public"."audit_log"."id";



CREATE TABLE IF NOT EXISTS "public"."bigquery_foreign_tables" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "text" NOT NULL,
    "table_name" "text" NOT NULL,
    "bigquery_table" "text" NOT NULL,
    "server_name" "text" NOT NULL,
    "columns" "jsonb" NOT NULL,
    "location" "text" DEFAULT 'US'::"text",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."bigquery_foreign_tables" OWNER TO "postgres";


COMMENT ON TABLE "public"."bigquery_foreign_tables" IS 'Registry of all BigQuery foreign tables';



CREATE TABLE IF NOT EXISTS "public"."bigquery_servers" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "text" NOT NULL,
    "server_name" "text" NOT NULL,
    "project_id" "text" NOT NULL,
    "dataset_id" "text" NOT NULL,
    "vault_key_id" "uuid" NOT NULL,
    "location" "text" DEFAULT 'US'::"text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."bigquery_servers" OWNER TO "postgres";


COMMENT ON TABLE "public"."bigquery_servers" IS 'Metadata for BigQuery foreign servers per client';



CREATE TABLE IF NOT EXISTS "public"."calendar_settings" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "calendar_id" "text",
    "enabled" boolean DEFAULT false NOT NULL,
    "range_days" integer DEFAULT 30 NOT NULL,
    "timezone" "text" DEFAULT 'America/Sao_Paulo'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "provider" "text",
    "calendar_name" "text"
);


ALTER TABLE "public"."calendar_settings" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_approval_rules" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "agent_slug" "text",
    "rule_type" "text" NOT NULL,
    "condition" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "action" "text" DEFAULT 'auto_approve'::"text",
    "active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "client_approval_rules_action_check" CHECK (("action" = ANY (ARRAY['auto_approve'::"text", 'skip_review'::"text"]))),
    CONSTRAINT "client_approval_rules_rule_type_check" CHECK (("rule_type" = ANY (ARRAY['amount_limit'::"text", 'category'::"text", 'supplier'::"text", 'similarity'::"text"])))
);


ALTER TABLE "public"."client_approval_rules" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_approval_stats" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "total_approved" integer DEFAULT 0,
    "total_rejected" integer DEFAULT 0,
    "total_edited" integer DEFAULT 0,
    "total_snoozed" integer DEFAULT 0,
    "trust_level" "text" DEFAULT 'manual'::"text",
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "client_approval_stats_trust_level_check" CHECK (("trust_level" = ANY (ARRAY['manual'::"text", 'similar_toggle'::"text", 'rules'::"text", 'full_config'::"text"])))
);


ALTER TABLE "public"."client_approval_stats" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_data_sources" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "text" NOT NULL,
    "credential_id" bigint,
    "source_type" "text" NOT NULL,
    "resource_type" "text" NOT NULL,
    "storage_type" "text" NOT NULL,
    "storage_location" "text" NOT NULL,
    "column_mapping" "jsonb",
    "source_columns" "jsonb",
    "source_sample_data" "jsonb",
    "sync_status" "text" DEFAULT 'pending'::"text",
    "last_synced_at" timestamp with time zone,
    "atualizado_em" timestamp with time zone DEFAULT "now"(),
    "error_message" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "unmapped_columns" "jsonb",
    "needs_review_columns" "jsonb",
    "match_confidence" "jsonb",
    "detected_entity_context" "text",
    "auto_column_mapping" "jsonb",
    "ignored_columns" "text"[],
    "is_auto_generated" boolean DEFAULT false,
    "reviewed_at" timestamp with time zone,
    "user_column_changes" "jsonb",
    "ingestion_quality" "jsonb"
);


ALTER TABLE "public"."client_data_sources" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_dimension_kpis" (
    "client_id" "uuid" NOT NULL,
    "dimension" "text" NOT NULL,
    "slug" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."client_dimension_kpis" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_enabled_agents" (
    "client_id" "uuid" NOT NULL,
    "agent_slug" "text" NOT NULL,
    "config" "jsonb" DEFAULT '{}'::"jsonb",
    "enabled_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "current_status" "text" DEFAULT 'idle'::"text",
    "last_activity_at" timestamp with time zone,
    "pending_count" integer DEFAULT 0
);


ALTER TABLE "public"."client_enabled_agents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_insights" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "dimension" "text" NOT NULL,
    "title" "text" NOT NULL,
    "body" "text",
    "severity" "text" DEFAULT 'info'::"text",
    "dismissed" boolean DEFAULT false,
    "dismissed_at" timestamp with time zone,
    "generated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "expires_at" timestamp with time zone,
    CONSTRAINT "client_insights_severity_check" CHECK (("severity" = ANY (ARRAY['info'::"text", 'warning'::"text", 'critical'::"text"])))
);


ALTER TABLE "public"."client_insights" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_knowledge_documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "document_type_id" "text" NOT NULL,
    "status" "text" DEFAULT 'missing'::"text" NOT NULL,
    "source" "text",
    "vector_document_id" "uuid",
    "field_coverage" "jsonb" DEFAULT '{}'::"jsonb",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "client_knowledge_documents_status_check" CHECK (("status" = ANY (ARRAY['missing'::"text", 'partial'::"text", 'complete'::"text"])))
);


ALTER TABLE "public"."client_knowledge_documents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_notification_preferences" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "notification_type" "text" NOT NULL,
    "channel" "text" NOT NULL,
    "enabled" boolean DEFAULT true,
    "quiet_hours_start" time without time zone,
    "quiet_hours_end" time without time zone,
    "timezone" "text" DEFAULT 'America/Sao_Paulo'::"text",
    CONSTRAINT "client_notification_preferences_channel_check" CHECK (("channel" = ANY (ARRAY['email'::"text", 'push'::"text", 'in_app'::"text"])))
);


ALTER TABLE "public"."client_notification_preferences" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_routine_executions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "routine_id" "text" NOT NULL,
    "triggered_by" "text" NOT NULL,
    "trigger_data" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "dispatched_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."client_routine_executions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."client_routines" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "routine_id" "text" NOT NULL,
    "notify_channel" "text" DEFAULT 'app'::"text" NOT NULL,
    "config" "jsonb" DEFAULT '{}'::"jsonb",
    "active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "last_run_at" timestamp with time zone,
    CONSTRAINT "client_routines_notify_channel_check" CHECK (("notify_channel" = ANY (ARRAY['email'::"text", 'whatsapp'::"text", 'app'::"text"])))
);


ALTER TABLE "public"."client_routines" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."clientes_blu" (
    "client_id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "api_key" "text",
    "nome_empresa" "text" DEFAULT 'Empresa'::"text" NOT NULL,
    "tipo_cliente" "text" DEFAULT 'standard'::"text",
    "tier" "text" DEFAULT 'free'::"text",
    "collection_rag" "text" DEFAULT 'default_collection'::"text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "external_user_id" "text",
    "onboarding_state" "jsonb" DEFAULT '{}'::"jsonb",
    "onboarding_completed_at" timestamp with time zone,
    "company_profile" "jsonb" DEFAULT '{}'::"jsonb",
    "brand_voice" "jsonb" DEFAULT '{}'::"jsonb",
    "team_structure" "jsonb" DEFAULT '{}'::"jsonb",
    "policies" "jsonb" DEFAULT '{}'::"jsonb",
    "data_schema" "jsonb" DEFAULT '{}'::"jsonb",
    "available_tools" "jsonb" DEFAULT '{}'::"jsonb",
    "cpf_cnpj" "text",
    CONSTRAINT "clientes_blu_auth_check" CHECK ((("api_key" IS NOT NULL) OR ("external_user_id" IS NOT NULL)))
);


ALTER TABLE "public"."clientes_blu" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."conversa" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."conversa" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."credencial_servico_externo" (
    "id" bigint NOT NULL,
    "client_id" "text" NOT NULL,
    "tipo" "text",
    "credenciais" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "nome" "text",
    "ativo" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "connection_metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "nome_servico" "text",
    "tipo_servico" "text",
    "status" "text" DEFAULT 'pending'::"text",
    "vault_key_id" "uuid",
    CONSTRAINT "credencial_servico_externo_tipo_check" CHECK (("tipo" = ANY (ARRAY['bigquery'::"text", 'google_drive'::"text", 'google_sheets'::"text", 'google_docs'::"text", 'google_calendar'::"text"])))
);


ALTER TABLE "public"."credencial_servico_externo" OWNER TO "postgres";


COMMENT ON COLUMN "public"."credencial_servico_externo"."connection_metadata" IS 'Connection metadata: project_id, dataset_id, table_name, location for BigQuery; credentials for other platforms';



CREATE SEQUENCE IF NOT EXISTS "public"."credencial_servico_externo_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."credencial_servico_externo_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."credencial_servico_externo_id_seq" OWNED BY "public"."credencial_servico_externo"."id";



CREATE TABLE IF NOT EXISTS "public"."cross_agent_routines" (
    "id" "text" NOT NULL,
    "name" "text" NOT NULL,
    "trigger_domain" "text",
    "trigger_document_id" "text",
    "trigger_status" "text",
    "trigger_condition" "text",
    "steps" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."cross_agent_routines" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."data_source_mappings" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "credential_id" "uuid" NOT NULL,
    "resource_type" character varying(50) NOT NULL,
    "source_columns" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "mapping" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "unmapped_columns" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "confidence_scores" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "status" character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "data_source_mappings_status_check" CHECK ((("status")::"text" = ANY ((ARRAY['pending'::character varying, 'needs_review'::character varying, 'ready'::character varying, 'error'::character varying])::"text"[])))
);


ALTER TABLE "public"."data_source_mappings" OWNER TO "postgres";


COMMENT ON TABLE "public"."data_source_mappings" IS 'Armazena mapeamentos de colunas entre fontes externas e schema canônico Blu';



COMMENT ON COLUMN "public"."data_source_mappings"."source_columns" IS 'Lista de colunas descobertas na fonte original';



COMMENT ON COLUMN "public"."data_source_mappings"."mapping" IS 'Mapeamento coluna_origem -> coluna_blu confirmado';



COMMENT ON COLUMN "public"."data_source_mappings"."confidence_scores" IS 'Score de confiança (0-1) do match automático por coluna';



COMMENT ON COLUMN "public"."data_source_mappings"."status" IS 'pending=aguardando, needs_review=precisa revisão, ready=pronto, error=erro';



CREATE TABLE IF NOT EXISTS "public"."doc_templates" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "name" "text" NOT NULL,
    "description" "text",
    "category" "text",
    "is_system" boolean DEFAULT false NOT NULL,
    "content" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."doc_templates" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."document_versions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "document_id" "uuid" NOT NULL,
    "version_number" integer DEFAULT 1 NOT NULL,
    "editor_content" "jsonb",
    "summary" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."document_versions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "title" "text" DEFAULT 'Sem título'::"text" NOT NULL,
    "agent_slug" "text" DEFAULT 'documentos'::"text" NOT NULL,
    "editor_content" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."documents" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."frontend_events" (
    "id" bigint NOT NULL,
    "client_id" "uuid",
    "event_name" "text" NOT NULL,
    "properties" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."frontend_events" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."frontend_events_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."frontend_events_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."frontend_events_id_seq" OWNED BY "public"."frontend_events"."id";



CREATE TABLE IF NOT EXISTS "public"."integration_configs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "provider" "text" NOT NULL,
    "config" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."integration_configs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."integration_tokens" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "provider" "text" NOT NULL,
    "account_email" "text" DEFAULT ''::"text" NOT NULL,
    "access_token_encrypted" "text",
    "refresh_token_encrypted" "text",
    "token_type" "text" DEFAULT 'Bearer'::"text",
    "scopes" "text"[],
    "is_default" boolean DEFAULT false,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."integration_tokens" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."knowledge_agent_requirements" (
    "agent_slug" "text" NOT NULL,
    "document_type_id" "text" NOT NULL,
    "requirement_type" "text" NOT NULL,
    "coverage_threshold" numeric DEFAULT 0.8 NOT NULL,
    CONSTRAINT "knowledge_agent_requirements_requirement_type_check" CHECK (("requirement_type" = ANY (ARRAY['minimum'::"text", 'nice_to_have'::"text"])))
);


ALTER TABLE "public"."knowledge_agent_requirements" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."knowledge_document_types" (
    "id" "text" NOT NULL,
    "domain_id" "text" NOT NULL,
    "subdomain_id" "text",
    "name" "text" NOT NULL,
    "type" "text" NOT NULL,
    "created_by" "text",
    "consumed_by" "text"[] DEFAULT '{}'::"text"[],
    "fields" "text"[] DEFAULT '{}'::"text"[],
    "status" "text" DEFAULT 'required'::"text" NOT NULL,
    "coverage_weight" numeric DEFAULT 1.0 NOT NULL,
    "tags" "text"[] DEFAULT '{}'::"text"[],
    "sort_order" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "knowledge_document_types_status_check" CHECK (("status" = ANY (ARRAY['required'::"text", 'optional'::"text", 'generated'::"text"])))
);


ALTER TABLE "public"."knowledge_document_types" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."knowledge_tag_definitions" (
    "tag" "text" NOT NULL,
    "description" "text",
    "consumed_by" "text"[] DEFAULT '{}'::"text"[]
);


ALTER TABLE "public"."knowledge_tag_definitions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."kpi_catalog" (
    "slug" "text" NOT NULL,
    "dimension" "text" NOT NULL,
    "label" "text" NOT NULL,
    "formula" "text" NOT NULL,
    "unit" "text" DEFAULT 'number'::"text" NOT NULL,
    "is_leading" boolean DEFAULT false NOT NULL,
    "tier_required" "text" DEFAULT 'BASIC'::"text" NOT NULL,
    "data_status" "text" DEFAULT 'live'::"text" NOT NULL,
    "rpc_column" "text",
    "description" "text",
    "references_url" "text",
    "sort_order" integer DEFAULT 0 NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "kpi_catalog_data_status_check" CHECK (("data_status" = ANY (ARRAY['live'::"text", 'proxy'::"text", 'external'::"text", 'pending_data'::"text"]))),
    CONSTRAINT "kpi_catalog_dimension_check" CHECK (("dimension" = ANY (ARRAY['finance'::"text", 'commercial'::"text", 'inventory'::"text", 'supply'::"text", 'marketing'::"text", 'admin'::"text"]))),
    CONSTRAINT "kpi_catalog_tier_required_check" CHECK (("tier_required" = ANY (ARRAY['BASIC'::"text", 'SME'::"text", 'PRO'::"text", 'PREMIUM'::"text", 'ENTERPRISE'::"text", 'ADMIN'::"text"]))),
    CONSTRAINT "kpi_catalog_unit_check" CHECK (("unit" = ANY (ARRAY['number'::"text", 'currency'::"text", 'percent'::"text", 'days'::"text", 'hours'::"text", 'ratio'::"text", 'count'::"text"])))
);


ALTER TABLE "public"."kpi_catalog" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."messages" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "session_id" "uuid",
    "channel" "text" NOT NULL,
    "direction" "text",
    "role" "text",
    "body" "text",
    "media_urls" "text"[],
    "status" "text" DEFAULT 'received'::"text",
    "provider" "text",
    "sender_ref" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "messages_channel_check" CHECK (("channel" = ANY (ARRAY['chat'::"text", 'whatsapp'::"text", 'sms'::"text", 'email'::"text", 'api'::"text"]))),
    CONSTRAINT "messages_direction_check" CHECK (("direction" = ANY (ARRAY['inbound'::"text", 'outbound'::"text"]))),
    CONSTRAINT "messages_role_check" CHECK (("role" = ANY (ARRAY['user'::"text", 'assistant'::"text", 'system'::"text", 'tool'::"text"])))
);


ALTER TABLE "public"."messages" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."notifications" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "type" "text" NOT NULL,
    "title" "text" NOT NULL,
    "body" "text",
    "agent_slug" "text",
    "related_entity_type" "text",
    "related_entity_id" "uuid",
    "urgency_level" "text" DEFAULT 'normal'::"text",
    "channels" "text"[] DEFAULT ARRAY['in_app'::"text"],
    "read_at" timestamp with time zone,
    "dismissed_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."notifications" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."nps_responses" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "score" integer NOT NULL,
    "comment" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "nps_responses_score_check" CHECK ((("score" >= 0) AND ("score" <= 10)))
);


ALTER TABLE "public"."nps_responses" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."report_runs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "schedule_id" "uuid",
    "client_id" "uuid",
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "output_url" "text",
    "error" "text",
    "started_at" timestamp with time zone DEFAULT "now"(),
    "completed_at" timestamp with time zone,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    CONSTRAINT "report_runs_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'running'::"text", 'completed'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."report_runs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."report_schedules" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "name" "text" NOT NULL,
    "report_type" "text" NOT NULL,
    "cron_expr" "text",
    "recipients" "text"[],
    "config" "jsonb" DEFAULT '{}'::"jsonb",
    "active" boolean DEFAULT true,
    "last_run_at" timestamp with time zone,
    "next_run_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."report_schedules" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."standalone_agent_sessions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "agent_catalog_id" "uuid" NOT NULL,
    "session_id" "text" NOT NULL,
    "config_status" "text" DEFAULT 'configuring'::"text",
    "collected_context" "jsonb" DEFAULT '{}'::"jsonb",
    "uploaded_file_ids" "uuid"[] DEFAULT ARRAY[]::"uuid"[],
    "uploaded_document_ids" "uuid"[] DEFAULT ARRAY[]::"uuid"[],
    "google_account_email" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "standalone_agent_sessions_config_status_check" CHECK (("config_status" = ANY (ARRAY['configuring'::"text", 'ready'::"text", 'active'::"text", 'archived'::"text"])))
);


ALTER TABLE "public"."standalone_agent_sessions" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."suppliers" WITH ("security_barrier"='true') AS
 SELECT ("fornecedor_id")::"text" AS "id",
    "client_id",
    "nome" AS "name",
    "cnpj",
    "category",
    "tags",
    "rating",
    "telefone" AS "contact_phone",
    "contact_email",
    "endereco_cidade" AS "city",
    "endereco_uf" AS "state",
    "performance_summary",
    "is_active",
    "receita_total",
    "ticket_medio",
    "total_pedidos_recebidos",
    "nivel_cluster",
    "dias_recencia",
    "frequencia_mensal",
    "atualizado_em" AS "updated_at"
   FROM "analytics_v2"."dim_fornecedores"
  WHERE ("client_id" = "public"."get_my_client_id"());


ALTER VIEW "public"."suppliers" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."uploaded_files_metadata" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid",
    "file_name" "text" NOT NULL,
    "storage_path" "text" NOT NULL,
    "bucket" "text" DEFAULT 'file-uploads'::"text" NOT NULL,
    "mime_type" "text",
    "size_bytes" bigint,
    "status" "text" DEFAULT 'uploaded'::"text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "content_hash" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."uploaded_files_metadata" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "vector_db"."document_chunks" (
    "id" integer NOT NULL,
    "document_id" "uuid" NOT NULL,
    "client_id" "uuid" NOT NULL,
    "content" "text" NOT NULL,
    "embedding" "extensions"."halfvec"(384),
    "chunk_index" integer DEFAULT 0 NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "fts" "tsvector" GENERATED ALWAYS AS ("to_tsvector"('"portuguese"'::"regconfig", "content")) STORED,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "content_hash" "text",
    "scope" "text",
    "category" "text",
    "theme" "text",
    "word_cloud" "text"[],
    "usage_context" "text"
);


ALTER TABLE "vector_db"."document_chunks" OWNER TO "postgres";


ALTER TABLE "vector_db"."document_chunks" ALTER COLUMN "id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "vector_db"."document_chunks_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "vector_db"."documents" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "client_id" "uuid" NOT NULL,
    "title" "text",
    "file_name" "text" NOT NULL,
    "file_type" "text",
    "storage_path" "text",
    "source" "text" DEFAULT 'upload'::"text" NOT NULL,
    "processing_mode" "text" DEFAULT 'simple'::"text" NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "scope" "text",
    "category" "text",
    "content_hash" "text",
    "error_message" "text",
    "chunk_count" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "source_url" "text",
    CONSTRAINT "documents_processing_mode_check" CHECK (("processing_mode" = ANY (ARRAY['simple'::"text", 'complex'::"text"]))),
    CONSTRAINT "documents_source_check" CHECK (("source" = ANY (ARRAY['upload'::"text", 'chat'::"text", 'url'::"text", 'api'::"text", 'generated'::"text", 'archived'::"text"]))),
    CONSTRAINT "documents_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'completed'::"text", 'failed'::"text"])))
);


ALTER TABLE "vector_db"."documents" OWNER TO "postgres";


ALTER TABLE ONLY "public"."audit_log" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."audit_log_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."credencial_servico_externo" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."credencial_servico_externo_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."frontend_events" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."frontend_events_id_seq"'::"regclass");



ALTER TABLE ONLY "analytics_v2"."dim_clientes"
    ADD CONSTRAINT "dim_clientes_client_cpf_uniq" UNIQUE ("client_id", "cpf_cnpj");



ALTER TABLE ONLY "analytics_v2"."dim_clientes"
    ADD CONSTRAINT "dim_clientes_pkey" PRIMARY KEY ("cliente_id");



ALTER TABLE ONLY "analytics_v2"."dim_datas"
    ADD CONSTRAINT "dim_datas_data_key" UNIQUE ("data");



ALTER TABLE ONLY "analytics_v2"."dim_datas"
    ADD CONSTRAINT "dim_datas_pkey" PRIMARY KEY ("data_id");



ALTER TABLE ONLY "analytics_v2"."dim_fornecedores"
    ADD CONSTRAINT "dim_fornecedores_client_cnpj_uniq" UNIQUE ("client_id", "cnpj");



ALTER TABLE ONLY "analytics_v2"."dim_fornecedores"
    ADD CONSTRAINT "dim_fornecedores_pkey" PRIMARY KEY ("fornecedor_id");



ALTER TABLE ONLY "analytics_v2"."dim_inventory"
    ADD CONSTRAINT "dim_inventory_client_sku_uniq" UNIQUE ("client_id", "sku");



ALTER TABLE ONLY "analytics_v2"."dim_inventory"
    ADD CONSTRAINT "dim_inventory_pkey" PRIMARY KEY ("inventory_id");



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_pkey" PRIMARY KEY ("transacao_id", "client_id");



ALTER TABLE ONLY "analytics_v2"."reg_jobs"
    ADD CONSTRAINT "reg_jobs_pkey" PRIMARY KEY ("job_id");



ALTER TABLE ONLY "public"."agent_catalog"
    ADD CONSTRAINT "agent_catalog_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."agent_catalog"
    ADD CONSTRAINT "agent_catalog_slug_key" UNIQUE ("slug");



ALTER TABLE ONLY "public"."approval_requests"
    ADD CONSTRAINT "approval_requests_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."audit_log"
    ADD CONSTRAINT "audit_log_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."bigquery_foreign_tables"
    ADD CONSTRAINT "bigquery_foreign_tables_client_id_table_name_key" UNIQUE ("client_id", "table_name");



ALTER TABLE ONLY "public"."bigquery_foreign_tables"
    ADD CONSTRAINT "bigquery_foreign_tables_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."bigquery_servers"
    ADD CONSTRAINT "bigquery_servers_client_id_key" UNIQUE ("client_id");



ALTER TABLE ONLY "public"."bigquery_servers"
    ADD CONSTRAINT "bigquery_servers_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."bigquery_servers"
    ADD CONSTRAINT "bigquery_servers_server_name_key" UNIQUE ("server_name");



ALTER TABLE ONLY "public"."calendar_settings"
    ADD CONSTRAINT "calendar_settings_client_id_key" UNIQUE ("client_id");



ALTER TABLE ONLY "public"."calendar_settings"
    ADD CONSTRAINT "calendar_settings_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_approval_rules"
    ADD CONSTRAINT "client_approval_rules_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_approval_stats"
    ADD CONSTRAINT "client_approval_stats_id_key" UNIQUE ("id");



ALTER TABLE ONLY "public"."client_approval_stats"
    ADD CONSTRAINT "client_approval_stats_pkey" PRIMARY KEY ("client_id");



ALTER TABLE ONLY "public"."client_data_sources"
    ADD CONSTRAINT "client_data_sources_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_dimension_kpis"
    ADD CONSTRAINT "client_dimension_kpis_pkey" PRIMARY KEY ("client_id", "dimension", "slug");



ALTER TABLE ONLY "public"."client_enabled_agents"
    ADD CONSTRAINT "client_enabled_agents_pkey" PRIMARY KEY ("client_id", "agent_slug");



ALTER TABLE ONLY "public"."client_insights"
    ADD CONSTRAINT "client_insights_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_knowledge_documents"
    ADD CONSTRAINT "client_knowledge_documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_notification_preferences"
    ADD CONSTRAINT "client_notification_preferences_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_notification_preferences"
    ADD CONSTRAINT "client_notification_preferences_unique" UNIQUE ("client_id", "notification_type", "channel");



ALTER TABLE ONLY "public"."client_routine_executions"
    ADD CONSTRAINT "client_routine_executions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_routines"
    ADD CONSTRAINT "client_routines_client_id_routine_id_key" UNIQUE ("client_id", "routine_id");



ALTER TABLE ONLY "public"."client_routines"
    ADD CONSTRAINT "client_routines_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."clientes_blu"
    ADD CONSTRAINT "clientes_blu_api_key_key" UNIQUE ("api_key");



ALTER TABLE ONLY "public"."clientes_blu"
    ADD CONSTRAINT "clientes_blu_external_user_id_key" UNIQUE ("external_user_id");



ALTER TABLE ONLY "public"."clientes_blu"
    ADD CONSTRAINT "clientes_blu_pkey" PRIMARY KEY ("client_id");



ALTER TABLE ONLY "public"."conversa"
    ADD CONSTRAINT "conversa_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."credencial_servico_externo"
    ADD CONSTRAINT "credencial_servico_externo_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."cross_agent_routines"
    ADD CONSTRAINT "cross_agent_routines_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."data_source_mappings"
    ADD CONSTRAINT "data_source_mappings_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."doc_templates"
    ADD CONSTRAINT "doc_templates_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_document_id_version_number_key" UNIQUE ("document_id", "version_number");



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."frontend_events"
    ADD CONSTRAINT "frontend_events_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."integration_configs"
    ADD CONSTRAINT "integration_configs_client_id_provider_key" UNIQUE ("client_id", "provider");



ALTER TABLE ONLY "public"."integration_configs"
    ADD CONSTRAINT "integration_configs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."integration_tokens"
    ADD CONSTRAINT "integration_tokens_client_id_provider_account_email_key" UNIQUE ("client_id", "provider", "account_email");



ALTER TABLE ONLY "public"."integration_tokens"
    ADD CONSTRAINT "integration_tokens_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."knowledge_agent_requirements"
    ADD CONSTRAINT "knowledge_agent_requirements_pkey" PRIMARY KEY ("agent_slug", "document_type_id");



ALTER TABLE ONLY "public"."knowledge_document_types"
    ADD CONSTRAINT "knowledge_document_types_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."knowledge_tag_definitions"
    ADD CONSTRAINT "knowledge_tag_definitions_pkey" PRIMARY KEY ("tag");



ALTER TABLE ONLY "public"."kpi_catalog"
    ADD CONSTRAINT "kpi_catalog_pkey" PRIMARY KEY ("slug");



ALTER TABLE ONLY "public"."messages"
    ADD CONSTRAINT "messages_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."nps_responses"
    ADD CONSTRAINT "nps_responses_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."report_runs"
    ADD CONSTRAINT "report_runs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."report_schedules"
    ADD CONSTRAINT "report_schedules_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."standalone_agent_sessions"
    ADD CONSTRAINT "standalone_agent_sessions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."standalone_agent_sessions"
    ADD CONSTRAINT "standalone_agent_sessions_session_id_key" UNIQUE ("session_id");



ALTER TABLE ONLY "public"."client_data_sources"
    ADD CONSTRAINT "unique_client_source_resource" UNIQUE ("client_id", "source_type", "resource_type");



ALTER TABLE ONLY "public"."data_source_mappings"
    ADD CONSTRAINT "unique_credential_resource" UNIQUE ("credential_id", "resource_type");



ALTER TABLE ONLY "public"."uploaded_files_metadata"
    ADD CONSTRAINT "uploaded_files_metadata_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."client_knowledge_documents"
    ADD CONSTRAINT "uq_client_document" UNIQUE ("client_id", "document_type_id");



ALTER TABLE ONLY "vector_db"."document_chunks"
    ADD CONSTRAINT "document_chunks_document_id_content_hash_key" UNIQUE ("document_id", "content_hash");



ALTER TABLE ONLY "vector_db"."document_chunks"
    ADD CONSTRAINT "document_chunks_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "vector_db"."documents"
    ADD CONSTRAINT "documents_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_dim_clientes_client" ON "analytics_v2"."dim_clientes" USING "btree" ("client_id");



CREATE UNIQUE INDEX "idx_dim_clientes_cpf_cnpj" ON "analytics_v2"."dim_clientes" USING "btree" ("client_id", "cpf_cnpj") WHERE ("cpf_cnpj" IS NOT NULL);



CREATE INDEX "idx_dim_forn_client" ON "analytics_v2"."dim_fornecedores" USING "btree" ("client_id");



CREATE INDEX "idx_dim_inv_client" ON "analytics_v2"."dim_inventory" USING "btree" ("client_id");



CREATE INDEX "idx_fato_client" ON "analytics_v2"."fato_transacoes" USING "btree" ("client_id");



CREATE INDEX "idx_fato_cliente_dim" ON "analytics_v2"."fato_transacoes" USING "btree" ("cliente_id");



CREATE INDEX "idx_fato_data" ON "analytics_v2"."fato_transacoes" USING "btree" ("data_competencia_id");



CREATE INDEX "idx_fato_fornecedor" ON "analytics_v2"."fato_transacoes" USING "btree" ("fornecedor_id");



CREATE INDEX "idx_mv_distribuicao_regional_client_id" ON "analytics_v2"."mv_distribuicao_regional" USING "btree" ("client_id");



CREATE INDEX "idx_mv_distribuicao_regional_uf" ON "analytics_v2"."mv_distribuicao_regional" USING "btree" ("endereco_uf");



CREATE INDEX "idx_mv_ultimos_pedidos_client_id" ON "analytics_v2"."mv_ultimos_pedidos" USING "btree" ("client_id");



CREATE INDEX "idx_reg_jobs_client_status" ON "analytics_v2"."reg_jobs" USING "btree" ("client_id", "status");



CREATE INDEX "idx_reg_jobs_created" ON "analytics_v2"."reg_jobs" USING "btree" ("created_at" DESC);



CREATE UNIQUE INDEX "mv_distribuicao_regional_unique_idx" ON "analytics_v2"."mv_distribuicao_regional" USING "btree" ("client_id", "endereco_uf", "endereco_cidade");



CREATE UNIQUE INDEX "mv_resumo_dashboard_client_id_idx" ON "analytics_v2"."mv_resumo_dashboard" USING "btree" ("client_id");



CREATE UNIQUE INDEX "mv_series_temporal_unique_idx" ON "analytics_v2"."mv_series_temporal" USING "btree" ("client_id", "data_periodo", "tipo_grafico", "dimensao");



CREATE UNIQUE INDEX "mv_ultimos_pedidos_unique_idx" ON "analytics_v2"."mv_ultimos_pedidos" USING "btree" ("client_id", "pedido_id");



CREATE INDEX "doc_templates_client_id_idx" ON "public"."doc_templates" USING "btree" ("client_id") WHERE ("client_id" IS NOT NULL);



CREATE INDEX "document_versions_document_id_idx" ON "public"."document_versions" USING "btree" ("document_id", "version_number" DESC);



CREATE INDEX "documents_client_id_idx" ON "public"."documents" USING "btree" ("client_id", "updated_at" DESC);



CREATE INDEX "idx_approval_agent_slug" ON "public"."approval_requests" USING "btree" ("client_id", "agent_slug");



CREATE INDEX "idx_approval_client_status" ON "public"."approval_requests" USING "btree" ("client_id", "status");



CREATE INDEX "idx_approval_session_id" ON "public"."approval_requests" USING "btree" ("session_id") WHERE ("session_id" IS NOT NULL);



CREATE INDEX "idx_audit_client" ON "public"."audit_log" USING "btree" ("client_id");



CREATE INDEX "idx_audit_created" ON "public"."audit_log" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_cds_client_id" ON "public"."client_data_sources" USING "btree" ("client_id");



CREATE INDEX "idx_cds_credential_id" ON "public"."client_data_sources" USING "btree" ("credential_id");



CREATE INDEX "idx_ckd_client" ON "public"."client_knowledge_documents" USING "btree" ("client_id");



CREATE INDEX "idx_ckd_client_status" ON "public"."client_knowledge_documents" USING "btree" ("client_id", "status");



CREATE INDEX "idx_clientes_blu_api_key" ON "public"."clientes_blu" USING "btree" ("api_key") WHERE ("api_key" IS NOT NULL);



CREATE INDEX "idx_clientes_blu_client_id" ON "public"."clientes_blu" USING "btree" ("client_id");



CREATE INDEX "idx_clientes_blu_external_user" ON "public"."clientes_blu" USING "btree" ("external_user_id");



CREATE INDEX "idx_clientes_blu_external_user_id" ON "public"."clientes_blu" USING "btree" ("external_user_id") WHERE ("external_user_id" IS NOT NULL);



CREATE INDEX "idx_clientes_blu_onboarding_incomplete" ON "public"."clientes_blu" USING "btree" ("client_id") WHERE ("onboarding_completed_at" IS NULL);



CREATE INDEX "idx_credencial_client_id" ON "public"."credencial_servico_externo" USING "btree" ("client_id");



CREATE INDEX "idx_fe_client_event" ON "public"."frontend_events" USING "btree" ("client_id", "event_name");



CREATE INDEX "idx_fe_created_at" ON "public"."frontend_events" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_insights_client_active" ON "public"."client_insights" USING "btree" ("client_id", "dismissed", "generated_at" DESC);



CREATE INDEX "idx_mappings_credential" ON "public"."data_source_mappings" USING "btree" ("credential_id");



CREATE INDEX "idx_mappings_resource" ON "public"."data_source_mappings" USING "btree" ("resource_type");



CREATE INDEX "idx_mappings_status" ON "public"."data_source_mappings" USING "btree" ("status");



CREATE INDEX "idx_messages_client" ON "public"."messages" USING "btree" ("client_id", "created_at" DESC);



CREATE INDEX "idx_messages_session" ON "public"."messages" USING "btree" ("session_id") WHERE ("session_id" IS NOT NULL);



CREATE INDEX "idx_notifications_client_unread" ON "public"."notifications" USING "btree" ("client_id", "read_at", "created_at" DESC) WHERE ("dismissed_at" IS NULL);



CREATE INDEX "idx_nps_client" ON "public"."nps_responses" USING "btree" ("client_id");



CREATE INDEX "idx_report_runs_client" ON "public"."report_runs" USING "btree" ("client_id", "started_at" DESC);



CREATE INDEX "idx_routine_exec_client" ON "public"."client_routine_executions" USING "btree" ("client_id", "routine_id", "created_at" DESC);



CREATE INDEX "idx_routine_exec_pending" ON "public"."client_routine_executions" USING "btree" ("status") WHERE ("status" = 'pending'::"text");



CREATE INDEX "idx_tokens_client_provider" ON "public"."integration_tokens" USING "btree" ("client_id", "provider");



CREATE INDEX "idx_uploaded_files_client" ON "public"."uploaded_files_metadata" USING "btree" ("client_id");



CREATE INDEX "idx_chunks_client" ON "vector_db"."document_chunks" USING "btree" ("client_id");



CREATE INDEX "idx_chunks_document" ON "vector_db"."document_chunks" USING "btree" ("document_id");



CREATE INDEX "idx_chunks_embedding" ON "vector_db"."document_chunks" USING "hnsw" ("embedding" "extensions"."halfvec_ip_ops");



CREATE INDEX "idx_chunks_fts" ON "vector_db"."document_chunks" USING "gin" ("fts");



CREATE INDEX "idx_docs_client" ON "vector_db"."documents" USING "btree" ("client_id");



CREATE INDEX "idx_docs_content_hash" ON "vector_db"."documents" USING "btree" ("content_hash") WHERE ("content_hash" IS NOT NULL);



CREATE INDEX "idx_docs_status" ON "vector_db"."documents" USING "btree" ("status");



CREATE OR REPLACE TRIGGER "trg_knowledge_on_etl_completed" AFTER UPDATE OF "status" ON "analytics_v2"."reg_jobs" FOR EACH ROW EXECUTE FUNCTION "analytics_v2"."on_etl_job_completed"();



CREATE OR REPLACE TRIGGER "trg_approval_requests_updated_at" BEFORE UPDATE ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();



CREATE OR REPLACE TRIGGER "trg_enqueue_routine_on_doc_complete" AFTER UPDATE OF "status" ON "public"."client_knowledge_documents" FOR EACH ROW EXECUTE FUNCTION "public"."on_knowledge_document_complete"();



CREATE OR REPLACE TRIGGER "trg_ensure_approval_stats" AFTER INSERT ON "public"."clientes_blu" FOR EACH ROW EXECUTE FUNCTION "public"."ensure_client_approval_stats"();



CREATE OR REPLACE TRIGGER "trg_knowledge_on_approval_completed" AFTER UPDATE OF "status" ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "public"."on_approval_completed"();



CREATE OR REPLACE TRIGGER "trg_update_approval_stats" AFTER UPDATE OF "status" ON "public"."approval_requests" FOR EACH ROW EXECUTE FUNCTION "public"."update_approval_stats"();



CREATE OR REPLACE TRIGGER "trigger_update_data_source_mappings_updated_at" BEFORE UPDATE ON "public"."data_source_mappings" FOR EACH ROW EXECUTE FUNCTION "public"."update_data_source_mappings_updated_at"();



ALTER TABLE ONLY "analytics_v2"."dim_clientes"
    ADD CONSTRAINT "dim_clientes_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."dim_fornecedores"
    ADD CONSTRAINT "dim_fornecedores_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."dim_inventory"
    ADD CONSTRAINT "dim_inventory_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_cliente_id_fkey" FOREIGN KEY ("cliente_id") REFERENCES "analytics_v2"."dim_clientes"("cliente_id") ON DELETE SET NULL;



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_data_competencia_id_fkey" FOREIGN KEY ("data_competencia_id") REFERENCES "analytics_v2"."dim_datas"("data_id") ON DELETE SET NULL;



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_fornecedor_id_fkey" FOREIGN KEY ("fornecedor_id") REFERENCES "analytics_v2"."dim_fornecedores"("fornecedor_id") ON DELETE SET NULL;



ALTER TABLE ONLY "analytics_v2"."fato_transacoes"
    ADD CONSTRAINT "fato_transacoes_produto_id_fkey" FOREIGN KEY ("produto_id") REFERENCES "analytics_v2"."dim_inventory"("inventory_id") ON DELETE SET NULL;



ALTER TABLE ONLY "analytics_v2"."reg_jobs"
    ADD CONSTRAINT "reg_jobs_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "analytics_v2"."reg_jobs"
    ADD CONSTRAINT "reg_jobs_credential_id_fkey" FOREIGN KEY ("credential_id") REFERENCES "public"."credencial_servico_externo"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."approval_requests"
    ADD CONSTRAINT "approval_requests_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."calendar_settings"
    ADD CONSTRAINT "calendar_settings_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_approval_rules"
    ADD CONSTRAINT "client_approval_rules_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_approval_stats"
    ADD CONSTRAINT "client_approval_stats_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_data_sources"
    ADD CONSTRAINT "client_data_sources_credential_id_fkey" FOREIGN KEY ("credential_id") REFERENCES "public"."credencial_servico_externo"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."client_dimension_kpis"
    ADD CONSTRAINT "client_dimension_kpis_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_dimension_kpis"
    ADD CONSTRAINT "client_dimension_kpis_slug_fkey" FOREIGN KEY ("slug") REFERENCES "public"."kpi_catalog"("slug") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_enabled_agents"
    ADD CONSTRAINT "client_enabled_agents_agent_slug_fkey" FOREIGN KEY ("agent_slug") REFERENCES "public"."agent_catalog"("slug") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_enabled_agents"
    ADD CONSTRAINT "client_enabled_agents_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_insights"
    ADD CONSTRAINT "client_insights_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_knowledge_documents"
    ADD CONSTRAINT "client_knowledge_documents_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_knowledge_documents"
    ADD CONSTRAINT "client_knowledge_documents_document_type_id_fkey" FOREIGN KEY ("document_type_id") REFERENCES "public"."knowledge_document_types"("id");



ALTER TABLE ONLY "public"."client_notification_preferences"
    ADD CONSTRAINT "client_notification_preferences_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_routine_executions"
    ADD CONSTRAINT "client_routine_executions_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."client_routine_executions"
    ADD CONSTRAINT "client_routine_executions_routine_id_fkey" FOREIGN KEY ("routine_id") REFERENCES "public"."cross_agent_routines"("id");



ALTER TABLE ONLY "public"."client_routines"
    ADD CONSTRAINT "client_routines_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."conversa"
    ADD CONSTRAINT "conversa_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."cross_agent_routines"
    ADD CONSTRAINT "cross_agent_routines_trigger_document_id_fkey" FOREIGN KEY ("trigger_document_id") REFERENCES "public"."knowledge_document_types"("id");



ALTER TABLE ONLY "public"."doc_templates"
    ADD CONSTRAINT "doc_templates_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."document_versions"
    ADD CONSTRAINT "document_versions_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "public"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."documents"
    ADD CONSTRAINT "documents_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."bigquery_foreign_tables"
    ADD CONSTRAINT "fk_server" FOREIGN KEY ("server_name") REFERENCES "public"."bigquery_servers"("server_name") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."frontend_events"
    ADD CONSTRAINT "frontend_events_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."integration_configs"
    ADD CONSTRAINT "integration_configs_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."integration_tokens"
    ADD CONSTRAINT "integration_tokens_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."knowledge_agent_requirements"
    ADD CONSTRAINT "knowledge_agent_requirements_agent_slug_fkey" FOREIGN KEY ("agent_slug") REFERENCES "public"."agent_catalog"("slug") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."knowledge_agent_requirements"
    ADD CONSTRAINT "knowledge_agent_requirements_document_type_id_fkey" FOREIGN KEY ("document_type_id") REFERENCES "public"."knowledge_document_types"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."messages"
    ADD CONSTRAINT "messages_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."messages"
    ADD CONSTRAINT "messages_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."conversa"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."notifications"
    ADD CONSTRAINT "notifications_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."nps_responses"
    ADD CONSTRAINT "nps_responses_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."report_runs"
    ADD CONSTRAINT "report_runs_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."report_runs"
    ADD CONSTRAINT "report_runs_schedule_id_fkey" FOREIGN KEY ("schedule_id") REFERENCES "public"."report_schedules"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."report_schedules"
    ADD CONSTRAINT "report_schedules_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."standalone_agent_sessions"
    ADD CONSTRAINT "standalone_agent_sessions_agent_catalog_id_fkey" FOREIGN KEY ("agent_catalog_id") REFERENCES "public"."agent_catalog"("id") ON DELETE RESTRICT;



ALTER TABLE ONLY "public"."standalone_agent_sessions"
    ADD CONSTRAINT "standalone_agent_sessions_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."uploaded_files_metadata"
    ADD CONSTRAINT "uploaded_files_metadata_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE ONLY "vector_db"."document_chunks"
    ADD CONSTRAINT "document_chunks_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "vector_db"."documents"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "vector_db"."documents"
    ADD CONSTRAINT "documents_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "public"."clientes_blu"("client_id") ON DELETE CASCADE;



ALTER TABLE "analytics_v2"."dim_clientes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "analytics_v2"."dim_fornecedores" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "analytics_v2"."dim_inventory" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "analytics_v2"."fato_transacoes" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "own client" ON "analytics_v2"."dim_clientes" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "analytics_v2"."dim_fornecedores" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "analytics_v2"."dim_inventory" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "analytics_v2"."fato_transacoes" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "analytics_v2"."reg_jobs" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



ALTER TABLE "analytics_v2"."reg_jobs" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "Authenticated users read own" ON "public"."clientes_blu" FOR SELECT USING (((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("external_user_id" = ("auth"."jwt"() ->> 'sub'::"text"))));



CREATE POLICY "Authenticated users update own" ON "public"."clientes_blu" FOR UPDATE USING (((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("external_user_id" = ("auth"."jwt"() ->> 'sub'::"text")))) WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("external_user_id" = ("auth"."jwt"() ->> 'sub'::"text"))));



CREATE POLICY "Service role unrestricted" ON "public"."clientes_blu" USING ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text")) WITH CHECK ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text"));



ALTER TABLE "public"."agent_catalog" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."approval_requests" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "approval_rules: client manages own" ON "public"."client_approval_rules" USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "approval_rules: client sees own" ON "public"."client_approval_rules" FOR SELECT USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "approval_stats: client sees own" ON "public"."client_approval_stats" FOR SELECT USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



ALTER TABLE "public"."audit_log" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."bigquery_foreign_tables" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "bigquery_foreign_tables_access" ON "public"."bigquery_foreign_tables" FOR SELECT USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text"))));



CREATE POLICY "bigquery_foreign_tables_update" ON "public"."bigquery_foreign_tables" FOR UPDATE USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text")))) WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text"))));



CREATE POLICY "bigquery_foreign_tables_write" ON "public"."bigquery_foreign_tables" FOR INSERT WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text"))));



ALTER TABLE "public"."bigquery_servers" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "bigquery_servers_access" ON "public"."bigquery_servers" FOR SELECT USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text"))));



CREATE POLICY "bigquery_servers_update" ON "public"."bigquery_servers" FOR UPDATE USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text")))) WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text"))));



CREATE POLICY "bigquery_servers_write" ON "public"."bigquery_servers" FOR INSERT WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text"))));



ALTER TABLE "public"."calendar_settings" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "car_public_read" ON "public"."cross_agent_routines" FOR SELECT USING (true);



CREATE POLICY "ckd_client_all" ON "public"."client_knowledge_documents" USING (("client_id" = "public"."get_my_client_id"()));



ALTER TABLE "public"."client_approval_rules" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_approval_stats" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_data_sources" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "client_data_sources_access" ON "public"."client_data_sources" FOR SELECT USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text"))));



CREATE POLICY "client_data_sources_update" ON "public"."client_data_sources" FOR UPDATE USING (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text")))) WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text"))));



CREATE POLICY "client_data_sources_write" ON "public"."client_data_sources" FOR INSERT WITH CHECK (((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text") OR ((("auth"."jwt"() ->> 'role'::"text") = 'authenticated'::"text") AND ("client_id" = ("public"."get_my_client_id"())::"text"))));



ALTER TABLE "public"."client_dimension_kpis" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_enabled_agents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_insights" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_knowledge_documents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_notification_preferences" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_routine_executions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."client_routines" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."clientes_blu" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."conversa" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."cross_agent_routines" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."doc_templates" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "doc_templates_delete" ON "public"."doc_templates" FOR DELETE USING ((("is_system" = false) AND ("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid")));



CREATE POLICY "doc_templates_insert" ON "public"."doc_templates" FOR INSERT WITH CHECK ((("is_system" = false) AND ("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid")));



CREATE POLICY "doc_templates_select" ON "public"."doc_templates" FOR SELECT USING ((("is_system" = true) OR ("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid")));



ALTER TABLE "public"."document_versions" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "document_versions_select" ON "public"."document_versions" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."documents" "d"
  WHERE (("d"."id" = "document_versions"."document_id") AND ("d"."client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid")))));



ALTER TABLE "public"."documents" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "documents_delete" ON "public"."documents" FOR DELETE USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "documents_insert" ON "public"."documents" FOR INSERT WITH CHECK (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "documents_select" ON "public"."documents" FOR SELECT USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "documents_update" ON "public"."documents" FOR UPDATE USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



ALTER TABLE "public"."frontend_events" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."integration_configs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."integration_tokens" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "kar_public_read" ON "public"."knowledge_agent_requirements" FOR SELECT USING (true);



CREATE POLICY "kdt_public_read" ON "public"."knowledge_document_types" FOR SELECT USING (true);



ALTER TABLE "public"."knowledge_agent_requirements" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."knowledge_document_types" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."knowledge_tag_definitions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."kpi_catalog" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "ktd_public_read" ON "public"."knowledge_tag_definitions" FOR SELECT USING (true);



ALTER TABLE "public"."messages" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "notif_prefs: client manages own" ON "public"."client_notification_preferences" USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "notif_prefs: client sees own" ON "public"."client_notification_preferences" FOR SELECT USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



ALTER TABLE "public"."notifications" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "notifications: client sees own" ON "public"."notifications" FOR SELECT USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



CREATE POLICY "notifications: client updates own" ON "public"."notifications" FOR UPDATE USING (("client_id" = (("auth"."jwt"() ->> 'client_id'::"text"))::"uuid"));



ALTER TABLE "public"."nps_responses" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "own client" ON "public"."approval_requests" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."audit_log" FOR SELECT TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."calendar_settings" FOR SELECT USING (((("auth"."jwt"() ->> 'sub'::"text") IS NULL) OR ("client_id" = "public"."get_my_client_id"())));



CREATE POLICY "own client" ON "public"."client_dimension_kpis" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."client_enabled_agents" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."client_insights" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."client_routine_executions" FOR SELECT USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."client_routines" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."conversa" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."frontend_events" FOR INSERT TO "authenticated" WITH CHECK (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."integration_configs" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."integration_tokens" FOR SELECT USING (((("auth"."jwt"() ->> 'sub'::"text") IS NULL) OR ("client_id" = "public"."get_my_client_id"())));



CREATE POLICY "own client" ON "public"."messages" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."nps_responses" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."report_runs" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."report_schedules" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."standalone_agent_sessions" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "public"."uploaded_files_metadata" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "read all" ON "public"."agent_catalog" FOR SELECT TO "authenticated" USING (("is_active" = true));



CREATE POLICY "read all" ON "public"."kpi_catalog" FOR SELECT TO "authenticated" USING (true);



ALTER TABLE "public"."report_runs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."report_schedules" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."standalone_agent_sessions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."uploaded_files_metadata" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "vector_db"."document_chunks" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "vector_db"."documents" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "own client" ON "vector_db"."document_chunks" FOR SELECT TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));



CREATE POLICY "own client" ON "vector_db"."documents" TO "authenticated" USING (("client_id" = "public"."get_my_client_id"()));





ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";






GRANT USAGE ON SCHEMA "analytics_v2" TO "authenticated";
GRANT USAGE ON SCHEMA "analytics_v2" TO "service_role";



GRANT USAGE ON SCHEMA "bigquery" TO "authenticated";
GRANT USAGE ON SCHEMA "bigquery" TO "service_role";






GRANT ALL ON SCHEMA "fdw" TO "service_role";






GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT USAGE ON SCHEMA "vector_db" TO "authenticated";
GRANT USAGE ON SCHEMA "vector_db" TO "service_role";



























































































































GRANT ALL ON FUNCTION "analytics_v2"."get_context_metrics_for_client"("p_client_id" "uuid") TO "service_role";








































































































































































































































































































































































































































































































































































GRANT ALL ON FUNCTION "public"."_bq_canonical_ref"("p_project_id" "text", "p_dataset_id" "text", "p_table_name" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."_bq_canonical_ref"("p_project_id" "text", "p_dataset_id" "text", "p_table_name" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."_bq_canonical_ref"("p_project_id" "text", "p_dataset_id" "text", "p_table_name" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."_bq_col_defs_from_jsonb"("p_columns" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."_bq_col_defs_from_jsonb"("p_columns" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."_bq_col_defs_from_jsonb"("p_columns" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."_bq_type_to_postgres_type"("p_bq_type" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."bootstrap_knowledge_from_onboarding"("p_client_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."bootstrap_knowledge_from_onboarding"("p_client_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."bootstrap_knowledge_from_onboarding"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_credential_id" "uuid", "p_location" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_credential_id" "uuid", "p_location" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_credential_id" "uuid", "p_location" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_location" "text", "p_timeout_ms" integer, "p_credential_id" bigint) TO "anon";
GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_location" "text", "p_timeout_ms" integer, "p_credential_id" bigint) TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table"("p_client_id" "text", "p_table_name" "text", "p_bigquery_table" "text", "p_location" "text", "p_timeout_ms" integer, "p_credential_id" bigint) TO "service_role";



GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table_from_schema"("p_client_id" "text", "p_columns" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table_from_schema"("p_client_id" "text", "p_columns" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_bigquery_foreign_table_from_schema"("p_client_id" "text", "p_columns" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_bigquery_server"("p_client_id" "text", "p_service_account_key" "jsonb", "p_project_id" "text", "p_dataset_id" "text", "p_location" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."decide_approval"("p_request_id" "uuid", "p_decision" "text", "p_reason" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."decide_approval"("p_request_id" "uuid", "p_decision" "text", "p_reason" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."decide_approval"("p_request_id" "uuid", "p_decision" "text", "p_reason" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."dismiss_insight"("p_insight_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."dismiss_insight"("p_insight_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."dismiss_insight"("p_insight_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."drop_bigquery_server"("p_client_id" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."enqueue_monthly_close"() TO "anon";
GRANT ALL ON FUNCTION "public"."enqueue_monthly_close"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."enqueue_monthly_close"() TO "service_role";



GRANT ALL ON FUNCTION "public"."enqueue_routine"("p_client_id" "uuid", "p_routine_id" "text", "p_triggered_by" "text", "p_trigger_data" "jsonb", "p_cooldown_h" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."enqueue_routine"("p_client_id" "uuid", "p_routine_id" "text", "p_triggered_by" "text", "p_trigger_data" "jsonb", "p_cooldown_h" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."enqueue_routine"("p_client_id" "uuid", "p_routine_id" "text", "p_triggered_by" "text", "p_trigger_data" "jsonb", "p_cooldown_h" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."ensure_client_approval_stats"() TO "anon";
GRANT ALL ON FUNCTION "public"."ensure_client_approval_stats"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."ensure_client_approval_stats"() TO "service_role";



GRANT ALL ON FUNCTION "public"."ensure_tenant_row"() TO "anon";
GRANT ALL ON FUNCTION "public"."ensure_tenant_row"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."ensure_tenant_row"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."exec_sql"("p_query" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."exec_sql"("p_query" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."expire_stale_insights"("p_days_old" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."expire_stale_insights"("p_days_old" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."expire_stale_insights"("p_days_old" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_agent_readiness"("p_client_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_agent_readiness"("p_client_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_agent_readiness"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_agent_runs_today"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_agent_runs_today"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_agent_runs_today"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_commercial_revenue_by_channel"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_commercial_revenue_by_channel"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_commercial_revenue_by_channel"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_commercial_top_clients"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_commercial_top_clients"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_commercial_top_clients"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_knowledge_coverage"("p_client_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_knowledge_coverage"("p_client_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_knowledge_coverage"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_my_client_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_my_client_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_my_client_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_my_dashboard_kpis"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_my_dashboard_kpis"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_my_dashboard_kpis"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_my_insights"("p_limit" integer, "p_status" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_nps_score"("p_window_days" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_nps_score"("p_window_days" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_nps_score"("p_window_days" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_pendencias"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_pendencias"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_pendencias"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_platform_google_oauth_config"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_platform_google_oauth_config"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_platform_google_oauth_config"() TO "service_role";



GRANT ALL ON FUNCTION "public"."get_recent_activity"("p_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_recent_activity"("p_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_recent_activity"("p_limit" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_new_auth_user"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_new_auth_user"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_new_auth_user"() TO "service_role";



GRANT ALL ON FUNCTION "public"."list_due_report_schedules"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_due_report_schedules"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_due_report_schedules"() TO "service_role";



GRANT ALL ON FUNCTION "public"."list_inbox_threads"("p_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."list_inbox_threads"("p_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_inbox_threads"("p_limit" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."list_kpi_catalog"("p_dimension" "text", "p_only_enabled" boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."list_kpi_catalog"("p_dimension" "text", "p_only_enabled" boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_kpi_catalog"("p_dimension" "text", "p_only_enabled" boolean) TO "service_role";



GRANT ALL ON TABLE "public"."approval_requests" TO "anon";
GRANT ALL ON TABLE "public"."approval_requests" TO "authenticated";
GRANT ALL ON TABLE "public"."approval_requests" TO "service_role";



GRANT ALL ON FUNCTION "public"."list_pending_approvals"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_pending_approvals"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_pending_approvals"() TO "service_role";



GRANT ALL ON FUNCTION "public"."list_report_runs"("p_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."list_report_runs"("p_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_report_runs"("p_limit" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."list_report_schedules"() TO "anon";
GRANT ALL ON FUNCTION "public"."list_report_schedules"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_report_schedules"() TO "service_role";



GRANT ALL ON FUNCTION "public"."merge_onboarding_state"("p_patch" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."merge_onboarding_state"("p_patch" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."merge_onboarding_state"("p_patch" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."on_approval_completed"() TO "anon";
GRANT ALL ON FUNCTION "public"."on_approval_completed"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."on_approval_completed"() TO "service_role";



GRANT ALL ON FUNCTION "public"."on_knowledge_document_complete"() TO "anon";
GRANT ALL ON FUNCTION "public"."on_knowledge_document_complete"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."on_knowledge_document_complete"() TO "service_role";



GRANT ALL ON FUNCTION "public"."onboarding_bootstrap_tx"("p_payload" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."onboarding_bootstrap_tx"("p_payload" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."onboarding_bootstrap_tx"("p_payload" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."process_pending_routine_executions"() TO "anon";
GRANT ALL ON FUNCTION "public"."process_pending_routine_executions"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."process_pending_routine_executions"() TO "service_role";



GRANT ALL ON FUNCTION "public"."record_audit"("p_action" "text", "p_entity_type" "text", "p_entity_id" "text", "p_payload" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."record_audit"("p_action" "text", "p_entity_type" "text", "p_entity_id" "text", "p_payload" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."record_audit"("p_action" "text", "p_entity_type" "text", "p_entity_id" "text", "p_payload" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."record_frontend_event"("p_event_name" "text", "p_properties" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."record_frontend_event"("p_event_name" "text", "p_properties" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."record_frontend_event"("p_event_name" "text", "p_properties" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."record_insight"("p_title" "text", "p_content" "text", "p_severity" "text", "p_data" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."record_insight"("p_title" "text", "p_content" "text", "p_severity" "text", "p_data" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."record_insight"("p_title" "text", "p_content" "text", "p_severity" "text", "p_data" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."request_approval"("p_action_type" "text", "p_payload" "jsonb", "p_expires_at" timestamp with time zone, "p_agent_slug" "text", "p_action" "text", "p_session_id" "text", "p_tool_call_id" "text", "p_routed_to_role" "text", "p_sla_hours" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."request_approval"("p_action_type" "text", "p_payload" "jsonb", "p_expires_at" timestamp with time zone, "p_agent_slug" "text", "p_action" "text", "p_session_id" "text", "p_tool_call_id" "text", "p_routed_to_role" "text", "p_sla_hours" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."request_approval"("p_action_type" "text", "p_payload" "jsonb", "p_expires_at" timestamp with time zone, "p_agent_slug" "text", "p_action" "text", "p_session_id" "text", "p_tool_call_id" "text", "p_routed_to_role" "text", "p_sla_hours" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."set_client_dimension_kpis"("p_dimension" "text", "p_slugs" "text"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."set_client_dimension_kpis"("p_dimension" "text", "p_slugs" "text"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_client_dimension_kpis"("p_dimension" "text", "p_slugs" "text"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."set_current_cliente_id"("p_client_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."set_current_cliente_id"("p_client_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_current_cliente_id"("p_client_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."trigger_column_discovery"("p_credential_id" bigint) TO "anon";
GRANT ALL ON FUNCTION "public"."trigger_column_discovery"("p_credential_id" bigint) TO "authenticated";
GRANT ALL ON FUNCTION "public"."trigger_column_discovery"("p_credential_id" bigint) TO "service_role";



GRANT ALL ON FUNCTION "public"."update_approval_stats"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_approval_stats"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_approval_stats"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_bigquery_foreign_table_columns"("p_client_id" "text", "p_columns" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."update_bigquery_foreign_table_columns"("p_client_id" "text", "p_columns" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_bigquery_foreign_table_columns"("p_client_id" "text", "p_columns" "jsonb") TO "service_role";



GRANT ALL ON FUNCTION "public"."update_data_source_mappings_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_data_source_mappings_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_data_source_mappings_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."upsert_client_document"("p_document_type_id" "text", "p_status" "text", "p_source" "text", "p_field_coverage" "jsonb", "p_metadata" "jsonb") TO "anon";
GRANT ALL ON FUNCTION "public"."upsert_client_document"("p_document_type_id" "text", "p_status" "text", "p_source" "text", "p_field_coverage" "jsonb", "p_metadata" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."upsert_client_document"("p_document_type_id" "text", "p_status" "text", "p_source" "text", "p_field_coverage" "jsonb", "p_metadata" "jsonb") TO "service_role";
























GRANT SELECT ON TABLE "analytics_v2"."dim_clientes" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."dim_clientes" TO "service_role";



GRANT ALL ON SEQUENCE "analytics_v2"."dim_clientes_cliente_id_seq" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."dim_datas" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."dim_datas" TO "service_role";



GRANT ALL ON SEQUENCE "analytics_v2"."dim_datas_data_id_seq" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."dim_fornecedores" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."dim_fornecedores" TO "service_role";



GRANT ALL ON SEQUENCE "analytics_v2"."dim_fornecedores_fornecedor_id_seq" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."dim_inventory" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."dim_inventory" TO "service_role";



GRANT ALL ON SEQUENCE "analytics_v2"."dim_inventory_inventory_id_seq" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."fato_transacoes" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."fato_transacoes" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."mv_distribuicao_regional" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."mv_distribuicao_regional" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."mv_resumo_dashboard" TO "authenticated";



GRANT SELECT ON TABLE "analytics_v2"."mv_series_temporal" TO "authenticated";



GRANT SELECT ON TABLE "analytics_v2"."mv_ultimos_pedidos" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."mv_ultimos_pedidos" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."reg_jobs" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."reg_jobs" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."v_distribuicao_regional" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."v_distribuicao_regional" TO "service_role";



GRANT SELECT ON TABLE "analytics_v2"."v_resumo_dashboard" TO "authenticated";



GRANT SELECT ON TABLE "analytics_v2"."v_series_temporal" TO "authenticated";



GRANT SELECT ON TABLE "analytics_v2"."v_ultimos_pedidos" TO "authenticated";
GRANT ALL ON TABLE "analytics_v2"."v_ultimos_pedidos" TO "service_role";


















GRANT ALL ON TABLE "public"."agent_catalog" TO "anon";
GRANT ALL ON TABLE "public"."agent_catalog" TO "authenticated";
GRANT ALL ON TABLE "public"."agent_catalog" TO "service_role";



GRANT ALL ON TABLE "public"."audit_log" TO "anon";
GRANT ALL ON TABLE "public"."audit_log" TO "authenticated";
GRANT ALL ON TABLE "public"."audit_log" TO "service_role";



GRANT ALL ON SEQUENCE "public"."audit_log_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."audit_log_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."audit_log_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."bigquery_foreign_tables" TO "anon";
GRANT ALL ON TABLE "public"."bigquery_foreign_tables" TO "authenticated";
GRANT ALL ON TABLE "public"."bigquery_foreign_tables" TO "service_role";



GRANT ALL ON TABLE "public"."bigquery_servers" TO "anon";
GRANT ALL ON TABLE "public"."bigquery_servers" TO "authenticated";
GRANT ALL ON TABLE "public"."bigquery_servers" TO "service_role";



GRANT ALL ON TABLE "public"."calendar_settings" TO "anon";
GRANT ALL ON TABLE "public"."calendar_settings" TO "authenticated";
GRANT ALL ON TABLE "public"."calendar_settings" TO "service_role";



GRANT ALL ON TABLE "public"."client_approval_rules" TO "anon";
GRANT ALL ON TABLE "public"."client_approval_rules" TO "authenticated";
GRANT ALL ON TABLE "public"."client_approval_rules" TO "service_role";



GRANT ALL ON TABLE "public"."client_approval_stats" TO "anon";
GRANT ALL ON TABLE "public"."client_approval_stats" TO "authenticated";
GRANT ALL ON TABLE "public"."client_approval_stats" TO "service_role";



GRANT ALL ON TABLE "public"."client_data_sources" TO "anon";
GRANT ALL ON TABLE "public"."client_data_sources" TO "authenticated";
GRANT ALL ON TABLE "public"."client_data_sources" TO "service_role";



GRANT ALL ON TABLE "public"."client_dimension_kpis" TO "anon";
GRANT ALL ON TABLE "public"."client_dimension_kpis" TO "authenticated";
GRANT ALL ON TABLE "public"."client_dimension_kpis" TO "service_role";



GRANT ALL ON TABLE "public"."client_enabled_agents" TO "anon";
GRANT ALL ON TABLE "public"."client_enabled_agents" TO "authenticated";
GRANT ALL ON TABLE "public"."client_enabled_agents" TO "service_role";



GRANT ALL ON TABLE "public"."client_insights" TO "anon";
GRANT ALL ON TABLE "public"."client_insights" TO "authenticated";
GRANT ALL ON TABLE "public"."client_insights" TO "service_role";



GRANT ALL ON TABLE "public"."client_knowledge_documents" TO "anon";
GRANT ALL ON TABLE "public"."client_knowledge_documents" TO "authenticated";
GRANT ALL ON TABLE "public"."client_knowledge_documents" TO "service_role";



GRANT ALL ON TABLE "public"."client_notification_preferences" TO "anon";
GRANT ALL ON TABLE "public"."client_notification_preferences" TO "authenticated";
GRANT ALL ON TABLE "public"."client_notification_preferences" TO "service_role";



GRANT ALL ON TABLE "public"."client_routine_executions" TO "anon";
GRANT ALL ON TABLE "public"."client_routine_executions" TO "authenticated";
GRANT ALL ON TABLE "public"."client_routine_executions" TO "service_role";



GRANT ALL ON TABLE "public"."client_routines" TO "anon";
GRANT ALL ON TABLE "public"."client_routines" TO "authenticated";
GRANT ALL ON TABLE "public"."client_routines" TO "service_role";



GRANT ALL ON TABLE "public"."clientes_blu" TO "anon";
GRANT ALL ON TABLE "public"."clientes_blu" TO "authenticated";
GRANT ALL ON TABLE "public"."clientes_blu" TO "service_role";



GRANT ALL ON TABLE "public"."conversa" TO "anon";
GRANT ALL ON TABLE "public"."conversa" TO "authenticated";
GRANT ALL ON TABLE "public"."conversa" TO "service_role";



GRANT ALL ON TABLE "public"."credencial_servico_externo" TO "anon";
GRANT ALL ON TABLE "public"."credencial_servico_externo" TO "authenticated";
GRANT ALL ON TABLE "public"."credencial_servico_externo" TO "service_role";



GRANT ALL ON SEQUENCE "public"."credencial_servico_externo_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."credencial_servico_externo_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."credencial_servico_externo_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."cross_agent_routines" TO "anon";
GRANT ALL ON TABLE "public"."cross_agent_routines" TO "authenticated";
GRANT ALL ON TABLE "public"."cross_agent_routines" TO "service_role";



GRANT ALL ON TABLE "public"."data_source_mappings" TO "anon";
GRANT ALL ON TABLE "public"."data_source_mappings" TO "authenticated";
GRANT ALL ON TABLE "public"."data_source_mappings" TO "service_role";



GRANT ALL ON TABLE "public"."doc_templates" TO "anon";
GRANT ALL ON TABLE "public"."doc_templates" TO "authenticated";
GRANT ALL ON TABLE "public"."doc_templates" TO "service_role";



GRANT ALL ON TABLE "public"."document_versions" TO "anon";
GRANT ALL ON TABLE "public"."document_versions" TO "authenticated";
GRANT ALL ON TABLE "public"."document_versions" TO "service_role";



GRANT ALL ON TABLE "public"."documents" TO "anon";
GRANT ALL ON TABLE "public"."documents" TO "authenticated";
GRANT ALL ON TABLE "public"."documents" TO "service_role";



GRANT ALL ON TABLE "public"."frontend_events" TO "anon";
GRANT ALL ON TABLE "public"."frontend_events" TO "authenticated";
GRANT ALL ON TABLE "public"."frontend_events" TO "service_role";



GRANT ALL ON SEQUENCE "public"."frontend_events_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."frontend_events_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."frontend_events_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."integration_configs" TO "anon";
GRANT ALL ON TABLE "public"."integration_configs" TO "authenticated";
GRANT ALL ON TABLE "public"."integration_configs" TO "service_role";



GRANT ALL ON TABLE "public"."integration_tokens" TO "anon";
GRANT ALL ON TABLE "public"."integration_tokens" TO "authenticated";
GRANT ALL ON TABLE "public"."integration_tokens" TO "service_role";



GRANT ALL ON TABLE "public"."knowledge_agent_requirements" TO "anon";
GRANT ALL ON TABLE "public"."knowledge_agent_requirements" TO "authenticated";
GRANT ALL ON TABLE "public"."knowledge_agent_requirements" TO "service_role";



GRANT ALL ON TABLE "public"."knowledge_document_types" TO "anon";
GRANT ALL ON TABLE "public"."knowledge_document_types" TO "authenticated";
GRANT ALL ON TABLE "public"."knowledge_document_types" TO "service_role";



GRANT ALL ON TABLE "public"."knowledge_tag_definitions" TO "anon";
GRANT ALL ON TABLE "public"."knowledge_tag_definitions" TO "authenticated";
GRANT ALL ON TABLE "public"."knowledge_tag_definitions" TO "service_role";



GRANT ALL ON TABLE "public"."kpi_catalog" TO "anon";
GRANT ALL ON TABLE "public"."kpi_catalog" TO "authenticated";
GRANT ALL ON TABLE "public"."kpi_catalog" TO "service_role";



GRANT ALL ON TABLE "public"."messages" TO "anon";
GRANT ALL ON TABLE "public"."messages" TO "authenticated";
GRANT ALL ON TABLE "public"."messages" TO "service_role";



GRANT ALL ON TABLE "public"."notifications" TO "anon";
GRANT ALL ON TABLE "public"."notifications" TO "authenticated";
GRANT ALL ON TABLE "public"."notifications" TO "service_role";



GRANT ALL ON TABLE "public"."nps_responses" TO "anon";
GRANT ALL ON TABLE "public"."nps_responses" TO "authenticated";
GRANT ALL ON TABLE "public"."nps_responses" TO "service_role";



GRANT ALL ON TABLE "public"."report_runs" TO "anon";
GRANT ALL ON TABLE "public"."report_runs" TO "authenticated";
GRANT ALL ON TABLE "public"."report_runs" TO "service_role";



GRANT ALL ON TABLE "public"."report_schedules" TO "anon";
GRANT ALL ON TABLE "public"."report_schedules" TO "authenticated";
GRANT ALL ON TABLE "public"."report_schedules" TO "service_role";



GRANT ALL ON TABLE "public"."standalone_agent_sessions" TO "anon";
GRANT ALL ON TABLE "public"."standalone_agent_sessions" TO "authenticated";
GRANT ALL ON TABLE "public"."standalone_agent_sessions" TO "service_role";



GRANT ALL ON TABLE "public"."suppliers" TO "anon";
GRANT ALL ON TABLE "public"."suppliers" TO "authenticated";
GRANT ALL ON TABLE "public"."suppliers" TO "service_role";



GRANT ALL ON TABLE "public"."uploaded_files_metadata" TO "anon";
GRANT ALL ON TABLE "public"."uploaded_files_metadata" TO "authenticated";
GRANT ALL ON TABLE "public"."uploaded_files_metadata" TO "service_role";









GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "vector_db"."document_chunks" TO "authenticated";
GRANT ALL ON TABLE "vector_db"."document_chunks" TO "service_role";



GRANT ALL ON SEQUENCE "vector_db"."document_chunks_id_seq" TO "service_role";



GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE "vector_db"."documents" TO "authenticated";
GRANT ALL ON TABLE "vector_db"."documents" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "analytics_v2" GRANT SELECT ON TABLES TO "authenticated";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "vector_db" GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES TO "authenticated";




























