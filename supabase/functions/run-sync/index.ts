import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import postgres from "https://deno.land/x/postgresjs@v3.4.5/mod.js";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const DB_URL = Deno.env.get("SUPABASE_DB_URL")!;

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

/** Service-role client — bypasses RLS */
function getServiceClient() {
  return createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

/** Helper: update reg_jobs row */
async function updateJob(
  supabase: ReturnType<typeof createClient>,
  jobId: string,
  patch: Record<string, unknown>
) {
  const { error } = await supabase
    .schema("analytics_v2")
    .from("reg_jobs")
    .update({ ...patch, updated_at: new Date().toISOString() })
    .eq("job_id", jobId);

  if (error) console.error(`[run-sync] updateJob ${jobId} failed:`, error);
}

/** Fire-and-forget: run the heavy sync in the background */
async function runSyncInBackground(
  jobId: string,
  clientId: string,
  credentialId: string,
  forceFullSync: boolean
) {
  const supabase = getServiceClient();

  // Direct postgres connection via pooler — bypasses PostgREST 60s gateway timeout
  const sql = postgres(DB_URL, { prepare: false });

  try {
    // Mark job as running
    await updateJob(supabase, jobId, {
      status: "running",
      started_at: new Date().toISOString(),
      progress_pct: 5,
    });

    console.log(
      `[run-sync] Starting sincronizar_dados_cliente for job ${jobId} (direct pg)`
    );

    // Set a generous statement timeout (10 min) and call the function directly
    // This bypasses PostgREST entirely — no 60s gateway timeout
    // Use a transaction so SET + SELECT run on the same pooled connection
    const rows = await sql.begin(async (tx: ReturnType<typeof postgres>) => {
      await tx`SET LOCAL statement_timeout = '600000'`;
      return await tx`
        SELECT sincronizar_dados_cliente(
          ${clientId}::uuid,
          ${parseInt(credentialId)}::integer,
          ${forceFullSync}::boolean
        ) as result
      `;
    });

    // Extract the result
    const syncResult = rows?.[0]?.result;

    console.log(`[run-sync] RPC completed for job ${jobId}:`, syncResult);

    // Parse result — it comes back as JSONB from the function
    let parsedResult = syncResult;
    if (typeof syncResult === "string") {
      try { parsedResult = JSON.parse(syncResult); } catch { parsedResult = { message: syncResult }; }
    }

    // Check if the function returned success: false
    if (parsedResult && parsedResult.success === false) {
      await updateJob(supabase, jobId, {
        status: "failed",
        error_message: parsedResult.error || "Sync function returned failure",
        completed_at: new Date().toISOString(),
        progress_pct: 0,
      });
      return;
    }

    // Mark completed
    await updateJob(supabase, jobId, {
      status: "completed",
      result: typeof parsedResult === "object" ? parsedResult : { message: String(parsedResult) },
      completed_at: new Date().toISOString(),
      progress_pct: 100,
    });
  } catch (err) {
    console.error(`[run-sync] Unexpected error for job ${jobId}:`, err);
    await updateJob(supabase, jobId, {
      status: "failed",
      error_message: err instanceof Error ? err.message : String(err),
      completed_at: new Date().toISOString(),
      progress_pct: 0,
    });
  } finally {
    // Close the direct connection
    await sql.end();
  }
}

Deno.serve(async (req: Request) => {
  // ── CORS preflight ──
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // ── Auth: extract client from JWT or body ──
    const body = await req.json();
    const { client_id, credential_id, force_full_sync = false } = body;

    if (!client_id || !credential_id) {
      return new Response(
        JSON.stringify({ error: "client_id and credential_id are required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const supabase = getServiceClient();

    // ── Create a job record in reg_jobs ──
    const { data: job, error: insertError } = await supabase
      .schema("analytics_v2")
      .from("reg_jobs")
      .insert({
        client_id,
        job_type: "bigquery_sync",
        status: "pending",
        input_params: { credential_id, force_full_sync },
        progress_pct: 0,
      })
      .select("job_id")
      .single();

    if (insertError || !job) {
      console.error("[run-sync] Failed to create job:", insertError);
      return new Response(
        JSON.stringify({ error: "Failed to create sync job", details: insertError }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const jobId = job.job_id;
    console.log(`[run-sync] Created job ${jobId} for client ${client_id}`);

    // ── Fire-and-forget: run sync in the background ──
    // EdgeRuntime.waitUntil keeps the isolate alive after we return
    // @ts-ignore — Deno Deploy / Supabase Edge Runtime API
    if (typeof EdgeRuntime !== "undefined" && EdgeRuntime.waitUntil) {
      // @ts-ignore
      EdgeRuntime.waitUntil(
        runSyncInBackground(jobId, client_id, credential_id, force_full_sync)
      );
    } else {
      // Fallback: just run it (will block until done, but at least works)
      runSyncInBackground(jobId, client_id, credential_id, force_full_sync);
    }

    // ── Return immediately with the job_id ──
    return new Response(
      JSON.stringify({
        success: true,
        job_id: jobId,
        message: "Sync job enqueued. Poll reg_jobs for progress.",
      }),
      {
        status: 202,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  } catch (err) {
    console.error("[run-sync] Handler error:", err);
    return new Response(
      JSON.stringify({
        error: "Internal error",
        details: err instanceof Error ? err.message : String(err),
      }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
