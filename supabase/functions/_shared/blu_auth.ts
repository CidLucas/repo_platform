/**
 * supabase/functions/_shared/blu_auth.ts
 *
 * Shared Edge Function authentication utilities for Blu platform.
 *
 * Pattern for every user-facing endpoint:
 *   1. requireAuth(req) → validates JWT via Supabase Auth API, returns UserContext
 *   2. createUserClient(ctx.token) → RLS-scoped client (SECURITY INVOKER)
 *   3. createServiceClient() → only for admin/system ops AFTER auth is confirmed
 *
 * Why Auth API (/auth/v1/user) instead of verify_jwt = true:
 *   Supabase's edge-layer JWT verification only handles HS256. The Auth API works
 *   with both HS256 and ES256 (used by newer Supabase projects). Internal validation
 *   also gives us access to app_metadata / user_metadata claims.
 *
 * Sensitive operations (data export, credential rotation, etc.) should additionally
 * call requireMFA(ctx) to enforce AAL2.
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.1";

// ── Types ────────────────────────────────────────────────────

export interface UserContext {
  /** Supabase auth.uid() */
  userId: string;
  /** Raw Bearer token — forward to createUserClient for RLS scoping. */
  token: string;
  /**
   * Tenant ID set by backend trigger via app_metadata — most trusted source.
   * Prefer this over userClientId whenever present.
   */
  appClientId?: string;
  /**
   * Tenant ID from user_metadata — set at social/onboarding time.
   * Fallback when app_metadata is not yet populated.
   */
  userClientId?: string;
  /** "aal1" = password only; "aal2" = MFA verified. */
  aal?: string;
  /** User's email address. */
  email?: string;
}

// ── Errors ───────────────────────────────────────────────────

export class AuthError extends Error {
  constructor(
    message: string,
    readonly status: 401 | 403,
  ) {
    super(message);
    this.name = "AuthError";
  }
}

// ── Token extraction ─────────────────────────────────────────

/**
 * Extract Bearer token from the Authorization header.
 * Throws AuthError(401) if the header is absent.
 */
export function extractToken(req: Request): string {
  const header =
    req.headers.get("authorization") ?? req.headers.get("Authorization");
  if (!header) throw new AuthError("Missing authorization header", 401);
  return header.replace(/^[Bb]earer\s+/, "");
}

// ── System (service-role) invocation ─────────────────────────

/**
 * Constant-time string compare to avoid timing oracles on shared secrets.
 */
function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

/**
 * Detect whether a request was made with a server-side service key.
 *
 * Accepts (in order):
 *   - the classic JWT service_role key (SUPABASE_SERVICE_ROLE_KEY env)
 *   - the SERVICE_ROLE_KEY env fallback
 *   - BLU_SYSTEM_INVOKE_KEY env — set this via `supabase secrets set` to the
 *     value stored in vault.secrets.app_service_role_key so cron dispatchers
 *     using the sb_secret_* format are accepted everywhere
 *   - any additional ad-hoc keys passed via `extraKeys`
 *
 * Returns true when the Bearer token matches one of the accepted keys.
 * Returns false when the header is missing or no key matches — callers should
 * then fall back to requireAuth() for the user JWT path.
 *
 * Centralised here so every edge function handles the dual format identically.
 */
export function isSystemInvocation(
  req: Request,
  extraKeys: ReadonlyArray<string | undefined> = [],
): boolean {
  const header =
    req.headers.get("authorization") ?? req.headers.get("Authorization");
  if (!header) return false;
  const token = header.replace(/^[Bb]earer\s+/, "");
  if (!token) return false;

  const accepted: string[] = [
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
    Deno.env.get("SERVICE_ROLE_KEY") ?? "",
    Deno.env.get("BLU_SYSTEM_INVOKE_KEY") ?? "",
    ...extraKeys,
  ].filter((k): k is string => !!k && k.length > 0);

  return accepted.some((k) => timingSafeEqual(token, k));
}

// ── JWT validation ───────────────────────────────────────────

/**
 * Validate a Bearer token via the Supabase Auth API.
 * Returns a fully populated UserContext on success, throws AuthError on failure.
 *
 * Supports ES256 and HS256 — use this instead of Supabase's built-in
 * verify_jwt edge setting which only handles HS256.
 */
export async function validateJWT(
  token: string,
  supabaseUrl: string,
  anonKey: string,
): Promise<UserContext> {
  const resp = await fetch(`${supabaseUrl}/auth/v1/user`, {
    headers: {
      Authorization: `Bearer ${token}`,
      apikey: anonKey,
    },
  });

  if (!resp.ok) {
    throw new AuthError("Invalid or expired token", 401);
  }

  const payload = await resp.json();
  const userId = payload?.id as string | undefined;
  if (!userId) throw new AuthError("Invalid auth payload: missing user id", 401);

  return {
    userId,
    token,
    appClientId: payload?.app_metadata?.client_id as string | undefined,
    userClientId: payload?.user_metadata?.client_id as string | undefined,
    aal: payload?.aal as string | undefined,
    email: payload?.email as string | undefined,
  };
}

/**
 * Extract and validate the JWT in one call.
 * Place at the top of every user-facing Edge Function handler (first ~5 lines).
 */
export async function requireAuth(
  req: Request,
  supabaseUrl: string,
  anonKey: string,
): Promise<UserContext> {
  const token = extractToken(req);
  return validateJWT(token, supabaseUrl, anonKey);
}

// ── MFA enforcement ──────────────────────────────────────────

/**
 * Enforce AAL2 (MFA) for sensitive operations.
 * Call after requireAuth() when the operation warrants MFA:
 *   - credential writes/deletes
 *   - data export
 *   - billing/plan changes
 *
 * Throws AuthError(403) when the session is only AAL1.
 */
export function requireMFA(ctx: UserContext): void {
  if (ctx.aal !== "aal2") {
    throw new AuthError(
      "MFA required for this operation. Please re-authenticate with a second factor.",
      403,
    );
  }
}

// ── Supabase clients ─────────────────────────────────────────

/**
 * Create a Supabase client that forwards the caller's JWT.
 *
 * All queries run under SECURITY INVOKER — RLS policies enforce auth.uid()
 * scoping automatically. Use this for every user-data read/write.
 */
export function createUserClient(
  token: string,
  supabaseUrl: string,
  anonKey: string,
) {
  return createClient(supabaseUrl, anonKey, {
    global: { headers: { Authorization: `Bearer ${token}` } },
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

/**
 * Create a service-role Supabase client (bypasses RLS).
 *
 * Only use for operations that genuinely require admin access:
 *   - system job execution (DDL RPCs, schema operations)
 *   - reading/writing encrypted credentials
 *   - multi-tenant writes that cannot be scoped to one JWT
 *
 * MUST be called AFTER an authorization check has already been performed.
 */
export function createServiceClient(
  supabaseUrl: string,
  serviceRoleKey: string,
) {
  return createClient(supabaseUrl, serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

// ── Client ID resolution ─────────────────────────────────────

/**
 * Resolve the tenant client_id for a validated user.
 *
 * Resolution order (matches apps/blu_dashboard/src/lib/auth.ts):
 *   1. app_metadata.client_id  — set by backend, most secure
 *   2. user_metadata.client_id — social/onboarding fallback
 *   3. clientes_blu DB lookup  — by external_user_id = auth.uid()
 *
 * Uses the userClient so the lookup is RLS-scoped to the caller's tenant.
 * Returns null when no client mapping exists (caller should return 403).
 */
export async function resolveClientId(
  ctx: UserContext,
  supabaseUrl: string,
  anonKey: string,
): Promise<string | null> {
  if (ctx.appClientId) return ctx.appClientId;
  if (ctx.userClientId) return ctx.userClientId;

  const userClient = createUserClient(ctx.token, supabaseUrl, anonKey);
  const { data } = await userClient
    .from("clientes_blu")
    .select("client_id")
    .eq("external_user_id", ctx.userId)
    .maybeSingle();

  return (data?.client_id as string | null) ?? null;
}
