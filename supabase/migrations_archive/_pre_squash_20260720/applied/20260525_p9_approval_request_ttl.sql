-- ============================================================================
-- Sprint 4 / D1 — TTL para approval_requests
-- ============================================================================
-- Problema: aprovações pendentes acumulam indefinidamente (60 pendentes hoje).
--   Sem expiração, side-effects de rotinas podem disparar tarde demais (ex:
--   redispatch_routine_after_approval gatilhado 30 dias depois).
--
-- Mudanças:
--   1) Backfill expires_at = created_at + 48h para pendentes sem TTL.
--   2) Default agora é now() + interval '48 hours' para novas rows.
--   3) Função public.expire_pending_approvals() marca status='expired'.
--   4) Ampliar status_check para incluir 'expired'.
--   5) Trigger NÃO dispara redispatch nem document_review actions (status
--      'expired' é distinto de 'approved'/'rejected' — checks dos triggers
--      existentes já guardam contra isso, validado em revisão).
--   6) Agendar pg_cron de 10 em 10 minutos.
--
-- IMPORTANTE: este arquivo NÃO tem BEGIN/COMMIT embutidos para permitir smoke
-- test envelopado em transação externa (lição aprendida com P8).
--
-- Auditoria 2026-05-25:
--   - 60 pendentes / 7 aprovadas; 0 com expires_at; 0 com action_type que
--     dispararia side-effect via update_of_status (não há routine_hitl,
--     document_review, sale_approval pendentes — backfill seguro).
--   - pg_cron 1.6.4 disponível.
--
-- NÃO APLICAR AUTOMATICAMENTE.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1) Ampliar CHECK constraint
-- ---------------------------------------------------------------------------
ALTER TABLE public.approval_requests
  DROP CONSTRAINT IF EXISTS approval_requests_status_check;

ALTER TABLE public.approval_requests
  ADD CONSTRAINT approval_requests_status_check
  CHECK (status = ANY (ARRAY[
    'pending'::text,
    'approved'::text,
    'rejected'::text,
    'cancelled'::text,
    'expired'::text
  ]));

-- ---------------------------------------------------------------------------
-- 2) Default expires_at
-- ---------------------------------------------------------------------------
ALTER TABLE public.approval_requests
  ALTER COLUMN expires_at SET DEFAULT (now() + interval '48 hours');

-- ---------------------------------------------------------------------------
-- 3) Backfill pendentes sem expires_at
--    -> CARÊNCIA: 48h a partir de AGORA (não de created_at), para não
--       expirar em massa 48+ aprovações antigas na primeira execução do cron
--       (auditoria: 48/61 pendentes têm created_at > 48h atrás).
-- ---------------------------------------------------------------------------
UPDATE public.approval_requests
SET expires_at = now() + interval '48 hours'
WHERE expires_at IS NULL
  AND status = 'pending';

-- ---------------------------------------------------------------------------
-- 4) Função: expirar pendentes vencidas
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.expire_pending_approvals()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $function$
DECLARE
  _expired int := 0;
  _row record;
BEGIN
  FOR _row IN
    SELECT id, client_id, action_type, agent_slug,
           COALESCE(NULLIF(title,''), action_type) AS friendly_title
    FROM public.approval_requests
    WHERE status = 'pending'
      AND expires_at IS NOT NULL
      AND expires_at < now()
    FOR UPDATE SKIP LOCKED
  LOOP
    UPDATE public.approval_requests
    SET status     = 'expired',
        decided_at = now(),
        decided_by = 'system_ttl'
    WHERE id = _row.id;

    -- Notificar dono (in_app apenas — operacional, sem email)
    INSERT INTO public.notifications (
      client_id, type, title, body,
      agent_slug, related_entity_type, related_entity_id,
      urgency_level, channels
    ) VALUES (
      _row.client_id,
      'approval_expired',
      'Aprovação expirou sem resposta',
      format('A aprovação "%s" expirou após 48h sem decisão.', _row.friendly_title),
      COALESCE(_row.agent_slug, 'system'),
      'approval_request',
      _row.id,
      'normal',
      ARRAY['in_app']::text[]
    );

    _expired := _expired + 1;
  END LOOP;

  IF _expired > 0 THEN
    RAISE NOTICE '[approval_ttl] expired % approvals at %', _expired, now();
  END IF;

  RETURN _expired;
END;
$function$;

COMMENT ON FUNCTION public.expire_pending_approvals() IS
  'Marca approval_requests pendentes vencidas (expires_at < now()) como '
  '"expired" e cria notification in_app. Chamada por pg_cron a cada 10 min.';

REVOKE ALL ON FUNCTION public.expire_pending_approvals() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.expire_pending_approvals() TO postgres;

-- ---------------------------------------------------------------------------
-- 5) Agendar pg_cron — 10 em 10 minutos
--    Idempotente: remove jobname anterior se existir
-- ---------------------------------------------------------------------------
DO $cron$
DECLARE
  _existing bigint;
BEGIN
  SELECT jobid INTO _existing
  FROM cron.job
  WHERE jobname = 'expire_pending_approvals_10min';

  IF _existing IS NOT NULL THEN
    PERFORM cron.unschedule(_existing);
  END IF;

  PERFORM cron.schedule(
    'expire_pending_approvals_10min',
    '*/10 * * * *',
    $$ SELECT public.expire_pending_approvals(); $$
  );
END;
$cron$;

-- ============================================================================
-- Verificação pós-apply:
--
--   SELECT pg_get_constraintdef(oid) FROM pg_constraint
--   WHERE conname='approval_requests_status_check';
--
--   SELECT column_default FROM information_schema.columns
--   WHERE table_name='approval_requests' AND column_name='expires_at';
--
--   SELECT status, count(*), count(expires_at) AS with_ttl
--   FROM approval_requests GROUP BY 1;
--
--   SELECT jobid, schedule, jobname FROM cron.job
--   WHERE jobname='expire_pending_approvals_10min';
--
--   -- Forçar expiração de teste (REVERSIBLE — rodar em transação):
--   BEGIN;
--   UPDATE approval_requests SET expires_at = now() - interval '1 min'
--   WHERE status='pending' LIMIT 1;
--   SELECT public.expire_pending_approvals();
--   SELECT status, decided_by FROM approval_requests WHERE decided_by='system_ttl';
--   ROLLBACK;
-- ============================================================================
