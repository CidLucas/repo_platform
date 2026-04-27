-- Migration: Approval Engine v1 — approval_requests table + tier rules + RPCs
-- Phase: Blu MVP, Phase 0 (F0.3) — ticket BLU-MVP-001
-- Date: 2026-04-26
--
-- The Approval Engine is the gatekeeper for every mutating MCP tool that
-- crosses a tenant policy threshold (RFQ → PO, outbound WhatsApp, scheduled
-- reports). It is consumed by:
--
--   - tool_pool_api MCP tools that wrap their state-changing helpers in a
--     `request_approval(...)` RPC call that raises ElicitationRequired until
--     a human decides;
--   - apps/vizu_dashboard ApprovalsTray (Phase 1 ticket BLU-MVP-024) which
--     reads the pending queue and writes decisions through `decide_approval`;
--   - libs/vizu_agent_framework.approval helper, which is the canonical
--     Python entry-point for both directions.
--
-- See:
--   - docs/plans/2026-04-26-blu-mvp-roadmap.md §5 Phase 0 (F0.3) and §9
--   - docs/internal/kpi-catalog.md §6 (admin KPIs read this table)
--   - /memories/repo/security-audit-rls-fix.md (RLS pattern)

BEGIN;

-- ─────────────────────────────────────────────────────────────────────
-- 1. Tier-default policy bag on client_enabled_agents
-- ─────────────────────────────────────────────────────────────────────

ALTER TABLE public.client_enabled_agents
  ADD COLUMN IF NOT EXISTS approval_policy jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN public.client_enabled_agents.approval_policy IS
  'Per-agent approval rules. Keys are action names (e.g. "create_purchase_order"). '
  'Values are objects with `mode` (always|threshold|never), `threshold` (numeric, '
  'optional), `routed_role` (optional, e.g. "finance-responsible"), and '
  '`sla_hours` (optional, default 72). Resolution order: action override → role '
  'policy → tier default → fallback "Owner-only". See roadmap §9.';

-- ─────────────────────────────────────────────────────────────────────
-- 2. approval_requests table
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.approval_requests (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id       uuid        NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
  agent_slug      text        NOT NULL REFERENCES public.agent_catalog(slug),
  action          text        NOT NULL,
  payload         jsonb       NOT NULL DEFAULT '{}'::jsonb,
  payload_hash    text        GENERATED ALWAYS AS (encode(digest(payload::text, 'sha256'), 'hex')) STORED,
  status          text        NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled')),
  requested_by    uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
  routed_to_role  text,
  decided_by      uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
  decision_reason text,
  session_id      text,
  tool_call_id    text,
  sla_hours       integer     NOT NULL DEFAULT 72 CHECK (sla_hours > 0),
  expires_at      timestamptz NOT NULL DEFAULT (now() + interval '72 hours'),
  decided_at      timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.approval_requests IS
  'Approval Engine v1 queue. Every mutating MCP tool that crosses a tenant '
  'policy threshold writes a row here and raises ElicitationRequired until '
  'a human resolves it.';

CREATE INDEX IF NOT EXISTS idx_approval_requests_client_pending
  ON public.approval_requests (client_id, created_at DESC)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_approval_requests_action
  ON public.approval_requests (client_id, action);

CREATE INDEX IF NOT EXISTS idx_approval_requests_expires
  ON public.approval_requests (expires_at)
  WHERE status = 'pending';

-- updated_at maintenance ------------------------------------------------------

CREATE OR REPLACE FUNCTION public.tg_approval_requests_set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS approval_requests_set_updated_at ON public.approval_requests;
CREATE TRIGGER approval_requests_set_updated_at
  BEFORE UPDATE ON public.approval_requests
  FOR EACH ROW EXECUTE FUNCTION public.tg_approval_requests_set_updated_at();

-- RLS -------------------------------------------------------------------------

ALTER TABLE public.approval_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS approval_requests_select ON public.approval_requests;
CREATE POLICY approval_requests_select ON public.approval_requests
  FOR SELECT TO authenticated
  USING (client_id::text = public.get_my_client_id());

-- Inserts go through `request_approval()` (SECURITY DEFINER); deny direct
-- insert from clients to keep payload_hash + sla_hours coherent.
DROP POLICY IF EXISTS approval_requests_insert ON public.approval_requests;
CREATE POLICY approval_requests_insert ON public.approval_requests
  FOR INSERT TO authenticated
  WITH CHECK (false);

-- Updates restricted to status/decision columns happen via decide_approval();
-- block direct UPDATE from clients.
DROP POLICY IF EXISTS approval_requests_update ON public.approval_requests;
CREATE POLICY approval_requests_update ON public.approval_requests
  FOR UPDATE TO authenticated
  USING (false) WITH CHECK (false);

DROP POLICY IF EXISTS approval_requests_service_role ON public.approval_requests;
CREATE POLICY approval_requests_service_role ON public.approval_requests
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- ─────────────────────────────────────────────────────────────────────
-- 3. RPCs — request_approval, decide_approval, list_pending_approvals
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.request_approval(
  p_agent_slug     text,
  p_action         text,
  p_payload        jsonb,
  p_session_id     text DEFAULT NULL,
  p_tool_call_id   text DEFAULT NULL,
  p_routed_to_role text DEFAULT NULL,
  p_sla_hours      integer DEFAULT 72
)
RETURNS public.approval_requests
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_client_id uuid;
  v_user_id   uuid;
  v_row       public.approval_requests;
BEGIN
  v_client_id := NULLIF(public.get_my_client_id(), '')::uuid;
  v_user_id   := auth.uid();

  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'request_approval: caller has no client_id'
      USING ERRCODE = '42501';
  END IF;

  IF p_action IS NULL OR length(btrim(p_action)) = 0 THEN
    RAISE EXCEPTION 'request_approval: action is required';
  END IF;

  IF p_sla_hours IS NULL OR p_sla_hours <= 0 THEN
    p_sla_hours := 72;
  END IF;

  INSERT INTO public.approval_requests (
    client_id, agent_slug, action, payload,
    requested_by, routed_to_role,
    session_id, tool_call_id,
    sla_hours, expires_at
  )
  VALUES (
    v_client_id, p_agent_slug, p_action, COALESCE(p_payload, '{}'::jsonb),
    v_user_id, p_routed_to_role,
    p_session_id, p_tool_call_id,
    p_sla_hours, now() + make_interval(hours => p_sla_hours)
  )
  RETURNING * INTO v_row;

  RETURN v_row;
END;
$$;

GRANT EXECUTE ON FUNCTION public.request_approval(text, text, jsonb, text, text, text, integer) TO authenticated, service_role;

COMMENT ON FUNCTION public.request_approval IS
  'Enqueue a new approval request. Caller is taken from auth.uid(); client_id '
  'from public.get_my_client_id(). Returns the inserted row.';

-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.decide_approval(
  p_request_id uuid,
  p_decision   text,
  p_reason     text DEFAULT NULL
)
RETURNS public.approval_requests
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_client_id uuid;
  v_user_id   uuid;
  v_row       public.approval_requests;
BEGIN
  v_client_id := NULLIF(public.get_my_client_id(), '')::uuid;
  v_user_id   := auth.uid();

  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'decide_approval: caller has no client_id'
      USING ERRCODE = '42501';
  END IF;

  IF p_decision NOT IN ('approved', 'rejected', 'cancelled') THEN
    RAISE EXCEPTION 'decide_approval: decision must be approved|rejected|cancelled'
      USING ERRCODE = '22023';
  END IF;

  UPDATE public.approval_requests
     SET status          = p_decision,
         decided_by      = v_user_id,
         decision_reason = p_reason,
         decided_at      = now()
   WHERE id = p_request_id
     AND client_id = v_client_id
     AND status = 'pending'
   RETURNING * INTO v_row;

  IF v_row.id IS NULL THEN
    RAISE EXCEPTION 'decide_approval: request not found, not pending, or not owned'
      USING ERRCODE = 'P0002';
  END IF;

  RETURN v_row;
END;
$$;

GRANT EXECUTE ON FUNCTION public.decide_approval(uuid, text, text) TO authenticated, service_role;

COMMENT ON FUNCTION public.decide_approval IS
  'Resolve a pending approval request as approved | rejected | cancelled. '
  'RLS-scoped via public.get_my_client_id().';

-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.list_pending_approvals(
  p_agent_slug text DEFAULT NULL,
  p_limit      integer DEFAULT 50
)
RETURNS SETOF public.approval_requests
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
  SELECT *
    FROM public.approval_requests
   WHERE status = 'pending'
     AND (p_agent_slug IS NULL OR agent_slug = p_agent_slug)
   ORDER BY created_at DESC
   LIMIT GREATEST(LEAST(COALESCE(p_limit, 50), 200), 1);
$$;

GRANT EXECUTE ON FUNCTION public.list_pending_approvals(text, integer) TO authenticated, service_role;

COMMENT ON FUNCTION public.list_pending_approvals IS
  'Return pending approvals for the caller''s tenant (RLS via get_my_client_id). '
  'Optional agent_slug filter; capped at 200 rows.';

-- ─────────────────────────────────────────────────────────────────────
-- 4. Sweeper — auto-expire pending approvals past their SLA
-- ─────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.expire_stale_approvals()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_count integer;
BEGIN
  UPDATE public.approval_requests
     SET status          = 'expired',
         decision_reason = 'auto-expired (SLA elapsed)',
         decided_at      = now()
   WHERE status = 'pending'
     AND expires_at < now();

  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$;

GRANT EXECUTE ON FUNCTION public.expire_stale_approvals() TO service_role;

COMMENT ON FUNCTION public.expire_stale_approvals IS
  'Sweep pending approvals past expires_at to status=expired. Schedule via '
  'pg_cron every 15 min. Returns the number of rows expired.';

COMMIT;
