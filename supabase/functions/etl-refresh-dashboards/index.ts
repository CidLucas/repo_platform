/**
 * etl-refresh-dashboards
 *
 * Processa um job do tipo `refresh_dashboards` na fila analytics_v2.reg_jobs.
 * Executa REFRESH nas 4 MVs de analytics_v2 (CONCURRENTLY onde possível)
 * para um client_id específico — chamado pelo dispatcher process_pending_jobs
 * via pg_net, ou manualmente via service role.
 *
 * Flow:
 *   1. Auth: aceita service-role (pg_net) ou JWT com validação.
 *   2. Carrega job, valida job_type='refresh_dashboards' e status='running'.
 *   3. Extrai client_id do job.
 *   4. Executa REFRESH MATERIALIZED VIEW CONCURRENTLY das 4 MVs via RPC.
 *   5. Marca job como completed.
 *
 * Idempotência: CONCURRENTLY nunca bloqueia leituras. Se falhar, marca failed
 * e o dispatcher pode re-enfileirar.
 */

import { createClient } from "@supabase/supabase-js";
import { corsHeaders, json } from "../_shared/cors.ts";
import { isSystemInvocation } from "../_shared/blu_auth.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY =
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ??
  Deno.env.get("BLU_SYSTEM_INVOKE_KEY")!;

const MATERIALIZED_VIEWS = [
  "analytics_v2.mv_distribuicao_regional",
  "analytics_v2.mv_resumo_dashboard",
  "analytics_v2.mv_series_temporal",
  "analytics_v2.mv_ultimos_pedidos",
];

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
    auth: { persistSession: false },
  });

  // ── 1. Auth ──────────────────────────────────────────────────
  const authHeader = req.headers.get("Authorization") ?? "";
  const token = authHeader.replace("Bearer ", "").trim();

  if (!token) {
    return json({ error: "missing authorization" }, 401);
  }

  // Aceita service-role direto; para JWT de usuário, valida via Auth API
  const isSys = isSystemInvocation(req, SERVICE_ROLE_KEY);
  if (!isSys) {
    // Valida JWT de usuário (manual rerun via dashboard)
    const { error: userErr } = await admin.auth.getUser(token);
    if (userErr) return json({ error: "unauthorized", detail: userErr.message }, 401);
  }

  // ── 2. Carregar job ──────────────────────────────────────────
  let body: { job_id?: string };
  try {
    body = await req.json();
  } catch {
    return json({ error: "invalid json body" }, 400);
  }

  const { job_id } = body;
  if (!job_id) return json({ error: "job_id is required" }, 400);

  const { data: job, error: jobErr } = await admin
    .from("reg_jobs")
    .select("job_id, client_id, job_type, status")
    .eq("job_id", job_id)
    .single();

  if (jobErr || !job) {
    return json({ error: "job not found", detail: jobErr?.message }, 404);
  }
  if (job.job_type !== "refresh_dashboards") {
    return json({ error: `unexpected job_type: ${job.job_type}` }, 400);
  }
  // dispatcher já marcou como 'running'; aceitar também 'pending' p/ reruns manuais
  if (!["running", "pending"].includes(job.status)) {
    return json({ error: `job status is '${job.status}', expected running or pending` }, 409);
  }

  const client_id: string = job.client_id;

  // ── 3. Refresh MVs via RPC (SECURITY DEFINER) ────────────────
  // Cada MV é refreshada via RPC para evitar conceder USAGE em analytics_v2
  // diretamente à edge function. A RPC refresh_client_dashboards executa
  // REFRESH MATERIALIZED VIEW CONCURRENTLY — requer índice único na MV.
  // Fallback: se a MV não tiver índice único, faz REFRESH normal (bloqueante).
  const { error: refreshErr } = await admin.rpc("refresh_client_dashboards", {
    p_client_id: client_id,
  });

  if (refreshErr) {
    // Marcar como failed
    await admin
      .from("reg_jobs")
      .update({
        status: "failed",
        error_message: refreshErr.message,
        updated_at: new Date().toISOString(),
      })
      .eq("job_id", job_id);

    return json({ error: "refresh failed", detail: refreshErr.message }, 500);
  }

  // ── 4. Marcar completed ──────────────────────────────────────
  const { error: doneErr } = await admin
    .from("reg_jobs")
    .update({
      status: "completed",
      completed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    .eq("job_id", job_id);

  if (doneErr) {
    return json({ error: "failed to mark completed", detail: doneErr.message }, 500);
  }

  return json({
    ok: true,
    job_id,
    client_id,
    views_refreshed: MATERIALIZED_VIEWS.length,
  });
});
