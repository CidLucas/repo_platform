/**
 * etl-bigquery-ingest
 *
 * Drives one reg_jobs row from `pending` → `completed`. Replaces the legacy
 * run_etl_job RPC which used FDW row-by-row scans (mai/2026: was hanging
 * 4 days on 119k rows due to wrappers_fdw_stats contention + WASM throughput).
 *
 * Flow:
 *   1. Auth: accept service-role (called by analytics_v2.process_pending_jobs
 *      via pg_net) OR user JWT (manual rerun from the dashboard).
 *   2. Load job + credential + data source.
 *   3. Decrypt the service_account_json via analytics_v2.get_credential_service_account
 *      (SECURITY DEFINER helper — service role can call vault directly, this just
 *      keeps the SQL clean).
 *   4. Run paginated SELECT against BigQuery (10k rows/page).
 *   5. For each page, bulk INSERT into analytics_v2.ingest_staging.
 *   6. Call analytics_v2.apply_staging_to_facts(job_id) — unified CSV/xlsx/BQ
 *      RPC that handles md5 transacao_id, 3-tier parse_ingest_date,
 *      cascade classify, idempotent upsert into fato_transacoes.
 *   7. Advance watermark on client_data_sources.
 *   8. Mark job completed.
 *
 * Error handling:
 *   Any throw → status='failed', error_message set, retry_count++. Caller
 *   (process_pending_jobs) can re-enqueue with backoff.
 *
 * Idempotency:
 *   ingest_staging rows are keyed by (job_id, source_id, row_index). If a
 *   prior partial run inserted rows, they're cleared at the start of the run.
 *   apply_staging_to_facts uses md5(client||cred||doc||date||sku||row) →
 *   ON CONFLICT DO UPDATE so reruns are safe.
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders, json } from "../_shared/cors.ts";
import {
  requireAuth,
  AuthError,
  createUserClient,
  isSystemInvocation,
} from "../_shared/blu_auth.ts";
import {
  getGoogleAccessToken,
  queryBigQueryPaginated,
  type BqResumeCursor,
} from "../_shared/bigquery_auth.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY =
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ??
  Deno.env.get("SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

const PAGE_SIZE = 10_000;
const STAGING_CHUNK = 500;

interface JobRow {
  job_id: string;
  client_id: string;
  credential_id: number | null;
  status: string;
  input_params: { force_full_sync?: boolean; credential_id?: number };
  retry_count: number;
}

interface CredentialRow {
  id: number;
  client_id: string;
  connection_metadata: {
    project_id: string;
    dataset_id: string;
    table_name: string;
    location?: string;
  };
}

interface DataSourceRow {
  id: string;
  watermark_column: string | null;
  last_watermark_value: string | null;
}

// ── auth ─────────────────────────────────────────────────────────────────────

/**
 * Returns true when the request is authenticated with the service-role key
 * (system invocation from pg_net). Falls back to user JWT validation otherwise.
 */
async function authorize(
  req: Request,
  jobClientId: string,
): Promise<{ mode: "service" | "user"; userId?: string }> {
  // System path: cron dispatcher (sb_secret_* in vault) or any direct
  // service-role invocation. Centralised in _shared/blu_auth.ts so every
  // edge function accepts the same set of system keys.
  if (isSystemInvocation(req)) {
    return { mode: "service" };
  }

  // User path: validate JWT, check that the user owns the job's client.
  const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);
  const userClient = createUserClient(ctx.token, SUPABASE_URL, SUPABASE_ANON_KEY);
  const { data: ownership } = await userClient
    .from("clientes_blu")
    .select("client_id")
    .eq("external_user_id", ctx.userId)
    .eq("client_id", jobClientId)
    .maybeSingle();
  if (!ownership) {
    throw new AuthError("Unauthorized: job belongs to another tenant", 403);
  }
  return { mode: "user", userId: ctx.userId };
}

// ── handler ──────────────────────────────────────────────────────────────────

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const service = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  let jobId: string | undefined;

  try {
    const body = await req.json();
    jobId = body.job_id as string;
    if (!jobId) return json({ error: "job_id is required" }, 400);

    // 1. Load job (service-role read; auth check happens next).
    const { data: job, error: jobErr } = await service.schema("analytics_v2").from("reg_jobs")
      .select("job_id, client_id, credential_id, status, input_params, retry_count")
      .eq("job_id", jobId)
      .maybeSingle<JobRow>();

    if (jobErr) throw new Error(`reg_jobs lookup failed: ${jobErr.message}`);
    if (!job) return json({ error: "job not found" }, 404);
    // credential_id can live in the column or in input_params.credential_id
    // (legacy rows from process_pending_etl_jobs use the input_params form).
    const credentialId = job.credential_id ?? job.input_params?.credential_id;
    if (!job.client_id || !credentialId) {
      throw new Error("job missing client_id or credential_id");
    }

    // 2. Authorize (service-role bypass, otherwise verify tenant ownership).
    await authorize(req, job.client_id);

    if (job.status === "running") {
      // Someone else already picked it up.
      return json({ ok: true, skipped: "already running" });
    }
    if (job.status === "completed") {
      return json({ ok: true, skipped: "already completed" });
    }

    // 3. Mark running.
    await service.schema("analytics_v2").from("reg_jobs")
      .update({ status: "running", started_at: new Date().toISOString() })
      .eq("job_id", jobId);

    // 4. Load credential metadata.
    const { data: cred, error: credErr } = await service
      .from("credencial_servico_externo")
      .select("id, client_id, connection_metadata")
      .eq("id", credentialId)
      .maybeSingle<CredentialRow>();
    if (credErr) throw new Error(`credential lookup failed: ${credErr.message}`);
    if (!cred) throw new Error(`credential ${credentialId} not found`);

    const { project_id, dataset_id, table_name } =
      cred.connection_metadata ?? ({} as CredentialRow["connection_metadata"]);
    if (!project_id || !dataset_id || !table_name) {
      throw new Error("credential connection_metadata missing project/dataset/table");
    }

    // 5. Decrypt service_account_json via SECURITY DEFINER helper.
    const { data: saJson, error: saErr } = await service.rpc(
      "get_credential_service_account",
      { p_credential_id: credentialId },
    );
    if (saErr) throw new Error(`vault decrypt failed: ${saErr.message}`);
    if (!saJson) throw new Error("vault returned empty service_account_json");

    // 6. Load data source (watermark + source_id for ingest_staging).
    const { data: source, error: srcErr } = await service
      .from("client_data_sources")
      .select("id, watermark_column, last_watermark_value")
      .eq("credential_id", credentialId)
      .maybeSingle<DataSourceRow>();
    if (srcErr) throw new Error(`data source lookup failed: ${srcErr.message}`);
    if (!source) throw new Error("client_data_sources row missing for credential");

    // 7. Build SELECT. Watermark column is text in BQ (createdat_*), but we
    // compare lexicographically only when the format is ISO 8601 — caller of
    // create_bigquery_foreign_table sets the column when it knows the schema.
    const forceFull = job.input_params?.force_full_sync === true;
    const fqTable = `\`${project_id}\`.\`${dataset_id}\`.\`${table_name}\``;
    let sql = `SELECT * FROM ${fqTable}`;
    if (
      !forceFull &&
      source.watermark_column &&
      source.last_watermark_value
    ) {
      // Cast both sides to STRING for safety; BQ infers the comparison correctly
      // when the column is already STRING/TIMESTAMP.
      const col = `\`${source.watermark_column}\``;
      const wm = source.last_watermark_value.replace(/'/g, "\\'");
      sql += ` WHERE CAST(${col} AS STRING) > '${wm}'`;
    }
    if (source.watermark_column) {
      sql += ` ORDER BY \`${source.watermark_column}\``;
    }

    console.log(`[etl-bigquery-ingest] job=${jobId} sql=${sql}`);

    // 8. Idempotent reruns: only wipe staging on a FRESH start. When resuming
    // from a saved BqResumeCursor we keep previously inserted rows.
    //
    // Recovery escape hatch: input_params.skip_ingestion=true skips BigQuery
    // entirely and goes straight to the apply step. Used when a previous run
    // already wrote all staging rows but the apply RPC failed — re-running
    // ingestion would just thrash BigQuery and the staging table for nothing.
    const skipIngestion = job.input_params?.skip_ingestion === true;
    const resumeCursor: BqResumeCursor | undefined =
      job.input_params?.bq_resume_cursor as BqResumeCursor | undefined;
    const priorRows: number =
      typeof job.input_params?.rows_so_far === "number"
        ? job.input_params.rows_so_far
        : 0;

    if (!resumeCursor && !skipIngestion) {
      await service
        .schema("analytics_v2")
        .from("ingest_staging")
        .delete()
        .eq("job_id", jobId);
    }

    let totalRows = priorRows;
    let maxWatermark = source.last_watermark_value ?? "";

    if (!skipIngestion) {
      // 9. Mint a fresh OAuth token (no caching — see _shared/bigquery_auth.ts).
      const accessToken = await getGoogleAccessToken(saJson);

      // 10. Stream BigQuery → staging, with a per-invocation time budget.
      //
      // The hosted edge runtime kills the worker around ~60s of wall time
      // (WORKER_RESOURCE_LIMIT — observed in prod on this project's free tier).
      // We bail cleanly well before that, persist a resume cursor onto the
      // job, mark it back to 'pending' and return 202. The next dispatcher
      // tick (analytics_v2.process_pending_jobs) picks it up and continues
      // from the saved pageToken.
      const INVOKE_BUDGET_MS = 25_000;
      const invokeStart = Date.now();

      const runResult = await queryBigQueryPaginated(
        accessToken,
        project_id,
      sql,
      async ({ rows, pageIndex, totalRows: bqTotal }) => {
        // Update watermark candidate from this page.
        if (source.watermark_column) {
          for (const row of rows) {
            const v = row[source.watermark_column!] as string | null;
            if (v && v > maxWatermark) maxWatermark = v;
          }
        }

        // Bulk INSERT into ingest_staging, chunked.
        for (let i = 0; i < rows.length; i += STAGING_CHUNK) {
          const chunk = rows.slice(i, i + STAGING_CHUNK);
          const payload = chunk.map((raw, k) => ({
            job_id: jobId,
            client_id: job.client_id,
            source_id: source.id,
            row_index: totalRows + i + k,
            raw_data: raw,
          }));
          const { error: insErr } = await service
            .schema("analytics_v2")
            .from("ingest_staging")
            .insert(payload);
          if (insErr) {
            throw new Error(
              `ingest_staging insert failed at page ${pageIndex} chunk ${i}: ${insErr.message}`,
            );
          }
        }

        totalRows += rows.length;

        // Progress feedback (best-effort, swallow errors).
        const pct =
          bqTotal > 0
            ? Math.min(95, Math.floor((totalRows / bqTotal) * 95))
            : null;
        await service.schema("analytics_v2").from("reg_jobs")
          .update({
            progress_pct: pct ?? 0,
            rows_inserted: totalRows,
          })
          .eq("job_id", jobId);

        // Bail out before the runtime kills us. The shared paginator will
        // return a BqResumeCursor pointing at the next unread page.
        if (Date.now() - invokeStart > INVOKE_BUDGET_MS) {
          return { stop: true };
        }
      },
      { pageSize: PAGE_SIZE, resumeFrom: resumeCursor },
    );

    // 10b. If we bailed mid-query, persist the cursor and yield back to the
    // dispatcher. The job goes back to 'pending' so the next cron tick picks
    // it up — no retry_count bump (this is cooperative chunking, not a failure).
    if (runResult.resume) {
      const newParams = {
        ...(job.input_params ?? {}),
        bq_resume_cursor: runResult.resume,
        rows_so_far: totalRows,
      };
      await service.schema("analytics_v2").from("reg_jobs")
        .update({
          status: "pending",
          input_params: newParams,
          rows_inserted: totalRows,
        })
        .eq("job_id", jobId);

      console.log(
        `[etl-bigquery-ingest] job=${jobId} yielding after ${totalRows} rows, ` +
          `resume pageToken=${runResult.resume.pageToken.slice(0, 20)}…`,
      );

      // G2: Daisy-chain — re-invoke immediately so the next chunk starts without
      // waiting for the next cron tick (~1 min). Cursor is already persisted above.
      // Fire-and-forget: if this fails, cron picks up the pending job as a safety net.
      // max_chain_attempts guard is in input_params to prevent infinite loops on stalled jobs.
      const chainAttempts = (job.input_params?.chain_attempts ?? 0) as number;
      const MAX_CHAIN_ATTEMPTS = 50;
      if (chainAttempts < MAX_CHAIN_ATTEMPTS) {
        // Bump chain_attempts counter (cursor + rows_so_far already saved above)
        await service.schema("analytics_v2").from("reg_jobs")
          .update({
            input_params: {
              ...(job.input_params ?? {}),
              bq_resume_cursor: runResult.resume,
              rows_so_far: totalRows,
              chain_attempts: chainAttempts + 1,
            },
          })
          .eq("job_id", jobId);

        const invokeKey = Deno.env.get("BLU_SYSTEM_INVOKE_KEY");
        const baseUrl = Deno.env.get("SUPABASE_URL");
        if (invokeKey && baseUrl) {
          fetch(`${baseUrl}/functions/v1/etl-bigquery-ingest`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${invokeKey}`,
            },
            body: JSON.stringify({ job_id: jobId }),
          }).catch((e) =>
            console.warn(`[etl-bigquery-ingest] daisy-chain failed (cron will retry): ${e}`)
          );
        } else {
          console.warn("[etl-bigquery-ingest] daisy-chain skipped: BLU_SYSTEM_INVOKE_KEY or SUPABASE_URL not set");
        }
      } else {
        console.warn(`[etl-bigquery-ingest] job=${jobId} reached max_chain_attempts=${MAX_CHAIN_ATTEMPTS}, letting cron pick up`);
      }

      return json({
        ok: true,
        job_id: jobId,
        rows: totalRows,
        partial: true,
        resume: true,
      }, 202);
    }

    console.log(
      `[etl-bigquery-ingest] job=${jobId} fetched ${totalRows} rows, applying to facts`,
    );

    // 10c. Query exhausted → clear the resume cursor before moving on.
    if (resumeCursor) {
      const cleaned = { ...(job.input_params ?? {}) };
      delete cleaned.bq_resume_cursor;
      delete cleaned.rows_so_far;
      await service.schema("analytics_v2").from("reg_jobs")
        .update({ input_params: cleaned })
        .eq("job_id", jobId);
    }
    } // end if (!skipIngestion)

    if (skipIngestion) {
      // For the apply path we need a totalRows that reflects what's already
      // in staging — read it back rather than trusting input_params.
      const { count: stagingCount } = await service
        .schema("analytics_v2")
        .from("ingest_staging")
        .select("*", { count: "exact", head: true })
        .eq("job_id", jobId);
      totalRows = stagingCount ?? 0;
      console.log(
        `[etl-bigquery-ingest] job=${jobId} skip_ingestion=true, ${totalRows} staging rows ready to apply`,
      );
    }

    // 11. Apply staging → fato_transacoes (unified RPC in analytics_v2).
    //
    // The SQL function reads source_id from reg_jobs.input_params, so we
    // backfill it here in case the enqueuer didn't set it (e.g. jobs created
    // via the older onboarding path that only knew the credential_id).
    if (!job.input_params || job.input_params.source_id !== source.id) {
      const patched = { ...(job.input_params ?? {}), source_id: source.id };
      await service.schema("analytics_v2").from("reg_jobs")
        .update({ input_params: patched })
        .eq("job_id", jobId);
    }

    const { error: applyErr } = await service
      .schema("analytics_v2")
      .rpc("apply_staging_to_facts", { p_job_id: jobId });
    if (applyErr) throw new Error(`apply_staging_to_facts failed: ${applyErr.message}`);

    // 12. Advance watermark on data source.
    if (source.watermark_column && maxWatermark) {
      await service
        .from("client_data_sources")
        .update({
          last_watermark_value: maxWatermark,
          last_synced_at: new Date().toISOString(),
          sync_status: "synced",
        })
        .eq("id", source.id);
    } else {
      await service
        .from("client_data_sources")
        .update({
          last_synced_at: new Date().toISOString(),
          sync_status: "synced",
        })
        .eq("id", source.id);
    }

    // 13. Mark job completed.
    await service.schema("analytics_v2").from("reg_jobs")
      .update({
        status: "completed",
        completed_at: new Date().toISOString(),
        rows_inserted: totalRows,
        progress_pct: 100,
      })
      .eq("job_id", jobId);

    return json({ ok: true, job_id: jobId, rows: totalRows });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("[etl-bigquery-ingest] failed:", message);

    if (jobId) {
      await service.schema("analytics_v2").from("reg_jobs")
        .update({
          status: "failed",
          error_message: message.slice(0, 2000),
          completed_at: new Date().toISOString(),
        })
        .eq("job_id", jobId);
      // Bump retry_count separately (Supabase JS has no atomic increment).
      const { data: cur } = await service.schema("analytics_v2").from("reg_jobs")
        .select("retry_count")
        .eq("job_id", jobId)
        .maybeSingle();
      await service.schema("analytics_v2").from("reg_jobs")
        .update({ retry_count: (cur?.retry_count ?? 0) + 1 })
        .eq("job_id", jobId);
    }

    if (err instanceof AuthError) {
      return json({ error: err.message }, err.status);
    }
    return json({ error: message }, 500);
  }
});
