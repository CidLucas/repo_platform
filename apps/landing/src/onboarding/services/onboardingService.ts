/**
 * Landing Onboarding Service — typed wrapper around Supabase writes for the
 * wizard. Mirrors the dashboard's onboardingService.ts shape so later
 * consolidation is trivial.
 *
 * Resolves the caller's tenant through RLS helpers; never accepts a
 * client_id argument from the UI.
 *
 * Reference: apps/vizu_dashboard/src/services/onboardingService.ts
 */

import { supabase } from "../../lib/supabase";
import type { OnboardingState } from "../state";
import type {
  BootstrapPayload,
  BootstrapResult,
  OnboardingData,
  OnboardingStateRecord,
} from "../types";

const TABLE = "clientes_vizu";
const MERGE_RPC = "merge_onboarding_state";
const BOOTSTRAP_FN = "onboarding-bootstrap";
const DRIVE_TOKEN_FN = "onboarding-capture-drive-token";

// ---------------------------------------------------------------------------
// Read
// ---------------------------------------------------------------------------

/**
 * Fetch `onboarding_state` + completion timestamp for the current tenant.
 * Returns `null` when the row is missing (pre-trigger legacy users, race).
 */
export async function getOnboardingState(): Promise<OnboardingStateRecord | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return null;

  const { data, error } = await supabase
    .from(TABLE)
    .select("onboarding_state, onboarding_completed_at")
    .maybeSingle();

  if (error) {
    console.error("[onboarding] getOnboardingState failed", error);
    return null;
  }
  if (!data) return null;

  return {
    onboarding_state: (data.onboarding_state ?? {}) as Partial<OnboardingState>,
    onboarding_completed_at: data.onboarding_completed_at ?? null,
  };
}

// ---------------------------------------------------------------------------
// Write
// ---------------------------------------------------------------------------

/**
 * Race-free JSONB merge into `clientes_vizu.onboarding_state` via the
 * `merge_onboarding_state(jsonb)` RPC. No-op when not authenticated.
 */
export async function patchOnboardingState(
  patch: Partial<OnboardingState>,
): Promise<void> {
  if (!patch || Object.keys(patch).length === 0) return;

  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return;

  const { error } = await supabase.rpc(MERGE_RPC, { p_patch: patch });
  if (error) {
    console.error("[onboarding] patchOnboardingState failed", error);
    throw error;
  }
}

/**
 * Persist Context 2.0 sections (company_profile, current_moment,
 * team_structure, policies). Omitted keys are left untouched.
 */
export async function saveContextSections(
  partial: Partial<OnboardingData>,
): Promise<void> {
  const payload: Record<string, unknown> = {};
  if (partial.company_profile !== undefined)
    payload.company_profile = partial.company_profile;
  if (partial.current_moment !== undefined)
    payload.current_moment = partial.current_moment;
  if (partial.team_structure !== undefined)
    payload.team_structure = partial.team_structure;
  if (partial.policies !== undefined) payload.policies = partial.policies;

  if (Object.keys(payload).length === 0) return;

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return;

  // RLS scopes the UPDATE to the current tenant's row via
  // `get_my_client_id()` — no `eq('client_id', …)` needed here, but adding
  // a filter keeps parity with the dashboard service's explicit form.
  const { error } = await supabase
    .from(TABLE)
    .update(payload)
    .eq("external_user_id", user.id);

  if (error) {
    console.error("[onboarding] saveContextSections failed", error);
    throw error;
  }
}

/**
 * Update a top-level column on `clientes_vizu` for the current tenant.
 * Used for `nome_empresa` (BusinessDNA) and similar scalar fields that
 * aren't part of the JSONB sections.
 */
export async function updateClientColumn(
  column: "nome_empresa",
  value: string | null,
): Promise<void> {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return;

  const { error } = await supabase
    .from(TABLE)
    .update({ [column]: value })
    .eq("external_user_id", user.id);

  if (error) {
    console.error(`[onboarding] updateClientColumn(${column}) failed`, error);
    throw error;
  }
}

// ---------------------------------------------------------------------------
// Edge function orchestration (Phases 4–5)
// ---------------------------------------------------------------------------

/**
 * Final LaunchPad call. Hands the full wizard state to the bootstrap edge
 * function which provisions agents, routines, prompts, and stamps
 * `onboarding_completed_at`.
 */
export async function runBootstrap(
  payload: BootstrapPayload,
): Promise<BootstrapResult> {
  const { data, error } = await supabase.functions.invoke<BootstrapResult>(
    BOOTSTRAP_FN,
    { body: payload },
  );
  if (error || !data) {
    console.error("[onboarding] runBootstrap failed", error);
    throw error ?? new Error("bootstrap returned empty response");
  }
  return data;
}

/**
 * Capture the Google Drive refresh token that Supabase Auth returns on
 * the session immediately after the OAuth callback. Supabase does NOT
 * persist `provider_refresh_token` server-side, so the client is the
 * only place it's readable — we forward it (over HTTPS, with the user's
 * JWT) to the edge function which Fernet-encrypts and upserts into
 * `integration_tokens`.
 */
export async function captureDriveToken(): Promise<{ connected: boolean }> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) {
    console.warn("[onboarding] captureDriveToken called without a session");
    return { connected: false };
  }

  // `provider_refresh_token` is only present when the OAuth flow was
  // started with `access_type=offline` + `prompt=consent` (see DataFork).
  const providerRefreshToken = (session as unknown as {
    provider_refresh_token?: string | null;
  }).provider_refresh_token;
  const providerToken = (session as unknown as {
    provider_token?: string | null;
  }).provider_token;

  if (!providerRefreshToken) {
    console.warn(
      "[onboarding] no provider_refresh_token on session — Google did not return one",
    );
    return { connected: false };
  }

  const body = {
    provider_refresh_token: providerRefreshToken,
    provider_token: providerToken ?? undefined,
    account_email: session.user?.email ?? undefined,
  };

  const { data, error } = await supabase.functions.invoke<{
    connected: boolean;
  }>(DRIVE_TOKEN_FN, { body });
  if (error || !data) {
    console.error("[onboarding] captureDriveToken failed", error);
    return { connected: false };
  }
  return data;
}

// ---------------------------------------------------------------------------
// Self-heal
// ---------------------------------------------------------------------------

/**
 * Idempotent "make sure my clientes_vizu row exists" RPC. Safe to call
 * after any session-present event; no-ops when the row already exists.
 */
export async function ensureTenantRow(): Promise<void> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return;

  const { error } = await supabase.rpc("ensure_tenant_row");
  if (error) {
    console.error("[onboarding] ensureTenantRow failed", error);
  }
}
