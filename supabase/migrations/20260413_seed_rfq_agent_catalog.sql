-- Migration: Seed RFQ Agent into agent_catalog
-- Purpose: Add procurement/RFQ agent to standalone agent catalog
-- Date: 2026-04-13

INSERT INTO public.agent_catalog (
    name, slug, description, category, icon,
    agent_config, prompt_name,
    required_context, required_files,
    requires_google, tier_required
)
VALUES (
    'Agente de Cotações',
    'rfq-agent',
    'Recebe listas de compras, envia cotações paralelas para fornecedores, compara respostas e gera listas de compra otimizadas por fornecedor.',
    'procurement',
    'ShoppingCart',
    '{
        "name": "rfq-agent",
        "role": "Especialista em Cotações e Compras",
        "elicitation_strategy": "structured_collection",
        "enabled_tools": [
            "parse_buying_list",
            "validate_buying_list",
            "list_suppliers",
            "dispatch_rfq",
            "check_rfq_responses",
            "submit_mock_response",
            "optimize_allocation",
            "generate_po_report",
            "create_purchase_order",
            "approve_purchase_order"
        ],
        "max_turns": 30,
        "use_langfuse": true,
        "model": "openai:gpt-4o"
    }'::JSONB,
    'standalone/rfq-agent',
    '[
        {"field": "company_name", "type": "text", "required": true, "label": "Nome da empresa", "prompt_hint": "Qual o nome da sua empresa?"},
        {"field": "industry", "type": "text", "required": true, "label": "Ramo de atividade", "prompt_hint": "Ex: Alimentos, Construção, Varejo"},
        {"field": "preferred_currency", "type": "text", "required": true, "label": "Moeda preferencial", "prompt_hint": "BRL, USD, EUR"},
        {"field": "procurement_frequency", "type": "text", "required": false, "label": "Frequência de compras", "prompt_hint": "Semanal, quinzenal, mensal"},
        {"field": "max_supplier_concentration", "type": "text", "required": false, "label": "Concentração máxima por fornecedor (%)", "prompt_hint": "Ex: 60"}
    ]'::JSONB,
    '{
        "csv": {"min": 0, "max": 5, "description": "Lista de compras (CSV/XLSX) ou digite diretamente no chat"},
        "text": {"min": 0, "max": 3, "description": "Documentos com políticas de compras (opcional)"}
    }'::JSONB,
    false,
    'BASIC'
);
