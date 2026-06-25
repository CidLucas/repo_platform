// supabase/functions/google-oauth-callback/index.ts
//
// Receives the OAuth authorization code from Google, exchanges it for tokens
// server-side (gets refresh_token reliably — bypasses Supabase Auth PKCE limitation),
// encrypts and saves to integration_tokens.
//
// This is a GET endpoint (Google redirects the browser here).
// After saving, redirects back to the app.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { storeGoogleToken } from "../_shared/store_google_token.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const REDIRECT_URI = `${SUPABASE_URL}/functions/v1/google-oauth-callback`;

// ── Helpers ───────────────────────────────────────────────────────────────────

async function getJson(url: string, init?: RequestInit) {
  const res = await fetch(url, init);
  const text = await res.text();
  try {
    return JSON.parse(text) as Record<string, unknown>;
  } catch {
    return { _raw: text } as Record<string, unknown>;
  }
}

function redirectTo(url: string) {
  const safe = (url && String(url).trim().length > 0) ? String(url).trim() : 'https://app.blu.direct#room/admin?tab=integracoes&google_error=empty_redirect';
  console.log('[google-oauth-callback] redirectTo ->', safe);
  const headers = new Headers();
  headers.set('Location', safe);
  headers.set('Content-Type', 'text/html; charset=utf-8');
  return new Response(
    `<html><body>Redirecting to <a href="${safe}">${safe}</a>...</body></html>`,
    { status: 302, headers }
  );
}

function buildRedirectReturn(stateData: { return_url?: string }) {
  try {
    const origin = new URL(stateData.return_url ?? "https://app.blu.direct").origin;
    return `${origin}#room/admin?tab=integracoes`;
  } catch {
    return "https://app.blu.direct#room/admin?tab=integracoes";
  }
}

// ── Main handler ──────────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  console.log('[google-oauth-callback] boot version=2026-06-03-v1', new Date().toISOString());
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const errorParam = url.searchParams.get("error");

  if (errorParam) {
    console.warn('[google-oauth-callback] errorParam', errorParam);
    return redirectTo(`https://app.blu.direct/#room/admin?tab=integracoes&google_error=${encodeURIComponent(errorParam)}`);
  }
  if (!code || !state) {
    console.warn('[google-oauth-callback] missing code/state');
    return redirectTo(`https://app.blu.direct/#room/admin?tab=integracoes&google_error=missing_code`);
  }

  let stateData: { uid: string; scope: string; ts: number; return_url?: string };
  try {
    stateData = JSON.parse(atob(state));
  } catch (e) {
    console.warn('[google-oauth-callback] invalid state', e);
    return redirectTo(`https://app.blu.direct/#room/admin?tab=integracoes&google_error=invalid_state`);
  }
  console.log('[google-oauth-callback] stateData', stateData);
  const returnBase = buildRedirectReturn(stateData);

  if (Date.now() - stateData.ts > 10 * 60 * 1000) {
    return redirectTo(`${returnBase}&google_error=state_expired`);
  }

  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  // Resolve client row for this Google identity uid
  let clientRow: { client_id: string } | null = null;
  try {
    const resolved = await admin
      .from("clientes_blu")
      .select("client_id")
      .eq("external_user_id", stateData.uid)
      .maybeSingle();
    clientRow = resolved.data ?? null;
  } catch (e) {
    console.error('[google-oauth-callback] clientes_blu lookup failed', e);
  }
  console.log('[google-oauth-callback] clientRow', clientRow);

  if (!clientRow?.client_id) {
    console.warn('[google-oauth-callback] no client');
    return redirectTo(`${returnBase}&google_error=no_client`);
  }

  // Load OAuth credentials and exchange the authorization code
  let oauthConfig: { client_id?: string; client_secret?: string } | null = null;
  try {
    const rpc = await admin.rpc("get_platform_google_oauth_config");
    oauthConfig = (rpc.data ?? null) as typeof rpc.data;
  } catch (e) {
    console.error('[google-oauth-callback] rpc failed', e);
  }
  console.log('[google-oauth-callback] oauthConfigPresent', Boolean(oauthConfig?.client_id) && Boolean(oauthConfig?.client_secret));

  if (!oauthConfig?.client_id || !oauthConfig?.client_secret) {
    console.warn('[google-oauth-callback] no oauth config');
    return redirectTo(`${returnBase}&google_error=no_config`);
  }

  const tokenResp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: oauthConfig.client_id,
      client_secret: oauthConfig.client_secret,
      redirect_uri: REDIRECT_URI,
      grant_type: "authorization_code",
    }),
  });

  if (!tokenResp.ok) {
    const text = await tokenResp.text().catch(() => '') || '';
    let parsed: Record<string, unknown> = {};
    try { parsed = JSON.parse(text); } catch { /* keep raw fallback if needed */ }
    const errDesc = typeof parsed.error_description === 'string' ? parsed.error_description : (typeof parsed.error === 'string' ? parsed.error : '');
    const errSuffix = `&google_http_status=${tokenResp.status}&google_status_text=${encodeURIComponent(tokenResp.statusText || '')}${errDesc ? `&google_error_description=${encodeURIComponent(errDesc)}` : ''}`;
    return redirectTo(`${returnBase}${errSuffix}&google_error=token_exchange_failed`);
  }

  const tokenPayload = await tokenResp.json();

  const refreshToken: string = (tokenPayload.refresh_token as string) ?? "";
  const accessToken: string = (tokenPayload.access_token as string) ?? "";

  if (!refreshToken || !accessToken) {
    return redirectTo(`${returnBase}&google_error=no_refresh_token`);
  }

  // Get identity info from Google (email + stable user id)
  const userinfoPayload = await getJson('https://www.googleapis.com/oauth2/v2/userinfo', {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  const accountEmail = String(userinfoPayload?.email ?? "").trim().toLowerCase();
  const googleUserId = String(userinfoPayload?.id ?? "").trim();
  const userIdHash = googleUserId ? `google:${googleUserId}` : "";

  if (!accountEmail || !userIdHash) {
    console.warn('[google-oauth-callback] email_unresolved payload keys', Object.keys(userinfoPayload ?? {}), 'text_preview', JSON.stringify(userinfoPayload).slice(0, 500));
    return redirectTo(`${returnBase}&google_error=email_unresolved`);
  }

  const scopes = String(stateData.scope).split(" ").filter(Boolean);

  const stored = await storeGoogleToken({
    admin,
    clientId: clientRow.client_id,
    refreshToken,
    accessToken,
    accountEmail,
    scopes,
    metadataSource: "admin-oauth",
    includeCalendarName: true,
  });
  if (!stored.ok) {
    if (stored.error === "integration_tokens_upsert_failed") {
      return redirectTo(`${returnBase}&google_error=db_error`);
    }
    return redirectTo(`${returnBase}&google_error=server_misconfig`);
  }

  return redirectTo(`${returnBase}&google_connected=1`);
});
