// supabase/functions/onboarding-capture-drive-token/index.ts
//
// Captures Google OAuth refresh token after OAuth callback and stores it encrypted.
// Also enables calendar_settings so google-calendar-events starts returning events.
//
// Uses Web Crypto API for Fernet-compatible encryption (no npm:fernet dependency)
// to avoid Deno npm-compat issues with the fernet package's Buffer/crypto usage.
//
// Request:
//   POST { provider_refresh_token: string,
//          provider_token?: string,
//          account_email?: string,
//          scopes?: string[] }
//
// Response:
//   200 { connected: true, account_email }
//   4xx { connected: false, error }

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { fernetEncrypt } from "../_shared/fernet.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const CREDENTIALS_ENCRYPTION_KEY = Deno.env.get("CREDENTIALS_ENCRYPTION_KEY");

const DEFAULT_SCOPES = [
  "https://www.googleapis.com/auth/drive.readonly",
  "https://www.googleapis.com/auth/spreadsheets.readonly",
];

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function jsonResp(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

// ── Auth ────────────────────────────────────────────────────────────────────

async function requireAuth(req: Request) {
  const header = req.headers.get("authorization") ?? req.headers.get("Authorization");
  if (!header) throw { status: 401, message: "Missing authorization header" };
  const token = header.replace(/^[Bb]earer\s+/, "");

  const resp = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    headers: { Authorization: `Bearer ${token}`, apikey: SUPABASE_ANON_KEY },
  });
  if (!resp.ok) throw { status: 401, message: "Invalid or expired token" };
  const payload = await resp.json();
  if (!payload?.id) throw { status: 401, message: "Invalid auth payload" };

  return {
    userId: payload.id as string,
    token,
    appClientId: payload?.app_metadata?.client_id as string | undefined,
    userClientId: payload?.user_metadata?.client_id as string | undefined,
    email: payload?.email as string | undefined,
  };
}

async function resolveClientId(ctx: {
  userId: string; token: string; appClientId?: string; userClientId?: string;
}): Promise<string | null> {
  if (ctx.appClientId) return ctx.appClientId;
  if (ctx.userClientId) return ctx.userClientId;
  const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: { headers: { Authorization: `Bearer ${ctx.token}` } },
    auth: { autoRefreshToken: false, persistSession: false },
  });
  const { data } = await userClient
    .from("clientes_blu")
    .select("client_id")
    .eq("external_user_id", ctx.userId)
    .maybeSingle();
  return (data?.client_id as string | null) ?? null;
}

// ── Handler ─────────────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return jsonResp({ connected: false, error: "method not allowed" }, 405);

  try {
    const ctx = await requireAuth(req);

    let body: { provider_refresh_token?: string; provider_token?: string; account_email?: string; scopes?: string[] } = {};
    try { body = await req.json(); } catch { return jsonResp({ connected: false, error: "invalid JSON body" }, 400); }

    const refreshToken = body.provider_refresh_token?.trim();
    if (!refreshToken) {
      return jsonResp({ connected: false, error: "missing provider_refresh_token — reconnect with prompt=consent" }, 400);
    }

    const clientId = await resolveClientId(ctx);
    if (!clientId) return jsonResp({ connected: false, error: "no clientes_blu row for this user" }, 403);

    if (!CREDENTIALS_ENCRYPTION_KEY) {
      console.error("[capture-drive-token] CREDENTIALS_ENCRYPTION_KEY not set");
      return jsonResp({ connected: false, error: "server misconfiguration: encryption key missing" }, 500);
    }

    const refreshEncrypted = await fernetEncrypt(CREDENTIALS_ENCRYPTION_KEY, refreshToken);
    const accessEncrypted = body.provider_token?.trim()
      ? await fernetEncrypt(CREDENTIALS_ENCRYPTION_KEY, body.provider_token.trim())
      : "";

    const accountEmail = (body.account_email?.trim() || ctx.email || "default@unknown.com").toLowerCase();
    const scopes = Array.isArray(body.scopes) && body.scopes.length > 0 ? body.scopes : DEFAULT_SCOPES;

    const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
      auth: { autoRefreshToken: false, persistSession: false },
    });

    const { error: upsertError } = await admin
      .from("integration_tokens")
      .upsert(
        {
          client_id: clientId,
          provider: "google",
          account_email: accountEmail,
          access_token_encrypted: accessEncrypted,
          refresh_token_encrypted: refreshEncrypted,
          token_type: "Bearer",
          scopes,
          is_default: true,
          metadata: { source: "landing-onboarding" },
          updated_at: new Date().toISOString(),
        },
        { onConflict: "client_id,provider,account_email" },
      );

    if (upsertError) {
      console.error("[capture-drive-token] integration_tokens upsert failed:", upsertError);
      return jsonResp({ connected: false, error: "failed to persist token" }, 500);
    }

    // Enable calendar so google-calendar-events serves events immediately after OAuth.
    const { error: settingsError } = await admin
      .from("calendar_settings")
      .upsert(
        {
          client_id: clientId,
          enabled: true,
          provider: "google",
          calendar_id: "primary",
          range_days: 7,
          updated_at: new Date().toISOString(),
        },
        { onConflict: "client_id" },
      );

    if (settingsError) {
      console.warn("[capture-drive-token] calendar_settings upsert failed:", settingsError);
    }

    return jsonResp({ connected: true, account_email: accountEmail });
  } catch (err: unknown) {
    const e = err as { status?: number; message?: string };
    if (e?.status === 401 || e?.status === 403) {
      return jsonResp({ connected: false, error: e.message }, e.status as 401 | 403);
    }
    console.error("[capture-drive-token] unhandled error:", err);
    return jsonResp({ connected: false, error: (err as Error).message || "internal error" }, 500);
  }
});
