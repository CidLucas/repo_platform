-- Migration: Create RFQ/Procurement tables
-- Purpose: supplier_roster, rfq_requests, purchase_orders for the RFQ Agent
-- Date: 2026-04-13

-- =============================================================================
-- 1. supplier_roster — Per-tenant supplier directory
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.supplier_roster (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    contact_email TEXT,
    contact_phone TEXT,
    categories TEXT[] DEFAULT ARRAY[]::TEXT[],
    metadata JSONB DEFAULT '{}'::JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_supplier_roster_client ON public.supplier_roster(client_id);

ALTER TABLE public.supplier_roster ENABLE ROW LEVEL SECURITY;

CREATE POLICY "supplier_roster_select" ON public.supplier_roster
    FOR SELECT USING (client_id = auth.uid()::UUID);

CREATE POLICY "supplier_roster_insert" ON public.supplier_roster
    FOR INSERT WITH CHECK (client_id = auth.uid()::UUID);

CREATE POLICY "supplier_roster_update" ON public.supplier_roster
    FOR UPDATE USING (client_id = auth.uid()::UUID);

CREATE POLICY "supplier_roster_delete" ON public.supplier_roster
    FOR DELETE USING (client_id = auth.uid()::UUID);

CREATE POLICY "supplier_roster_service" ON public.supplier_roster
    FOR ALL USING (auth.role() = 'service_role');

-- =============================================================================
-- 2. rfq_requests — Individual RFQ dispatches
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.rfq_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    client_id UUID NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES public.supplier_roster(id) ON DELETE CASCADE,
    items JSONB NOT NULL DEFAULT '[]'::JSONB,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sent', 'responded', 'expired', 'cancelled')),
    sent_at TIMESTAMPTZ,
    deadline TIMESTAMPTZ,
    response_data JSONB,
    raw_response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rfq_requests_session ON public.rfq_requests(session_id);
CREATE INDEX idx_rfq_requests_client ON public.rfq_requests(client_id);
CREATE INDEX idx_rfq_requests_status ON public.rfq_requests(status);

ALTER TABLE public.rfq_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "rfq_requests_select" ON public.rfq_requests
    FOR SELECT USING (client_id = auth.uid()::UUID);

CREATE POLICY "rfq_requests_insert" ON public.rfq_requests
    FOR INSERT WITH CHECK (client_id = auth.uid()::UUID);

CREATE POLICY "rfq_requests_update" ON public.rfq_requests
    FOR UPDATE USING (client_id = auth.uid()::UUID);

CREATE POLICY "rfq_requests_service" ON public.rfq_requests
    FOR ALL USING (auth.role() = 'service_role');

-- =============================================================================
-- 3. purchase_orders — Generated POs (post-optimization)
-- =============================================================================
CREATE TABLE IF NOT EXISTS public.purchase_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    client_id UUID NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES public.supplier_roster(id) ON DELETE CASCADE,
    items JSONB NOT NULL DEFAULT '[]'::JSONB,
    total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'BRL',
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'pending_approval', 'approved', 'sent')),
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_purchase_orders_session ON public.purchase_orders(session_id);
CREATE INDEX idx_purchase_orders_client ON public.purchase_orders(client_id);

ALTER TABLE public.purchase_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "purchase_orders_select" ON public.purchase_orders
    FOR SELECT USING (client_id = auth.uid()::UUID);

CREATE POLICY "purchase_orders_insert" ON public.purchase_orders
    FOR INSERT WITH CHECK (client_id = auth.uid()::UUID);

CREATE POLICY "purchase_orders_update" ON public.purchase_orders
    FOR UPDATE USING (client_id = auth.uid()::UUID);

CREATE POLICY "purchase_orders_service" ON public.purchase_orders
    FOR ALL USING (auth.role() = 'service_role');
