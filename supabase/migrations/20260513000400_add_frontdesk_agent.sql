-- Phase 3: Add Frontdesk specialist to agent_catalog
--
-- The Frontdesk is the default entry point agent. It handles simple RAG and SQL
-- queries inline and routes complex multi-domain tasks to specialist agents.

INSERT INTO public.agent_catalog (
    slug,
    name,
    description,
    prompt_name,
    agent_config,
    tier_required
) VALUES (
    'frontdesk',
    'Frontdesk',
    'Entry point specialist. Handles simple RAG and SQL queries directly. Routes complex or multi-domain tasks to specialist agents. Use as the first point of contact for all user requests.',
    'agents/frontdesk',
    '{
        "enabled_tools": ["executar_rag_cliente", "execute_sql", "ferramenta_publica_de_teste"],
        "max_turns": 4,
        "tags": ["frontdesk", "routing", "rag", "sql"]
    }'::jsonb,
    'BASIC'
)
ON CONFLICT (slug) DO UPDATE
    SET name         = EXCLUDED.name,
        description  = EXCLUDED.description,
        prompt_name  = EXCLUDED.prompt_name,
        agent_config = EXCLUDED.agent_config;
