-- =====================================================================
-- Add Context 2.0 JSONB columns to clientes_vizu
-- =====================================================================
-- Purpose: Store client-specific context sections for prompt injection.
--          These sections are loaded by ContextService and injected into
--          Langfuse prompts via {{context_sections}} variable.
-- Created: 2026-04-10
-- =====================================================================

-- Core Identity (quarterly updates)
ALTER TABLE public.clientes_vizu
  ADD COLUMN IF NOT EXISTS company_profile JSONB,
  ADD COLUMN IF NOT EXISTS brand_voice JSONB;

-- Operations (weekly updates)
ALTER TABLE public.clientes_vizu
  ADD COLUMN IF NOT EXISTS current_moment JSONB,
  ADD COLUMN IF NOT EXISTS team_structure JSONB,
  ADD COLUMN IF NOT EXISTS policies JSONB;

-- Technical (on-change updates)
ALTER TABLE public.clientes_vizu
  ADD COLUMN IF NOT EXISTS data_schema JSONB,
  ADD COLUMN IF NOT EXISTS available_tools JSONB;

-- CPF/CNPJ (used by VizuClientContext model)
ALTER TABLE public.clientes_vizu
  ADD COLUMN IF NOT EXISTS cpf_cnpj TEXT;

-- Comments
COMMENT ON COLUMN public.clientes_vizu.company_profile IS 'Context 2.0: Company identity — mission, vision, values, archetype (JSONB)';
COMMENT ON COLUMN public.clientes_vizu.brand_voice IS 'Context 2.0: Communication style — tone, phrases to use/avoid (JSONB)';
COMMENT ON COLUMN public.clientes_vizu.current_moment IS 'Context 2.0: Current priorities, challenges, wins, metrics (JSONB)';
COMMENT ON COLUMN public.clientes_vizu.team_structure IS 'Context 2.0: Key contacts, escalation paths, business hours (JSONB)';
COMMENT ON COLUMN public.clientes_vizu.policies IS 'Context 2.0: Rules, guardrails, approval workflows (JSONB)';
COMMENT ON COLUMN public.clientes_vizu.data_schema IS 'Context 2.0: Available data tables, formats, key fields (JSONB)';
COMMENT ON COLUMN public.clientes_vizu.available_tools IS 'Context 2.0: Tool permissions — enabled_tool_names, default_system_prompt (JSONB)';
COMMENT ON COLUMN public.clientes_vizu.cpf_cnpj IS 'CPF ou CNPJ do cliente';
