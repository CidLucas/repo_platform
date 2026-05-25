-- Trigger: when polp_integrations.status becomes 'OUTDATED', immediately call sync
CREATE OR REPLACE FUNCTION public.trg_polp_outdated_enqueue_sync()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Only act when transitioning INTO OUTDATED (not already OUTDATED)
  IF NEW.status = 'OUTDATED' AND (OLD.status IS DISTINCT FROM 'OUTDATED') THEN
    PERFORM analytics_v2.sync_polp_transactions(NEW.client_id);
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_polp_outdated_sync ON public.polp_integrations;
CREATE TRIGGER trg_polp_outdated_sync
  AFTER UPDATE OF status ON public.polp_integrations
  FOR EACH ROW
  EXECUTE FUNCTION public.trg_polp_outdated_enqueue_sync();
