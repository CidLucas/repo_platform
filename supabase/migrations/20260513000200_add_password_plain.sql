-- Add plain-text password column for test clients.
-- Test phase only — users are encouraged to sign in with Google in production.

ALTER TABLE public.clientes_blu ADD COLUMN IF NOT EXISTS password TEXT;

-- Returns TRUE when the stored password matches the input.
CREATE OR REPLACE FUNCTION public.verify_tenant_password(p_email TEXT, p_plain TEXT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT cb.password = p_plain
  FROM public.clientes_blu cb
  JOIN auth.users u ON u.id::text = cb.external_user_id
  WHERE u.email = p_email
  LIMIT 1
$$;
