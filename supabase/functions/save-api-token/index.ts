// supabase/functions/save-api-token/index.ts
//
// Saves a plain API token (Slack Bot Token, Monday API Token, etc.) encrypted
// into the integration_tokens table.
//
// Uses Web Crypto API for Fernet-compatible encryption (no npm:fernet dependency).
//
// Request:
//   POST { provider: string, api_token: string, account_label?: string }
//
// Response:
//   200 { connected: true, provider, account_label }
//   4xx { connected: false, error }

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { fernetEncrypt } from "../_shared/fernet.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const CREDENTIALS_ENCRYPTION_KEY = Deno.env.get("CREDENTIALS_ENCRYPTION_KEY");

const ALLOWED_PROVIDERS = ["slack", "monday", "notion", "asana", "clickup", "linear"];

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

// ── Provider token validation ────────────────────────────────────────────────
// Each provider gets a lightweight probe: we try the cheapest authenticated
// endpoint and fail fast if the token is invalid.

async function validateToken(provider: string, apiToken: string): Promise<{ ok: boolean; account_label?: string; error?: string }> {
  try {
    if (provider === "monday") {
      // Monday GraphQL — cheapest query: just fetch the caller's name
      const resp = await fetch("https://api.monday.com/v2", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiToken}`,
          "Content-Type": "application/json",
          "API-Version": "2024-01",
        },
        body: JSON.stringify({ query: "{ me { name email } }" }),
      });
      if (!resp.ok) {
        const txt = await resp.text().catch(() => "");
        return { ok: false, error: `Monday rejeitou o token (HTTP ${resp.status}). Verifique se o token é válido e tem permissão me:write.` };
      }
      const data = await resp.json();
      if (data.errors?.length) {
        return { ok: false, error: `Monday: ${data.errors[0]?.message ?? "token inválido"}` };
      }
      const name: string = data?.data?.me?.name ?? "";
      const email: string = data?.data?.me?.email ?? "";
      return { ok: true, account_label: email || name || "monday" };
    }

    if (provider === "notion") {
      const resp = await fetch("https://api.notion.com/v1/users/me", {
        headers: {
          Authorization: `Bearer ${apiToken}`,
          "Notion-Version": "2022-06-28",
        },
      });
      if (!resp.ok) {
        return { ok: false, error: `Notion rejeitou o token (HTTP ${resp.status}). Verifique se é um token de integração interno válido.` };
      }
      const data = await resp.json();
      const name: string = data?.name ?? data?.bot?.owner?.user?.name ?? "";
      return { ok: true, account_label: name || "notion" };
    }

    if (provider === "slack") {
      const resp = await fetch("https://slack.com/api/auth.test", {
        headers: { Authorization: `Bearer ${apiToken}` },
      });
      if (!resp.ok) {
        return { ok: false, error: `Slack rejeitou o token (HTTP ${resp.status}).` };
      }
      const data = await resp.json();
      if (!data.ok) {
        return { ok: false, error: `Slack: ${data.error ?? "token inválido"}` };
      }
      return { ok: true, account_label: data.team ?? "slack" };
    }

    if (provider === "asana") {
      const resp = await fetch("https://app.asana.com/api/1.0/users/me", {
        headers: { Authorization: `Bearer ${apiToken}` },
      });
      if (!resp.ok) {
        return { ok: false, error: `Asana rejeitou o token (HTTP ${resp.status}).` };
      }
      const data = await resp.json();
      const name: string = data?.data?.name ?? "";
      return { ok: true, account_label: name || "asana" };
    }

    if (provider === "linear") {
      const resp = await fetch("https://api.linear.app/graphql", {
        method: "POST",
        headers: { Authorization: apiToken, "Content-Type": "application/json" },
        body: JSON.stringify({ query: "{ viewer { name email } }" }),
      });
      if (!resp.ok) {
        return { ok: false, error: `Linear rejeitou o token (HTTP ${resp.status}).` };
      }
      const data = await resp.json();
      if (data.errors?.length) {
        return { ok: false, error: `Linear: ${data.errors[0]?.message ?? "token inválido"}` };
      }
      const name: string = data?.data?.viewer?.name ?? "";
      return { ok: true, account_label: name || "linear" };
    }

    if (provider === "clickup") {
      const resp = await fetch("https://api.clickup.com/api/v2/user", {
        headers: { Authorization: apiToken },
      });
      if (!resp.ok) {
        return { ok: false, error: `ClickUp rejeitou o token (HTTP ${resp.status}).` };
      }
      const data = await resp.json();
      const name: string = data?.user?.username ?? data?.user?.email ?? "";
      return { ok: true, account_label: name || "clickup" };
    }

    // Unknown provider — skip validation, save as-is
    return { ok: true, account_label: provider };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { ok: false, error: `Erro de rede ao validar token (${provider}): ${msg}` };
  }
}



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

    let body: { provider?: string; api_token?: string; account_label?: string } = {};
    try { body = await req.json(); } catch { return jsonResp({ connected: false, error: "invalid JSON body" }, 400); }

    const provider = body.provider?.trim();
    if (!provider || !ALLOWED_PROVIDERS.includes(provider)) {
      return jsonResp({ connected: false, error: `provider must be one of: ${ALLOWED_PROVIDERS.join(", ")}` }, 400);
    }

    const apiToken = body.api_token?.trim();
    if (!apiToken) {
      return jsonResp({ connected: false, error: "missing api_token" }, 400);
    }

    // Debug: log token shape to help diagnose clipboard/encoding issues
    console.log(`[save-api-token] provider=${provider} token_len=${apiToken.length} prefix=${apiToken.slice(0,10)} suffix=${apiToken.slice(-6)} has_space=${apiToken.includes(' ')} has_newline=${apiToken.includes('\n')}`);

    const clientId = await resolveClientId(ctx);
    if (!clientId) return jsonResp({ connected: false, error: "no clientes_blu row for this user" }, 403);

    if (!CREDENTIALS_ENCRYPTION_KEY) {
      console.error("[save-api-token] CREDENTIALS_ENCRYPTION_KEY not set");
      return jsonResp({ connected: false, error: "server misconfiguration: encryption key missing" }, 500);
    }

    // ── Validate token against provider API before persisting ─────────────────
    const validation = await validateToken(provider, apiToken);
    if (!validation.ok) {
      console.warn(`[save-api-token] token validation failed for provider=${provider} client=${clientId}: ${validation.error}`);
      return jsonResp({
        connected: false,
        error: validation.error,
      }, 422);
    }

    const accessTokenEncrypted = await fernetEncrypt(CREDENTIALS_ENCRYPTION_KEY, apiToken);
    // Use validated account label if the caller didn't provide one
    const accountLabel = body.account_label?.trim() || validation.account_label || "default";

    const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
      auth: { autoRefreshToken: false, persistSession: false },
    });

    const { error: upsertError } = await admin
      .from("integration_tokens")
      .upsert(
        {
          client_id: clientId,
          provider,
          account_email: accountLabel,
          access_token_encrypted: accessTokenEncrypted,
          refresh_token_encrypted: "",
          token_type: "api_token",
          scopes: [],
          is_default: true,
          metadata: { source: "admin-integration-modal" },
          updated_at: new Date().toISOString(),
        },
        { onConflict: "client_id,provider,account_email" },
      );

    if (upsertError) {
      console.error("[save-api-token] integration_tokens upsert failed:", upsertError);
      return jsonResp({ connected: false, error: "failed to persist token" }, 500);
    }

    return jsonResp({ connected: true, provider, account_label: accountLabel, validated: true });
  } catch (err: unknown) {
    const e = err as { status?: number; message?: string };
    if (e?.status === 401 || e?.status === 403) {
      return jsonResp({ connected: false, error: e.message }, e.status as 401 | 403);
    }
    console.error("[save-api-token] unhandled error:", err);
    return jsonResp({ connected: false, error: (err as Error).message || "internal error" }, 500);
  }
});
