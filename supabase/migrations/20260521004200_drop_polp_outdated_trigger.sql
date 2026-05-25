
-- Drop trigger desnecessário: sync já coberto por polp-webhook (tempo real) + pg_cron 6h
DROP TRIGGER IF EXISTS trg_polp_outdated_sync ON public.polp_integrations;
DROP FUNCTION IF EXISTS public.trg_polp_outdated_enqueue_sync();
