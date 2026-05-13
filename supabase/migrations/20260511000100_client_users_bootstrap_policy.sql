-- Fix the client_users INSERT policy to allow bootstrapping:
-- existing clients have no rows yet, so they'd be locked out of inserting their owner row.
-- Allow the insert if no rows exist yet for this client_id (first row = owner bootstrap).

DROP POLICY IF EXISTS "client_users_insert" ON "public"."client_users";

CREATE POLICY "client_users_insert"
  ON "public"."client_users"
  FOR INSERT
  WITH CHECK (
    client_id = public.get_my_client_id()
    AND (
      -- Bootstrap: no users exist yet for this workspace → allow (will be the owner row)
      NOT EXISTS (
        SELECT 1 FROM public.client_users WHERE client_id = public.get_my_client_id()
      )
      -- Or the inserter is already an owner/admin of this workspace
      OR EXISTS (
        SELECT 1 FROM public.client_users cu
        WHERE cu.client_id = public.get_my_client_id()
          AND cu.auth_user_id = auth.uid()
          AND cu.role IN ('owner', 'admin')
      )
    )
  );
