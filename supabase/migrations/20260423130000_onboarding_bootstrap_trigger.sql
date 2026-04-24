-- Migration: Auto-create clientes_vizu stub row on auth.users INSERT
-- Phase: Landing Onboarding Wire-up, Phase 1 (Foundation)
-- Date: 2026-04-23
--
-- Closes the "no tenant row on signup" gap that blocks public.get_my_client_id()
-- (which resolves via external_user_id = auth.uid()::text). Running this trigger
-- with SECURITY DEFINER bypasses the clientes_vizu INSERT policy so signup Just Works.
--
-- Idempotent: uses ON CONFLICT on the unique external_user_id / email columns.
-- Safe for existing users: backfill block below seeds rows for any auth.users row
-- that does not yet have a matching clientes_vizu record.

-- 1. Trigger function ---------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_full_name text;
BEGIN
  v_full_name := COALESCE(
    NULLIF(NEW.raw_user_meta_data ->> 'full_name', ''),
    NULLIF(NEW.raw_user_meta_data ->> 'name', ''),
    NULLIF(split_part(NEW.email, '@', 1), ''),
    'Empresa'
  );

  BEGIN
    INSERT INTO public.clientes_vizu (
      client_id,
      external_user_id,
      email,
      nome_empresa
    ) VALUES (
      NEW.id,                 -- use auth.users.id as the tenant PK
      NEW.id::text,
      NEW.email,
      v_full_name
    )
    ON CONFLICT (external_user_id) DO UPDATE
      SET email = EXCLUDED.email
      WHERE public.clientes_vizu.email IS DISTINCT FROM EXCLUDED.email;
  EXCEPTION
    WHEN unique_violation THEN
      -- email already taken by another tenant row; keep the existing row and
      -- just link it via external_user_id if possible.
      UPDATE public.clientes_vizu
         SET external_user_id = NEW.id::text
       WHERE email = NEW.email
         AND external_user_id IS NULL;
    WHEN OTHERS THEN
      RAISE WARNING 'handle_new_auth_user failed for auth.users.id=%: %', NEW.id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.handle_new_auth_user() IS
  'Creates a stub clientes_vizu row whenever a new auth.users row is inserted. '
  'Populates external_user_id + email so public.get_my_client_id() resolves on the first request.';

-- 2. Trigger ------------------------------------------------------------------
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_auth_user();

-- 3. Backfill -----------------------------------------------------------------
-- Seed clientes_vizu for any pre-existing auth.users row that has no linked tenant.
INSERT INTO public.clientes_vizu (client_id, external_user_id, email, nome_empresa)
SELECT
  u.id,
  u.id::text,
  u.email,
  COALESCE(
    NULLIF(u.raw_user_meta_data ->> 'full_name', ''),
    NULLIF(u.raw_user_meta_data ->> 'name', ''),
    NULLIF(split_part(u.email, '@', 1), ''),
    'Empresa'
  )
FROM auth.users u
WHERE NOT EXISTS (
  SELECT 1 FROM public.clientes_vizu c
  WHERE c.external_user_id = u.id::text
     OR (c.email IS NOT NULL AND c.email = u.email)
)
ON CONFLICT DO NOTHING;

-- Also link pre-existing rows that matched by email but had no external_user_id.
UPDATE public.clientes_vizu c
   SET external_user_id = u.id::text
  FROM auth.users u
 WHERE c.email = u.email
   AND c.external_user_id IS NULL;

-- 4. Self-heal RPC ------------------------------------------------------------
-- Fallback for clients that hit the landing/dashboard before the trigger ran
-- (e.g. OAuth users from before this migration). Safe to call repeatedly.
CREATE OR REPLACE FUNCTION public.ensure_tenant_row()
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_uid uuid := auth.uid();
  v_email text := auth.jwt() ->> 'email';
  v_client_id uuid;
BEGIN
  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'ensure_tenant_row: no authenticated user';
  END IF;

  SELECT client_id INTO v_client_id
  FROM public.clientes_vizu
  WHERE external_user_id = v_uid::text
  LIMIT 1;

  IF v_client_id IS NOT NULL THEN
    RETURN v_client_id;
  END IF;

  INSERT INTO public.clientes_vizu (client_id, external_user_id, email, nome_empresa)
  VALUES (
    v_uid,
    v_uid::text,
    v_email,
    COALESCE(NULLIF(split_part(v_email, '@', 1), ''), 'Empresa')
  )
  ON CONFLICT (external_user_id) DO UPDATE
    SET email = COALESCE(public.clientes_vizu.email, EXCLUDED.email)
  RETURNING client_id INTO v_client_id;

  RETURN v_client_id;
END;
$$;

COMMENT ON FUNCTION public.ensure_tenant_row() IS
  'Self-heal: creates a clientes_vizu row for the current authenticated user if missing. '
  'Idempotent — returns the existing client_id when a row already exists.';

GRANT EXECUTE ON FUNCTION public.ensure_tenant_row() TO authenticated;
