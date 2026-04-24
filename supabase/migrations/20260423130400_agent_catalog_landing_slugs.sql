-- Migration: Seed landing-canonical agent slugs into agent_catalog
-- Phase: Landing Onboarding Wire-up, Phase 1 (Foundation)
-- Date: 2026-04-23
--
-- The landing wizard (apps/landing/src/onboarding/state.ts::ALL_AGENTS) exposes
-- 8 canonical agents to the user. Each one must map 1:1 to an agent_catalog
-- row so that public.client_enabled_agents.agent_slug FK resolves.
--
-- These are starter configurations — enabled_tools use names validated against
-- vizu_tool_registry.BUILTIN_TOOLS and existing standalone agents. Prompts are
-- seeded later (Phase 4) by the onboarding-bootstrap edge function via the
-- Langfuse public API; the prompt_name column here is the canonical pointer.
--
-- Idempotent via ON CONFLICT (slug) DO UPDATE.

INSERT INTO public.agent_catalog (
  name, slug, description, category, icon,
  agent_config, prompt_name,
  required_context, required_files,
  requires_google, tier_required, is_active
) VALUES
  (
    'Agente de Analytics',
    'analytics',
    'Transforma dados em respostas e dashboards. Executa SQL sobre dados estruturados e CSVs.',
    'analytics',
    'BarChart2',
    '{
      "name": "analytics_agent",
      "role": "Business Analytics Specialist",
      "elicitation_strategy": "structured_collection",
      "enabled_tools": ["executar_sql_agent", "execute_csv_query", "list_csv_datasets", "executar_rag_cliente"],
      "max_turns": 25,
      "model": "openai:gpt-4o"
    }'::jsonb,
    'landing/analytics',
    '[]'::jsonb,
    '{}'::jsonb,
    false, 'BASIC', true
  ),
  (
    'Agente de Estoque',
    'inventory',
    'Alerta de reposição, análise de giro e cotação automática com fornecedores.',
    'operations',
    'Package',
    '{
      "name": "inventory_agent",
      "role": "Inventory & Procurement Specialist",
      "elicitation_strategy": "structured_collection",
      "enabled_tools": ["executar_sql_agent", "executar_rag_cliente"],
      "max_turns": 25,
      "model": "openai:gpt-4o-mini"
    }'::jsonb,
    'landing/inventory',
    '[]'::jsonb,
    '{}'::jsonb,
    false, 'BASIC', true
  ),
  (
    'Agente de Marketing',
    'marketing',
    'Monitora campanhas, menções de marca e performance de conteúdo.',
    'marketing',
    'Megaphone',
    '{
      "name": "marketing_agent",
      "role": "Marketing Performance Specialist",
      "elicitation_strategy": "structured_collection",
      "enabled_tools": ["monitor_company", "monitor_keywords", "monitor_feature", "executar_rag_cliente"],
      "max_turns": 25,
      "model": "openai:gpt-4o-mini"
    }'::jsonb,
    'landing/marketing',
    '[]'::jsonb,
    '{}'::jsonb,
    false, 'BASIC', true
  ),
  (
    'Agente de CRM',
    'crm',
    'Mantém a base de clientes ativa com follow-ups automáticos e alertas de churn.',
    'crm',
    'Users',
    '{
      "name": "crm_agent",
      "role": "Customer Relationship Specialist",
      "elicitation_strategy": "structured_collection",
      "enabled_tools": ["executar_sql_agent", "executar_rag_cliente"],
      "max_turns": 20,
      "model": "openai:gpt-4o-mini"
    }'::jsonb,
    'landing/crm',
    '[]'::jsonb,
    '{}'::jsonb,
    false, 'BASIC', true
  ),
  (
    'Agente de Agendamento',
    'scheduling',
    'Gerencia a agenda, resolve conflitos e envia lembretes.',
    'operations',
    'Calendar',
    '{
      "name": "scheduling_agent",
      "role": "Scheduling Specialist",
      "elicitation_strategy": "structured_collection",
      "enabled_tools": ["executar_rag_cliente"],
      "max_turns": 20,
      "model": "openai:gpt-4o-mini"
    }'::jsonb,
    'landing/scheduling',
    '[]'::jsonb,
    '{}'::jsonb,
    true,  -- requires Google (Calendar)
    'BASIC', true
  ),
  (
    'Agente de Projetos',
    'projects',
    'Acompanha tarefas, prazos e responsáveis dos projetos em andamento.',
    'operations',
    'KanbanSquare',
    '{
      "name": "projects_agent",
      "role": "Project Tracking Specialist",
      "elicitation_strategy": "structured_collection",
      "enabled_tools": ["executar_rag_cliente", "executar_sql_agent"],
      "max_turns": 20,
      "model": "openai:gpt-4o-mini"
    }'::jsonb,
    'landing/projects',
    '[]'::jsonb,
    '{}'::jsonb,
    false, 'BASIC', true
  ),
  (
    'Agente de Documentos',
    'documents',
    'Organiza contratos, notas e anexos. Extrai dados estruturados via OCR.',
    'knowledge',
    'FileText',
    '{
      "name": "documents_agent",
      "role": "Document Intelligence Specialist",
      "elicitation_strategy": "structured_collection",
      "enabled_tools": ["extract_document_with_ocr", "summarize_document_sections", "extract_structured_data", "write_summary_to_kb", "executar_rag_cliente"],
      "max_turns": 25,
      "model": "openai:gpt-4o-mini"
    }'::jsonb,
    'landing/documents',
    '[]'::jsonb,
    '{"text": {"min": 0, "max": 20, "description": "Documentos (PDF, DOCX, imagens)"}}'::jsonb,
    false, 'SME', true
  ),
  (
    'Agente Financeiro',
    'finance',
    'Contas a pagar, receber e fluxo de caixa. Integra com ERPs e planilhas.',
    'finance',
    'DollarSign',
    '{
      "name": "finance_agent",
      "role": "Financial Operations Specialist",
      "elicitation_strategy": "structured_collection",
      "enabled_tools": ["executar_sql_agent", "execute_csv_query", "list_csv_datasets", "executar_rag_cliente"],
      "max_turns": 25,
      "model": "openai:gpt-4o"
    }'::jsonb,
    'landing/finance',
    '[]'::jsonb,
    '{}'::jsonb,
    false, 'BASIC', true
  )
ON CONFLICT (slug) DO UPDATE SET
  name             = EXCLUDED.name,
  description      = EXCLUDED.description,
  category         = EXCLUDED.category,
  icon             = EXCLUDED.icon,
  agent_config     = EXCLUDED.agent_config,
  prompt_name      = EXCLUDED.prompt_name,
  required_context = EXCLUDED.required_context,
  required_files   = EXCLUDED.required_files,
  requires_google  = EXCLUDED.requires_google,
  tier_required    = EXCLUDED.tier_required,
  is_active        = EXCLUDED.is_active,
  updated_at       = now();
