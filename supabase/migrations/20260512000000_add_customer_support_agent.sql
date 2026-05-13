-- ─────────────────────────────────────────────────────────────────────────────
-- Add Customer Support agent to agent_catalog
--
-- Standalone agent specialized in app navigation help, explaining features,
-- and guiding users through routine creation step-by-step via chat.
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.agent_catalog
  (name, slug, description, category, icon, agent_config, prompt_name,
   required_context, requires_google, tier_required, is_active)
VALUES (
  'Suporte ao Aplicativo',
  'customer-support',
  'Ajuda com o app: cria rotinas, explica funcionalidades e orienta o uso da plataforma.',
  'suporte',
  '🛎️',
  '{
    "name": "customer-support",
    "role": "Especialista em suporte ao app e criação de rotinas de automação",
    "enabled_tools": [
      "listar_rotinas_catalogo",
      "listar_rotinas_personalizadas",
      "criar_rotina_personalizada",
      "ativar_rotina_catalogo",
      "enviar_rotina_para_aprovacao"
    ],
    "max_turns": 15,
    "use_langfuse": true
  }'::jsonb,
  'agents/customer-support',
  '[]'::jsonb,
  false,
  'BASIC',
  true
)
ON CONFLICT (slug) DO UPDATE SET
  agent_config = EXCLUDED.agent_config,
  updated_at   = now();
