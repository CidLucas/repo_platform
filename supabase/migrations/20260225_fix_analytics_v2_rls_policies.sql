-- Migration: Fix analytics_v2 RLS policies to use JWT auth
-- Date: 2026-02-25
-- Description: Updates all RLS policies to use a function that looks up client_id
--              from the authenticated user's email instead of relying on session variables.

-- 1. Create helper function to get current user's client_id from JWT email
CREATE OR REPLACE FUNCTION public.get_my_client_id()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT client_id::text
  FROM public.clientes_vizu
  WHERE email = auth.jwt() ->> 'email'
  LIMIT 1;
$$;

-- 2. Update RLS policies - Dimension tables

-- dim_clientes
DROP POLICY IF EXISTS clientes_client_isolation ON analytics_v2.dim_clientes;
CREATE POLICY clientes_client_isolation ON analytics_v2.dim_clientes 
  FOR ALL 
  USING (client_id = public.get_my_client_id());

-- dim_fornecedores  
DROP POLICY IF EXISTS fornecedores_client_isolation ON analytics_v2.dim_fornecedores;
CREATE POLICY fornecedores_client_isolation ON analytics_v2.dim_fornecedores
  FOR ALL
  USING (client_id = public.get_my_client_id());

-- dim_produtos
DROP POLICY IF EXISTS produtos_client_isolation ON analytics_v2.dim_produtos;
CREATE POLICY produtos_client_isolation ON analytics_v2.dim_produtos
  FOR ALL
  USING (client_id = public.get_my_client_id());

-- dim_inventory
DROP POLICY IF EXISTS erp_inventory_tenant_isolation ON analytics_v2.dim_inventory;
CREATE POLICY erp_inventory_tenant_isolation ON analytics_v2.dim_inventory
  FOR ALL
  USING (client_id = public.get_my_client_id());

-- 3. Update RLS policies - Fact tables

-- fcx_vendas
DROP POLICY IF EXISTS vendas_client_isolation ON analytics_v2.fcx_vendas;
CREATE POLICY vendas_client_isolation ON analytics_v2.fcx_vendas
  FOR ALL
  USING (client_id = public.get_my_client_id());

-- fcx_compras
DROP POLICY IF EXISTS compras_client_isolation ON analytics_v2.fcx_compras;
CREATE POLICY compras_client_isolation ON analytics_v2.fcx_compras
  FOR ALL
  USING (client_id = public.get_my_client_id());

-- fcx_inventory_movements
DROP POLICY IF EXISTS erp_inventory_movements_tenant_isolation ON analytics_v2.fcx_inventory_movements;
CREATE POLICY erp_inventory_movements_tenant_isolation ON analytics_v2.fcx_inventory_movements
  FOR ALL
  USING (client_id = public.get_my_client_id());

-- fcx_purchase_orders
DROP POLICY IF EXISTS erp_purchase_orders_tenant_isolation ON analytics_v2.fcx_purchase_orders;
CREATE POLICY erp_purchase_orders_tenant_isolation ON analytics_v2.fcx_purchase_orders
  FOR ALL
  USING (client_id = public.get_my_client_id());

-- fcx_purchase_order_items
DROP POLICY IF EXISTS erp_po_items_tenant_isolation ON analytics_v2.fcx_purchase_order_items;
CREATE POLICY erp_po_items_tenant_isolation ON analytics_v2.fcx_purchase_order_items
  FOR ALL
  USING (client_id = public.get_my_client_id());

-- 4. Update RLS policies - Registry tables

-- reg_jobs
DROP POLICY IF EXISTS erp_jobs_tenant_isolation ON analytics_v2.reg_jobs;
CREATE POLICY erp_jobs_tenant_isolation ON analytics_v2.reg_jobs
  FOR ALL
  USING (client_id = public.get_my_client_id());

-- reg_webhook_events
DROP POLICY IF EXISTS erp_webhook_events_tenant_isolation ON analytics_v2.reg_webhook_events;
CREATE POLICY erp_webhook_events_tenant_isolation ON analytics_v2.reg_webhook_events
  FOR ALL
  USING (client_id = public.get_my_client_id());

-- 5. Update v_resumo_dashboard view to use the function
CREATE OR REPLACE VIEW analytics_v2.v_resumo_dashboard AS
SELECT 
    public.get_my_client_id() AS client_id,
    (SELECT count(*) FROM analytics_v2.dim_clientes WHERE client_id = public.get_my_client_id()) AS total_clientes,
    (SELECT count(*) FROM analytics_v2.dim_fornecedores WHERE client_id = public.get_my_client_id()) AS total_fornecedores,
    (SELECT count(*) FROM analytics_v2.dim_produtos WHERE client_id = public.get_my_client_id()) AS total_produtos,
    (SELECT count(DISTINCT pedido_id) FROM analytics_v2.fcx_vendas WHERE client_id = public.get_my_client_id()) AS total_pedidos,
    (SELECT COALESCE(sum(valor_total), 0) FROM analytics_v2.fcx_vendas WHERE client_id = public.get_my_client_id()) AS receita_total,
    (SELECT COALESCE(avg(valor_total), 0) FROM analytics_v2.fcx_vendas WHERE client_id = public.get_my_client_id()) AS ticket_medio,
    now() AS gerado_em;
