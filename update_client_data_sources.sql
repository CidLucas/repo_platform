-- Update client_data_sources to use the mapped VIEW instead of raw foreign table
-- This makes the analytics API query the view with canonical column names

UPDATE client_data_sources
SET
    storage_location = 'bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_silver_mapped',
    updated_at = NOW()
WHERE
    client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723'
    AND storage_type = 'foreign_table'
    AND storage_location = 'bigquery.e0e9c949_18fe_4d9a_9295_d5dfb2cc9723_products_invoices';

-- Verify the update
SELECT
    client_id,
    source_name,
    storage_type,
    storage_location,
    sync_status,
    last_synced_at
FROM client_data_sources
WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
