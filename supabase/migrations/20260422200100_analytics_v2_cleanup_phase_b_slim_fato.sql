-- Analytics V2 Cleanup — Phase B
-- Slim fato_transacoes + realign kept RPCs & helper functions.
--
-- Changes:
--   • Snapshot fato_transacoes into analytics_v2_legacy.fato_transacoes_full
--     (preserves invoice/NF/fiscal columns for polen / future BI use).
--   • Drop 34 unused wide/invoice/fiscal columns from analytics_v2.fato_transacoes.
--   • Drop fato_transacoes.inventory_id (legacy link to dim_resources).
--     produto_id (→ dim_inventory.inventory_id) becomes the sole product FK.
--   • Rewrite RPCs and aggregate helpers to use produto_id instead of inventory_id.
--   • Add FK produto_id → dim_inventory(inventory_id) so PostgREST embeds work.
--
-- Dropped columns:
--   data_vencimento_id, data_efetiva_id, categoria_id, inventory_id, parcela,
--   origem_tabela, origem_id, updated_at, movement_type,
--   nf_numero, valor_nf, quantidade_kg, valor_unitario_kg, danfe,
--   data_criacao_origem, is_blocked, volume, volume_validado, valor_validado,
--   id_credito, data_credito, status_produto, data_criacao_produto,
--   was_purchased, was_compensation, compensations_ids,
--   purchase_order_ids, purchase_order_codes, in_offer, has_credit,
--   product_invalidations, cpl_adicional, fisco_adicional, danfe_materials,
--   filial_id, filial_cnpj
--
-- Kept columns (target minimal schema):
--   transacao_id, client_id, tipo_id, data_competencia_id,
--   cliente_id, fornecedor_id, produto_id,
--   documento, quantidade, valor_unitario, valor, status, created_at

BEGIN;

-- ── 1. Snapshot current wide fact ─────────────────────────────────────
CREATE TABLE analytics_v2_legacy.fato_transacoes_full AS
  TABLE analytics_v2.fato_transacoes;
COMMENT ON TABLE analytics_v2_legacy.fato_transacoes_full IS
  'Snapshot of analytics_v2.fato_transacoes before Apr 2026 slimming. Retains NF/invoice/fiscal columns.';
REVOKE ALL ON analytics_v2_legacy.fato_transacoes_full FROM anon, authenticated;
GRANT  SELECT ON analytics_v2_legacy.fato_transacoes_full TO service_role;

-- ── 2. Drop dependent functions (recreated below) ────────────────────
-- These reference columns we drop. Recreated in step 5 against the slim schema.
-- Cover every possible existing signature so CREATE OR REPLACE below cannot
-- collide on return type.
DROP FUNCTION IF EXISTS analytics_v2.atualizar_agregados()                CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.atualizar_agregados(text)            CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.atualizar_agregados(uuid)            CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.calcular_tier_produtos_abc()         CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.calcular_tier_produtos_abc(text)     CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.calcular_tier_produtos_abc(uuid)     CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.get_client_top_products(text)        CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.get_product_top_clients(text)        CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.get_product_top_regions(text)        CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.get_product_revenue_series(text)     CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.get_supplier_top_products(text)      CASCADE;

-- Inventory ingestion helper, references column we drop.
DROP FUNCTION IF EXISTS analytics_v2.ingest_invoices_from_bq()           CASCADE;
DROP FUNCTION IF EXISTS analytics_v2.sync_invoices_client(text)          CASCADE;

-- Recreate ensure-dim-datas trigger without data_efetiva_id (column is going away).
DROP TRIGGER IF EXISTS trg_ensure_dim_datas_for_fato ON analytics_v2.fato_transacoes;
CREATE OR REPLACE FUNCTION analytics_v2.trg_ensure_dim_datas_for_fato()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.data_competencia_id := analytics_v2.ensure_dim_data(NEW.data_competencia_id);
  RETURN NEW;
END;
$$;
CREATE TRIGGER trg_ensure_dim_datas_for_fato
  BEFORE INSERT OR UPDATE OF data_competencia_id
  ON analytics_v2.fato_transacoes
  FOR EACH ROW EXECUTE FUNCTION analytics_v2.trg_ensure_dim_datas_for_fato();

-- Drop materialized views (3 reference ft.inventory_id; recreated at end with ft.produto_id).
-- CASCADE drops v_resumo_dashboard, v_series_temporal, v_distribuicao_regional too; recreated below.
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_dashboard       CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_series_temporal        CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_distribuicao_regional  CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_clientes        CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_fornecedores    CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.mv_resumo_produtos        CASCADE;

-- ── 3. Slim fato_transacoes ──────────────────────────────────────────
ALTER TABLE analytics_v2.fato_transacoes
  DROP COLUMN IF EXISTS data_vencimento_id,
  DROP COLUMN IF EXISTS data_efetiva_id,
  DROP COLUMN IF EXISTS categoria_id,
  DROP COLUMN IF EXISTS inventory_id,
  DROP COLUMN IF EXISTS parcela,
  DROP COLUMN IF EXISTS origem_tabela,
  DROP COLUMN IF EXISTS origem_id,
  DROP COLUMN IF EXISTS updated_at,
  DROP COLUMN IF EXISTS movement_type,
  DROP COLUMN IF EXISTS nf_numero,
  DROP COLUMN IF EXISTS valor_nf,
  DROP COLUMN IF EXISTS quantidade_kg,
  DROP COLUMN IF EXISTS valor_unitario_kg,
  DROP COLUMN IF EXISTS danfe,
  DROP COLUMN IF EXISTS data_criacao_origem,
  DROP COLUMN IF EXISTS is_blocked,
  DROP COLUMN IF EXISTS volume,
  DROP COLUMN IF EXISTS volume_validado,
  DROP COLUMN IF EXISTS valor_validado,
  DROP COLUMN IF EXISTS id_credito,
  DROP COLUMN IF EXISTS data_credito,
  DROP COLUMN IF EXISTS status_produto,
  DROP COLUMN IF EXISTS data_criacao_produto,
  DROP COLUMN IF EXISTS was_purchased,
  DROP COLUMN IF EXISTS was_compensation,
  DROP COLUMN IF EXISTS compensations_ids,
  DROP COLUMN IF EXISTS purchase_order_ids,
  DROP COLUMN IF EXISTS purchase_order_codes,
  DROP COLUMN IF EXISTS in_offer,
  DROP COLUMN IF EXISTS has_credit,
  DROP COLUMN IF EXISTS product_invalidations,
  DROP COLUMN IF EXISTS cpl_adicional,
  DROP COLUMN IF EXISTS fisco_adicional,
  DROP COLUMN IF EXISTS danfe_materials,
  DROP COLUMN IF EXISTS filial_id,
  DROP COLUMN IF EXISTS filial_cnpj;

-- ── 4. Add FK for PostgREST embeds (fato_transacoes → dim_inventory) ──
ALTER TABLE analytics_v2.fato_transacoes
  ADD CONSTRAINT fato_transacoes_produto_id_fkey
  FOREIGN KEY (produto_id) REFERENCES analytics_v2.dim_inventory(inventory_id)
  ON DELETE SET NULL;

-- Indexes on product link (partial: skip NULL since many rows lack product data)
CREATE INDEX IF NOT EXISTS idx_fato_transacoes_produto_id
  ON analytics_v2.fato_transacoes(produto_id)
  WHERE produto_id IS NOT NULL;

-- ── 5. Recreate RPCs using produto_id ────────────────────────────────
CREATE OR REPLACE FUNCTION analytics_v2.get_client_top_products(p_client_name text)
RETURNS TABLE(name text, total numeric, percentual numeric)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH vendas AS (
    SELECT di.nome, SUM(ft.valor) AS total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id
    JOIN analytics_v2.dim_inventory di ON ft.produto_id = di.inventory_id
    WHERE dc.nome ILIKE '%' || p_client_name || '%'
      AND ft.client_id = public.get_my_client_id()
    GROUP BY di.nome
  ),
  total AS (SELECT NULLIF(SUM(total), 0) AS grand FROM vendas)
  SELECT v.nome,
         v.total,
         ROUND((v.total / t.grand) * 100, 2) AS percentual
  FROM vendas v CROSS JOIN total t
  ORDER BY v.total DESC
  LIMIT 10;
$$;

CREATE OR REPLACE FUNCTION analytics_v2.get_product_top_clients(p_product_name text)
RETURNS TABLE(name text, total numeric, percentual numeric)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH vendas AS (
    SELECT dc.nome, SUM(ft.valor) AS total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_inventory di ON ft.produto_id = di.inventory_id
    JOIN analytics_v2.dim_clientes  dc ON ft.cliente_id = dc.cliente_id
    WHERE di.nome ILIKE '%' || p_product_name || '%'
      AND ft.client_id = public.get_my_client_id()
    GROUP BY dc.nome
  ),
  total AS (SELECT NULLIF(SUM(total), 0) AS grand FROM vendas)
  SELECT v.nome,
         v.total,
         ROUND((v.total / t.grand) * 100, 2) AS percentual
  FROM vendas v CROSS JOIN total t
  ORDER BY v.total DESC
  LIMIT 10;
$$;

CREATE OR REPLACE FUNCTION analytics_v2.get_product_top_regions(p_product_name text)
RETURNS TABLE(name text, total numeric, percentual numeric)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH vendas AS (
    SELECT dc.endereco_uf AS nome, SUM(ft.valor) AS total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_inventory di ON ft.produto_id = di.inventory_id
    JOIN analytics_v2.dim_clientes  dc ON ft.cliente_id = dc.cliente_id
    WHERE di.nome ILIKE '%' || p_product_name || '%'
      AND ft.client_id = public.get_my_client_id()
      AND dc.endereco_uf IS NOT NULL
    GROUP BY dc.endereco_uf
  ),
  total AS (SELECT NULLIF(SUM(total), 0) AS grand FROM vendas)
  SELECT v.nome,
         v.total,
         ROUND((v.total / t.grand) * 100, 2) AS percentual
  FROM vendas v CROSS JOIN total t
  ORDER BY v.total DESC
  LIMIT 10;
$$;

CREATE OR REPLACE FUNCTION analytics_v2.get_product_revenue_series(p_product_name text)
RETURNS TABLE(periodo text, total numeric)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  SELECT to_char(dd.data, 'YYYY-MM') AS periodo,
         SUM(ft.valor)               AS total
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_inventory di ON ft.produto_id = di.inventory_id
  JOIN analytics_v2.dim_datas    dd ON ft.data_competencia_id = dd.data_id
  WHERE di.nome ILIKE '%' || p_product_name || '%'
    AND ft.client_id = public.get_my_client_id()
  GROUP BY to_char(dd.data, 'YYYY-MM')
  ORDER BY 1;
$$;

CREATE OR REPLACE FUNCTION analytics_v2.get_supplier_top_products(p_supplier_name text)
RETURNS TABLE(name text, total numeric, percentual numeric)
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
  WITH compras AS (
    SELECT di.nome, SUM(ft.valor) AS total
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_fornecedores df ON ft.fornecedor_id = df.fornecedor_id
    JOIN analytics_v2.dim_inventory    di ON ft.produto_id    = di.inventory_id
    WHERE df.nome ILIKE '%' || p_supplier_name || '%'
      AND ft.client_id = public.get_my_client_id()
    GROUP BY di.nome
  ),
  total AS (SELECT NULLIF(SUM(total), 0) AS grand FROM compras)
  SELECT c.nome,
         c.total,
         ROUND((c.total / t.grand) * 100, 2) AS percentual
  FROM compras c CROSS JOIN total t
  ORDER BY c.total DESC
  LIMIT 10;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.get_client_top_products(text)     TO authenticated;
GRANT EXECUTE ON FUNCTION analytics_v2.get_product_top_clients(text)     TO authenticated;
GRANT EXECUTE ON FUNCTION analytics_v2.get_product_top_regions(text)     TO authenticated;
GRANT EXECUTE ON FUNCTION analytics_v2.get_product_revenue_series(text)  TO authenticated;
GRANT EXECUTE ON FUNCTION analytics_v2.get_supplier_top_products(text)   TO authenticated;

-- ── 6. Recreate aggregate helpers against slim schema ────────────────

CREATE OR REPLACE FUNCTION analytics_v2.atualizar_agregados(p_client_id text DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
BEGIN
  -- dim_clientes aggregates
  WITH agg AS (
    SELECT
      ft.cliente_id,
      SUM(ft.valor)                           AS receita_total,
      SUM(ft.quantidade)                      AS quantidade_total,
      COUNT(DISTINCT ft.documento)            AS total_pedidos,
      AVG(ft.valor)                           AS ticket_medio,
      MIN(dd.data)                            AS data_primeira_compra,
      MAX(dd.data)                            AS data_ultima_compra
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.cliente_id IS NOT NULL
      AND (p_client_id IS NULL OR ft.client_id = p_client_id)
    GROUP BY ft.cliente_id
  )
  UPDATE analytics_v2.dim_clientes c
  SET receita_total         = agg.receita_total,
      quantidade_total      = agg.quantidade_total,
      total_pedidos         = agg.total_pedidos,
      ticket_medio          = agg.ticket_medio,
      data_primeira_compra  = agg.data_primeira_compra,
      data_ultima_compra    = agg.data_ultima_compra,
      dias_recencia         = (CURRENT_DATE - agg.data_ultima_compra),
      atualizado_em         = now()
  FROM agg
  WHERE c.cliente_id = agg.cliente_id
    AND (p_client_id IS NULL OR c.client_id = p_client_id);

  -- dim_fornecedores aggregates
  WITH agg AS (
    SELECT
      ft.fornecedor_id,
      SUM(ft.valor)                           AS receita_total,
      COUNT(DISTINCT ft.documento)            AS total_pedidos_recebidos,
      AVG(ft.valor)                           AS ticket_medio,
      MIN(dd.data)                            AS data_primeira_transacao,
      MAX(dd.data)                            AS data_ultima_transacao
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.fornecedor_id IS NOT NULL
      AND (p_client_id IS NULL OR ft.client_id = p_client_id)
    GROUP BY ft.fornecedor_id
  )
  UPDATE analytics_v2.dim_fornecedores f
  SET receita_total             = agg.receita_total,
      total_pedidos_recebidos   = agg.total_pedidos_recebidos,
      ticket_medio              = agg.ticket_medio,
      data_primeira_transacao   = agg.data_primeira_transacao,
      data_ultima_transacao     = agg.data_ultima_transacao,
      dias_recencia             = (CURRENT_DATE - agg.data_ultima_transacao),
      atualizado_em             = now()
  FROM agg
  WHERE f.fornecedor_id = agg.fornecedor_id
    AND (p_client_id IS NULL OR f.client_id = p_client_id);

  -- dim_inventory aggregates
  WITH agg AS (
    SELECT
      ft.produto_id,
      SUM(ft.valor)                   AS receita_total,
      SUM(ft.quantidade)              AS quantidade_total_vendida,
      AVG(ft.valor_unitario)          AS preco_medio,
      COUNT(DISTINCT ft.documento)    AS total_pedidos,
      AVG(ft.quantidade)              AS quantidade_media_por_pedido,
      MAX(dd.data)                    AS data_ultima_venda
    FROM analytics_v2.fato_transacoes ft
    JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
    WHERE ft.produto_id IS NOT NULL
      AND (p_client_id IS NULL OR ft.client_id = p_client_id)
    GROUP BY ft.produto_id
  )
  UPDATE analytics_v2.dim_inventory i
  SET receita_total                 = agg.receita_total,
      quantidade_total_vendida      = agg.quantidade_total_vendida,
      preco_medio                   = agg.preco_medio,
      total_pedidos                 = agg.total_pedidos,
      quantidade_media_por_pedido   = agg.quantidade_media_por_pedido,
      data_ultima_venda             = agg.data_ultima_venda,
      dias_recencia                 = (CURRENT_DATE - agg.data_ultima_venda),
      updated_at                    = now()
  FROM agg
  WHERE i.inventory_id = agg.produto_id
    AND (p_client_id IS NULL OR i.client_id = p_client_id);
END;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.atualizar_agregados(text) TO authenticated, service_role;

-- Product ABC tiering — simplified to use produto_id & work off slim fact
CREATE OR REPLACE FUNCTION analytics_v2.calcular_tier_produtos_abc(p_client_id text DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = analytics_v2, public
AS $$
BEGIN
  WITH receita_por_produto AS (
    SELECT ft.client_id,
           ft.produto_id,
           SUM(ft.valor) AS receita
    FROM analytics_v2.fato_transacoes ft
    WHERE ft.produto_id IS NOT NULL
      AND (p_client_id IS NULL OR ft.client_id = p_client_id)
    GROUP BY ft.client_id, ft.produto_id
  ),
  ranked AS (
    SELECT rpp.*,
           receita / NULLIF(SUM(receita) OVER (PARTITION BY client_id), 0) AS share,
           SUM(receita) OVER (
             PARTITION BY client_id
             ORDER BY receita DESC
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) / NULLIF(SUM(receita) OVER (PARTITION BY client_id), 0) AS cum_share
    FROM receita_por_produto rpp
  ),
  tiered AS (
    SELECT client_id,
           produto_id,
           CASE
             WHEN cum_share <= 0.80 THEN 'A'
             WHEN cum_share <= 0.95 THEN 'B'
             ELSE 'C'
           END AS nivel_cluster,
           ROUND(COALESCE(share, 0) * 100, 2) AS pontuacao_cluster
    FROM ranked
  )
  UPDATE analytics_v2.dim_inventory i
  SET nivel_cluster     = t.nivel_cluster,
      pontuacao_cluster = t.pontuacao_cluster,
      updated_at        = now()
  FROM tiered t
  WHERE i.inventory_id = t.produto_id
    AND i.client_id    = t.client_id;
END;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.calcular_tier_produtos_abc(text) TO authenticated, service_role;

-- ── 7. Recreate materialized views with ft.produto_id ────────────────

-- mv_resumo_dashboard
CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_dashboard AS
WITH last_30_days AS (
  SELECT ft.client_id,
    SUM(ft.valor)                       AS receita,
    SUM(ft.quantidade)                  AS quantidade,
    COUNT(DISTINCT ft.cliente_id)       AS clientes_unicos,
    COUNT(DISTINCT ft.produto_id)       AS produtos_unicos,
    COUNT(DISTINCT ft.fornecedor_id)    AS fornecedores_unicos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= (CURRENT_DATE - INTERVAL '30 days') AND dd.data IS NOT NULL
  GROUP BY ft.client_id
),
previous_30_days AS (
  SELECT ft.client_id,
    SUM(ft.valor)                       AS receita,
    SUM(ft.quantidade)                  AS quantidade,
    COUNT(DISTINCT ft.cliente_id)       AS clientes_unicos,
    COUNT(DISTINCT ft.produto_id)       AS produtos_unicos,
    COUNT(DISTINCT ft.fornecedor_id)    AS fornecedores_unicos
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= (CURRENT_DATE - INTERVAL '60 days')
    AND dd.data <  (CURRENT_DATE - INTERVAL '30 days')
    AND dd.data IS NOT NULL
  GROUP BY ft.client_id
),
client_agg AS (
  SELECT c.client_id,
    COUNT(*)                                                             AS total_clientes,
    COUNT(*) FILTER (WHERE c.dias_recencia <= 90)                        AS clientes_ativos,
    COUNT(*) FILTER (WHERE c.total_pedidos = 1)                          AS clientes_novos,
    COUNT(DISTINCT c.endereco_uf) FILTER (WHERE c.endereco_uf IS NOT NULL) AS total_regioes
  FROM analytics_v2.dim_clientes c
  GROUP BY c.client_id
),
fornecedor_agg AS (
  SELECT f.client_id,
    COUNT(*) AS total_fornecedores,
    COALESCE(AVG(f.frequencia_mensal), 0::numeric) AS frequencia_media_fornecedores
  FROM analytics_v2.dim_fornecedores f
  GROUP BY f.client_id
),
inventory_agg AS (
  SELECT i.client_id,
    COUNT(*) AS total_produtos,
    COALESCE(SUM(i.quantidade_total_vendida), 0::numeric) AS quantidade_total_vendida
  FROM analytics_v2.dim_inventory i
  GROUP BY i.client_id
),
fact_agg AS (
  SELECT ft.client_id,
    COUNT(DISTINCT ft.documento)          AS total_pedidos,
    COALESCE(SUM(ft.valor), 0::numeric)   AS receita_total,
    COALESCE(AVG(ft.valor), 0::numeric)   AS ticket_medio
  FROM analytics_v2.fato_transacoes ft
  GROUP BY ft.client_id
)
SELECT cl.client_id,
  COALESCE(ca.total_clientes, 0::bigint)         AS total_clientes,
  COALESCE(fa2.total_fornecedores, 0::bigint)    AS total_fornecedores,
  COALESCE(ia.total_produtos, 0::bigint)         AS total_produtos,
  COALESCE(fa.total_pedidos, 0::bigint)          AS total_pedidos,
  COALESCE(fa.receita_total, 0::numeric)         AS receita_total,
  COALESCE(fa.ticket_medio, 0::numeric)          AS ticket_medio,
  COALESCE(ia.quantidade_total_vendida, 0::numeric) AS quantidade_total_vendida,
  COALESCE(l30.receita, 0::numeric)              AS receita_mes_atual,
  COALESCE(l30.quantidade, 0::numeric)           AS quantidade_mes_atual,
  COALESCE(l30.clientes_unicos, 0::bigint)       AS clientes_mes_atual,
  COALESCE(l30.produtos_unicos, 0::bigint)       AS produtos_mes_atual,
  COALESCE(l30.fornecedores_unicos, 0::bigint)   AS fornecedores_mes_atual,
  CASE WHEN COALESCE(p30.receita, 0) > 0 THEN ((COALESCE(l30.receita, 0) - p30.receita) / p30.receita * 100)::numeric(10,2) END AS crescimento_receita,
  CASE WHEN COALESCE(p30.clientes_unicos, 0) > 0 THEN ((COALESCE(l30.clientes_unicos, 0)::numeric - p30.clientes_unicos) / p30.clientes_unicos * 100)::numeric(10,2) END AS crescimento_clientes,
  CASE WHEN COALESCE(p30.produtos_unicos, 0) > 0 THEN ((COALESCE(l30.produtos_unicos, 0)::numeric - p30.produtos_unicos) / p30.produtos_unicos * 100)::numeric(10,2) END AS crescimento_produtos,
  CASE WHEN COALESCE(p30.quantidade, 0) > 0 THEN ((COALESCE(l30.quantidade, 0) - p30.quantidade) / p30.quantidade * 100)::numeric(10,2) END AS crescimento_quantidade,
  COALESCE(fa2.frequencia_media_fornecedores, 0::numeric) AS frequencia_media_fornecedores,
  COALESCE(ca.total_regioes, 0::bigint)          AS total_regioes,
  to_char(CURRENT_DATE, 'YYYY-MM')               AS ultimo_mes,
  COALESCE(ca.clientes_ativos, 0::bigint)        AS clientes_ativos,
  COALESCE(ca.clientes_novos, 0::bigint)         AS clientes_novos,
  now()                                           AS gerado_em
FROM (SELECT DISTINCT ft.client_id FROM analytics_v2.fato_transacoes ft) cl
LEFT JOIN last_30_days     l30 ON l30.client_id = cl.client_id
LEFT JOIN previous_30_days p30 ON p30.client_id = cl.client_id
LEFT JOIN client_agg       ca  ON ca.client_id  = cl.client_id
LEFT JOIN fornecedor_agg   fa2 ON fa2.client_id = cl.client_id
LEFT JOIN inventory_agg    ia  ON ia.client_id  = cl.client_id
LEFT JOIN fact_agg         fa  ON fa.client_id  = cl.client_id;

CREATE UNIQUE INDEX idx_mv_resumo_dashboard_client_id
  ON analytics_v2.mv_resumo_dashboard(client_id);

-- mv_series_temporal
CREATE MATERIALIZED VIEW analytics_v2.mv_series_temporal AS
SELECT ft.client_id, 'produtos'::text AS tipo_grafico, 'contagem'::text AS dimensao,
       to_char(dd.data, 'YYYY-MM') AS periodo,
       date_trunc('month', dd.data)::date AS data_periodo,
       COUNT(DISTINCT ft.produto_id) AS total
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date
UNION ALL
SELECT ft.client_id, 'produtos', 'receita', to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date,
       COALESCE(SUM(ft.valor),0)::bigint
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date
UNION ALL
SELECT ft.client_id, 'produtos', 'quantidade', to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date,
       COALESCE(SUM(ft.quantidade),0)::bigint
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date
UNION ALL
SELECT ft.client_id, 'clientes', 'contagem', to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date,
       COUNT(DISTINCT ft.cliente_id)
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date
UNION ALL
SELECT ft.client_id, 'clientes', 'receita', to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date,
       COALESCE(SUM(ft.valor),0)::bigint
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date
UNION ALL
SELECT ft.client_id, 'clientes', 'quantidade', to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date,
       COALESCE(SUM(ft.quantidade),0)::bigint
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date
UNION ALL
SELECT ft.client_id, 'fornecedores', 'contagem', to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date,
       COUNT(DISTINCT ft.fornecedor_id)
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date
UNION ALL
SELECT ft.client_id, 'fornecedores', 'receita', to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date,
       COALESCE(SUM(ft.valor),0)::bigint
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date
UNION ALL
SELECT ft.client_id, 'fornecedores', 'quantidade', to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date,
       COALESCE(SUM(ft.quantidade),0)::bigint
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date
UNION ALL
SELECT ft.client_id, 'pedidos', 'total', to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date,
       COUNT(DISTINCT ft.documento)
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date
UNION ALL
SELECT ft.client_id, 'receita', 'receita', to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date,
       COALESCE(SUM(ft.valor),0)::bigint
FROM analytics_v2.fato_transacoes ft JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
WHERE dd.data IS NOT NULL GROUP BY ft.client_id, to_char(dd.data,'YYYY-MM'), date_trunc('month',dd.data)::date;

CREATE UNIQUE INDEX ux_mv_series_temporal
  ON analytics_v2.mv_series_temporal(client_id, tipo_grafico, dimensao, data_periodo);

-- mv_distribuicao_regional (unchanged)
CREATE MATERIALIZED VIEW analytics_v2.mv_distribuicao_regional AS
WITH estado_para_regiao(sigla_estado, nome_regiao) AS (
  VALUES ('AC','Norte'),('AM','Norte'),('AP','Norte'),('PA','Norte'),('RO','Norte'),('RR','Norte'),('TO','Norte'),
         ('AL','Nordeste'),('BA','Nordeste'),('CE','Nordeste'),('MA','Nordeste'),('PB','Nordeste'),('PE','Nordeste'),('PI','Nordeste'),('RN','Nordeste'),('SE','Nordeste'),
         ('DF','Centro-Oeste'),('GO','Centro-Oeste'),('MT','Centro-Oeste'),('MS','Centro-Oeste'),
         ('ES','Sudeste'),('MG','Sudeste'),('RJ','Sudeste'),('SP','Sudeste'),
         ('PR','Sul'),('RS','Sul'),('SC','Sul')
),
totais_regionais AS (
  SELECT ft.client_id,
         COALESCE(dc.endereco_uf, 'Não informado') AS estado,
         COALESCE(sr.nome_regiao,  'Não informado') AS regiao,
         COUNT(DISTINCT ft.documento) AS total
  FROM analytics_v2.fato_transacoes ft
  LEFT JOIN analytics_v2.dim_clientes dc ON ft.cliente_id = dc.cliente_id AND ft.client_id = dc.client_id
  LEFT JOIN estado_para_regiao sr ON dc.endereco_uf = sr.sigla_estado
  GROUP BY ft.client_id, dc.endereco_uf, sr.nome_regiao
),
totais_cliente AS (
  SELECT client_id, SUM(total) AS total_geral FROM totais_regionais GROUP BY client_id
)
SELECT tr.client_id,
  'pedidos_por_regiao'::text AS tipo_grafico,
  'pedidos'::text            AS dimensao,
  tr.estado, tr.regiao, tr.total,
  CASE WHEN tc.total_geral > 0 THEN tr.total::numeric / tc.total_geral * 100 ELSE 0 END AS percentual
FROM totais_regionais tr
JOIN totais_cliente  tc ON tr.client_id = tc.client_id;

CREATE UNIQUE INDEX ux_mv_distribuicao_regional
  ON analytics_v2.mv_distribuicao_regional(client_id, tipo_grafico, dimensao, estado, regiao);

-- mv_resumo_clientes (unchanged — does not reference ft.inventory_id)
CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_clientes AS
WITH transacoes_30_dias AS (
  SELECT ft.client_id, ft.cliente_id,
         SUM(ft.valor) AS receita_30_dias,
         SUM(ft.quantidade) AS quantidade_30_dias,
         COUNT(DISTINCT ft.documento) AS pedidos_30_dias
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= (CURRENT_DATE - INTERVAL '30 days')
  GROUP BY ft.client_id, ft.cliente_id
),
transacoes_anteriores AS (
  SELECT ft.client_id, ft.cliente_id,
         SUM(ft.valor) AS receita_anterior,
         SUM(ft.quantidade) AS quantidade_anterior,
         COUNT(DISTINCT ft.documento) AS pedidos_anterior
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= (CURRENT_DATE - INTERVAL '60 days')
    AND dd.data <  (CURRENT_DATE - INTERVAL '30 days')
  GROUP BY ft.client_id, ft.cliente_id
),
clientes_com_30d AS (
  SELECT c.*,
         COALESCE(t30.receita_30_dias, 0) AS receita_30_dias,
         COALESCE(t30.quantidade_30_dias, 0) AS quantidade_30_dias,
         COALESCE(t30.pedidos_30_dias, 0) AS pedidos_30_dias,
         COALESCE(ta.receita_anterior, 0) AS receita_anterior,
         COALESCE(ta.quantidade_anterior, 0) AS quantidade_anterior,
         COALESCE(ta.pedidos_anterior, 0) AS pedidos_anterior
  FROM analytics_v2.dim_clientes c
  LEFT JOIN transacoes_30_dias    t30 ON c.cliente_id = t30.cliente_id AND c.client_id = t30.client_id
  LEFT JOIN transacoes_anteriores ta  ON c.cliente_id = ta.cliente_id  AND c.client_id = ta.client_id
)
SELECT client_id,
  COUNT(*) AS total_clientes,
  COALESCE(SUM(receita_total), 0) AS receita_total,
  COALESCE(SUM(quantidade_total), 0) AS quantidade_total,
  COALESCE(AVG(ticket_medio), 0) AS ticket_medio_geral,
  COALESCE(AVG(frequencia_mensal), 0) AS frequencia_media,
  COALESCE(AVG(dias_recencia), 0)::integer AS recencia_media_dias,
  COUNT(*) FILTER (WHERE dias_recencia <= 90) AS clientes_ativos,
  COUNT(*) FILTER (WHERE total_pedidos = 1)    AS clientes_novos,
  COUNT(*) FILTER (WHERE dias_recencia <= 30)  AS novos_ultimos_30_dias,
  COALESCE(SUM(receita_30_dias), 0) AS receita_30_dias,
  COALESCE(SUM(quantidade_30_dias), 0) AS quantidade_30_dias,
  COALESCE(SUM(pedidos_30_dias), 0)::numeric AS pedidos_30_dias,
  COUNT(*) FILTER (WHERE receita_30_dias > 0) AS clientes_ativos_30_dias,
  CASE WHEN COALESCE(SUM(receita_anterior), 0)    > 0 THEN ROUND((SUM(receita_30_dias)    - SUM(receita_anterior))    / SUM(receita_anterior)    * 100, 2) END AS crescimento_receita,
  CASE WHEN COALESCE(SUM(quantidade_anterior), 0) > 0 THEN ROUND((SUM(quantidade_30_dias) - SUM(quantidade_anterior)) / SUM(quantidade_anterior) * 100, 2) END AS crescimento_quantidade,
  CASE WHEN COALESCE(SUM(pedidos_anterior), 0)    > 0 THEN ROUND((SUM(pedidos_30_dias)    - SUM(pedidos_anterior))    / SUM(pedidos_anterior)    * 100, 2) END AS crescimento_pedidos,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='A') AS tier_a_count,
  COALESCE(SUM(receita_total)     FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_receita,
  COALESCE(SUM(quantidade_total)  FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_quantidade,
  COALESCE(AVG(ticket_medio)      FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_ticket_medio,
  COALESCE(SUM(receita_30_dias)   FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_receita_30_dias,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='B') AS tier_b_count,
  COALESCE(SUM(receita_total)     FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_receita,
  COALESCE(SUM(quantidade_total)  FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_quantidade,
  COALESCE(AVG(ticket_medio)      FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_ticket_medio,
  COALESCE(SUM(receita_30_dias)   FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_receita_30_dias,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='C') AS tier_c_count,
  COALESCE(SUM(receita_total)     FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_receita,
  COALESCE(SUM(quantidade_total)  FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_quantidade,
  COALESCE(AVG(ticket_medio)      FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_ticket_medio,
  COALESCE(SUM(receita_30_dias)   FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_receita_30_dias,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='D') AS tier_d_count,
  COALESCE(SUM(receita_total)     FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_receita,
  COALESCE(SUM(quantidade_total)  FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_quantidade,
  COALESCE(AVG(ticket_medio)      FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_ticket_medio,
  COALESCE(SUM(receita_30_dias)   FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_receita_30_dias
FROM clientes_com_30d
GROUP BY client_id;

CREATE UNIQUE INDEX idx_mv_resumo_clientes_client
  ON analytics_v2.mv_resumo_clientes(client_id);

-- mv_resumo_fornecedores (ft.inventory_id → ft.produto_id)
CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_fornecedores AS
WITH transacoes_30_dias AS (
  SELECT ft.client_id, ft.fornecedor_id,
         SUM(ft.valor) AS receita_30_dias,
         SUM(ft.quantidade) AS quantidade_30_dias,
         COUNT(DISTINCT ft.documento)   AS pedidos_30_dias,
         COUNT(DISTINCT ft.produto_id)  AS produtos_30_dias
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= (CURRENT_DATE - INTERVAL '30 days')
  GROUP BY ft.client_id, ft.fornecedor_id
),
transacoes_anteriores AS (
  SELECT ft.client_id, ft.fornecedor_id,
         SUM(ft.valor) AS receita_anterior,
         SUM(ft.quantidade) AS quantidade_anterior,
         COUNT(DISTINCT ft.documento) AS pedidos_anterior
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= (CURRENT_DATE - INTERVAL '60 days')
    AND dd.data <  (CURRENT_DATE - INTERVAL '30 days')
  GROUP BY ft.client_id, ft.fornecedor_id
),
fornecedores_com_30d AS (
  SELECT f.*,
         COALESCE(t30.receita_30_dias, 0) AS receita_30_dias,
         COALESCE(t30.quantidade_30_dias, 0) AS quantidade_30_dias,
         COALESCE(t30.pedidos_30_dias, 0) AS pedidos_30_dias,
         COALESCE(t30.produtos_30_dias, 0) AS produtos_30_dias,
         COALESCE(ta.receita_anterior, 0)    AS receita_anterior,
         COALESCE(ta.quantidade_anterior, 0) AS quantidade_anterior,
         COALESCE(ta.pedidos_anterior, 0)    AS pedidos_anterior
  FROM analytics_v2.dim_fornecedores f
  LEFT JOIN transacoes_30_dias    t30 ON f.fornecedor_id = t30.fornecedor_id AND f.client_id = t30.client_id
  LEFT JOIN transacoes_anteriores ta  ON f.fornecedor_id = ta.fornecedor_id  AND f.client_id = ta.client_id
)
SELECT client_id,
  COUNT(*) AS total_fornecedores,
  COALESCE(SUM(receita_total), 0) AS receita_total,
  COALESCE(SUM(total_produtos_fornecidos), 0) AS total_produtos_fornecidos,
  COALESCE(AVG(ticket_medio), 0) AS ticket_medio_geral,
  COALESCE(AVG(frequencia_mensal), 0) AS frequencia_media,
  COALESCE(AVG(dias_recencia), 0)::integer AS recencia_media_dias,
  COUNT(*) FILTER (WHERE dias_recencia <= 30) AS novos_ultimos_30_dias,
  COALESCE(SUM(receita_30_dias), 0)     AS receita_30_dias,
  COALESCE(SUM(quantidade_30_dias), 0)  AS quantidade_30_dias,
  COALESCE(SUM(pedidos_30_dias), 0)::numeric  AS pedidos_30_dias,
  COALESCE(SUM(produtos_30_dias), 0)::numeric AS produtos_30_dias,
  COUNT(*) FILTER (WHERE receita_30_dias > 0) AS fornecedores_ativos_30_dias,
  CASE WHEN COALESCE(SUM(receita_anterior), 0)    > 0 THEN ROUND((SUM(receita_30_dias)    - SUM(receita_anterior))    / SUM(receita_anterior)    * 100, 2) END AS crescimento_receita,
  CASE WHEN COALESCE(SUM(quantidade_anterior), 0) > 0 THEN ROUND((SUM(quantidade_30_dias) - SUM(quantidade_anterior)) / SUM(quantidade_anterior) * 100, 2) END AS crescimento_quantidade,
  CASE WHEN COALESCE(SUM(pedidos_anterior), 0)    > 0 THEN ROUND((SUM(pedidos_30_dias)    - SUM(pedidos_anterior))    / SUM(pedidos_anterior)    * 100, 2) END AS crescimento_pedidos,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='A') AS tier_a_count,
  COALESCE(SUM(receita_total)              FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_receita,
  COALESCE(SUM(total_produtos_fornecidos)  FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_produtos,
  COALESCE(AVG(ticket_medio)               FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_ticket_medio,
  COALESCE(SUM(receita_30_dias)            FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_receita_30_dias,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='B') AS tier_b_count,
  COALESCE(SUM(receita_total)              FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_receita,
  COALESCE(SUM(total_produtos_fornecidos)  FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_produtos,
  COALESCE(AVG(ticket_medio)               FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_ticket_medio,
  COALESCE(SUM(receita_30_dias)            FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_receita_30_dias,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='C') AS tier_c_count,
  COALESCE(SUM(receita_total)              FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_receita,
  COALESCE(SUM(total_produtos_fornecidos)  FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_produtos,
  COALESCE(AVG(ticket_medio)               FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_ticket_medio,
  COALESCE(SUM(receita_30_dias)            FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_receita_30_dias,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='D') AS tier_d_count,
  COALESCE(SUM(receita_total)              FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_receita,
  COALESCE(SUM(total_produtos_fornecidos)  FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_produtos,
  COALESCE(AVG(ticket_medio)               FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_ticket_medio,
  COALESCE(SUM(receita_30_dias)            FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_receita_30_dias
FROM fornecedores_com_30d
GROUP BY client_id;

CREATE UNIQUE INDEX idx_mv_resumo_fornecedores_client
  ON analytics_v2.mv_resumo_fornecedores(client_id);

-- mv_resumo_produtos (ft.inventory_id → ft.produto_id; join to dim_inventory unchanged)
CREATE MATERIALIZED VIEW analytics_v2.mv_resumo_produtos AS
WITH transacoes_30_dias AS (
  SELECT ft.client_id, ft.produto_id AS inventory_id,
         SUM(ft.valor) AS receita_30_dias,
         SUM(ft.quantidade) AS quantidade_30_dias,
         COUNT(DISTINCT ft.documento) AS pedidos_30_dias
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= (CURRENT_DATE - INTERVAL '30 days')
  GROUP BY ft.client_id, ft.produto_id
),
transacoes_anteriores AS (
  SELECT ft.client_id, ft.produto_id AS inventory_id,
         SUM(ft.valor) AS receita_anterior,
         SUM(ft.quantidade) AS quantidade_anterior,
         COUNT(DISTINCT ft.documento) AS pedidos_anterior
  FROM analytics_v2.fato_transacoes ft
  JOIN analytics_v2.dim_datas dd ON ft.data_competencia_id = dd.data_id
  WHERE dd.data >= (CURRENT_DATE - INTERVAL '60 days')
    AND dd.data <  (CURRENT_DATE - INTERVAL '30 days')
  GROUP BY ft.client_id, ft.produto_id
),
produtos_com_30d AS (
  SELECT p.*,
         COALESCE(t30.receita_30_dias, 0)    AS receita_30_dias,
         COALESCE(t30.quantidade_30_dias, 0) AS quantidade_30_dias,
         COALESCE(t30.pedidos_30_dias, 0)    AS pedidos_30_dias,
         COALESCE(ta.receita_anterior, 0)    AS receita_anterior,
         COALESCE(ta.quantidade_anterior, 0) AS quantidade_anterior,
         COALESCE(ta.pedidos_anterior, 0)    AS pedidos_anterior
  FROM analytics_v2.dim_inventory p
  LEFT JOIN transacoes_30_dias    t30 ON p.inventory_id = t30.inventory_id AND p.client_id = t30.client_id
  LEFT JOIN transacoes_anteriores ta  ON p.inventory_id = ta.inventory_id  AND p.client_id = ta.client_id
)
SELECT client_id,
  COUNT(*) AS total_produtos,
  COALESCE(SUM(receita_total), 0) AS receita_total,
  COALESCE(SUM(quantidade_total_vendida), 0) AS quantidade_total,
  CASE WHEN SUM(quantidade_total_vendida) > 0 THEN (SUM(receita_total) / SUM(quantidade_total_vendida))::numeric(15,2) ELSE 0 END AS ticket_medio,
  COALESCE(AVG(frequencia_mensal), 0) AS frequencia_media,
  COALESCE(AVG(dias_recencia), 0)::integer AS recencia_media_dias,
  COALESCE(SUM(receita_30_dias), 0)    AS receita_30_dias,
  COALESCE(SUM(quantidade_30_dias), 0) AS quantidade_30_dias,
  COALESCE(SUM(pedidos_30_dias), 0)::numeric AS pedidos_30_dias,
  COUNT(*) FILTER (WHERE receita_30_dias > 0) AS produtos_ativos_30_dias,
  CASE WHEN SUM(quantidade_30_dias) > 0 THEN (SUM(receita_30_dias) / SUM(quantidade_30_dias))::numeric(15,2) ELSE 0 END AS ticket_medio_30_dias,
  CASE WHEN COALESCE(SUM(receita_anterior), 0)    > 0 THEN ROUND((SUM(receita_30_dias)    - SUM(receita_anterior))    / SUM(receita_anterior)    * 100, 2) END AS crescimento_receita,
  CASE WHEN COALESCE(SUM(quantidade_anterior), 0) > 0 THEN ROUND((SUM(quantidade_30_dias) - SUM(quantidade_anterior)) / SUM(quantidade_anterior) * 100, 2) END AS crescimento_quantidade,
  CASE WHEN COALESCE(SUM(pedidos_anterior), 0)    > 0 THEN ROUND((SUM(pedidos_30_dias)    - SUM(pedidos_anterior))    / SUM(pedidos_anterior)    * 100, 2) END AS crescimento_pedidos,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='A') AS tier_a_count,
  COALESCE(SUM(receita_total)             FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_receita,
  COALESCE(SUM(quantidade_total_vendida)  FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_quantidade,
  CASE WHEN SUM(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster::text)='A') > 0 THEN (SUM(receita_total) FILTER (WHERE upper(nivel_cluster::text)='A') / SUM(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster::text)='A'))::numeric(15,2) ELSE 0 END AS tier_a_ticket_medio,
  COALESCE(SUM(receita_30_dias)           FILTER (WHERE upper(nivel_cluster::text)='A'), 0) AS tier_a_receita_30_dias,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='B') AS tier_b_count,
  COALESCE(SUM(receita_total)             FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_receita,
  COALESCE(SUM(quantidade_total_vendida)  FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_quantidade,
  CASE WHEN SUM(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster::text)='B') > 0 THEN (SUM(receita_total) FILTER (WHERE upper(nivel_cluster::text)='B') / SUM(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster::text)='B'))::numeric(15,2) ELSE 0 END AS tier_b_ticket_medio,
  COALESCE(SUM(receita_30_dias)           FILTER (WHERE upper(nivel_cluster::text)='B'), 0) AS tier_b_receita_30_dias,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='C') AS tier_c_count,
  COALESCE(SUM(receita_total)             FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_receita,
  COALESCE(SUM(quantidade_total_vendida)  FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_quantidade,
  CASE WHEN SUM(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster::text)='C') > 0 THEN (SUM(receita_total) FILTER (WHERE upper(nivel_cluster::text)='C') / SUM(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster::text)='C'))::numeric(15,2) ELSE 0 END AS tier_c_ticket_medio,
  COALESCE(SUM(receita_30_dias)           FILTER (WHERE upper(nivel_cluster::text)='C'), 0) AS tier_c_receita_30_dias,
  COUNT(*) FILTER (WHERE upper(nivel_cluster::text)='D') AS tier_d_count,
  COALESCE(SUM(receita_total)             FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_receita,
  COALESCE(SUM(quantidade_total_vendida)  FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_quantidade,
  CASE WHEN SUM(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster::text)='D') > 0 THEN (SUM(receita_total) FILTER (WHERE upper(nivel_cluster::text)='D') / SUM(quantidade_total_vendida) FILTER (WHERE upper(nivel_cluster::text)='D'))::numeric(15,2) ELSE 0 END AS tier_d_ticket_medio,
  COALESCE(SUM(receita_30_dias)           FILTER (WHERE upper(nivel_cluster::text)='D'), 0) AS tier_d_receita_30_dias
FROM produtos_com_30d
GROUP BY client_id;

CREATE UNIQUE INDEX idx_mv_resumo_produtos_client
  ON analytics_v2.mv_resumo_produtos(client_id);

-- ── 8. Recreate client-facing views over the MVs ─────────────────────
CREATE OR REPLACE VIEW analytics_v2.v_resumo_dashboard
  WITH (security_invoker = true) AS
SELECT * FROM analytics_v2.mv_resumo_dashboard;

CREATE OR REPLACE VIEW analytics_v2.v_series_temporal
  WITH (security_invoker = true) AS
SELECT client_id, tipo_grafico, dimensao, periodo, data_periodo, total
FROM analytics_v2.mv_series_temporal
WHERE client_id = public.get_my_client_id();

CREATE OR REPLACE VIEW analytics_v2.v_distribuicao_regional
  WITH (security_invoker = true) AS
SELECT client_id, tipo_grafico, dimensao, estado, regiao, total, percentual
FROM analytics_v2.mv_distribuicao_regional
WHERE client_id = public.get_my_client_id();

CREATE OR REPLACE VIEW analytics_v2.v_ultimos_pedidos
  WITH (security_invoker = true) AS
WITH my_cid AS (SELECT public.get_my_client_id() AS cid)
SELECT ft.client_id,
       ft.documento                                 AS pedido_id,
       dd.data                                      AS data_transacao,
       dc.cpf_cnpj                                  AS cliente_cpf_cnpj,
       dc.nome                                      AS cliente_nome,
       SUM(ft.valor)::text                          AS valor_pedido,
       COUNT(*)                                     AS qtd_produtos,
       ROW_NUMBER() OVER (ORDER BY dd.data DESC, ft.documento DESC) AS ordem
FROM analytics_v2.fato_transacoes ft
JOIN analytics_v2.dim_datas    dd ON dd.data_id    = ft.data_competencia_id
LEFT JOIN analytics_v2.dim_clientes dc ON dc.cliente_id = ft.cliente_id
CROSS JOIN my_cid m
WHERE ft.client_id = m.cid
GROUP BY ft.client_id, ft.documento, dd.data, dc.cpf_cnpj, dc.nome;

GRANT SELECT ON analytics_v2.v_resumo_dashboard       TO authenticated;
GRANT SELECT ON analytics_v2.v_series_temporal        TO authenticated;
GRANT SELECT ON analytics_v2.v_distribuicao_regional  TO authenticated;
GRANT SELECT ON analytics_v2.v_ultimos_pedidos        TO authenticated;
GRANT SELECT ON analytics_v2.mv_resumo_clientes       TO authenticated;
GRANT SELECT ON analytics_v2.mv_resumo_fornecedores   TO authenticated;
GRANT SELECT ON analytics_v2.mv_resumo_produtos       TO authenticated;

COMMIT;
