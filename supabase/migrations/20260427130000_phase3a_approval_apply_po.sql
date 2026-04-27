-- Migration: Phase 3A (P3.1) — apply approval decisions to purchase_orders.
--
-- When `decide_approval()` resolves an `approval_requests` row for the RFQ
-- agent, this trigger keeps the linked `purchase_orders` row in sync:
--
--   action='create_purchase_order'  approved → PO.status = 'draft'   (now eligible for approve_purchase_order)
--                                   rejected → PO.status = 'cancelled'
--
--   action='approve_purchase_order' approved → PO.status = 'approved' + approved_by/approved_at
--                                   rejected → PO.status = 'draft'
--
-- Tickets: BLU-MVP-040 (P3.1).

BEGIN;

-- ─────────────────────────────────────────────────────────────────────
-- 1. Extend purchase_orders.status to allow 'cancelled'
-- ─────────────────────────────────────────────────────────────────────

ALTER TABLE public.purchase_orders
  DROP CONSTRAINT IF EXISTS purchase_orders_status_check;

ALTER TABLE public.purchase_orders
  ADD CONSTRAINT purchase_orders_status_check
  CHECK (status IN ('draft', 'pending_approval', 'approved', 'sent', 'cancelled'));

-- ─────────────────────────────────────────────────────────────────────
-- 2. Apply trigger
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.tg_approval_apply_purchase_order()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_po_id uuid;
BEGIN
  -- Only react to a fresh decision (pending → approved|rejected).
  IF NEW.status NOT IN ('approved', 'rejected') THEN
    RETURN NEW;
  END IF;
  IF OLD.status = NEW.status THEN
    RETURN NEW;
  END IF;
  IF NEW.action NOT IN ('create_purchase_order', 'approve_purchase_order') THEN
    RETURN NEW;
  END IF;

  v_po_id := NULLIF(NEW.payload ->> 'po_id', '')::uuid;
  IF v_po_id IS NULL THEN
    RAISE LOG 'tg_approval_apply_purchase_order: approval % action=% missing payload.po_id',
              NEW.id, NEW.action;
    RETURN NEW;
  END IF;

  IF NEW.action = 'create_purchase_order' THEN
    IF NEW.status = 'approved' THEN
      UPDATE public.purchase_orders
         SET status = 'draft'
       WHERE id = v_po_id
         AND client_id = NEW.client_id
         AND status = 'pending_approval';
    ELSE  -- rejected
      UPDATE public.purchase_orders
         SET status = 'cancelled'
       WHERE id = v_po_id
         AND client_id = NEW.client_id
         AND status IN ('pending_approval', 'draft');
    END IF;

  ELSIF NEW.action = 'approve_purchase_order' THEN
    IF NEW.status = 'approved' THEN
      UPDATE public.purchase_orders
         SET status      = 'approved',
             approved_by = NEW.decided_by,
             approved_at = COALESCE(NEW.decided_at, now())
       WHERE id = v_po_id
         AND client_id = NEW.client_id
         AND status IN ('pending_approval', 'draft');
    ELSE  -- rejected
      UPDATE public.purchase_orders
         SET status = 'draft'
       WHERE id = v_po_id
         AND client_id = NEW.client_id
         AND status = 'pending_approval';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS approval_apply_purchase_order ON public.approval_requests;
CREATE TRIGGER approval_apply_purchase_order
  AFTER UPDATE ON public.approval_requests
  FOR EACH ROW
  WHEN (OLD.status IS DISTINCT FROM NEW.status)
  EXECUTE FUNCTION public.tg_approval_apply_purchase_order();

COMMENT ON FUNCTION public.tg_approval_apply_purchase_order IS
  'Phase 3A (P3.1): mirror Approval Engine decisions onto purchase_orders.status.';

COMMIT;
