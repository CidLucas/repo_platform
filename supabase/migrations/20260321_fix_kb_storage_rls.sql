-- Migration: Fix knowledge-base storage RLS policies
-- Problem: auth.uid() returns Supabase auth user ID, but storage path uses
--          clientes_vizu.client_id. These are different UUIDs.
-- Solution: Helper function resolves auth user → client_id, policies accept both.

-- 1. Create resolver function
CREATE OR REPLACE FUNCTION public.get_client_id_for_auth_user()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT client_id::text
  FROM public.clientes_vizu
  WHERE external_user_id = auth.uid()::text
  LIMIT 1;
$$;

-- 2. Recreate knowledge-base policies

DROP POLICY IF EXISTS "KB: Users can upload to own folder" ON storage.objects;
CREATE POLICY "KB: Users can upload to own folder" ON storage.objects
  FOR INSERT
  WITH CHECK (
    bucket_id = 'knowledge-base'
    AND (
      (storage.foldername(name))[1] = (auth.uid())::text
      OR (storage.foldername(name))[1] = public.get_client_id_for_auth_user()
    )
  );

DROP POLICY IF EXISTS "KB: Users can read own files" ON storage.objects;
CREATE POLICY "KB: Users can read own files" ON storage.objects
  FOR SELECT
  USING (
    bucket_id = 'knowledge-base'
    AND (
      (storage.foldername(name))[1] = (auth.uid())::text
      OR (storage.foldername(name))[1] = public.get_client_id_for_auth_user()
    )
  );

DROP POLICY IF EXISTS "KB: Users can update own files" ON storage.objects;
CREATE POLICY "KB: Users can update own files" ON storage.objects
  FOR UPDATE
  USING (
    bucket_id = 'knowledge-base'
    AND (
      (storage.foldername(name))[1] = (auth.uid())::text
      OR (storage.foldername(name))[1] = public.get_client_id_for_auth_user()
    )
  );

DROP POLICY IF EXISTS "KB: Users can delete own files" ON storage.objects;
CREATE POLICY "KB: Users can delete own files" ON storage.objects
  FOR DELETE
  USING (
    bucket_id = 'knowledge-base'
    AND (
      (storage.foldername(name))[1] = (auth.uid())::text
      OR (storage.foldername(name))[1] = public.get_client_id_for_auth_user()
    )
  );
