// Edge Function: google-calendar-events
//
// Returns the authenticated client's upcoming Google Calendar events for the
// dashboard Agenda card. Reads per-client preferences from
// `public.calendar_settings`, decrypts the OAuth refresh_token stored in
// `public.integration_tokens` (Fernet, same key used by the Python backend),
// exchanges it for a fresh access_token via Google's token endpoint, and calls
// the Calendar v3 events.list API.
//
// Auth: requires a valid Supabase user JWT (verify_jwt = true in config.toml).
// Body (optional): { "rangeDays": number }  → overrides calendar_settings.range_days.
// Response shapes:
//   { events: AgendaEvent[], disabled: false, fetched_at, range_days }
//   { events: [],            disabled: true,  reason }
//
// Failure modes are surfaced as `disabled: true` + a typed `reason` so the
// dashboard can render an onboarding/CTA empty state without leaking errors.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import Fernet from "npm:fernet@0.4.0";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const CREDENTIALS_ENCRYPTION_KEY = Deno.env.get("CREDENTIALS_ENCRYPTION_KEY");

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function getServiceClient() {
  return createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

function decryptFernet(ciphertext: string): string {
  if (!CREDENTIALS_ENCRYPTION_KEY) {
    throw new Error("CREDENTIALS_ENCRYPTION_KEY not set");
  }
  // npm:fernet expects the secret as a urlsafe-base64 string (32 bytes).
  // The Python backend stores it the same way (Fernet.generate_key()).
  const secret = new Fernet.Secret(CREDENTIALS_ENCRYPTION_KEY);
  // ttl=0 disables expiry checking — refresh tokens persist long-term.
  const token = new Fernet.Token({ secret, token: ciphertext, ttl: 0 });
  return token.decode();
}

async function exchangeRefreshToken(
  refreshToken: string,
  clientId: string,
  clientSecret: string,
): Promise<string> {
  const params = new URLSearchParams({
    client_id: clientId,
    client_secret: clientSecret,
    refresh_token: refreshToken,
    grant_type: "refresh_token",
  });
  const resp = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: params.toString(),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`token_refresh_failed:${resp.status}:${text}`);
  }
  const data = await resp.json();
  if (!data.access_token) {
    throw new Error("token_refresh_failed:no_access_token");
  }
  return data.access_token as string;
}

interface AgendaEventPayload {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string;
  type: "meeting" | "call" | "deadline";
  location: string | null;
  attendees_count: number;
  hangout_link: string | null;
}

function classifyEventType(ev: Record<string, unknown>): AgendaEventPayload["type"] {
  const summary = String(ev.summary || "").toLowerCase();
  if (ev.hangoutLink || ev.conferenceData) return "meeting";
  if (
    summary.includes("call") ||
    summary.includes("ligar") ||
    summary.includes("ligação") ||
    summary.includes("ligacao")
  ) {
    return "call";
  }
  if (
    summary.includes("prazo") ||
    summary.includes("deadline") ||
    summary.includes("entrega")
  ) {
    return "deadline";
  }
  return "meeting";
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const startedAt = Date.now();
  let clientIdLog: string | null = null;
  let calendarIdLog: string | null = null;

  try {
    // ── Auth: validate JWT via Auth API (supports ES256) ──
    const authHeader = req.headers.get("authorization");
    if (!authHeader) {
      return json({ error: "Missing authorization header" }, 401);
    }
    const token = authHeader.replace(/^[Bb]earer\s+/, "");
    const userResp = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
      headers: {
        Authorization: `Bearer ${token}`,
        apikey: SUPABASE_ANON_KEY,
      },
    });
    if (!userResp.ok) {
      return json({ error: "Invalid or expired token" }, 401);
    }
    const userPayload = await userResp.json();
    const userId = userPayload?.id as string | undefined;
    if (!userId) return json({ error: "Invalid auth payload" }, 401);

    // ── Body (optional rangeDays override) ──
    let body: { rangeDays?: number } = {};
    if (req.method === "POST") {
      try {
        body = await req.json();
      } catch {
        // empty body is fine
      }
    }

    const supabase = getServiceClient();

    // ── Resolve client_id from authenticated user ──
    const { data: clientRow, error: clientErr } = await supabase
      .from("clientes_blu")
      .select("client_id")
      .eq("external_user_id", userId)
      .maybeSingle();

    if (clientErr) {
      console.error("[google-calendar-events] client lookup failed", clientErr);
      return json({ error: "Failed to resolve client" }, 500);
    }
    if (!clientRow) {
      return json({
        events: [],
        disabled: true,
        reason: "no_client",
        fetched_at: new Date().toISOString(),
      });
    }
    const clientId = String(clientRow.client_id);
    clientIdLog = clientId;

    // ── Calendar settings ──
    const { data: settings } = await supabase
      .from("calendar_settings")
      .select("calendar_id, enabled, range_days, timezone")
      .eq("client_id", clientId)
      .maybeSingle();

    if (!settings || !settings.enabled) {
      return json({
        events: [],
        disabled: true,
        reason: "calendar_disabled",
        fetched_at: new Date().toISOString(),
      });
    }

    const calendarId = settings.calendar_id || "primary";
    calendarIdLog = calendarId;
    const rangeDays = Math.max(
      1,
      Math.min(60, Number(body.rangeDays ?? settings.range_days ?? 7)),
    );

    // ── Default Google integration tokens for this client ──
    const { data: tokens, error: tokensErr } = await supabase
      .from("integration_tokens")
      .select("refresh_token_encrypted")
      .eq("client_id", clientId)
      .eq("provider", "google")
      .order("is_default", { ascending: false })
      .order("updated_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (tokensErr) {
      console.error("[google-calendar-events] tokens lookup failed", tokensErr);
      return json({ error: "Failed to read integration tokens" }, 500);
    }
    if (!tokens?.refresh_token_encrypted) {
      return json({
        events: [],
        disabled: true,
        reason: "reauth_required",
        fetched_at: new Date().toISOString(),
      });
    }

    let refreshToken: string;
    try {
      refreshToken = decryptFernet(tokens.refresh_token_encrypted);
    } catch (e) {
      console.error("[google-calendar-events] decrypt failed", e);
      return json({
        events: [],
        disabled: true,
        reason: "decrypt_failed",
        fetched_at: new Date().toISOString(),
      });
    }

    // ── Platform OAuth client config (vault-backed RPC) ──
    const { data: oauthConfig, error: oauthErr } = await supabase.rpc(
      "get_platform_google_oauth_config",
    );
    if (oauthErr || !oauthConfig?.client_id || !oauthConfig?.client_secret) {
      console.error(
        "[google-calendar-events] platform oauth config missing",
        oauthErr,
      );
      return json({
        events: [],
        disabled: true,
        reason: "oauth_not_configured",
        fetched_at: new Date().toISOString(),
      });
    }

    // ── Refresh access token ──
    let accessToken: string;
    try {
      accessToken = await exchangeRefreshToken(
        refreshToken,
        oauthConfig.client_id,
        oauthConfig.client_secret,
      );
    } catch (e) {
      console.error("[google-calendar-events] token refresh failed", e);
      // Mark calendar as disabled so the next visit prompts re-auth.
      await supabase
        .from("calendar_settings")
        .update({ enabled: false })
        .eq("client_id", clientId);
      return json({
        events: [],
        disabled: true,
        reason: "reauth_required",
        fetched_at: new Date().toISOString(),
      });
    }

    // ── Calendar API call ──
    const now = new Date();
    const timeMin = now.toISOString();
    const timeMax = new Date(
      now.getTime() + rangeDays * 24 * 60 * 60 * 1000,
    ).toISOString();

    const url = new URL(
      `https://www.googleapis.com/calendar/v3/calendars/${encodeURIComponent(
        calendarId,
      )}/events`,
    );
    url.searchParams.set("timeMin", timeMin);
    url.searchParams.set("timeMax", timeMax);
    url.searchParams.set("singleEvents", "true");
    url.searchParams.set("orderBy", "startTime");
    url.searchParams.set("maxResults", "50");

    const eventsResp = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    if (eventsResp.status === 401 || eventsResp.status === 403) {
      await supabase
        .from("calendar_settings")
        .update({ enabled: false })
        .eq("client_id", clientId);
      return json({
        events: [],
        disabled: true,
        reason: "reauth_required",
        fetched_at: new Date().toISOString(),
      });
    }
    if (!eventsResp.ok) {
      const errText = await eventsResp.text();
      console.error(
        "[google-calendar-events] calendar API error",
        eventsResp.status,
        errText,
      );
      return json(
        { error: "calendar_api_error", status: eventsResp.status },
        502,
      );
    }

    const eventsData = await eventsResp.json();
    const events: AgendaEventPayload[] = (eventsData.items || []).map(
      (ev: Record<string, unknown>) => {
        const start = ev.start as { dateTime?: string; date?: string } | undefined;
        const end = ev.end as { dateTime?: string; date?: string } | undefined;
        const attendees = (ev.attendees as unknown[] | undefined) ?? [];
        return {
          id: String(ev.id ?? ""),
          title: String(ev.summary ?? "(sem título)"),
          starts_at: String(start?.dateTime ?? start?.date ?? ""),
          ends_at: String(end?.dateTime ?? end?.date ?? ""),
          type: classifyEventType(ev),
          location: (ev.location as string | undefined) ?? null,
          attendees_count: Array.isArray(attendees) ? attendees.length : 0,
          hangout_link: (ev.hangoutLink as string | undefined) ?? null,
        };
      },
    );

    console.log(
      JSON.stringify({
        fn: "google-calendar-events",
        client_id: clientId,
        calendar_id: calendarId,
        status: "ok",
        events_count: events.length,
        range_days: rangeDays,
        latency_ms: Date.now() - startedAt,
      }),
    );

    return json({
      events,
      disabled: false,
      fetched_at: new Date().toISOString(),
      range_days: rangeDays,
    });
  } catch (e) {
    console.error(
      JSON.stringify({
        fn: "google-calendar-events",
        client_id: clientIdLog,
        calendar_id: calendarIdLog,
        status: "error",
        latency_ms: Date.now() - startedAt,
        error: e instanceof Error ? e.message : String(e),
      }),
    );
    return json(
      {
        error: "internal_error",
        message: e instanceof Error ? e.message : String(e),
      },
      500,
    );
  }
});
