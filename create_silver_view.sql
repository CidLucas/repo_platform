-- Create a VIEW that maps BigQuery foreign table columns to canonical schema
-- This VIEW sits between the foreign table and the analytics API
-- Replace 'e0e9c949_18fe_4d9a_9295_d5dfb2cc9723' with your actual client_id

-- First, drop the view if it exists
DROP VIEW IF EXISTS bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_silver_mapped;

-- Create the mapped view
CREATE VIEW bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_silver_mapped AS
SELECT
    -- Order/Invoice identification
    id_product::text AS order_id,

    -- Date fields - map createdat_product to data_transacao
    createdat_product::timestamp AS data_transacao,

    -- Product description
    description_product::text AS raw_product_description,

    -- Quantities and prices
    COALESCE(quantitytraded_product, 0)::numeric AS quantidade,
    COALESCE(unitprice_product, 0)::numeric AS valor_unitario,
    COALESCE(totalprice_product, 0)::numeric AS valor_total_emitter,

    -- Status
    COALESCE(status_product, 'unknown')::text AS status,

    -- Additional fields that might be useful
    commercialunit_product::text AS commercial_unit,
    material::text AS material,
    ncm::text AS ncm,
    cfop::text AS cfop,

    -- Keep original column names as backup for debugging
    id_product,
    createdat_product,
    description_product,
    unitprice_product,
    quantitytraded_product,
    totalprice_product,
    status_product

FROM bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_products_invoices;

-- Grant access
GRANT SELECT ON bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_silver_mapped TO anon, authenticated, service_role;

-- Update client_data_sources to point to the new VIEW instead of the foreign table
-- UPDATE client_data_sources
-- SET storage_location = 'bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_silver_mapped'
-- WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723'
--   AND storage_type = 'foreign_table';

COMMENT ON VIEW bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_silver_mapped IS
'Mapped view that translates BigQuery foreign table column names to canonical Vizu schema';
