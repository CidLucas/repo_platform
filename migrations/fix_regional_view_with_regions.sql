-- Migration: Add Brazilian region mapping to v_regional view
-- Replaces region_name (UF) with state (UF) and region (Brazilian region)
-- Date: 2024

-- Drop existing view
DROP VIEW IF EXISTS analytics_v2.v_regional CASCADE;

-- Create improved view with Brazilian region mapping
CREATE OR REPLACE VIEW analytics_v2.v_regional AS
WITH
-- Brazilian state to region mapping
state_to_region AS (
    SELECT * FROM (VALUES
        -- North (Norte)
        ('AC', 'Norte'), ('AM', 'Norte'), ('AP', 'Norte'),
        ('PA', 'Norte'), ('RO', 'Norte'), ('RR', 'Norte'), ('TO', 'Norte'),
        -- Northeast (Nordeste)
        ('AL', 'Nordeste'), ('BA', 'Nordeste'), ('CE', 'Nordeste'),
        ('MA', 'Nordeste'), ('PB', 'Nordeste'), ('PE', 'Nordeste'),
        ('PI', 'Nordeste'), ('RN', 'Nordeste'), ('SE', 'Nordeste'),
        -- Center-West (Centro-Oeste)
        ('DF', 'Centro-Oeste'), ('GO', 'Centro-Oeste'),
        ('MT', 'Centro-Oeste'), ('MS', 'Centro-Oeste'),
        -- Southeast (Sudeste)
        ('ES', 'Sudeste'), ('MG', 'Sudeste'),
        ('RJ', 'Sudeste'), ('SP', 'Sudeste'),
        -- South (Sul)
        ('PR', 'Sul'), ('RS', 'Sul'), ('SC', 'Sul')
    ) AS mapping(state_code, region_name)
),
regional_totals AS (
    SELECT
        f.client_id,
        COALESCE(c.endereco_uf, 'Não informado') AS state,
        COALESCE(sr.region_name, 'Não informado') AS region,
        COUNT(DISTINCT f.order_id) AS total,
        COUNT(DISTINCT f.order_id) AS contagem
    FROM analytics_v2.fact_sales f
    LEFT JOIN analytics_v2.dim_customer c
        ON f.customer_cpf_cnpj = c.cpf_cnpj
        AND f.client_id = c.client_id
    LEFT JOIN state_to_region sr
        ON c.endereco_uf = sr.state_code
    GROUP BY f.client_id, c.endereco_uf, sr.region_name
),
client_totals AS (
    SELECT
        client_id,
        SUM(total) AS grand_total
    FROM regional_totals
    GROUP BY client_id
)
-- Customers by region
SELECT
    rt.client_id,
    'clientes_por_regiao' AS chart_type,
    'customers' AS dimension,
    rt.state,
    rt.region,
    rt.total,
    rt.contagem,
    CASE
        WHEN ct.grand_total > 0
        THEN (rt.total::numeric / ct.grand_total * 100)
        ELSE 0
    END AS percentual
FROM regional_totals rt
JOIN client_totals ct ON rt.client_id = ct.client_id

UNION ALL

-- Suppliers by region (same logic, different chart_type)
SELECT
    rt.client_id,
    'fornecedores_por_regiao' AS chart_type,
    'suppliers' AS dimension,
    rt.state,
    rt.region,
    rt.total,
    rt.contagem,
    CASE
        WHEN ct.grand_total > 0
        THEN (rt.total::numeric / ct.grand_total * 100)
        ELSE 0
    END AS percentual
FROM regional_totals rt
JOIN client_totals ct ON rt.client_id = ct.client_id;

-- Add comment
COMMENT ON VIEW analytics_v2.v_regional IS
'Regional breakdown with Brazilian region mapping (Norte, Nordeste, Centro-Oeste, Sudeste, Sul).
Replaces region_name/region_type with state (UF) and region (geographic region).';
