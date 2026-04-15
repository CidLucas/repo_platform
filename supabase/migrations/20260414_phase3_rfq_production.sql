-- Migration: Phase 3 RFQ — Production Readiness
-- Purpose: Update agent_catalog with Phase 3 tools (Google Sheets, Supplier CRUD)
--          Enable Google integration for rfq-agent
-- Date: 2026-04-14

-- =============================================================================
-- 1. Update agent_catalog — Add Phase 3 tools, enable Google
-- =============================================================================
UPDATE public.agent_catalog
SET
    agent_config = jsonb_set(
        agent_config,
        '{enabled_tools}',
        '[
            "parse_buying_list",
            "validate_buying_list",
            "list_suppliers",
            "dispatch_rfq",
            "check_rfq_responses",
            "submit_mock_response",
            "optimize_allocation",
            "generate_po_report",
            "create_purchase_order",
            "approve_purchase_order",
            "suggest_counter_offer",
            "dispatch_rfq_whatsapp",
            "parse_supplier_reply",
            "import_buying_list_from_sheets",
            "export_po_to_sheets",
            "add_supplier",
            "update_supplier",
            "remove_supplier"
        ]'::JSONB
    ),
    requires_google = true,
    description = 'Recebe listas de compras (CSV/Sheets/digitadas), envia cotações paralelas para fornecedores, compara respostas, otimiza alocação e gera pedidos de compra. Integra com Google Sheets para importação e exportação.'
WHERE slug = 'rfq-agent';

-- =============================================================================
-- 2. Add sheets_config to required_context for Sheets integration
-- =============================================================================
UPDATE public.agent_catalog
SET
    required_context = required_context || '[
        {"field": "default_spreadsheet_id", "type": "text", "required": false, "label": "Planilha Google padrão (ID)", "prompt_hint": "ID da planilha para importar/exportar (opcional)"}
    ]'::JSONB
WHERE slug = 'rfq-agent';
