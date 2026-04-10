-- Fix RLS policies on vector_db.documents table
-- The client_id column stores clientes_vizu.client_id, NOT auth.uid().
-- We reuse the public.get_client_id_for_auth_user() function created in
-- 20260321_fix_kb_storage_rls.sql to resolve auth.uid() → client_id.

-- DROP existing user-facing policies (keep service_role policy untouched)
DROP POLICY IF EXISTS "Users can insert own documents" ON vector_db.documents;
DROP POLICY IF EXISTS "Users can view own or platform documents" ON vector_db.documents;
DROP POLICY IF EXISTS "Users can update own documents" ON vector_db.documents;
DROP POLICY IF EXISTS "Users can delete own documents" ON vector_db.documents;

-- RECREATE with resolved client_id (cast text → uuid for comparison)
CREATE POLICY "Users can insert own documents"
  ON vector_db.documents FOR INSERT
  WITH CHECK (
    client_id = auth.uid()
    OR client_id = public.get_client_id_for_auth_user()::uuid
  );

CREATE POLICY "Users can view own or platform documents"
  ON vector_db.documents FOR SELECT
  USING (
    scope = 'platform'
    OR client_id = auth.uid()
    OR client_id = public.get_client_id_for_auth_user()::uuid
  );

CREATE POLICY "Users can update own documents"
  ON vector_db.documents FOR UPDATE
  USING (
    client_id = auth.uid()
    OR client_id = public.get_client_id_for_auth_user()::uuid
  );

CREATE POLICY "Users can delete own documents"
  ON vector_db.documents FOR DELETE
  USING (
    client_id = auth.uid()
    OR client_id = public.get_client_id_for_auth_user()::uuid
  );
