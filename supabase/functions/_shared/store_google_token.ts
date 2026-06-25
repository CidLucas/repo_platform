/**
 * supabase/functions/_shared/store_google_token.ts
 *
 * Shared Google OAuth token persistence used by google-oauth-callback and
 * onboarding-capture-drive-token. Both endpoints end with the same trio:
 *
 *   1. Fernet-encrypt the refresh + access tokens
 *   2. Upsert into integration_tokens (key: client_id, provider, account_email)
 *   3. Upsert into calendar_settings so google-calendar-events serves
 *      events immediately after OAuth
 *
 * What each caller does OUTSIDE this helper:
 *   - google-oauth-callback: full Google OAuth roundtrip (token exchange
 *     + userinfo fetch) and the state-blob validation
 *   - onboarding-capture-drive-token: validates the user JWT, resolves
 *     client_id from app_metadata/user_metadata/DB
 *
 * Both pass the resolved client_id + tokens + account_email to this helper.
 */

import { fernetEncrypt } from "./fernet.ts";

// deno-lint-ignore no-explicit-any
type ServiceClient = any;

export interface StoreGoogleTokenParams {
  /** Service-role Supabase client. */
  admin: ServiceClient;
  /** Resolved tenant ID. */
  clientId: string;
  /** Google refresh token (required, never empty). */
  refreshToken: string;
  /** Google access token. Empty string is allowed and means "store refresh only". */
  accessToken?: string;
  /** Lower-cased Gmail/Google Workspace email. */
  accountEmail: string;
  /** OAuth scopes that were granted. */
  scopes: string[];
  /** Written to integration_tokens.metadata.source for audit. */
  metadataSource: string;
  /**
   * When true (default), the calendar_settings row is written with
   * `calendar_name = accountEmail`. When false, the row is left without
   * a calendar_name (the landing wizard uses this — it doesn't have a
   * friendly name yet, the user can set it later).
   */
  includeCalendarName?: boolean;
}

export interface StoreGoogleTokenResult {
  ok: true;
}

export type StoreGoogleTokenResponse =
  | StoreGoogleTokenResult
  | { ok: false; error: "encryption_key_missing" | "integration_tokens_upsert_failed" };

const CREDENTIALS_ENCRYPTION_KEY = Deno.env.get("CREDENTIALS_ENCRYPTION_KEY");

/**
 * Encrypt and persist a Google OAuth token pair. Returns ok:false (not
 * throws) so the caller can return a structured 4xx/5xx without unwinding
 * the whole request. Throws only on programmer error.
 *
 * calendar_settings is best-effort: a failure is logged but does not fail
 * the request (mirroring the behaviour of both original callers).
 */
export async function storeGoogleToken(
  params: StoreGoogleTokenParams,
): Promise<StoreGoogleTokenResponse> {
  if (!CREDENTIALS_ENCRYPTION_KEY) {
    console.error("[store_google_token] CREDENTIALS_ENCRYPTION_KEY not set");
    return { ok: false, error: "encryption_key_missing" };
  }

  // ── 1. Encrypt tokens ────────────────────────────────────────────────────
  const refreshEncrypted = await fernetEncrypt(CREDENTIALS_ENCRYPTION_KEY, params.refreshToken);
  const accessEncrypted = params.accessToken
    ? await fernetEncrypt(CREDENTIALS_ENCRYPTION_KEY, params.accessToken)
    : "";

  // ── 2. Upsert integration_tokens ─────────────────────────────────────────
  const { error: upsertErr } = await params.admin
    .from("integration_tokens")
    .upsert(
      {
        client_id: params.clientId,
        provider: "google",
        account_email: params.accountEmail,
        access_token_encrypted: accessEncrypted,
        refresh_token_encrypted: refreshEncrypted,
        token_type: "Bearer",
        scopes: params.scopes,
        is_default: true,
        metadata: { source: params.metadataSource },
        updated_at: new Date().toISOString(),
      },
      { onConflict: "client_id,provider,account_email" },
    );

  if (upsertErr) {
    console.error("[store_google_token] integration_tokens upsert failed:", upsertErr);
    return { ok: false, error: "integration_tokens_upsert_failed" };
  }

  // ── 3. Upsert calendar_settings so the Agenda card lights up (best-effort)
  const calendarRow: Record<string, unknown> = {
    client_id: params.clientId,
    enabled: true,
    provider: "google",
    calendar_id: "primary",
    range_days: 7,
    updated_at: new Date().toISOString(),
  };
  if (params.includeCalendarName ?? true) {
    calendarRow.calendar_name = params.accountEmail;
  }

  const { error: settingsErr } = await params.admin
    .from("calendar_settings")
    .upsert(calendarRow, { onConflict: "client_id" });

  if (settingsErr) {
    console.warn("[store_google_token] calendar_settings upsert failed:", settingsErr);
  }

  return { ok: true };
}
