-- =============================================================================
-- Migration: Phase 7 — Storage buckets and object policies baseline
-- Date: 2026-04-28
-- Purpose: Create file storage buckets and set up bucket-level RLS policies
-- =============================================================================

BEGIN;

-- ============================================================================
-- Create storage buckets
-- ============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES
  ('knowledge-base', 'knowledge-base', false, 52428800,
   ARRAY['application/pdf','text/plain','text/markdown',
         'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
         'application/vnd.openxmlformats-officedocument.presentationml.presentation']),
  ('file-uploads',   'file-uploads',   false, 52428800,
   NULL)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- RLS policies for storage objects (client-scoped via folder structure)
-- ============================================================================

CREATE POLICY "client kb access" ON storage.objects FOR ALL TO authenticated
  USING (bucket_id = 'knowledge-base' AND (storage.foldername(name))[1] = public.get_my_client_id()::text)
  WITH CHECK (bucket_id = 'knowledge-base' AND (storage.foldername(name))[1] = public.get_my_client_id()::text);

CREATE POLICY "client file access" ON storage.objects FOR ALL TO authenticated
  USING (bucket_id = 'file-uploads' AND (storage.foldername(name))[1] = public.get_my_client_id()::text)
  WITH CHECK (bucket_id = 'file-uploads' AND (storage.foldername(name))[1] = public.get_my_client_id()::text);

COMMIT;
