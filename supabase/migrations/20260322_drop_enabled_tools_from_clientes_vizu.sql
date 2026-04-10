-- Migration: Drop legacy enabled_tools column from clientes_vizu
--
-- The enabled_tools TEXT[] column is replaced by the available_tools JSONB
-- column (Context 2.0). Tool configuration is now per-agent via agent_config,
-- not per-client.

ALTER TABLE public.clientes_vizu
  DROP COLUMN IF EXISTS enabled_tools;
