// supabase/functions/google-oauth-start/index.ts
//
// Initiates a direct Google OAuth flow (not via Supabase Auth).
// Returns a redirect URL to Google with the correct params to get a refresh_token.
//
// Request:
//   POST { scope: string }   (e.g. "https://www.googleapis.com/auth/calendar.readonly")
//   Authorization: Bearer <jwt>
//
// Response:
//   200 { url: string }   — redirect the browser to this URL

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

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

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return jsonResp({ error: "method not allowed" }, 405);

  // Auth
  const authHeader = req.headers.get("Authorization") ?? "";
  const token = authHeader.replace(/^Bearer\s+/i, "").trim();
  if (!token) return jsonResp({ error: "unauthorized" }, 401);

  const userClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: { headers: { Authorization: `Bearer ${token}` } },
    auth: { autoRefreshToken: false, persistSession: false },
  });
  const { data: { user }, error: authErr } = await userClient.auth.getUser();
  if (authErr || !user) return jsonResp({ error: "unauthorized" }, 401);

  const body = await req.json().catch(() => ({}));
  const scope: string = body.scope ?? "https://www.googleapis.com/auth/calendar.readonly";

  // Get Google OAuth credentials from platform config
  const { data: oauthConfig } = await userClient.rpc("get_platform_google_oauth_config");
  if (!oauthConfig?.client_id) return jsonResp({ error: "google oauth not configured" }, 500);

  // Store user id and return URL in state
  const returnUrl = body.return_url ?? `${req.headers.get("origin") ?? "https://app.blu.direct"}/#room/admin?tab=integracoes`;
  const state = btoa(JSON.stringify({ uid: user.id, scope, ts: Date.now(), return_url: returnUrl }));

  const REDIRECT_URI = `${SUPABASE_URL}/functions/v1/google-oauth-callback`;

  const params = new URLSearchParams({
    client_id: oauthConfig.client_id,
    redirect_uri: REDIRECT_URI,
    response_type: "code",
    scope,
    access_type: "offline",
    prompt: "consent",
    state,
  });

  return jsonResp({ url: `https://accounts.google.com/o/oauth2/v2/auth?${params}` });
});
