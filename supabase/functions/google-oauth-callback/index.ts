// supabase/functions/google-oauth-callback/index.ts
//
// Receives the OAuth authorization code from Google, exchanges it for tokens
// server-side (gets refresh_token reliably — bypasses Supabase Auth PKCE limitation),
// encrypts and saves to integration_tokens.
//
// This is a GET endpoint (Google redirects the browser here).
// After saving, redirects back to the app.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const CREDENTIALS_ENCRYPTION_KEY = Deno.env.get("CREDENTIALS_ENCRYPTION_KEY")!;

const REDIRECT_URI = `${SUPABASE_URL}/functions/v1/google-oauth-callback`;

// ── Fernet encryption (same as onboarding-capture-drive-token) ───────────────
function base64urlDecode(str: string): Uint8Array {
  const base64 = str.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64 + "==".slice(0, (4 - (base64.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

function base64urlEncode(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_");
}

function concatBytes(...arrays: Uint8Array[]): Uint8Array {
  const total = arrays.reduce((s, a) => s + a.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const arr of arrays) { out.set(arr, offset); offset += arr.length; }
  return out;
}

async function fernetEncrypt(keyBase64url: string, plaintext: string): Promise<string> {
  const keyBytes = base64urlDecode(keyBase64url);
  const signingKey = keyBytes.slice(0, 16);
  const encryptionKey = keyBytes.slice(16, 32);
  const ts = Math.floor(Date.now() / 1000);
  const timeBytes = new Uint8Array(8);
  const view = new DataView(timeBytes.buffer);
  view.setUint32(0, Math.floor(ts / 0x100000000), false);
  view.setUint32(4, ts >>> 0, false);
  const iv = crypto.getRandomValues(new Uint8Array(16));
  const aesKey = await crypto.subtle.importKey("raw", encryptionKey, { name: "AES-CBC" }, false, ["encrypt"]);
  const ciphertextBuf = await crypto.subtle.encrypt({ name: "AES-CBC", iv }, aesKey, new TextEncoder().encode(plaintext));
  const ciphertext = new Uint8Array(ciphertextBuf);
  const version = new Uint8Array([0x80]);
  const toSign = concatBytes(version, timeBytes, iv, ciphertext);
  const hmacKey = await crypto.subtle.importKey("raw", signingKey, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const hmac = new Uint8Array(await crypto.subtle.sign("HMAC", hmacKey, toSign));
  return base64urlEncode(concatBytes(version, timeBytes, iv, ciphertext, hmac));
}

function redirectTo(url: string) {
  return new Response(null, { status: 302, headers: { Location: url } });
}

Deno.serve(async (req: Request) => {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const errorParam = url.searchParams.get("error");

  if (errorParam) {
    console.error("[google-oauth-callback] google returned error:", errorParam);
    return redirectTo(`https://app.blu.direct/#room/admin?tab=integracoes&google_error=${encodeURIComponent(errorParam)}`);
  }

  if (!code || !state) {
    return redirectTo(`https://app.blu.direct/#room/admin?tab=integracoes&google_error=missing_code`);
  }

  // Decode state
  let stateData: { uid: string; scope: string; ts: number; return_url?: string };
  try {
    stateData = JSON.parse(atob(state));
  } catch {
    return redirectTo(`https://app.blu.direct/#room/admin?tab=integracoes&google_error=invalid_state`);
  }

  const RETURN_ORIGIN = (() => { try { return new URL(stateData.return_url ?? "https://app.blu.direct").origin; } catch { return "https://app.blu.direct"; } })();
  const RETURN_BASE = `${RETURN_ORIGIN}/#room/admin?tab=integracoes`;

  // Reject stale state (> 10 min)
  if (Date.now() - stateData.ts > 10 * 60 * 1000) {
    return redirectTo(`${RETURN_BASE}&google_error=state_expired`);
  }

  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  // Get Google OAuth credentials
  const { data: oauthConfig } = await admin.rpc("get_platform_google_oauth_config");
  if (!oauthConfig?.client_id || !oauthConfig?.client_secret) {
    return redirectTo(`${RETURN_BASE}&google_error=no_config`);
  }

  // Exchange code for tokens
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
    const text = await tokenResp.text();
    console.error("[google-oauth-callback] token exchange failed:", text);
    return redirectTo(`${RETURN_BASE}&google_error=token_exchange_failed`);
  }

  const tokenData = await tokenResp.json();
  const refreshToken: string = tokenData.refresh_token;
  const accessToken: string = tokenData.access_token;

  if (!refreshToken) {
    console.error("[google-oauth-callback] no refresh_token in response — prompt=consent may not have been respected");
    return redirectTo(`${RETURN_BASE}&google_error=no_refresh_token`);
  }

  // Get user email from Google
  let accountEmail = "";
  try {
    const userinfoResp = await fetch("https://www.googleapis.com/oauth2/v2/userinfo", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (userinfoResp.ok) {
      const info = await userinfoResp.json();
      accountEmail = info.email ?? "";
    }
  } catch { /* best effort */ }

  // Resolve client_id from user id
  const { data: clientRow } = await admin
    .from("clientes_blu")
    .select("client_id")
    .eq("external_user_id", stateData.uid)
    .maybeSingle();

  if (!clientRow?.client_id) {
    console.error("[google-oauth-callback] no clientes_blu row for uid:", stateData.uid);
    return redirectTo(`${RETURN_BASE}&google_error=no_client`);
  }

  const clientId = clientRow.client_id;

  // If we still don't have the email, check if there's an existing token row for this client
  // to reuse the email (avoids creating a duplicate row with "default@unknown.com" as key).
  if (!accountEmail) {
    const { data: existingToken } = await admin
      .from("integration_tokens")
      .select("account_email")
      .eq("client_id", clientId)
      .eq("provider", "google")
      .not("account_email", "eq", "default@unknown.com")
      .maybeSingle();
    accountEmail = existingToken?.account_email ?? "default@unknown.com";
    if (!existingToken) {
      console.warn("[google-oauth-callback] userinfo failed and no prior token — using fallback email");
    }
  }
  const refreshEncrypted = await fernetEncrypt(CREDENTIALS_ENCRYPTION_KEY, refreshToken);
  const accessEncrypted = await fernetEncrypt(CREDENTIALS_ENCRYPTION_KEY, accessToken);

  const scopes = stateData.scope.split(" ").filter(Boolean);

  // Save tokens
  const { error: upsertErr } = await admin
    .from("integration_tokens")
    .upsert(
      {
        client_id: clientId,
        provider: "google",
        account_email: accountEmail || "default@unknown.com",
        access_token_encrypted: accessEncrypted,
        refresh_token_encrypted: refreshEncrypted,
        token_type: "Bearer",
        scopes,
        is_default: true,
        metadata: { source: "admin-oauth" },
        updated_at: new Date().toISOString(),
      },
      { onConflict: "client_id,provider,account_email" },
    );

  if (upsertErr) {
    console.error("[google-oauth-callback] upsert failed:", upsertErr);
    return redirectTo(`${RETURN_BASE}&google_error=db_error`);
  }

  // Enable calendar_settings
  await admin
    .from("calendar_settings")
    .upsert(
      {
        client_id: clientId,
        enabled: true,
        provider: "google",
        calendar_id: "primary",
        calendar_name: accountEmail,
        range_days: 7,
        updated_at: new Date().toISOString(),
      },
      { onConflict: "client_id" },
    );

  console.log("[google-oauth-callback] google token saved for client:", clientId);
  return redirectTo(`${RETURN_BASE}&google_connected=1`);
});
