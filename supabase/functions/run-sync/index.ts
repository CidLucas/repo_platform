import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const RUNNING_JOB_GRACE_MINUTES = 35;

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

Deno.serve(async (req: Request) => {
  // ── CORS preflight ──
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // ── Auth: validate JWT via Auth API (supports ES256) ──
    const authHeader = req.headers.get("authorization");
    if (!authHeader) {
      return json({ error: "Missing authorization header" }, 401);
    }

    const token = authHeader.replace(/^[Bb]earer\s+/, "");
    const userResp = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
      method: "GET",
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

    const supabase = getServiceClient();

    // ── Parse body ──
    const body = await req.json();
    const { client_id, credential_id, force_full_sync = false } = body;

    if (!client_id || !credential_id) {
      return json({ error: "client_id and credential_id are required" }, 400);
    }

    const normalizedCredentialId = Number(credential_id);
    if (!Number.isInteger(normalizedCredentialId) || normalizedCredentialId <= 0) {
      return json({ error: "credential_id must be a positive integer" }, 400);
    }

    // ── Ownership check ──
    // clientes_vizu.client_id is UUID while reg_jobs.client_id is TEXT.
    // Query by user first, then compare IDs in application code to avoid
    // Postgres uuid=text operator mismatch.
    const { data: userClients, error: userClientsError } = await supabase
      .from("clientes_vizu")
      .select("client_id")
      .eq("external_user_id", userId);

    if (userClientsError) {
      console.error("[run-sync] Failed ownership lookup:", userClientsError);
      return json({ error: "Failed to validate client ownership" }, 500);
    }

    const ownsClient = (userClients ?? []).some(
      (row) => String(row.client_id) === String(client_id)
    );

    if (!ownsClient) {
      return json(
        { error: "Unauthorized: client_id does not belong to authenticated user" },
        403
      );
    }

    // ── Mapping readiness gate ──
    // Sync must only run after foreign-table discovery and column mapping have
    // been persisted to client_data_sources. Without that, the SQL worker has
    // no reliable routing metadata and falls into schema/type mismatches.
    const { data: dataSource, error: dataSourceError } = await supabase
      .from("client_data_sources")
      .select("id, source_columns, column_mapping")
      .eq("client_id", client_id)
      .eq("credential_id", normalizedCredentialId)
      .order("atualizado_em", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (dataSourceError) {
      console.error("[run-sync] Failed data source lookup:", dataSourceError);
      return json({ error: "Failed to validate data source mapping" }, 500);
    }

    if (!dataSource) {
      return json(
        {
          error:
            "No discovered data source found for this credential. Run column discovery/mapping before syncing.",
        },
        409
      );
    }

    const sourceColumns = Array.isArray(dataSource.source_columns)
      ? dataSource.source_columns
      : [];
    const columnMapping =
      dataSource.column_mapping && typeof dataSource.column_mapping === "object"
        ? (dataSource.column_mapping as Record<string, unknown>)
        : {};

    if (sourceColumns.length === 0) {
      return json(
        {
          error:
            "This data source has no discovered source columns yet. Re-run discovery before syncing.",
        },
        409
      );
    }

    if (Object.keys(columnMapping).length === 0) {
      return json(
        {
          error:
            "This data source has no saved column mapping. Run match-columns before syncing.",
        },
        409
      );
    }

    // ── Duplicate guard: block only pending or non-stale running jobs ──
    // Jobs stuck 'running' for >= 15 min are cleaned up by the janitor cron
    // and should not block new submissions.
    const runningGraceIso = new Date(
      Date.now() - RUNNING_JOB_GRACE_MINUTES * 60 * 1000
    ).toISOString();
    const { data: existingJob } = await supabase
      .schema("analytics_v2")
      .from("reg_jobs")
      .select("job_id, status")
      .eq("client_id", client_id)
      .eq("job_type", "bigquery_sync")
      .contains("input_params", { credential_id: normalizedCredentialId })
      .or(
        `status.eq.pending,and(status.eq.running,started_at.gt.${runningGraceIso})`
      )
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (existingJob?.job_id) {
      return json(
        {
          error: "A sync job is already in progress for this data source",
          existing_job_id: existingJob.job_id,
          status: existingJob.status,
        },
        409
      );
    }

    // ── Enqueue: insert reg_jobs row as 'pending' ──
    // pg_cron will pick this up within 30 seconds and run
    // sincronizar_dados_cliente() directly in Postgres (no wall-clock limit).
    const { data: job, error: insertError } = await supabase
      .schema("analytics_v2")
      .from("reg_jobs")
      .insert({
        client_id,
        job_type: "bigquery_sync",
        status: "pending",
        input_params: {
          credential_id: normalizedCredentialId,
          force_full_sync: Boolean(force_full_sync),
        },
        progress_pct: 0,
      })
      .select("job_id")
      .single();

    if (insertError || !job) {
      console.error("[run-sync] Failed to create job:", insertError);
      return json({ error: "Failed to create sync job", details: insertError }, 500);
    }

    console.log(
      `[run-sync] Enqueued job ${job.job_id} for client ${client_id} credential ${normalizedCredentialId}.`
    );

    return json(
      {
        success: true,
        job_id: job.job_id,
        message: "Sync job enqueued. pg_cron will execute within 30 seconds.",
      },
      202
    );
  } catch (err) {
    console.error("[run-sync] Handler error:", err);
    return json(
      {
        error: "Internal error",
        details: err instanceof Error ? err.message : String(err),
      },
      500
    );
  }
});
