// supabase/functions/onboarding-capture-drive-token/index.ts
//
// Landing DataFork → after Google Drive OAuth, capture the provider
// refresh token and persist it (Fernet-encrypted) in `integration_tokens`
// so downstream agents can read Drive on the user's behalf.
//
// Supabase only exposes `provider_token` / `provider_refresh_token` on the
// session returned immediately after the OAuth callback — they are NOT
// persisted on the user object server-side. The client therefore pulls
// them from `supabase.auth.getSession()` and POSTs them to this function.
// We still validate the caller's JWT server-side and only accept writes
// for that caller's tenant.
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
//
// No token material is returned or logged.

import Fernet from "npm:fernet@0.4.0";
import {
  requireAuth,
  createServiceClient,
  resolveClientId,
  AuthError,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const CREDENTIALS_ENCRYPTION_KEY = Deno.env.get("CREDENTIALS_ENCRYPTION_KEY");

const DEFAULT_SCOPES = [
  "https://www.googleapis.com/auth/drive.readonly",
  "https://www.googleapis.com/auth/spreadsheets.readonly",
];

function encryptFernet(plaintext: string): string {
  if (!CREDENTIALS_ENCRYPTION_KEY) {
    throw new Error("CREDENTIALS_ENCRYPTION_KEY not set");
  }
  // Same scheme as libs/blu_context_service + google-calendar-events:
  // Python's cryptography.fernet.Fernet with urlsafe-base64 32-byte key.
  const secret = new Fernet.Secret(CREDENTIALS_ENCRYPTION_KEY);
  const token = new Fernet.Token({ secret, time: Date.now() });
  return token.encode(plaintext);
}

interface RequestBody {
  provider_refresh_token?: string;
  provider_token?: string;
  account_email?: string;
  scopes?: string[];
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (req.method !== "POST") {
    return json({ connected: false, error: "method not allowed" }, 405);
  }

  try {
    // ── 1. Auth: validate JWT, extract user context ──────────────────────────
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);

    // ── 2. Parse body ────────────────────────────────────────────────────────
    let body: RequestBody = {};
    try {
      body = (await req.json()) as RequestBody;
    } catch {
      return json({ connected: false, error: "invalid JSON body" }, 400);
    }
    const refreshToken = body.provider_refresh_token?.trim();
    if (!refreshToken) {
      // OAuth didn't return a refresh token (common when the user had
      // already granted consent and the client forgot prompt=consent).
      return json(
        {
          connected: false,
          error: "missing provider_refresh_token — reconnect with prompt=consent",
        },
        400,
      );
    }

    // ── 3. Resolve tenant client_id (RLS-scoped, never from wire) ───────────
    // Resolution order: app_metadata → user_metadata → clientes_blu DB lookup.
    const clientId = await resolveClientId(ctx, SUPABASE_URL, SUPABASE_ANON_KEY);
    if (!clientId) {
      return json(
        { connected: false, error: "no clientes_blu row for this user" },
        403,
      );
    }

    // ── 4. Encrypt + upsert via service client ───────────────────────────────
    // Service role is appropriate here: writing encrypted credential material
    // requires bypassing RLS to ensure uniform behavior across envs where
    // JWT→RLS resolution differs (e.g. legacy email-based rows).
    const refreshEncrypted = encryptFernet(refreshToken);
    const accessEncrypted = body.provider_token?.trim()
      ? encryptFernet(body.provider_token.trim())
      : "";

    const accountEmail = (
      body.account_email?.trim() ||
      ctx.email ||
      "default@unknown.com"
    ).toLowerCase();

    const scopes =
      Array.isArray(body.scopes) && body.scopes.length > 0
        ? body.scopes
        : DEFAULT_SCOPES;

    const admin = createServiceClient(SUPABASE_URL, SERVICE_ROLE_KEY);

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
      console.error("[capture-drive-token] upsert failed:", upsertError);
      return json(
        { connected: false, error: "failed to persist token" },
        500,
      );
    }

    return json({ connected: true, account_email: accountEmail });
  } catch (err) {
    if (err instanceof AuthError) {
      return json({ connected: false, error: err.message }, err.status);
    }
    console.error("[capture-drive-token] unhandled error:", err);
    return json(
      { connected: false, error: (err as Error).message || "internal error" },
      500,
    );
  }
});
