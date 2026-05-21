-- ─────────────────────────────────────────────────────────────────────────────
-- INF-03 · sale_approved event trigger
--
-- When an approval_request transitions to status='approved' and the
-- action_type identifies a sale/order, fire the 'sale_approved' domain event
-- so any client_routines subscribed to that event (e.g. Follow-up de Vendas)
-- are automatically enqueued.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.on_approval_sale_approved()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Only fire when status transitions to 'approved'
  IF OLD.status = NEW.status OR NEW.status <> 'approved' THEN
    RETURN NEW;
  END IF;

  -- Only for sale/order action types
  IF NEW.action_type NOT IN ('sale', 'venda', 'pedido') THEN
    RETURN NEW;
  END IF;

  BEGIN
    PERFORM public.fire_event_for_client(
      'sale_approved',
      NEW.client_id,
      jsonb_build_object('approval_id', NEW.id, 'payload', NEW.payload)
    );
  EXCEPTION WHEN others THEN
    RAISE WARNING '[on_approval_sale_approved] fire_event failed for approval=%: %',
      NEW.id, SQLERRM;
  END;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sale_approved ON public.approval_requests;
CREATE TRIGGER trg_sale_approved
  AFTER UPDATE ON public.approval_requests
  FOR EACH ROW
  EXECUTE FUNCTION public.on_approval_sale_approved();
