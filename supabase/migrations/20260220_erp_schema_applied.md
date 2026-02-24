# ERP Schema Migrations — Applied via Supabase MCP

The following migrations were applied in sequence to implement the ERP API layer.

## Migrations Applied

| Name | Description |
|------|-------------|
| `erp_schema_phase1_columns` | Added ERP-standard columns to `dim_customer`, `dim_supplier`, `dim_product`, `fact_sales` |
| `erp_schema_phase2_views_v2` | Created 11 ERP views (erp_customers, erp_suppliers, erp_products, erp_orders, etc.) |
| `erp_schema_phase3_search_functions` | Created 3 search RPC functions (erp_search, erp_customer_lookup, erp_supplier_lookup) |
| `erp_schema_phase4_new_tables` | Created 6 new tables (erp_jobs, erp_inventory, erp_inventory_movements, erp_purchase_orders, erp_purchase_order_items, erp_webhook_events) |
| `erp_schema_phase5_write_functions` | Created 10 write RPC functions (erp_create_customer, erp_create_order, erp_inventory_adjust, etc.) |
| `erp_schema_phase6_grants` | Granted permissions to authenticated and service_role |

## Objects Created

### Views (11)
- `analytics_v2.erp_customers` - Customer list with computed metrics
- `analytics_v2.erp_customer_detail` - Same as erp_customers
- `analytics_v2.erp_suppliers` - Supplier list with computed metrics
- `analytics_v2.erp_supplier_detail` - Same as erp_suppliers
- `analytics_v2.erp_products` - Product list with computed metrics
- `analytics_v2.erp_product_detail` - Same as erp_products
- `analytics_v2.erp_orders` - Order headers aggregated from fact_sales
- `analytics_v2.erp_order_items` - Order line items
- `analytics_v2.erp_transactions` - Fully denormalized transactions
- `analytics_v2.erp_dashboard_summary` - Quick summary metrics
- `analytics_v2.erp_recent_orders` - Last 50 orders

### Tables (6)
- `analytics_v2.erp_jobs` - Async job tracking
- `analytics_v2.erp_inventory` - Current inventory levels
- `analytics_v2.erp_inventory_movements` - Inventory movement history
- `analytics_v2.erp_purchase_orders` - Purchase order headers
- `analytics_v2.erp_purchase_order_items` - Purchase order line items
- `analytics_v2.erp_webhook_events` - Outbound webhook queue

### Functions (13)
**Search:**
- `erp_search(p_query, p_entity_types, p_limit)` - Universal search
- `erp_customer_lookup(p_cpf_cnpj, p_name, p_telefone)` - Customer lookup
- `erp_supplier_lookup(p_cnpj, p_name)` - Supplier lookup

**Write:**
- `erp_create_customer(...)` - Create customer
- `erp_update_customer(...)` - Update customer
- `erp_create_product(...)` - Create product
- `erp_create_supplier(...)` - Create supplier
- `erp_create_order(p_customer_id, p_order_id, p_items)` - Create order with items
- `erp_inventory_adjust(...)` - Adjust inventory with movement tracking
- `erp_create_purchase_order(...)` - Create purchase order
- `erp_receive_purchase_order(...)` - Receive items against PO
- `erp_create_job(...)` - Create async job
- `erp_update_job(...)` - Update job status

## Multi-tenancy

All views and functions use `current_setting('app.current_cliente_id', true)` for RLS.
Tables have RLS policies with `client_id` isolation.

## Frontend Service

See `apps/vizu_dashboard/src/services/erpService.ts` for typed Supabase SDK calls.
