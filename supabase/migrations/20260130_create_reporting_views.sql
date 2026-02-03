-- ============================================================================
-- Create Reporting Views for Analytics V2
-- These views compute data from fact_sales and dimension tables
-- Date: 2026-01-30
-- ============================================================================

-- Drop existing materialized views or tables
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.v_time_series CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.v_regional CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.v_last_orders CASCADE;
DROP MATERIALIZED VIEW IF EXISTS analytics_v2.v_customer_products CASCADE;

-- Also drop if they were created as regular tables
DROP TABLE IF EXISTS analytics_v2.v_time_series CASCADE;
DROP TABLE IF EXISTS analytics_v2.v_regional CASCADE;
DROP TABLE IF EXISTS analytics_v2.v_last_orders CASCADE;
DROP TABLE IF EXISTS analytics_v2.v_customer_products CASCADE;

-- ============================================================================
-- 1. v_time_series - Monthly aggregates by chart_type
-- ============================================================================
CREATE OR REPLACE VIEW analytics_v2.v_time_series AS
-- Fornecedores no tempo (unique suppliers per month)
SELECT 
    f.client_id,
    'fornecedores_no_tempo' as chart_type,
    'suppliers' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COUNT(DISTINCT f.supplier_cnpj) as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE

UNION ALL

-- Clientes no tempo (unique customers per month)
SELECT 
    f.client_id,
    'clientes_no_tempo' as chart_type,
    'customers' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COUNT(DISTINCT f.customer_cpf_cnpj) as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE

UNION ALL

-- Produtos no tempo (unique products per month)
SELECT 
    f.client_id,
    'produtos_no_tempo' as chart_type,
    'products' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COUNT(DISTINCT f.product_id) as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE

UNION ALL

-- Pedidos no tempo (unique orders per month)
SELECT 
    f.client_id,
    'pedidos_no_tempo' as chart_type,
    'orders' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COUNT(DISTINCT f.order_id) as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE

UNION ALL

-- Receita no tempo (total revenue per month)
SELECT 
    f.client_id,
    'receita_no_tempo' as chart_type,
    'revenue' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COALESCE(SUM(f.valor_total), 0)::BIGINT as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE

UNION ALL

-- Receita fornecedores no tempo
SELECT 
    f.client_id,
    'receita_fornecedores_no_tempo' as chart_type,
    'supplier_revenue' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COALESCE(SUM(f.valor_total), 0)::BIGINT as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE

UNION ALL

-- Receita clientes no tempo
SELECT 
    f.client_id,
    'receita_clientes_no_tempo' as chart_type,
    'customer_revenue' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COALESCE(SUM(f.valor_total), 0)::BIGINT as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE

UNION ALL

-- Ticket médio fornecedores no tempo
SELECT 
    f.client_id,
    'ticket_medio_fornecedores_no_tempo' as chart_type,
    'supplier_avg_ticket' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COALESCE(AVG(f.valor_total), 0)::BIGINT as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE

UNION ALL

-- Ticket médio clientes no tempo
SELECT 
    f.client_id,
    'ticket_medio_clientes_no_tempo' as chart_type,
    'customer_avg_ticket' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COALESCE(AVG(f.valor_total), 0)::BIGINT as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE

UNION ALL

-- Quantidade fornecedores no tempo
SELECT 
    f.client_id,
    'quantidade_fornecedores_no_tempo' as chart_type,
    'supplier_quantity' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COALESCE(SUM(f.quantidade), 0)::BIGINT as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE

UNION ALL

-- Quantidade clientes no tempo
SELECT 
    f.client_id,
    'quantidade_clientes_no_tempo' as chart_type,
    'customer_quantity' as dimension,
    TO_CHAR(f.data_transacao, 'YYYY-MM') as period,
    DATE_TRUNC('month', f.data_transacao)::DATE as period_date,
    COALESCE(SUM(f.quantidade), 0)::BIGINT as total
FROM analytics_v2.fact_sales f
WHERE f.data_transacao IS NOT NULL
GROUP BY f.client_id, TO_CHAR(f.data_transacao, 'YYYY-MM'), DATE_TRUNC('month', f.data_transacao)::DATE;

-- ============================================================================
-- 2. v_regional - Geographic breakdown
-- ============================================================================
CREATE OR REPLACE VIEW analytics_v2.v_regional AS
WITH regional_totals AS (
    SELECT 
        f.client_id,
        COALESCE(c.endereco_uf, 'Não informado') as region_name,
        COUNT(DISTINCT f.order_id) as total,
        COUNT(DISTINCT f.order_id) as contagem
    FROM analytics_v2.fact_sales f
    LEFT JOIN analytics_v2.dim_customer c 
        ON f.customer_cpf_cnpj = c.cpf_cnpj AND f.client_id::TEXT = c.client_id::TEXT
    GROUP BY f.client_id, COALESCE(c.endereco_uf, 'Não informado')
),
client_totals AS (
    SELECT client_id, SUM(total) as grand_total
    FROM regional_totals
    GROUP BY client_id
)
-- Fornecedores por região
SELECT 
    rt.client_id,
    'fornecedores_por_regiao' as chart_type,
    'suppliers' as dimension,
    rt.region_name,
    'state' as region_type,
    rt.total,
    rt.contagem,
    CASE WHEN ct.grand_total > 0 THEN (rt.total::DECIMAL / ct.grand_total * 100) ELSE 0 END as percentual
FROM regional_totals rt
JOIN client_totals ct ON rt.client_id = ct.client_id

UNION ALL

-- Clientes por região
SELECT 
    rt.client_id,
    'clientes_por_regiao' as chart_type,
    'customers' as dimension,
    rt.region_name,
    'state' as region_type,
    rt.total,
    rt.contagem,
    CASE WHEN ct.grand_total > 0 THEN (rt.total::DECIMAL / ct.grand_total * 100) ELSE 0 END as percentual
FROM regional_totals rt
JOIN client_totals ct ON rt.client_id = ct.client_id;

-- ============================================================================
-- 3. v_last_orders - Recent orders
-- ============================================================================
CREATE OR REPLACE VIEW analytics_v2.v_last_orders AS
WITH order_summary AS (
    SELECT 
        f.client_id,
        f.order_id,
        f.data_transacao,
        f.customer_cpf_cnpj,
        MAX(c.name) as customer_name,
        SUM(f.valor_total) as ticket_pedido,
        COUNT(*) as qtd_produtos,
        ROW_NUMBER() OVER (PARTITION BY f.client_id ORDER BY f.data_transacao DESC, f.order_id DESC) as order_rank
    FROM analytics_v2.fact_sales f
    LEFT JOIN analytics_v2.dim_customer c 
        ON f.customer_cpf_cnpj = c.cpf_cnpj AND f.client_id::TEXT = c.client_id::TEXT
    WHERE f.data_transacao IS NOT NULL
    GROUP BY f.client_id, f.order_id, f.data_transacao, f.customer_cpf_cnpj
)
SELECT 
    client_id,
    order_id,
    data_transacao,
    customer_cpf_cnpj,
    customer_name,
    ticket_pedido,
    qtd_produtos,
    order_rank
FROM order_summary
WHERE order_rank <= 100;  -- Limit to last 100 orders per client

-- ============================================================================
-- 4. v_customer_products - Customer-Product relationships
-- ============================================================================
CREATE OR REPLACE VIEW analytics_v2.v_customer_products AS
SELECT 
    f.client_id,
    f.customer_cpf_cnpj,
    c.name as customer_name,
    p.product_name,
    SUM(f.quantidade) as quantidade_total,
    SUM(f.valor_total) as valor_total,
    COUNT(DISTINCT f.order_id) as num_purchases,
    MAX(f.data_transacao) as last_purchase
FROM analytics_v2.fact_sales f
LEFT JOIN analytics_v2.dim_customer c 
    ON f.customer_cpf_cnpj = c.cpf_cnpj AND f.client_id::TEXT = c.client_id::TEXT
LEFT JOIN analytics_v2.dim_product p 
    ON f.product_id = p.product_id AND f.client_id::TEXT = p.client_id::TEXT
WHERE f.customer_cpf_cnpj IS NOT NULL 
  AND f.product_id IS NOT NULL
GROUP BY f.client_id, f.customer_cpf_cnpj, c.name, p.product_name;

-- ============================================================================
-- Grant permissions
-- ============================================================================
GRANT SELECT ON analytics_v2.v_time_series TO authenticated;
GRANT SELECT ON analytics_v2.v_regional TO authenticated;
GRANT SELECT ON analytics_v2.v_last_orders TO authenticated;
GRANT SELECT ON analytics_v2.v_customer_products TO authenticated;

GRANT SELECT ON analytics_v2.v_time_series TO service_role;
GRANT SELECT ON analytics_v2.v_regional TO service_role;
GRANT SELECT ON analytics_v2.v_last_orders TO service_role;
GRANT SELECT ON analytics_v2.v_customer_products TO service_role;

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON VIEW analytics_v2.v_time_series IS 'Time-series aggregates computed from fact_sales';
COMMENT ON VIEW analytics_v2.v_regional IS 'Regional breakdown computed from fact_sales + dim_customer';
COMMENT ON VIEW analytics_v2.v_last_orders IS 'Last orders computed from fact_sales';
COMMENT ON VIEW analytics_v2.v_customer_products IS 'Customer-product relationships from fact_sales';
