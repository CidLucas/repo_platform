-- ─────────────────────────────────────────────────────────────────────────────
-- Fase 1 Quick Win · HITL Documental
-- Adds status column to public.documents and a trigger that publishes
-- a draft document when its linked approval_request is approved.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Add status column (draft | published | archived) with default 'published'
--    so existing documents stay visible.
ALTER TABLE public.documents
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'published'
  CHECK (status IN ('draft', 'published', 'archived'));

-- 2. Trigger function: when approval_requests.status flips to 'approved'
--    and action_type = 'document_review', publish the linked document.
CREATE OR REPLACE FUNCTION public.on_document_review_approved()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_document_id uuid;
BEGIN
  -- Only act on document_review approvals
  IF NEW.action_type <> 'document_review' THEN
    RETURN NEW;
  END IF;
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  v_document_id := (NEW.payload->>'document_id')::uuid;
  IF v_document_id IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    UPDATE public.documents
      SET status = 'published', updated_at = now()
    WHERE id = v_document_id
      AND client_id = NEW.client_id
      AND status = 'draft';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_document_review_approved] failed for doc=%: %', v_document_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;

-- 3. Attach the trigger (drop first to make idempotent)
DROP TRIGGER IF EXISTS trg_document_review_approved ON public.approval_requests;
CREATE TRIGGER trg_document_review_approved
  AFTER UPDATE OF status ON public.approval_requests
  FOR EACH ROW
  EXECUTE FUNCTION public.on_document_review_approved();

-- 4. When approval is rejected, mark document as archived (won't appear in lists)
CREATE OR REPLACE FUNCTION public.on_document_review_rejected()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_document_id uuid;
BEGIN
  IF NEW.action_type <> 'document_review' THEN
    RETURN NEW;
  END IF;
  IF OLD.status = NEW.status OR NEW.status <> 'rejected' THEN
    RETURN NEW;
  END IF;

  v_document_id := (NEW.payload->>'document_id')::uuid;
  IF v_document_id IS NULL THEN
    RETURN NEW;
  END IF;

  BEGIN
    UPDATE public.documents
      SET status = 'archived', updated_at = now()
    WHERE id = v_document_id
      AND client_id = NEW.client_id
      AND status = 'draft';
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_document_review_rejected] failed for doc=%: %', v_document_id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_document_review_rejected ON public.approval_requests;
CREATE TRIGGER trg_document_review_rejected
  AFTER UPDATE OF status ON public.approval_requests
  FOR EACH ROW
  EXECUTE FUNCTION public.on_document_review_rejected();

-- 5. RLS: drafts are visible only to the owning client (same as published)
-- The existing documents RLS policies already filter by client_id, so no change needed.
-- But we need to update fetchRecentDocuments to exclude drafts from the 'ativos' tab
-- (handled in frontend).

COMMENT ON COLUMN public.documents.status IS
  'draft = gerado por agente aguardando aprovação HITL | published = aprovado/manual | archived = rejeitado';
