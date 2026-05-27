// supabase/functions/onboarding-bootstrap/index.ts
//
// Landing LaunchPad → one atomic provisioning call. Steps:
//   1. Verify caller JWT via Auth API.
//   2. Map wizard state → Context 2.0 sections via mappers.ts (same
//      module as apps/landing/src/onboarding/mappers.ts, ported to Deno).
//   3. Call public.onboarding_bootstrap_tx(jsonb) with the caller's JWT
//      so SECURITY INVOKER + RLS scope writes to the right tenant.
//
// Request:  POST { ...OnboardingState }   (full wizard state; server re-validates)
// Response: 200 { client_id, agents, routines }
//
// NOTE (Mai/2026): Langfuse prompt seeding foi REMOVIDO. Decisão validada com
// Lucas: NENHUM prompt tenant-scoped vai pro Langfuse — overrides são só
// globais. O seed síncrono aqui (6 fetches HTTP us.cloud.langfuse.com,
// namespace `landing/<slug>` que retornava 404 porque o catalog usa
// `agents/<slug>`) travava a edge function por segundos e bloqueava o redirect
// do wizard ("Iniciando seu bureau" preso). Ver
// docs/observability/onboarding-trace-mai2026-partial.md.

import {
  requireAuth,
  createUserClient,
  createServiceClient,
  AuthError,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";
import {
  mapBusinessDNAToCompanyProfile,
  mapContactToTeamStructure,
  mapRulesToPolicies,
  type OnboardingState,
} from "./mappers.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

interface BootstrapTxResult {
  client_id: string;
  agents: number;
  routines: number;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }
  if (req.method !== "POST") {
    return json({ error: "method not allowed" }, 405);
  }

  try {
    // ── 1. Auth: validate JWT, extract user context ──────────────────────────
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);
    const userClient = createUserClient(ctx.token, SUPABASE_URL, SUPABASE_ANON_KEY);

    // ── 2. Parse body ────────────────────────────────────────────────────────
    let state: OnboardingState;
    try {
      state = (await req.json()) as OnboardingState;
    } catch {
      return json({ error: "Invalid JSON body" }, 400);
    }
    if (!state || typeof state !== "object") {
      return json({ error: "Body must be an OnboardingState object" }, 400);
    }

    // ── Build bootstrap payload (Context 2.0 sections + agents/routines) ──
    const payload = {
      company_profile: mapBusinessDNAToCompanyProfile(state),
      team_structure: mapContactToTeamStructure(state),
      policies: mapRulesToPolicies(state),
      agents: Array.isArray(state.agents) ? state.agents : [],
      routines: Array.isArray(state.routines) ? state.routines : [],
      notify_channel: state.notifyChannel ?? "email",
      nome_empresa: (state.empresa ?? "").trim() || null,
      cnpj: (state.cnpj ?? "").replace(/\D/g, "") || null,
    };

    // ── 3. Ensure clientes_blu row exists before the transaction ────────────
    // ensure_tenant_row() is SECURITY DEFINER — it inserts the row bypassing
    // RLS if the handle_new_auth_user trigger missed it (e.g. some OAuth flows).
    const { error: ensureError } = await userClient.rpc("ensure_tenant_row");
    if (ensureError) {
      console.error("[onboarding-bootstrap] ensure_tenant_row failed:", ensureError);
      return json(
        { error: "Failed to initialize tenant", details: ensureError.message },
        500,
      );
    }

    // ── 4. Call the atomic RPC with the caller's JWT (RLS scope) ────────────
    const { data: txData, error: txError } = await userClient.rpc(
      "onboarding_bootstrap_tx",
      { p_payload: payload },
    );
    if (txError) {
      console.error("[onboarding-bootstrap] RPC failed:", txError);
      return json(
        { error: "bootstrap transaction failed", details: txError.message },
        500,
      );
    }
    const result = txData as BootstrapTxResult;

    // ── Best-effort knowledge document bootstrap ──────────────────────────────
    // Seeds initial client_knowledge_documents rows from onboarding data so
    // coverage scores are non-zero from day one.
    if (SUPABASE_SERVICE_ROLE_KEY) {
      try {
        const svc = createServiceClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
        const { error: kbErr } = await svc.rpc("bootstrap_knowledge_from_onboarding", {
          p_client_id: result.client_id,
        });
        if (kbErr) {
          console.warn("[onboarding-bootstrap] bootstrap_knowledge_from_onboarding failed:", kbErr.message);
        }
      } catch (err) {
        console.warn("[onboarding-bootstrap] Knowledge bootstrap error:", err);
      }
    }

    // ── 5. Fire website-context-builder if a website was provided ────────────
    if (state.website && SUPABASE_SERVICE_ROLE_KEY) {
      const ctxPayload = {
        client_id: result.client_id,
        website: state.website,
        onboarding_state: {
          nome: state.nome,
          empresa: state.empresa,
          website: state.website,
          vertical: state.vertical,
          teamSize: state.porte,
          email: state.email,
        },
      };
      EdgeRuntime.waitUntil(
        fetch(`${SUPABASE_URL}/functions/v1/website-context-builder`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
          },
          body: JSON.stringify(ctxPayload),
        }).then(async (r) => {
          if (!r.ok) {
            const txt = await r.text().catch(() => "");
            console.warn(`[onboarding-bootstrap] website-context-builder responded ${r.status}: ${txt}`);
          } else {
            console.log(`[onboarding-bootstrap] website-context-builder triggered for ${result.client_id}`);
          }
        }).catch((err) => {
          console.warn("[onboarding-bootstrap] website-context-builder fire failed:", err);
        }),
      );
    }

    // ── 6. Fire generate-context-report (best-effort; skips if no data yet) ─
    if (SUPABASE_SERVICE_ROLE_KEY) {
      EdgeRuntime.waitUntil(
        fetch(`${SUPABASE_URL}/functions/v1/generate-context-report`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
          },
          body: JSON.stringify({ client_id: result.client_id }),
        }).then(async (r) => {
          const body = await r.json().catch(() => ({}));
          if (!r.ok) {
            console.warn(`[onboarding-bootstrap] generate-context-report ${r.status}:`, body);
          } else if (body.skipped) {
            console.log(`[onboarding-bootstrap] generate-context-report skipped (no data yet) for ${result.client_id}`);
          } else {
            console.log(`[onboarding-bootstrap] context report generated: doc=${body.document_id}`);
          }
        }).catch((err) => {
          console.warn("[onboarding-bootstrap] generate-context-report fire failed:", err);
        }),
      );
    }

    // ── 7. Fire onboarding_complete routine (best-effort) ────────────────────
    // The routine is event-triggered and requires an explicit dispatch call —
    // check_and_enqueue_triggers() only polls cron/numeric triggers.
    // We call dispatch_routine_event() via service role so it can bypass RLS
    // to insert the execution row.  waitUntil keeps the response fast.
    if (SUPABASE_SERVICE_ROLE_KEY && result.routines > 0) {
      const svcForEvent = createServiceClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
      EdgeRuntime.waitUntil(
        (async () => {
          try {
            const { data, error } = await svcForEvent.rpc("dispatch_routine_event", {
              p_routine_id: "onboarding_complete",
              p_client_id: result.client_id,
              p_trigger_data: { event_type: "onboarding_completed" },
            });
            if (error) {
              console.warn("[onboarding-bootstrap] dispatch_routine_event failed:", error.message);
            } else if (data) {
              console.log(`[onboarding-bootstrap] onboarding_complete routine dispatched: exec=${data}`);
            } else {
              console.log("[onboarding-bootstrap] dispatch_routine_event returned null (guard blocked or no subscription)");
            }
          } catch (err) {
            console.warn("[onboarding-bootstrap] dispatch_routine_event error:", err);
          }
        })(),
      );
    }

    return json({
      client_id: result.client_id,
      agents: result.agents,
      routines: result.routines,
    });
  } catch (err) {
    if (err instanceof AuthError) {
      return json({ error: err.message }, err.status);
    }
    console.error("[onboarding-bootstrap] Unhandled error:", err);
    return json(
      { error: "internal error", details: (err as Error).message },
      500,
    );
  }
});
