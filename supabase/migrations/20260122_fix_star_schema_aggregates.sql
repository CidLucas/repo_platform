-- Star Schema Correction: Move Aggregated Metrics to Dimensions
-- Proper star schema: dimensions have aggregates, facts have transactional data

-- ============================================================================
-- STEP 1: Alter Dimension Tables to Include Aggregated Metrics
-- ============================================================================

-- ALTER dim_customer to include order metrics
ALTER TABLE analytics_v2.dim_customer ADD COLUMN IF NOT EXISTS (
    total_orders INTEGER DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    avg_order_value DECIMAL(15,2) DEFAULT 0,
    total_quantity DECIMAL(15,2) DEFAULT 0,
    orders_last_30_days INTEGER DEFAULT 0,
    frequency_per_month DECIMAL(10,2) DEFAULT 0,
    recency_days INTEGER DEFAULT 0,
    lifetime_start_date DATE,
    lifetime_end_date DATE
);

-- ALTER dim_supplier to include sales metrics
ALTER TABLE analytics_v2.dim_supplier ADD COLUMN IF NOT EXISTS (
    total_orders_received INTEGER DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    avg_order_value DECIMAL(15,2) DEFAULT 0,
    total_products_supplied INTEGER DEFAULT 0,
    frequency_per_month DECIMAL(10,2) DEFAULT 0,
    recency_days INTEGER DEFAULT 0,
    first_transaction_date DATE,
    last_transaction_date DATE
);

-- ALTER dim_product to include sales metrics
ALTER TABLE analytics_v2.dim_product ADD COLUMN IF NOT EXISTS (
    total_quantity_sold DECIMAL(15,2) DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    avg_price DECIMAL(15,2) DEFAULT 0,
    number_of_orders INTEGER DEFAULT 0,
    avg_quantity_per_order DECIMAL(10,2) DEFAULT 0,
    frequency_per_month DECIMAL(10,2) DEFAULT 0,
    recency_days INTEGER DEFAULT 0,
    last_sale_date DATE,
    cluster_score DECIMAL(5,2),
    cluster_tier VARCHAR(50)
);

-- ============================================================================
-- STEP 2: Create Proper Transactional Fact Tables
-- ============================================================================

-- fact_sales: Individual order transactions (grain: order_id, line_item_sequence)
CREATE TABLE IF NOT EXISTS analytics_v2.fact_sales (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL,
    order_id VARCHAR(255) NOT NULL,
    line_item_sequence INTEGER NOT NULL, -- Which line in the order (1, 2, 3...)
    order_date DATE,

    -- Customer reference
    customer_cpf_cnpj VARCHAR(20),
    customer_name VARCHAR(255),

    -- Supplier reference
    supplier_cnpj VARCHAR(20),
    supplier_name VARCHAR(255),

    -- Product reference
    product_name VARCHAR(500),

    -- Transaction details (granular)
    quantity DECIMAL(15,2),
    unit_price DECIMAL(15,2),
    line_total DECIMAL(15,2),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_fact_sales_client_id ON analytics_v2.fact_sales(client_id);
CREATE INDEX idx_fact_sales_order_id ON analytics_v2.fact_sales(order_id);
CREATE INDEX idx_fact_sales_order_date ON analytics_v2.fact_sales(order_date);
CREATE INDEX idx_fact_sales_customer ON analytics_v2.fact_sales(customer_cpf_cnpj);
CREATE INDEX idx_fact_sales_product ON analytics_v2.fact_sales(product_name);

-- ============================================================================
-- STEP 3: Create Bridge Tables for Many-to-Many Relationships
-- ============================================================================

-- fact_customer_product: Customer's interaction with each product
CREATE TABLE IF NOT EXISTS analytics_v2.fact_customer_product (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL,
    customer_cpf_cnpj VARCHAR(20) NOT NULL,
    product_name VARCHAR(500) NOT NULL,

    -- Aggregates for this customer-product pair
    quantity_purchased DECIMAL(15,2),
    times_purchased INTEGER,
    total_spent DECIMAL(15,2),
    avg_price_paid DECIMAL(15,2),
    first_purchase_date DATE,
    last_purchase_date DATE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_fact_customer_product_client ON analytics_v2.fact_customer_product(client_id);
CREATE INDEX idx_fact_customer_product_customer ON analytics_v2.fact_customer_product(customer_cpf_cnpj);
CREATE INDEX idx_fact_customer_product_product ON analytics_v2.fact_customer_product(product_name);

-- ============================================================================
-- STEP 4: Materialized Views for Performance
-- ============================================================================

-- Materialized View: Customer Summary (for dashboards)
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_v2.mv_customer_summary AS
SELECT
    c.client_id,
    c.customer_id,
    c.name,
    c.cpf_cnpj,
    c.estado,
    COUNT(DISTINCT f.order_id) as total_orders,
    SUM(f.line_total) as lifetime_value,
    AVG(f.line_total) as avg_order_value,
    SUM(f.quantity) as total_quantity,
    MAX(f.order_date) as last_order_date,
    MIN(f.order_date) as first_order_date,
    EXTRACT(DAY FROM NOW() - MAX(f.order_date)) as days_since_last_order
FROM analytics_v2.dim_customer c
LEFT JOIN analytics_v2.fact_sales f ON c.cpf_cnpj = f.customer_cpf_cnpj AND c.client_id = f.client_id
GROUP BY c.client_id, c.customer_id, c.name, c.cpf_cnpj, c.estado;

CREATE INDEX idx_mv_customer_summary_client ON analytics_v2.mv_customer_summary(client_id);
CREATE INDEX idx_mv_customer_summary_customer ON analytics_v2.mv_customer_summary(customer_id);

-- Materialized View: Product Summary
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_v2.mv_product_summary AS
SELECT
    p.client_id,
    p.product_id,
    p.product_name,
    COUNT(DISTINCT f.order_id) as times_sold,
    SUM(f.quantity) as total_quantity_sold,
    SUM(f.line_total) as total_revenue,
    AVG(f.line_total) as avg_order_value,
    AVG(f.unit_price) as avg_price,
    MIN(f.unit_price) as min_price,
    MAX(f.unit_price) as max_price,
    MAX(f.order_date) as last_sold_date,
    COUNT(DISTINCT f.customer_cpf_cnpj) as unique_customers
FROM analytics_v2.dim_product p
LEFT JOIN analytics_v2.fact_sales f ON p.product_name = f.product_name AND p.client_id = f.client_id
GROUP BY p.client_id, p.product_id, p.product_name;

CREATE INDEX idx_mv_product_summary_client ON analytics_v2.mv_product_summary(client_id);

-- Materialized View: Monthly Sales Trend
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics_v2.mv_monthly_sales_trend AS
SELECT
    f.client_id,
    DATE_TRUNC('month', f.order_date)::DATE as month,
    COUNT(DISTINCT f.order_id) as orders_that_month,
    COUNT(DISTINCT f.customer_cpf_cnpj) as unique_customers_that_month,
    SUM(f.line_total) as revenue_that_month,
    AVG(f.line_total) as avg_order_value_that_month
FROM analytics_v2.fact_sales f
GROUP BY f.client_id, DATE_TRUNC('month', f.order_date)::DATE;

CREATE INDEX idx_mv_monthly_sales_client ON analytics_v2.mv_monthly_sales_trend(client_id);
CREATE INDEX idx_mv_monthly_sales_month ON analytics_v2.mv_monthly_sales_trend(month);

-- ============================================================================
-- STEP 5: Refresh Functions
-- ============================================================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION analytics_v2.refresh_materialized_views()
RETURNS TABLE(view_name TEXT, status TEXT) AS $$
DECLARE
    v_start_time TIMESTAMP;
BEGIN
    v_start_time := NOW();

    -- Refresh mv_customer_summary
    BEGIN
        REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_customer_summary;
        RETURN QUERY SELECT 'mv_customer_summary'::TEXT,
            'Refreshed in ' || (EXTRACT(SECOND FROM NOW() - v_start_time))::TEXT || 's'::TEXT;
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT 'mv_customer_summary'::TEXT, 'Error: ' || SQLERRM::TEXT;
    END;

    -- Refresh mv_product_summary
    BEGIN
        REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_product_summary;
        RETURN QUERY SELECT 'mv_product_summary'::TEXT,
            'Refreshed in ' || (EXTRACT(SECOND FROM NOW() - v_start_time))::TEXT || 's'::TEXT;
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT 'mv_product_summary'::TEXT, 'Error: ' || SQLERRM::TEXT;
    END;

    -- Refresh mv_monthly_sales_trend
    BEGIN
        REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_v2.mv_monthly_sales_trend;
        RETURN QUERY SELECT 'mv_monthly_sales_trend'::TEXT,
            'Refreshed in ' || (EXTRACT(SECOND FROM NOW() - v_start_time))::TEXT || 's'::TEXT;
    EXCEPTION WHEN OTHERS THEN
        RETURN QUERY SELECT 'mv_monthly_sales_trend'::TEXT, 'Error: ' || SQLERRM::TEXT;
    END;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- STEP 6: Update Statistics Trigger
-- ============================================================================

-- Trigger to update dimension aggregates when fact_sales changes
CREATE OR REPLACE FUNCTION analytics_v2.update_customer_metrics_trigger()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE analytics_v2.dim_customer
    SET
        total_orders = (SELECT COUNT(DISTINCT order_id) FROM analytics_v2.fact_sales
                       WHERE customer_cpf_cnpj = NEW.customer_cpf_cnpj AND client_id = NEW.client_id),
        total_revenue = (SELECT SUM(line_total) FROM analytics_v2.fact_sales
                        WHERE customer_cpf_cnpj = NEW.customer_cpf_cnpj AND client_id = NEW.client_id),
        avg_order_value = (SELECT AVG(line_total) FROM analytics_v2.fact_sales
                          WHERE customer_cpf_cnpj = NEW.customer_cpf_cnpj AND client_id = NEW.client_id),
        lifetime_end_date = NEW.order_date,
        updated_at = NOW()
    WHERE cpf_cnpj = NEW.customer_cpf_cnpj AND client_id = NEW.client_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_update_customer_metrics
AFTER INSERT ON analytics_v2.fact_sales
FOR EACH ROW
EXECUTE FUNCTION analytics_v2.update_customer_metrics_trigger();

-- Similar trigger for products
CREATE OR REPLACE FUNCTION analytics_v2.update_product_metrics_trigger()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE analytics_v2.dim_product
    SET
        total_quantity_sold = (SELECT SUM(quantity) FROM analytics_v2.fact_sales
                              WHERE product_name = NEW.product_name AND client_id = NEW.client_id),
        total_revenue = (SELECT SUM(line_total) FROM analytics_v2.fact_sales
                        WHERE product_name = NEW.product_name AND client_id = NEW.client_id),
        number_of_orders = (SELECT COUNT(DISTINCT order_id) FROM analytics_v2.fact_sales
                           WHERE product_name = NEW.product_name AND client_id = NEW.client_id),
        last_sale_date = NEW.order_date,
        updated_at = NOW()
    WHERE product_name = NEW.product_name AND client_id = NEW.client_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_update_product_metrics
AFTER INSERT ON analytics_v2.fact_sales
FOR EACH ROW
EXECUTE FUNCTION analytics_v2.update_product_metrics_trigger();
