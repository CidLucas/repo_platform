ERP API Endpoints — Supabase-Native Implementation Plan

Context
The analytics API currently serves dashboard-oriented endpoints via FastAPI.  The ERP API spec (docs/erp-api-spec.md) defines 38 RESTful endpoints (21 read + 17 write) — none exist today.


Approach: Create PostgreSQL views + RLS policies + RPC functions in the database. Supabase PostgREST auto-generates the REST API. Zero new Python endpoint code for reads.

Gap Analysis
Domain	Spec Endpoints	Status
Orders	4 (2 read + 2 write)	Views needed for aggregated data from fact_sales
Purchase Orders	4 (2 read + 2 write)	New tables + views needed
Transactions	2 (1 read + 1 write)	View over fact_sales
Inventory	5 (3 read + 2 write)	New tables + views needed
Customers	7 (5 read + 2 write)	Views over dim_customer + fact_sales
Suppliers	7 (5 read + 2 write)	Views over dim_supplier + fact_sales
Products	3 (3 read)	View over dim_product
Search	1 (read)	RPC function
Jobs	1 (read)	New table
Webhooks	4 (write)	RPC functions
Total	38	All via Supabase — no FastAPI code
How It Works
Read Endpoints → PostgreSQL Views + PostgREST
PostgREST auto-exposes any table or view as a REST endpoint with built-in:

Pagination: ?limit=50&offset=0 (or Range header)
Filtering: ?customer_name=ilike.*maria*&cluster_tier=eq.A
Sorting: ?order=total_revenue.desc
Column selection: ?select=customer_id,name,total_revenue
Full-text search: ?name=plfts.maria
Example: GET https://<project>.supabase.co/rest/v1/erp_customers?limit=50&offset=0&order=total_revenue.desc

Write Endpoints → PostgreSQL RPC Functions
Complex writes (order creation with line items, inventory adjustments) use supabase.rpc('create_order', { payload }) which maps to PostgreSQL functions.

Multi-Tenant Isolation → RLS Policies
All views and tables get RLS policies that filter by client_id extracted from the JWT. The existing set_current_cliente_id() function already supports this pattern.

Frontend Integration
The Supabase client is already imported in the frontend (apps/vizu_dashboard/src/lib/supabase.ts). New ERP calls would use:


// Read: paginated customer list
const { data, count } = await supabase
  .from('erp_customers')
  .select('*', { count: 'exact' })
  .ilike('name', '%maria%')
  .eq('cluster_tier', 'A')
  .order('total_revenue', { ascending: false })
  .range(0, 49)

// Write: create order via RPC
const { data } = await supabase.rpc('erp_create_order', {
  p_customer_cpf_cnpj: '123.456.789-00',
  p_items: [{ product_name: 'Widget A', quantity: 10, unit_price: 50 }]
})
Existing dashboard endpoints (Axios → FastAPI) remain unchanged.

Implementation Phases
Phase 1: RLS Setup + Customer/Supplier/Product Views
SQL Migration — Views for READ endpoints:


-- 1. Customers list view (GET /api/customers)
CREATE OR REPLACE VIEW erp.erp_customers AS
SELECT
  customer_id,
  customer_name AS name,
  customer_cpf_cnpj AS cpf_cnpj,
  telefone,
  endereco_cidade,
  endereco_uf,
  total_orders,
  lifetime_value AS total_revenue,
  avg_order_value,
  quantidade_total AS total_quantity,
  frequencia_pedidos_mes AS frequency_per_month,
  recencia_dias AS recency_days,
  cluster_score,
  cluster_tier,
  primeira_venda AS first_order_date,
  ultima_venda AS last_order_date,
  endereco_rua,
  endereco_numero,
  endereco_bairro,
  endereco_cep,
  created_at,
  updated_at,
  client_id
FROM analytics_v2.dim_customer;

-- 2. Suppliers list view (GET /api/suppliers)
CREATE OR REPLACE VIEW erp.erp_suppliers AS
SELECT
  supplier_id,
  name,
  cnpj,
  telefone,
  endereco_cidade,
  endereco_uf,
  total_orders_received,
  total_revenue,
  avg_order_value,
  total_products_supplied,
  frequencia_pedidos_mes AS frequency_per_month,
  recencia_dias AS recency_days,
  cluster_score,
  cluster_tier,
  first_transaction_date,
  last_transaction_date,
  created_at,
  updated_at,
  client_id
FROM analytics_v2.dim_supplier;

-- 3. Products list view (GET /api/products)
CREATE OR REPLACE VIEW erp.erp_products AS
SELECT
  product_id,
  product_name,
  categoria,
  ncm,
  cfop,
  total_quantity_sold,
  total_revenue,
  avg_price,
  num_pedidos_unicos AS number_of_orders,
  qtd_media_por_pedido AS avg_quantity_per_order,
  frequencia_pedidos_mes AS frequency_per_month,
  recencia_dias AS recency_days,
  ultima_venda AS last_sale_date,
  cluster_score,
  cluster_tier,
  created_at,
  updated_at,
  client_id
FROM analytics_v2.dim_product;
RLS Policies:


-- Enable RLS on all ERP views
ALTER VIEW erp.erp_customers SET (security_invoker = true);
ALTER VIEW erp.erp_suppliers SET (security_invoker = true);
ALTER VIEW erp.erp_products SET (security_invoker = true);

-- RLS on underlying tables (if not already enabled)
ALTER TABLE analytics_v2.dim_customer ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON analytics_v2.dim_customer
  FOR ALL USING (client_id = (current_setting('app.current_cliente_id'))::uuid);

-- Repeat for dim_supplier, dim_product, fact_sales
Frontend service file:

Create apps/vizu_dashboard/src/services/erpService.ts with typed Supabase calls
Files to modify:

apps/vizu_dashboard/src/lib/supabase.ts — already exists, no changes needed
Phase 2: Order/Transaction Views + Cross-Entity Views
SQL Migration — Aggregated order views:


-- 4. Orders list view (aggregated from fact_sales)
CREATE OR REPLACE VIEW erp.erp_orders AS
SELECT
  order_id,
  MIN(data_transacao) AS data_transacao,
  MAX(customer_cpf_cnpj) AS customer_cpf_cnpj,
  MAX(c.customer_name) AS customer_name,
  MAX(supplier_cnpj) AS supplier_cnpj,
  MAX(s.name) AS supplier_name,
  COUNT(*) AS line_count,
  SUM(valor_total) AS order_total,
  f.client_id
FROM analytics_v2.fact_sales f
LEFT JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
LEFT JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
GROUP BY f.order_id, f.client_id;

-- 5. Transactions list view (raw fact_sales)
CREATE OR REPLACE VIEW erp.erp_transactions AS
SELECT
  fact_id,
  order_id,
  line_item_sequence,
  data_transacao,
  customer_cpf_cnpj,
  c.customer_name,
  supplier_cnpj,
  s.name AS supplier_name,
  p.product_name,
  quantidade,
  valor_unitario,
  valor_total,
  f.created_at,
  f.client_id
FROM analytics_v2.fact_sales f
LEFT JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
LEFT JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
LEFT JOIN analytics_v2.dim_product p ON f.product_id = p.product_id;

-- 6. Customer orders view (GET /api/customers/{id}/orders)
CREATE OR REPLACE VIEW erp.erp_customer_orders AS
SELECT
  order_id,
  MIN(data_transacao) AS data_transacao,
  COUNT(*) AS line_count,
  SUM(valor_total) AS order_total,
  MAX(s.name) AS supplier_name,
  f.customer_id,
  f.client_id
FROM analytics_v2.fact_sales f
LEFT JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id
GROUP BY f.order_id, f.customer_id, f.client_id;

-- 7. Customer products view (GET /api/customers/{id}/products)
CREATE OR REPLACE VIEW erp.erp_customer_products AS
SELECT
  f.customer_id,
  f.product_id,
  p.product_name,
  SUM(quantidade) AS total_quantity,
  SUM(valor_total) AS total_spent,
  COUNT(DISTINCT order_id) AS purchase_count,
  MAX(data_transacao) AS last_purchase,
  f.client_id
FROM analytics_v2.fact_sales f
LEFT JOIN analytics_v2.dim_product p ON f.product_id = p.product_id
GROUP BY f.customer_id, f.product_id, p.product_name, f.client_id;

-- 8. Supplier orders view (GET /api/suppliers/{id}/orders)
CREATE OR REPLACE VIEW erp.erp_supplier_orders AS
SELECT
  order_id,
  MIN(data_transacao) AS data_transacao,
  COUNT(*) AS line_count,
  SUM(valor_total) AS order_total,
  MAX(c.customer_name) AS customer_name,
  f.supplier_id,
  f.client_id
FROM analytics_v2.fact_sales f
LEFT JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
GROUP BY f.order_id, f.supplier_id, f.client_id;

-- 9. Supplier products view (GET /api/suppliers/{id}/products)
CREATE OR REPLACE VIEW erp.erp_supplier_products AS
SELECT
  f.supplier_id,
  f.product_id,
  p.product_name,
  SUM(quantidade) AS total_quantity,
  SUM(valor_total) AS total_value,
  COUNT(DISTINCT order_id) AS order_count,
  MAX(data_transacao) AS last_supplied,
  f.client_id
FROM analytics_v2.fact_sales f
LEFT JOIN analytics_v2.dim_product p ON f.product_id = p.product_id
GROUP BY f.supplier_id, f.product_id, p.product_name, f.client_id;

-- 10. Product sales view (GET /api/products/{id}/sales)
CREATE OR REPLACE VIEW erp.erp_product_sales AS
SELECT
  f.product_id,
  order_id,
  data_transacao,
  c.customer_name,
  s.name AS supplier_name,
  quantidade,
  valor_unitario,
  valor_total,
  f.client_id
FROM analytics_v2.fact_sales f
LEFT JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
LEFT JOIN analytics_v2.dim_supplier s ON f.supplier_id = s.supplier_id;

-- 11. Order detail view (GET /api/orders/{order_id} — line items)
CREATE OR REPLACE VIEW erp.erp_order_items AS
SELECT
  order_id,
  line_item_sequence,
  p.product_id,
  p.product_name,
  quantidade,
  valor_unitario,
  valor_total,
  f.client_id
FROM analytics_v2.fact_sales f
LEFT JOIN analytics_v2.dim_product p ON f.product_id = p.product_id;
Phase 3: Search + Lookup RPC Functions

-- 12. Universal search function (GET /api/search)
CREATE OR REPLACE FUNCTION erp.erp_search(
  p_query TEXT,
  p_entity TEXT DEFAULT NULL,
  p_limit INT DEFAULT 5
)
RETURNS TABLE(entity_type TEXT, id TEXT, name TEXT, subtitle TEXT)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
  v_client_id UUID := (current_setting('app.current_cliente_id'))::uuid;
  v_pattern TEXT := '%' || p_query || '%';
BEGIN
  IF p_entity IS NULL OR p_entity = 'customers' THEN
    RETURN QUERY
    SELECT 'customer'::TEXT, customer_id::TEXT, customer_name, customer_cpf_cnpj
    FROM analytics_v2.dim_customer
    WHERE client_id = v_client_id
      AND (customer_name ILIKE v_pattern OR customer_cpf_cnpj ILIKE v_pattern)
    LIMIT p_limit;
  END IF;

  IF p_entity IS NULL OR p_entity = 'suppliers' THEN
    RETURN QUERY
    SELECT 'supplier'::TEXT, supplier_id::TEXT, s.name, cnpj
    FROM analytics_v2.dim_supplier s
    WHERE client_id = v_client_id
      AND (s.name ILIKE v_pattern OR cnpj ILIKE v_pattern)
    LIMIT p_limit;
  END IF;

  IF p_entity IS NULL OR p_entity = 'products' THEN
    RETURN QUERY
    SELECT 'product'::TEXT, product_id::TEXT, product_name, categoria
    FROM analytics_v2.dim_product
    WHERE client_id = v_client_id
      AND product_name ILIKE v_pattern
    LIMIT p_limit;
  END IF;

  IF p_entity IS NULL OR p_entity = 'orders' THEN
    RETURN QUERY
    SELECT DISTINCT 'order'::TEXT, f.order_id::TEXT, f.order_id, customer_cpf_cnpj
    FROM analytics_v2.fact_sales f
    WHERE f.client_id = v_client_id
      AND f.order_id ILIKE v_pattern
    LIMIT p_limit;
  END IF;
END;
$$;

-- 13. Customer lookup by CPF/CNPJ (GET /api/customers/lookup)
CREATE OR REPLACE FUNCTION erp.erp_customer_lookup(p_cpf_cnpj TEXT)
RETURNS SETOF erp.erp_customers
LANGUAGE sql SECURITY DEFINER
AS $$
  SELECT * FROM erp.erp_customers
  WHERE client_id = (current_setting('app.current_cliente_id'))::uuid
    AND cpf_cnpj = p_cpf_cnpj
  LIMIT 1;
$$;

-- 14. Supplier lookup by CNPJ (GET /api/suppliers/lookup)
CREATE OR REPLACE FUNCTION erp.erp_supplier_lookup(p_cnpj TEXT)
RETURNS SETOF erp.erp_suppliers
LANGUAGE sql SECURITY DEFINER
AS $$
  SELECT * FROM erp.erp_suppliers
  WHERE client_id = (current_setting('app.current_cliente_id'))::uuid
    AND cnpj = p_cnpj
  LIMIT 1;
$$;
Phase 4: New Tables (Inventory, Purchase Orders, Jobs)

-- 15. Jobs table for async writes
CREATE TABLE erp.jobs (
  job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL,
  entity_type VARCHAR(50) NOT NULL,
  operation VARCHAR(20) NOT NULL,
  external_id VARCHAR(255),
  status VARCHAR(20) DEFAULT 'pending',
  entity_id VARCHAR(255),
  payload JSONB NOT NULL,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(client_id, external_id)
);
ALTER TABLE erp.jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON erp.jobs
  FOR ALL USING (client_id = (current_setting('app.current_cliente_id'))::uuid);

-- 16. Inventory tables
CREATE TABLE erp.inventory (
  inventory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL,
  product_id UUID NOT NULL,
  product_name VARCHAR(500),
  sku VARCHAR(100),
  current_stock INTEGER DEFAULT 0,
  minimum_stock INTEGER DEFAULT 0,
  warehouse_location VARCHAR(255),
  last_movement_date TIMESTAMPTZ,
  last_movement_type VARCHAR(20),
  total_sold INTEGER DEFAULT 0,
  total_restocked INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(client_id, product_id)
);
ALTER TABLE erp.inventory ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON erp.inventory
  FOR ALL USING (client_id = (current_setting('app.current_cliente_id'))::uuid);

CREATE TABLE erp.inventory_movements (
  movement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL,
  product_id UUID NOT NULL,
  movement_type VARCHAR(20) NOT NULL,
  movement_date TIMESTAMPTZ DEFAULT NOW(),
  quantity INTEGER NOT NULL,
  stock_after INTEGER,
  reference_type VARCHAR(50),
  reference_id VARCHAR(255),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE erp.inventory_movements ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON erp.inventory_movements
  FOR ALL USING (client_id = (current_setting('app.current_cliente_id'))::uuid);

-- 17. Purchase orders tables
CREATE TABLE erp.purchase_orders (
  po_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL,
  external_id VARCHAR(255),
  supplier_id UUID,
  supplier_cnpj VARCHAR(50),
  supplier_name VARCHAR(500),
  status VARCHAR(20) DEFAULT 'draft',
  total_value DECIMAL(12,2) DEFAULT 0,
  notes TEXT,
  order_date TIMESTAMPTZ DEFAULT NOW(),
  expected_delivery TIMESTAMPTZ,
  payment_terms VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(client_id, external_id)
);
ALTER TABLE erp.purchase_orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON erp.purchase_orders
  FOR ALL USING (client_id = (current_setting('app.current_cliente_id'))::uuid);

CREATE TABLE erp.purchase_order_items (
  item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  po_id UUID NOT NULL REFERENCES erp.purchase_orders(po_id),
  product_name VARCHAR(500),
  sku VARCHAR(100),
  quantity DECIMAL(12,2) NOT NULL,
  unit_price DECIMAL(12,2) NOT NULL,
  total_value DECIMAL(12,2) NOT NULL
);

-- 18. Webhook events table
CREATE TABLE erp.webhook_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  external_id VARCHAR(255),
  payload JSONB NOT NULL,
  status VARCHAR(20) DEFAULT 'received',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE erp.webhook_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON erp.webhook_events
  FOR ALL USING (client_id = (current_setting('app.current_cliente_id'))::uuid);
Phase 5: Write RPC Functions

-- 19. Create order (POST /api/orders)
CREATE OR REPLACE FUNCTION erp.erp_create_order(
  p_customer_cpf_cnpj TEXT,
  p_order_number TEXT DEFAULT NULL,
  p_order_date TIMESTAMPTZ DEFAULT NOW(),
  p_items JSONB DEFAULT '[]',
  p_external_id TEXT DEFAULT NULL,
  p_notes TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
  v_client_id UUID := (current_setting('app.current_cliente_id'))::uuid;
  v_job_id UUID;
BEGIN
  -- Create job for async processing
  INSERT INTO erp.jobs (client_id, entity_type, operation, external_id, payload, status)
  VALUES (
    v_client_id, 'order', 'create', p_external_id,
    jsonb_build_object(
      'customer_cpf_cnpj', p_customer_cpf_cnpj,
      'order_number', p_order_number,
      'order_date', p_order_date,
      'items', p_items,
      'notes', p_notes
    ),
    'pending'
  )
  ON CONFLICT (client_id, external_id) DO UPDATE SET updated_at = NOW()
  RETURNING job_id INTO v_job_id;

  RETURN jsonb_build_object('status', 'queued', 'job_id', v_job_id);
END;
$$;

-- 20. Create customer (POST /api/customers)
CREATE OR REPLACE FUNCTION erp.erp_create_customer(
  p_name TEXT,
  p_cpf_cnpj TEXT DEFAULT NULL,
  p_telefone TEXT DEFAULT NULL,
  p_endereco_rua TEXT DEFAULT NULL,
  p_endereco_numero TEXT DEFAULT NULL,
  p_endereco_bairro TEXT DEFAULT NULL,
  p_endereco_cidade TEXT DEFAULT NULL,
  p_endereco_uf TEXT DEFAULT NULL,
  p_endereco_cep TEXT DEFAULT NULL,
  p_external_id TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
  v_client_id UUID := (current_setting('app.current_cliente_id'))::uuid;
  v_customer_id UUID := gen_random_uuid();
BEGIN
  INSERT INTO analytics_v2.dim_customer (
    customer_id, client_id, customer_name, customer_cpf_cnpj,
    telefone, endereco_rua, endereco_numero, endereco_bairro,
    endereco_cidade, endereco_uf, endereco_cep,
    created_at, updated_at
  ) VALUES (
    v_customer_id, v_client_id, p_name, p_cpf_cnpj,
    p_telefone, p_endereco_rua, p_endereco_numero, p_endereco_bairro,
    p_endereco_cidade, p_endereco_uf, p_endereco_cep,
    NOW(), NOW()
  );

  RETURN jsonb_build_object('status', 'created', 'customer_id', v_customer_id);
END;
$$;

-- Similar RPC functions for:
-- erp_update_customer, erp_create_supplier, erp_update_supplier,
-- erp_update_order, erp_create_transaction,
-- erp_create_purchase_order, erp_update_purchase_order,
-- erp_inventory_adjust, erp_inventory_restock,
-- erp_webhook_order_created, erp_webhook_payment_received, etc.
Phase 6: Frontend Service + Types
Create: apps/vizu_dashboard/src/services/erpService.ts


import { supabase } from '../lib/supabase';

// Generic paginated response
interface PaginatedResponse<T> {
  data: T[];
  pagination: { total: number; limit: number; offset: number; has_more: boolean };
}

// Helper to wrap Supabase response in spec pagination envelope
async function paginatedQuery<T>(
  table: string,
  { limit = 50, offset = 0, orderBy, filters }: QueryOptions
): Promise<PaginatedResponse<T>> {
  let query = supabase.from(table).select('*', { count: 'exact' });
  // Apply filters, ordering, range...
  const { data, count } = await query.range(offset, offset + limit - 1);
  return {
    data: data as T[],
    pagination: { total: count ?? 0, limit, offset, has_more: (offset + limit) < (count ?? 0) }
  };
}

// Customers
export const listCustomers = (opts) => paginatedQuery<Customer>('erp_customers', opts);
export const getCustomer = (id: string) => supabase.from('erp_customers').select('*').eq('customer_id', id).single();
export const lookupCustomer = (cpf: string) => supabase.rpc('erp_customer_lookup', { p_cpf_cnpj: cpf });
export const createCustomer = (data) => supabase.rpc('erp_create_customer', data);

// Orders, Suppliers, Products, Inventory, etc. — same pattern
What This Eliminates vs. Custom FastAPI Approach
Component	FastAPI Approach	Supabase Approach
Endpoint files	10 new Python files	0 (auto-generated)
Repository methods	~30 new SQL methods	0 (PostgREST handles queries)
Pydantic schemas	~40 new models	0 (views define the shape)
Pagination logic	Custom implementation	Built-in (limit/offset/Range)
Filtering logic	Custom query params	Built-in (eq, ilike, gt, etc.)
Auth/multi-tenancy	Per-endpoint dependency	RLS policies (database-level)
New code to write	~3000+ lines of Python	~500 lines of SQL + ~200 lines of TypeScript
Files Summary
SQL migration file (single file):

Creates erp schema
11 views over existing analytics_v2 tables
6 new tables (jobs, inventory, inventory_movements, purchase_orders, purchase_order_items, webhook_events)
RLS policies on all tables/views
~15 RPC functions for writes + search + lookups
Frontend (1 new file):

apps/vizu_dashboard/src/services/erpService.ts — typed Supabase SDK calls with pagination wrapper
Existing files — NO changes:

All FastAPI endpoints remain untouched
analyticsService.ts remains untouched
Dashboard continues working via Axios → FastAPI
Verification
After running the migration, check Supabase dashboard → API docs to see all new endpoints auto-documented
Test read: supabase.from('erp_customers').select('*', { count: 'exact' }).range(0, 9) returns paginated customers
Test filtering: .ilike('name', '%maria%').eq('cluster_tier', 'A') filters correctly
Test RLS: query without set_current_cliente_id() returns empty results
Test write: supabase.rpc('erp_create_customer', { p_name: 'Test' }) creates customer
Test search: supabase.rpc('erp_search', { p_query: 'maria' }) returns cross-entity results
Existing dashboard endpoints (/api/clientes, /api/fornecedores, etc.) still work unchanged