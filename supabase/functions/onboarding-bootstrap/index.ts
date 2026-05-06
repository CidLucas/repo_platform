// supabase/functions/onboarding-bootstrap/index.ts
//
// Landing LaunchPad → one atomic provisioning call. Steps:
//   1. Verify caller JWT via Auth API.
//   2. Map wizard state → Context 2.0 sections via mappers.ts (same
//      module as apps/landing/src/onboarding/mappers.ts, ported to Deno).
//   3. Call public.onboarding_bootstrap_tx(jsonb) with the caller's JWT
//      so SECURITY INVOKER + RLS scope writes to the right tenant.
//   4. Best-effort Langfuse prompt seeding — for each selected agent
//      slug, clone default/<slug> (or landing/<slug>) into
//      tenant/<client_id>/<slug>. Failures are logged but do NOT fail
//      the call (recorded in onboarding_state.langfuse_seed_status so a
//      retry job can re-run). Pattern mirrors scripts/create_standalone_prompts.py.
//
// Request:  POST { ...OnboardingState }   (full wizard state; server re-validates)
// Response: 200 { client_id, agents, routines, prompts_seeded }

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

const LANGFUSE_BASE_URL =
  Deno.env.get("LANGFUSE_HOST") ??
  Deno.env.get("LANGFUSE_BASE_URL") ??
  "https://us.cloud.langfuse.com";
const LANGFUSE_PUBLIC_KEY = Deno.env.get("LANGFUSE_PUBLIC_KEY") ?? "";
const LANGFUSE_SECRET_KEY = Deno.env.get("LANGFUSE_SECRET_KEY") ?? "";

interface BootstrapTxResult {
  client_id: string;
  agents: number;
  routines: number;
}

interface LangfusePrompt {
  name?: string;
  prompt?: string;
  type?: string;
  tags?: string[];
  config?: Record<string, unknown>;
}

// Fetch the current prompt body (label=production) for a canonical slug.
// Returns null when the source prompt is missing — seeding is skipped for
// that agent and the caller receives a smaller `prompts_seeded` count.
async function fetchSourcePrompt(
  sourceName: string,
  auth: string,
): Promise<LangfusePrompt | null> {
  const url = `${LANGFUSE_BASE_URL}/api/public/v2/prompts/${encodeURIComponent(sourceName)}?label=production`;
  const resp = await fetch(url, {
    method: "GET",
    headers: { Authorization: auth, "Content-Type": "application/json" },
  });
  if (resp.status === 404) return null;
  if (!resp.ok) {
    console.warn(
      `[onboarding-bootstrap] Langfuse GET ${sourceName} failed: ${resp.status}`,
    );
    return null;
  }
  return (await resp.json()) as LangfusePrompt;
}

// Create a tenant-scoped copy of a source prompt. Idempotent: Langfuse
// versions are append-only; re-running just creates a new version with
// the same body, which the PromptLoader then serves via label.
async function createTenantPrompt(
  tenantName: string,
  source: LangfusePrompt,
  auth: string,
  clientId: string,
  slug: string,
): Promise<boolean> {
  const url = `${LANGFUSE_BASE_URL}/api/public/v2/prompts`;
  const payload = {
    name: tenantName,
    prompt: source.prompt ?? "",
    type: source.type ?? "text",
    labels: ["production"],
    tags: [
      ...(source.tags ?? []),
      "tenant",
      `client:${clientId}`,
      `agent:${slug}`,
    ],
    config: source.config ?? {},
  };
  const resp = await fetch(url, {
    method: "POST",
    headers: { Authorization: auth, "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    console.warn(
      `[onboarding-bootstrap] Langfuse POST ${tenantName} failed: ${resp.status} ${text}`,
    );
    return false;
  }
  return true;
}

async function seedLangfusePrompts(
  clientId: string,
  agents: string[],
): Promise<number> {
  if (!LANGFUSE_PUBLIC_KEY || !LANGFUSE_SECRET_KEY) {
    console.warn(
      "[onboarding-bootstrap] Langfuse keys not configured; skipping prompt seed",
    );
    return 0;
  }
  const auth = `Basic ${btoa(`${LANGFUSE_PUBLIC_KEY}:${LANGFUSE_SECRET_KEY}`)}`;

  let seeded = 0;
  for (const slug of agents) {
    // Canonical landing prompts are seeded at `landing/<slug>` (see
    // 20260423130400_agent_catalog_landing_slugs.sql::prompt_name).
    const sourceName = `landing/${slug}`;
    const tenantName = `tenant/${clientId}/${slug}`;
    try {
      const source = await fetchSourcePrompt(sourceName, auth);
      if (!source || !source.prompt) continue;
      const ok = await createTenantPrompt(tenantName, source, auth, clientId, slug);
      if (ok) seeded += 1;
    } catch (err) {
      console.warn(
        `[onboarding-bootstrap] Langfuse seed error for ${slug}:`,
        err,
      );
    }
  }
  return seeded;
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
    };

    // ── 3. Call the atomic RPC with the caller's JWT (RLS scope) ────────────
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

    // ── Best-effort Langfuse prompt seeding (outside the transaction) ──
    let promptsSeeded = 0;
    try {
      promptsSeeded = await seedLangfusePrompts(result.client_id, payload.agents);
    } catch (err) {
      console.warn("[onboarding-bootstrap] Langfuse seeding errored:", err);
    }

    // Record seed status on onboarding_state so a retry job can re-run
    // if Langfuse was unreachable. Uses the caller's JWT + the existing
    // merge_onboarding_state RPC so we only patch the status key and
    // preserve the rest of the wizard state blob.
    try {
      await userClient.rpc("merge_onboarding_state", {
        p_patch: {
          langfuse_seed_status: {
            seeded: promptsSeeded,
            requested: payload.agents.length,
            at: new Date().toISOString(),
          },
        },
      });
    } catch (err) {
      console.warn("[onboarding-bootstrap] Failed to stamp seed status:", err);
    }

    // ── 4. Fire website-context-builder if a website was provided ────────────
    if (state.website && SUPABASE_SERVICE_ROLE_KEY) {
      const ctxPayload = {
        client_id: result.client_id,
        website: state.website,
        onboarding_state: {
          nome: state.nome,
          empresa: state.empresa,
          website: state.website,
          vertical: state.vertical,
          teamSize: state.teamSize,
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

    return json({
      client_id: result.client_id,
      agents: result.agents,
      routines: result.routines,
      prompts_seeded: promptsSeeded,
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
