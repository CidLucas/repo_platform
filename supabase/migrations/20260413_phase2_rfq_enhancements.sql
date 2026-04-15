-- Migration: Phase 2 RFQ enhancements
-- Purpose: Add Phase 2 columns for constraints, WhatsApp, follow-up tracking
-- Date: 2026-04-13

-- =============================================================================
-- 1. supplier_roster — Add MOQ rules, payment terms, avg delivery
-- =============================================================================
ALTER TABLE public.supplier_roster
    ADD COLUMN IF NOT EXISTS moq_rules JSONB DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS payment_terms TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS delivery_days_avg INTEGER DEFAULT 0;

COMMENT ON COLUMN public.supplier_roster.moq_rules IS
    'Per-item or default MOQ rules. Format: {"default": 100, "Parafuso M6": 500}';
COMMENT ON COLUMN public.supplier_roster.payment_terms IS
    'Default payment terms text, e.g. "30 dias", "60/90 dias"';
COMMENT ON COLUMN public.supplier_roster.delivery_days_avg IS
    'Average delivery time in days (historical)';

-- =============================================================================
-- 2. rfq_requests — Add WhatsApp tracking, follow-up count, channel
-- =============================================================================
ALTER TABLE public.rfq_requests
    ADD COLUMN IF NOT EXISTS communication_channel TEXT DEFAULT 'mock',
    ADD COLUMN IF NOT EXISTS whatsapp_message_sid TEXT,
    ADD COLUMN IF NOT EXISTS follow_up_count INTEGER DEFAULT 0;

COMMENT ON COLUMN public.rfq_requests.communication_channel IS
    'Channel used: mock, whatsapp, email';
COMMENT ON COLUMN public.rfq_requests.whatsapp_message_sid IS
    'Twilio Message SID for WhatsApp-dispatched RFQs';
COMMENT ON COLUMN public.rfq_requests.follow_up_count IS
    'Number of follow-up reminders sent';

CREATE INDEX IF NOT EXISTS idx_rfq_requests_channel
    ON public.rfq_requests(communication_channel);

-- =============================================================================
-- 3. Update agent_catalog — Add Phase 2 tools and workflow_graph
-- =============================================================================
UPDATE public.agent_catalog
SET
    agent_config = jsonb_set(
        agent_config,
        '{enabled_tools}',
        '["parse_buying_list","validate_buying_list","list_suppliers","dispatch_rfq","check_rfq_responses","submit_mock_response","optimize_allocation","generate_po_report","create_purchase_order","approve_purchase_order","suggest_counter_offer","dispatch_rfq_whatsapp","parse_supplier_reply"]'::JSONB
    ),
    workflow_graph = '{
        "nodes": [
            {"id": "init", "type": "init"},
            {"id": "elicit", "type": "elicit"},
            {"id": "execute_tool", "type": "execute_tool"},
            {"id": "respond", "type": "respond"},
            {"id": "rfq_wait_responses", "type": "rfq_wait_responses"},
            {"id": "rfq_follow_up", "type": "rfq_follow_up"},
            {"id": "end", "type": "end"}
        ],
        "edges": [
            {"source": "__start__", "target": "init"},
            {"source": "init", "target": "elicit", "label": "elicit"},
            {"source": "init", "target": "respond", "label": "respond"},
            {"source": "init", "target": "end", "label": "end"},
            {"source": "elicit", "target": "execute_tool", "label": "needs_tool"},
            {"source": "elicit", "target": "elicit", "label": "needs_elicitation"},
            {"source": "elicit", "target": "respond", "label": "ready_to_respond"},
            {"source": "elicit", "target": "end", "label": "end"},
            {"source": "execute_tool", "target": "respond", "label": "success"},
            {"source": "execute_tool", "target": "respond", "label": "error"},
            {"source": "execute_tool", "target": "elicit", "label": "needs_elicitation"},
            {"source": "execute_tool", "target": "end", "label": "end"},
            {"source": "respond", "target": "init", "label": "init"},
            {"source": "respond", "target": "end", "label": "end"},
            {"source": "rfq_wait_responses", "target": "respond"},
            {"source": "rfq_follow_up", "target": "rfq_wait_responses"},
            {"source": "end", "target": "__end__"}
        ]
    }'::JSONB
WHERE slug = 'rfq-agent';
