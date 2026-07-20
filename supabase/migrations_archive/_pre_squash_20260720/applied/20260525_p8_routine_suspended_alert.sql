-- ============================================================================
-- Sprint 3 / C1 — Alerta de circuit breaker (status='suspended' em rotinas)
-- ============================================================================
-- Contexto:
--   record_routine_failure(client_id, routine_id) já existe no baseline e tenta
--   setar status='suspended' após N falhas consecutivas, MAS:
--     1. CHECK constraint client_routines_status_check NAO permite 'suspended'
--        → circuit breaker está silenciosamente quebrado (violaria constraint
--          em runtime quando atingisse threshold).
--     2. A função em si nao foi persistida no schema live (squash recente
--        removeu — confirmado via pg_proc).
--     3. Nao existe sinal para operadores quando rotina é suspensa.
--
-- Mudanças:
--   1) Ampliar status_check para incluir 'suspended'.
--   2) (Re)criar record_routine_failure idempotente.
--   3) Trigger AFTER UPDATE em client_routines que, quando status muda para
--      'suspended', insere row em notifications (in_app + email) com urgência
--      'high', associando ao client_id e à própria rotina (related_entity_*).
--
-- Auditoria 2026-05-25:
--   - psql \d client_routines confirmou status_check sem 'suspended'.
--   - SELECT pg_get_functiondef('record_routine_failure') retornou 0 rows.
--   - notifications schema validado (client_id NOT NULL, type text, urgency_level,
--     channels text[] default ['in_app'], related_entity_type/id).
--
-- NÃO APLICAR AUTOMATICAMENTE.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Ampliar CHECK constraint para aceitar 'suspended'
-- ---------------------------------------------------------------------------
ALTER TABLE public.client_routines
  DROP CONSTRAINT IF EXISTS client_routines_status_check;

ALTER TABLE public.client_routines
  ADD CONSTRAINT client_routines_status_check
  CHECK (status = ANY (ARRAY[
    'active'::text,
    'inactive'::text,
    'pending_approval'::text,
    'draft'::text,
    'suspended'::text
  ]));

-- ---------------------------------------------------------------------------
-- 2) (Re)criar circuit breaker: record_routine_failure
--    Idempotente — CREATE OR REPLACE.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.record_routine_failure(
  p_client_id    uuid,
  p_routine_id   text,
  p_max_failures integer DEFAULT 3
)
RETURNS text
LANGUAGE plpgsql
AS $function$
DECLARE
  _new_failures int;
  _new_status   text;
BEGIN
  UPDATE public.client_routines
  SET consecutive_failures = consecutive_failures + 1
  WHERE client_id  = p_client_id
    AND routine_id = p_routine_id
  RETURNING consecutive_failures INTO _new_failures;

  IF _new_failures IS NULL THEN
    RETURN 'not_found';
  END IF;

  IF _new_failures >= p_max_failures THEN
    UPDATE public.client_routines
    SET status = 'suspended',
        active = false
    WHERE client_id  = p_client_id
      AND routine_id = p_routine_id;
    _new_status := 'suspended';
    RAISE NOTICE '[circuit_breaker] routine % client % suspended after % failures',
      p_routine_id, p_client_id, _new_failures;
  ELSE
    _new_status := 'active';
  END IF;

  RETURN _new_status;
END;
$function$;

COMMENT ON FUNCTION public.record_routine_failure(uuid, text, integer) IS
  'Circuit breaker: incrementa consecutive_failures e suspende rotina quando '
  'threshold atingido. Chamada pelo agent_api após falha em execução.';

-- ---------------------------------------------------------------------------
-- 3) Trigger: notificar quando rotina vai para suspended
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.notify_routine_suspended()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $function$
DECLARE
  _routine_name text;
BEGIN
  -- Apenas transições para 'suspended' (não re-notifica se já estava)
  IF NEW.status <> 'suspended' OR OLD.status = 'suspended' THEN
    RETURN NEW;
  END IF;

  -- Nome amigável: fallback p/ routine_id se name vazio
  _routine_name := COALESCE(NULLIF(NEW.name, ''), NEW.routine_id);

  INSERT INTO public.notifications (
    client_id,
    type,
    title,
    body,
    agent_slug,
    related_entity_type,
    related_entity_id,
    urgency_level,
    channels
  ) VALUES (
    NEW.client_id,
    'routine_suspended',
    'Rotina suspensa por falhas consecutivas',
    format(
      'A rotina "%s" foi suspensa automaticamente após %s falhas consecutivas. '
      'Revise a configuração e reative manualmente.',
      _routine_name,
      NEW.consecutive_failures
    ),
    'system',
    'client_routine',
    NEW.id,
    'high',
    ARRAY['in_app','email']::text[]
  );

  RETURN NEW;
END;
$function$;

COMMENT ON FUNCTION public.notify_routine_suspended() IS
  'Trigger fn: insere notification quando client_routines.status muda para '
  '"suspended" (circuit breaker). Lê NEW.consecutive_failures.';

-- EXECUTE só para roles que precisam invocar via trigger (postgres/supabase_admin)
REVOKE ALL ON FUNCTION public.notify_routine_suspended() FROM PUBLIC;

DROP TRIGGER IF EXISTS trg_client_routines_suspended_notify ON public.client_routines;

CREATE TRIGGER trg_client_routines_suspended_notify
  AFTER UPDATE OF status ON public.client_routines
  FOR EACH ROW
  WHEN (NEW.status = 'suspended' AND OLD.status IS DISTINCT FROM 'suspended')
  EXECUTE FUNCTION public.notify_routine_suspended();

COMMIT;

-- ============================================================================
-- Verificação pós-apply:
--
--   -- check constraint atualizado
--   SELECT pg_get_constraintdef(oid)
--   FROM pg_constraint
--   WHERE conname='client_routines_status_check';
--
--   -- função recriada
--   SELECT proname FROM pg_proc
--   WHERE proname IN ('record_routine_failure','notify_routine_suspended');
--
--   -- trigger ativo
--   SELECT tgname, tgenabled FROM pg_trigger
--   WHERE tgname='trg_client_routines_suspended_notify';
--
--   -- smoke (rollback ao final):
--   BEGIN;
--   UPDATE client_routines SET status='suspended', consecutive_failures=3
--   WHERE id=(SELECT id FROM client_routines WHERE status='active' LIMIT 1);
--   SELECT type, title, urgency_level, channels, created_at
--   FROM notifications WHERE type='routine_suspended' ORDER BY created_at DESC LIMIT 1;
--   ROLLBACK;
-- ============================================================================
