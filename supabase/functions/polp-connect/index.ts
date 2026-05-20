/**
 * polp-connect — Initiate a Polp Open Finance bank connection
 *
 * Called by AdminScreen when user clicks "Conectar" on the Open Finance card.
 * Uses Blu's shared POLP_API_CLIENT / POLP_API_SECRET env vars (never sent to frontend).
 * Creates an integration in Polp, stores the mapping in polp_integrations, and
 * returns url_to_authenticate when the institution requires MFA/OAuth via Pluggy.
 */

import {
  createServiceClient,
  createUserClient,
  requireAuth,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const POLP_API_CLIENT = Deno.env.get("POLP_API_CLIENT")!;
const POLP_API_SECRET = Deno.env.get("POLP_API_SECRET")!;
const POLP_BASE_URL = "https://dev.polp.com.br/api/v1";

const polpHeaders = {
  "x-api-client": POLP_API_CLIENT,
  "x-api-secret": POLP_API_SECRET,
  "Content-Type": "application/json",
};

interface ConnectRequest {
  client_id: string;
  institution_id: number;
  cpf?: string;
  cnpj?: string;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  try {
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);
    const userClient = createUserClient(ctx.token, SUPABASE_URL, Deno.env.get("SUPABASE_ANON_KEY")!);
    const svc = createServiceClient(SUPABASE_URL, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

    const body = await req.json() as Partial<ConnectRequest>;
    const { client_id, institution_id, cpf, cnpj } = body;

    if (!client_id || !institution_id) {
      return json({ error: "client_id and institution_id are required" }, 400);
    }

    // Verify the authenticated user belongs to this client
    const { data: membership } = await userClient
      .from("client_users")
      .select("id")
      .eq("client_id", client_id)
      .eq("auth_user_id", ctx.userId)
      .single();

    if (!membership) return json({ error: "Forbidden" }, 403);

    // Create integration in Polp
    const polpBody: Record<string, unknown> = { institution_id };
    if (cpf) polpBody.cpf = cpf;
    if (cnpj) polpBody.cnpj = cnpj;

    const polpRes = await fetch(`${POLP_BASE_URL}/integrations`, {
      method: "POST",
      headers: polpHeaders,
      body: JSON.stringify(polpBody),
    });

    if (!polpRes.ok) {
      const err = await polpRes.json().catch(() => ({}));
      return json({ error: "Polp API error", detail: err }, 502);
    }

    let { data: polpIntg } = await polpRes.json();

    // PAR request_uris embedded in url_to_authenticate expire in ~90s.
    // Polp reuses existing integrations (idempotent by institution_id), so a
    // previous connect attempt's URL may already be expired. When that happens,
    // call the reconnect endpoint to force Polp to issue a fresh auth URL.
    const expiresAt = polpIntg?.url_to_authenticate_expires_at
      ? new Date(polpIntg.url_to_authenticate_expires_at)
      : null;
    const urlExpired = polpIntg?.url_to_authenticate && expiresAt && expiresAt < new Date();

    console.log("[polp-connect]", {
      id: polpIntg?.id,
      status: polpIntg?.status,
      expires_at: polpIntg?.url_to_authenticate_expires_at,
      url_expired: urlExpired,
    });

    if (urlExpired) {
      const reconnectRes = await fetch(
        `${POLP_BASE_URL}/integrations/${polpIntg.id}/reconnect`,
        { method: "POST", headers: polpHeaders }
      );
      if (reconnectRes.ok) {
        const { data: refreshed } = await reconnectRes.json();
        if (refreshed) polpIntg = refreshed;
      } else {
        console.warn("[polp-connect] reconnect failed:", await reconnectRes.text());
      }
    }

    // Store integration mapping in our DB using service role (bypasses RLS for insert)
    const { error: dbErr } = await svc.from("polp_integrations").upsert({
      client_id,
      polp_integration_id: polpIntg.id,
      institution_id: polpIntg.institution_id,
      status: polpIntg.status,
      execution_status: polpIntg.execution_status,
      url_to_authenticate: polpIntg.url_to_authenticate,
      url_to_authenticate_expires_at: polpIntg.url_to_authenticate_expires_at,
      updated_at: new Date().toISOString(),
    }, { onConflict: "client_id,polp_integration_id" });

    if (dbErr) {
      console.error("DB insert error:", dbErr);
      return json({ error: "Failed to store integration" }, 500);
    }

    return json({
      polp_integration_id: polpIntg.id,
      status: polpIntg.status,
      url_to_authenticate: polpIntg.url_to_authenticate,
      url_to_authenticate_expires_at: polpIntg.url_to_authenticate_expires_at,
    });
  } catch (err) {
    const status = (err as { status?: number }).status ?? 500;
    return json({ error: (err as Error).message }, status);
  }
});
