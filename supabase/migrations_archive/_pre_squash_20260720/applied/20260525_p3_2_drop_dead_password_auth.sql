-- 20260525_p3_2_drop_dead_password_auth.sql
-- P3.2: Drop dead tenant password column + verify_tenant_password function.
-- Audit: 0 callers in repo, 0 rows in clientes_blu with non-null password.
-- Real auth is via Supabase Auth (auth.users + JWT). This is leftover from a
-- prior auth scheme and constitutes attack surface (plain-text password compare).

BEGIN;

DROP FUNCTION IF EXISTS public.verify_tenant_password(text, text);

-- The active_clientes_blu view references the password column; rebuild it
-- without password before dropping the column.
DROP VIEW IF EXISTS public.active_clientes_blu;

ALTER TABLE public.clientes_blu DROP COLUMN IF EXISTS password;

CREATE VIEW public.active_clientes_blu AS
  SELECT
    client_id,
    api_key,
    nome_empresa,
    tipo_cliente,
    tier,
    collection_rag,
    created_at,
    updated_at,
    external_user_id,
    onboarding_state,
    onboarding_completed_at,
    company_profile,
    brand_voice,
    team_structure,
    policies,
    data_schema,
    available_tools,
    cpf_cnpj,
    deleted_at
  FROM public.clientes_blu
  WHERE deleted_at IS NULL;

COMMIT;
