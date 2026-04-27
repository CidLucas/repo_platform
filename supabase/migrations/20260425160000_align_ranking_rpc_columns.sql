-- Align RPC return-column names with frontend `toSimpleRanking` mapper
-- (analyticsService.ts expects `nome` / `receita_total`; existing RPCs returned
-- `name` / `total`, so detail-modal rankings rendered empty rows).
-- Standardizes on (nome, receita_total, percentual) — same shape as
-- get_supplier_top_clients which already uses (nome, receita_total).
-- RETURNS TABLE column rename requires DROP+CREATE.

BEGIN;

SET LOCAL statement_timeout = '2min';

DROP FUNCTION IF EXISTS analytics_v2.get_client_top_products(text);
DROP FUNCTION IF EXISTS analytics_v2.get_product_top_clients(text);
DROP FUNCTION IF EXISTS analytics_v2.get_product_top_regions(text);
DROP FUNCTION IF EXISTS analytics_v2.get_supplier_top_products(text);

CREATE FUNCTION analytics_v2.get_client_top_products(p_client_name text)
RETURNS TABLE(nome text, receita_total numeric, percentual numeric)
LANGUAGE sql STABLE
SET search_path = analytics_v2, public
AS $$
    WITH vendas AS (
        SELECT di.nome, SUM(ft.valor) AS total
        FROM analytics_v2.fato_transacoes ft
        JOIN analytics_v2.dim_clientes  dc ON ft.cliente_id = dc.cliente_id
        JOIN analytics_v2.dim_inventory di ON ft.produto_id = di.inventory_id
        WHERE dc.nome ILIKE '%' || p_client_name || '%'
          AND ft.client_id = public.get_my_client_id()
        GROUP BY di.nome
    ),
    total AS (SELECT NULLIF(SUM(total), 0) AS grand FROM vendas)
    SELECT v.nome,
           v.total                                  AS receita_total,
           ROUND((v.total / t.grand) * 100, 2)      AS percentual
    FROM vendas v CROSS JOIN total t
    ORDER BY v.total DESC
    LIMIT 10;
$$;

CREATE FUNCTION analytics_v2.get_product_top_clients(p_product_name text)
RETURNS TABLE(nome text, receita_total numeric, percentual numeric)
LANGUAGE sql STABLE
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
           v.total                                  AS receita_total,
           ROUND((v.total / t.grand) * 100, 2)      AS percentual
    FROM vendas v CROSS JOIN total t
    ORDER BY v.total DESC
    LIMIT 10;
$$;

CREATE FUNCTION analytics_v2.get_product_top_regions(p_product_name text)
RETURNS TABLE(nome text, receita_total numeric, percentual numeric)
LANGUAGE sql STABLE
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
           v.total                                  AS receita_total,
           ROUND((v.total / t.grand) * 100, 2)      AS percentual
    FROM vendas v CROSS JOIN total t
    ORDER BY v.total DESC
    LIMIT 10;
$$;

CREATE FUNCTION analytics_v2.get_supplier_top_products(p_supplier_name text)
RETURNS TABLE(nome text, receita_total numeric, percentual numeric)
LANGUAGE sql STABLE
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
           c.total                                  AS receita_total,
           ROUND((c.total / t.grand) * 100, 2)      AS percentual
    FROM compras c CROSS JOIN total t
    ORDER BY c.total DESC
    LIMIT 10;
$$;

GRANT EXECUTE ON FUNCTION analytics_v2.get_client_top_products(text)   TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION analytics_v2.get_product_top_clients(text)   TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION analytics_v2.get_product_top_regions(text)   TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION analytics_v2.get_supplier_top_products(text) TO authenticated, service_role;

COMMIT;
