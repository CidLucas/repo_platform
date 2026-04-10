-- Migration: Add admin role support
-- Adds is_admin column to clientes_vizu and a helper RPC to set app_metadata.role

-- 1. Add is_admin boolean column to clientes_vizu (defaults to false)
ALTER TABLE public.clientes_vizu
  ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;

-- 2. Create an enum type for user roles (used as documentation / future constraint)
DO $$ BEGIN
  CREATE TYPE public.user_role AS ENUM ('user', 'admin');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

-- 3. RPC: set_user_role — allows service_role to set app_metadata.role on a Supabase user
--    This is called by backend admin tooling, NOT by end users.
CREATE OR REPLACE FUNCTION public.set_user_role(
  target_user_id UUID,
  new_role TEXT
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF new_role NOT IN ('user', 'admin') THEN
    RAISE EXCEPTION 'Invalid role: %. Must be user or admin.', new_role;
  END IF;

  UPDATE auth.users
  SET raw_app_meta_data = raw_app_meta_data || jsonb_build_object('role', new_role)
  WHERE id = target_user_id;

  -- Keep clientes_vizu.is_admin in sync
  UPDATE public.clientes_vizu
  SET is_admin = (new_role = 'admin')
  WHERE client_id = target_user_id;
END;
$$;

-- Only service_role can call this
REVOKE ALL ON FUNCTION public.set_user_role(UUID, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.set_user_role(UUID, TEXT) FROM anon;
REVOKE ALL ON FUNCTION public.set_user_role(UUID, TEXT) FROM authenticated;

-- 4. Index for quick admin lookups
CREATE INDEX IF NOT EXISTS idx_clientes_vizu_is_admin
  ON public.clientes_vizu (is_admin)
  WHERE is_admin = true;
