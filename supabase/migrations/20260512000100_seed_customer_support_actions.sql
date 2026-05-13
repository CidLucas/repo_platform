-- ─────────────────────────────────────────────────────────────────────────────
-- Seed agent_action_catalog for customer-support agent
--
-- These rows appear as selectable actions in RoutinesPanel QuickBuilder
-- dropdowns, allowing clients to compose custom routines using the
-- customer-support agent's tools.
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.agent_action_catalog
  (id, agent_slug, action_id, label, description, input_schema, trigger_capable, is_active, sort_order)
VALUES
  (
    'customer-support.criar_rotina',
    'customer-support',
    'criar_rotina',
    'Criar rotina personalizada',
    'Cria uma nova rotina personalizada em rascunho para revisão e ativação posterior.',
    '[
      {"name": "name",         "type": "string", "label": "Nome da rotina", "required": true},
      {"name": "steps",        "type": "array",  "label": "Passos",         "required": true},
      {"name": "description",  "type": "string", "label": "Descrição",      "required": false},
      {"name": "trigger_type", "type": "string", "label": "Gatilho",        "required": false}
    ]'::jsonb,
    false,
    true,
    10
  ),
  (
    'customer-support.enviar_aprovacao',
    'customer-support',
    'enviar_aprovacao',
    'Enviar rotina para aprovação',
    'Submete uma rotina existente em rascunho para revisão e ativação.',
    '[
      {"name": "routine_id", "type": "string", "label": "ID da rotina", "required": true}
    ]'::jsonb,
    false,
    true,
    20
  ),
  (
    'customer-support.ativar_catalogo',
    'customer-support',
    'ativar_catalogo',
    'Ativar/desativar rotina de catálogo',
    'Liga ou desliga uma rotina pré-definida do catálogo para o cliente.',
    '[
      {"name": "routine_id", "type": "string",  "label": "ID da rotina de catálogo", "required": true},
      {"name": "active",     "type": "boolean", "label": "Ativar?",                   "required": true}
    ]'::jsonb,
    false,
    true,
    30
  )
ON CONFLICT (id) DO NOTHING;
