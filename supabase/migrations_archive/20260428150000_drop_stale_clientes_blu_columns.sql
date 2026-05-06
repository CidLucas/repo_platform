-- Drop columns removed in the 2026-04-28 schema baseline.
-- Columns kept: tipo_cliente (legacy compat in backend model),
--               brand_voice, data_schema, available_tools, cpf_cnpj (all used by Tool Pool API).
ALTER TABLE public.clientes_blu
  DROP COLUMN IF EXISTS prompt_base,
  DROP COLUMN IF EXISTS horario_funcionamento,
  DROP COLUMN IF EXISTS current_moment,
  DROP COLUMN IF EXISTS enabled_tools,
  DROP COLUMN IF EXISTS email;
