-- Migration: onboarding_state JSONB + completion timestamp on clientes_vizu
-- Phase: Landing Onboarding Wire-up, Phase 1 (Foundation)
-- Date: 2026-04-23
--
-- Server-side resumable onboarding state for the landing wizard. Each step
-- autosaves a JSONB patch via public.merge_onboarding_state(); LaunchPad
-- stamps onboarding_completed_at to close out the flow.

-- 1. Columns ------------------------------------------------------------------
ALTER TABLE public.clientes_vizu
  ADD COLUMN IF NOT EXISTS onboarding_state       jsonb       NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS onboarding_completed_at timestamptz;

COMMENT ON COLUMN public.clientes_vizu.onboarding_state IS
  'Landing onboarding wizard state (resumable). See apps/landing/src/onboarding/state.ts::OnboardingState.';
COMMENT ON COLUMN public.clientes_vizu.onboarding_completed_at IS
  'Set by supabase/functions/onboarding-bootstrap when the wizard finishes. NULL means incomplete.';

-- 2. Partial index used by dashboard "continue onboarding" banner -------------
CREATE INDEX IF NOT EXISTS idx_clientes_vizu_onboarding_incomplete
  ON public.clientes_vizu (client_id)
  WHERE onboarding_completed_at IS NULL;

-- 3. Race-free JSONB merge RPC ------------------------------------------------
-- Used by apps/landing/src/onboarding/services/onboardingService.ts to patch
-- slices of state concurrently (e.g. Drive OAuth redirect + BusinessDNA
-- autosave). Relies on jsonb '||' merge — commutative for top-level keys.
CREATE OR REPLACE FUNCTION public.merge_onboarding_state(p_patch jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_client_id uuid;
  v_new_state jsonb;
BEGIN
  IF p_patch IS NULL OR jsonb_typeof(p_patch) <> 'object' THEN
    RAISE EXCEPTION 'merge_onboarding_state: p_patch must be a JSON object';
  END IF;

  -- Caller must resolve to a tenant via the standard RLS helper.
  SELECT NULLIF(public.get_my_client_id(), '')::uuid INTO v_client_id;
  IF v_client_id IS NULL THEN
    RAISE EXCEPTION 'merge_onboarding_state: no tenant for current user';
  END IF;

  UPDATE public.clientes_vizu
     SET onboarding_state = COALESCE(onboarding_state, '{}'::jsonb) || p_patch,
         updated_at = now()
   WHERE client_id = v_client_id
  RETURNING onboarding_state INTO v_new_state;

  RETURN v_new_state;
END;
$$;

COMMENT ON FUNCTION public.merge_onboarding_state(jsonb) IS
  'Merges a JSONB patch into clientes_vizu.onboarding_state for the caller''s tenant. '
  'SECURITY INVOKER — all writes are caller-scoped via public.get_my_client_id().';

GRANT EXECUTE ON FUNCTION public.merge_onboarding_state(jsonb) TO authenticated;
