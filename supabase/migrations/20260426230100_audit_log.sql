-- Migration: audit_log table + record_audit() RPC
-- Phase: Blu MVP, Phase 0 (F0.4) — ticket BLU-MVP-002
-- Date: 2026-04-26
--
-- Single canonical event table for every mutating MCP tool, approval
-- decision, scheduled report dispatch, and outbound message. Read by:
--
--   - public.get_admin_indicators(p_period) → "Auditabilidade" KPI
--     (kpi-catalog.md §6 Administrativo);
--   - HITL console;
--   - Grafana ("Blu MVP" folder) via OTel→Loki extraction.
--
-- Retention: 7 years (LGPD Art. 18 + Brazilian fiscal). Sweeper to be
-- added when retention column is needed; for MVP keep all rows.

BEGIN;

CREATE TABLE IF NOT EXISTS public.audit_log (
  id           bigserial   PRIMARY KEY,
  client_id    uuid        REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
  actor_user   uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
  actor_kind   text        NOT NULL DEFAULT 'user'
    CHECK (actor_kind IN ('user', 'agent', 'system', 'cron', 'webhook')),
  agent_slug   text,
  action       text        NOT NULL,
  resource     text,
  resource_id  text,
  payload      jsonb       NOT NULL DEFAULT '{}'::jsonb,
  payload_hash text        GENERATED ALWAYS AS (encode(digest(payload::text, 'sha256'), 'hex')) STORED,
  decision     text,
  outcome      text        NOT NULL DEFAULT 'success'
    CHECK (outcome IN ('success', 'failure', 'partial', 'pending')),
  session_id   text,
  trace_id     text,
  span_id      text,
  ip_address   inet,
  user_agent   text,
  created_at   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.audit_log IS
  'Append-only audit trail for every state-changing action across MCP tools, '
  'approvals, and scheduled jobs. Retention 7y per LGPD Art. 18.';

CREATE INDEX IF NOT EXISTS idx_audit_log_client_recent
  ON public.audit_log (client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_action
  ON public.audit_log (client_id, action);

CREATE INDEX IF NOT EXISTS idx_audit_log_resource
  ON public.audit_log (resource, resource_id)
  WHERE resource IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_log_trace
  ON public.audit_log (trace_id)
  WHERE trace_id IS NOT NULL;

-- RLS -------------------------------------------------------------------------
-- Append-only from the application layer: all writes go through
-- record_audit() (SECURITY DEFINER). Direct INSERT is denied for clients.

ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS audit_log_select ON public.audit_log;
CREATE POLICY audit_log_select ON public.audit_log
  FOR SELECT TO authenticated
  USING (client_id::text = public.get_my_client_id());

DROP POLICY IF EXISTS audit_log_insert ON public.audit_log;
CREATE POLICY audit_log_insert ON public.audit_log
  FOR INSERT TO authenticated
  WITH CHECK (false);

DROP POLICY IF EXISTS audit_log_update ON public.audit_log;
CREATE POLICY audit_log_update ON public.audit_log
  FOR UPDATE TO authenticated
  USING (false) WITH CHECK (false);

DROP POLICY IF EXISTS audit_log_delete ON public.audit_log;
CREATE POLICY audit_log_delete ON public.audit_log
  FOR DELETE TO authenticated
  USING (false);

DROP POLICY IF EXISTS audit_log_service_role ON public.audit_log;
CREATE POLICY audit_log_service_role ON public.audit_log
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- ─────────────────────────────────────────────────────────────────────
-- record_audit() — canonical write path
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.record_audit(
  p_action      text,
  p_payload     jsonb DEFAULT '{}'::jsonb,
  p_resource    text DEFAULT NULL,
  p_resource_id text DEFAULT NULL,
  p_actor_kind  text DEFAULT 'user',
  p_agent_slug  text DEFAULT NULL,
  p_decision    text DEFAULT NULL,
  p_outcome     text DEFAULT 'success',
  p_session_id  text DEFAULT NULL,
  p_trace_id    text DEFAULT NULL,
  p_span_id     text DEFAULT NULL,
  p_client_id   uuid DEFAULT NULL
)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_client_id uuid;
  v_user_id   uuid;
  v_id        bigint;
BEGIN
  IF p_action IS NULL OR length(btrim(p_action)) = 0 THEN
    RAISE EXCEPTION 'record_audit: action is required';
  END IF;

  IF p_actor_kind NOT IN ('user', 'agent', 'system', 'cron', 'webhook') THEN
    RAISE EXCEPTION 'record_audit: invalid actor_kind %', p_actor_kind;
  END IF;

  v_user_id := auth.uid();

  -- Service-role / cron callers may pass client_id explicitly. Authenticated
  -- callers always resolve via the JWT to prevent spoofing.
  IF v_user_id IS NULL THEN
    v_client_id := p_client_id;
  ELSE
    v_client_id := NULLIF(public.get_my_client_id(), '')::uuid;
  END IF;

  INSERT INTO public.audit_log (
    client_id, actor_user, actor_kind, agent_slug,
    action, resource, resource_id,
    payload, decision, outcome,
    session_id, trace_id, span_id
  )
  VALUES (
    v_client_id, v_user_id, p_actor_kind, p_agent_slug,
    p_action, p_resource, p_resource_id,
    COALESCE(p_payload, '{}'::jsonb), p_decision, COALESCE(p_outcome, 'success'),
    p_session_id, p_trace_id, p_span_id
  )
  RETURNING id INTO v_id;

  RETURN v_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.record_audit(text, jsonb, text, text, text, text, text, text, text, text, text, uuid)
  TO authenticated, service_role;

COMMENT ON FUNCTION public.record_audit IS
  'Append a row to audit_log. Authenticated callers: client_id is taken from '
  'the JWT (cannot be spoofed). Service-role callers may pass p_client_id. '
  'Returns the inserted bigserial id.';

-- ─────────────────────────────────────────────────────────────────────
-- Trigger: stamp audit_log entries on every approval decision
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.tg_approval_requests_audit()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO public.audit_log (
      client_id, actor_user, actor_kind, agent_slug,
      action, resource, resource_id,
      payload, decision, outcome, session_id
    ) VALUES (
      NEW.client_id, NEW.requested_by, 'user', NEW.agent_slug,
      'approval.requested', 'approval_requests', NEW.id::text,
      NEW.payload, NULL, 'pending', NEW.session_id
    );
    RETURN NEW;
  END IF;

  IF TG_OP = 'UPDATE' AND NEW.status IS DISTINCT FROM OLD.status THEN
    INSERT INTO public.audit_log (
      client_id, actor_user, actor_kind, agent_slug,
      action, resource, resource_id,
      payload, decision, outcome, session_id
    ) VALUES (
      NEW.client_id, NEW.decided_by, 'user', NEW.agent_slug,
      'approval.' || NEW.status, 'approval_requests', NEW.id::text,
      jsonb_build_object(
        'reason', NEW.decision_reason,
        'payload_hash', NEW.payload_hash,
        'sla_hours', NEW.sla_hours
      ),
      NEW.status,
      CASE WHEN NEW.status = 'approved' THEN 'success' ELSE 'failure' END,
      NEW.session_id
    );
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS approval_requests_audit_ins ON public.approval_requests;
CREATE TRIGGER approval_requests_audit_ins
  AFTER INSERT ON public.approval_requests
  FOR EACH ROW EXECUTE FUNCTION public.tg_approval_requests_audit();

DROP TRIGGER IF EXISTS approval_requests_audit_upd ON public.approval_requests;
CREATE TRIGGER approval_requests_audit_upd
  AFTER UPDATE ON public.approval_requests
  FOR EACH ROW EXECUTE FUNCTION public.tg_approval_requests_audit();

COMMIT;
