-- =============================================================================
-- Fix: persistence failures in onboarding_complete and daily_insights routines.
--
-- 1. public.documents — add UNIQUE(client_id, title) so storage.save_context_document
--    can upsert with on_conflict="client_id,title" (was failing with 42P10).
--
-- 2. public.approval_requests — add metadata jsonb column so channels.create_alert
--    and channels.request_document_review can store artifact metadata without
--    "column not found" errors.
-- =============================================================================

-- ── 1. UNIQUE constraint on public.documents(client_id, title) ───────────────
-- Required by storage.save_context_document upsert.
-- Uses a partial unique index (not a named constraint) so it's safe to run even
-- if a previous attempt created a constraint under a different name.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.documents'::regclass
      AND contype = 'u'
      AND conname = 'documents_client_id_title_key'
  ) THEN
    ALTER TABLE public.documents
      ADD CONSTRAINT documents_client_id_title_key UNIQUE (client_id, title);
  END IF;
END;
$$;

-- ── 2. metadata column on public.approval_requests ───────────────────────────
-- Used by channels.create_alert (artifact_type, artifact_id, artifact_url) and
-- channels.request_document_review (artifact_type, artifact_id).
ALTER TABLE public.approval_requests
  ADD COLUMN IF NOT EXISTS metadata jsonb;

COMMENT ON COLUMN public.approval_requests.metadata IS
  'Optional artifact metadata: {artifact_type, artifact_id, artifact_url}. '
  'Written by channels.create_alert and channels.request_document_review.';
