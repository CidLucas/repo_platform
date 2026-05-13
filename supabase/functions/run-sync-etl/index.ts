/**
 * run-sync-etl — Sync orchestrator
 *
 * Validates auth/ownership, guards against duplicate jobs, creates a reg_jobs
 * record (status=pending), and returns the job_id immediately.
 *
 * The actual ETL runs in the database via analytics_v2.run_etl_job(), dispatched
 * by pg_cron (process_pending_etl_jobs) within ~1 minute of the job being created.
 * The DB function uses SET statement_timeout=0 so FDW scans complete without timeout.
 */

import {
  AuthError,
  createServiceClient,
  createUserClient,
  requireAuth,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

interface SyncRequest {
  client_id: string;
  credential_id: number;
  column_mapping?: Record<string, string>;
  force_full_sync?: boolean;
  skip_job_tracking?: boolean;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  if (req.method !== "POST") {
    return json({ error: "Method not allowed" }, 405);
  }

  const requestId = crypto.randomUUID();
  const startTime = Date.now();

  try {
    // ── 1. Auth ──────────────────────────────────────────────────────────────
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);
    const userId = ctx.userId;

    // ── 2. Parse body ────────────────────────────────────────────────────────
    const contentType = req.headers.get("content-type");
    if (!contentType?.includes("application/json")) {
      return json({ error: "Content-Type must be application/json" }, 400);
    }

    let body: Partial<SyncRequest>;
    try {
      body = await req.json() as Partial<SyncRequest>;
    } catch {
      return json({ error: "Invalid JSON in request body" }, 400);
    }

    const { client_id, credential_id, force_full_sync = false, skip_job_tracking = false } = body;

    if (!client_id || !credential_id) {
      return json({ error: "client_id and credential_id are required" }, 400);
    }

    const normalizedCredentialId = Number(credential_id);
    if (!Number.isInteger(normalizedCredentialId) || normalizedCredentialId <= 0) {
      return json({ error: "credential_id must be a positive integer" }, 400);
    }

    const svc = createServiceClient(SUPABASE_URL, SERVICE_ROLE_KEY);

    // ── 3. Ownership check ───────────────────────────────────────────────────
    const userClient = createUserClient(ctx.token, SUPABASE_URL, SUPABASE_ANON_KEY);

    const { data: userClients, error: userClientsError } = await userClient
      .from("clientes_blu")
      .select("client_id")
      .eq("external_user_id", userId);

    if (userClientsError) {
      console.error(`[run-sync-etl] ${requestId} Ownership lookup failed:`, userClientsError);
      return json({ error: "Failed to validate client ownership" }, 500);
    }

    const ownsClient = (userClients ?? []).some(
      (row: { client_id: string }) => String(row.client_id) === String(client_id),
    );
    if (!ownsClient) {
      return json({ error: "Unauthorized: client_id does not belong to authenticated user" }, 403);
    }

    // ── 4. Duplicate guard ───────────────────────────────────────────────────
    if (!skip_job_tracking) {
      const { data: existingJob } = await svc
        .schema("analytics_v2")
        .from("reg_jobs")
        .select("job_id, status")
        .eq("client_id", client_id)
        .eq("job_type", "bigquery_sync")
        .in("status", ["pending", "running"])
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle();

      if (existingJob?.job_id) {
        return json({
          error: "A sync job is already in progress",
          existing_job_id: existingJob.job_id,
          status: existingJob.status,
        }, 409);
      }
    }

    // ── 5. Persist column_mapping to client_data_sources (durable config for recurring syncs) ──
    const column_mapping = body.column_mapping ?? null;
    if (column_mapping && Object.keys(column_mapping).length > 0) {
      const { error: mappingErr } = await svc
        .from("client_data_sources")
        .update({
          column_mapping,
          sync_status: "mapping_confirmed",
          updated_at: new Date().toISOString(),
        })
        .eq("client_id", client_id)
        .eq("credential_id", normalizedCredentialId);

      if (mappingErr) {
        console.warn(`[run-sync-etl] ${requestId} Failed to persist column_mapping:`, mappingErr);
      }
    }

    // ── 6. Create job ────────────────────────────────────────────────────────
    let jobId: string | null = null;
    if (!skip_job_tracking) {
      const { data: job, error: jobErr } = await svc
        .schema("analytics_v2")
        .from("reg_jobs")
        .insert({
          client_id,
          job_type: "bigquery_sync",
          status: "pending",
          input_params: { credential_id: normalizedCredentialId, force_full_sync: Boolean(force_full_sync) },
          progress_pct: 0,
        })
        .select("job_id")
        .single();

      if (jobErr || !job) {
        console.error(`[run-sync-etl] ${requestId} Failed to create job:`, jobErr);
        return json({ error: "Failed to create sync job" }, 500);
      }
      jobId = job.job_id;
    }

    // ── 7. Return — pg_cron dispatches the ETL within ~1 minute ─────────────
    const initDuration = Date.now() - startTime;
    console.log(`[run-sync-etl] ${requestId} Queued job=${jobId} in ${initDuration}ms`);

    return json({
      success: true,
      job_id: jobId,
      request_id: requestId,
      message: skip_job_tracking
        ? "Sync started (job tracking disabled)."
        : "Sync job queued. ETL will start within ~1 minute.",
    }, 200, {
      "X-Request-Id": requestId,
      "X-Duration-Ms": String(initDuration),
    });

  } catch (err) {
    if (err instanceof AuthError) {
      return json({ error: err.message }, err.status);
    }
    console.error(`[run-sync-etl] ${requestId} Handler error:`, err);
    return json({
      error: "Internal error",
      details: err instanceof Error ? err.message : String(err),
    }, 500);
  }
});
