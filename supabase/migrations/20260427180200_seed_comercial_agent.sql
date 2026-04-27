-- Migration: Seed Comercial Agent (Phase 3B C3.2)
-- Purpose: Register 'comercial-agent' in agent_catalog so approval_requests
-- rows with action='send_consumer_reply' satisfy the FK constraint.
-- Date: 2026-04-27

INSERT INTO public.agent_catalog (
    name, slug, description, category, icon,
    agent_config, prompt_name,
    required_context, required_files,
    requires_google, tier_required
)
VALUES (
    'Agente Comercial',
    'comercial-agent',
    'Lê o inbox de WhatsApp/Gmail dos clientes, redige respostas em PT-BR e dispara envios pelos canais configurados respeitando a política de aprovação do tenant.',
    'comercial',
    'MessageCircle',
    '{
        "name": "comercial-agent",
        "role": "Especialista em Atendimento Comercial",
        "elicitation_strategy": "free_form",
        "enabled_tools": [
            "list_inbox_threads",
            "get_thread_messages",
            "draft_consumer_reply",
            "send_consumer_reply"
        ],
        "max_turns": 30,
        "use_langfuse": true,
        "model": "openai:gpt-4o-mini"
    }'::JSONB,
    'standalone/comercial-agent',
    '[]'::JSONB,
    '[]'::JSONB,
    FALSE,
    'BASIC'
)
ON CONFLICT (slug) DO NOTHING;
