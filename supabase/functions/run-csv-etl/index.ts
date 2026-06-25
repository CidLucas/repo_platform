/**
 * run-csv-etl — CSV sync orchestrator
 *
 * Mirrors run-sync-etl but for CSV sources (source_type='csv').
 *
 * 1. Auth + ownership check
 * 2. Persists confirmed column_mapping + user_column_changes to client_data_sources
 * 3. Downloads CSV from Storage, parses rows, stages them in csv_import_staging
 * 4. Creates reg_jobs record (job_type='csv_sync', status='pending')
 * 5. Executes sincronizar_csv_cliente inline via svc.rpc as a pg_cron fallback
 * 6. Returns job_id — pg_cron will still pick up the job if inline failed
 */

import {
  AuthError,
  createServiceClient,
  requireAuth,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";
import { parseCSV, scoreSheetName } from "../_shared/sheet_intake.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

interface RunCsvEtlRequest {
  client_id: string;
  source_id: string;
  column_mapping: Record<string, string>;
  // Source columns the user explicitly excluded. Stored as metadata only —
  // the ETL ignores any canonical not present in column_mapping, so exclusion
  // is implicit. This field is not used to filter staged rows.
  ignored_columns?: string[];
}

// =============================================================================
// Handler
// =============================================================================

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const requestId = crypto.randomUUID();
  const startTime = Date.now();

  try {
    // ── 1. Auth ───────────────────────────────────────────────────────────────
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);

    const contentType = req.headers.get("content-type");
    if (!contentType?.includes("application/json")) {
      return json({ error: "Content-Type must be application/json" }, 400);
    }

    let body: Partial<RunCsvEtlRequest>;
    try {
      body = await req.json() as Partial<RunCsvEtlRequest>;
    } catch {
      return json({ error: "Invalid JSON in request body" }, 400);
    }

    const { client_id, source_id, column_mapping: rawMapping, ignored_columns = [] } = body;

    if (!client_id || !source_id || !rawMapping) {
      return json({ error: "client_id, source_id and column_mapping are required" }, 400);
    }
    if (Object.keys(rawMapping).length === 0) {
      return json({ error: "column_mapping cannot be empty" }, 400);
    }

    // Frontend sends { source_col → canonical }; sincronizar_csv_cliente expects
    // { canonical → source_col }. Invert here so the DB contract is canonical-keyed.
    const column_mapping: Record<string, string> = {};
    for (const [src, can] of Object.entries(rawMapping as Record<string, string>)) {
      if (can && can !== "ignorar") column_mapping[can] = src;
    }

    const svc = createServiceClient(SUPABASE_URL, SERVICE_ROLE_KEY);

    // ── 2. Ownership check ────────────────────────────────────────────────────
    const { data: userClients } = await svc
      .from("clientes_blu")
      .select("client_id")
      .eq("external_user_id", ctx.userId);

    const ownsClient = (userClients ?? []).some(
      (r: { client_id: string }) => String(r.client_id) === String(client_id),
    );
    if (!ownsClient) {
      return json({ error: "Unauthorized: client_id does not belong to authenticated user" }, 403);
    }

    // ── 3. Fetch and validate data source ─────────────────────────────────────
    const { data: dataSource, error: dsErr } = await svc
      .from("client_data_sources")
      .select("id, storage_location, storage_type, auto_column_mapping, sync_status")
      .eq("id", source_id)
      .eq("client_id", client_id)
      .maybeSingle();

    if (dsErr || !dataSource) return json({ error: "Data source not found" }, 404);
    if (dataSource.storage_type !== "csv_file") {
      return json({ error: "Data source is not a CSV file" }, 400);
    }

    // ── 4. Duplicate job guard ────────────────────────────────────────────────
    // Scope to this specific source_id so clients with multiple sources can
    // run concurrent ETL jobs without false 409 conflicts.
    const { data: existingJob } = await svc
      .schema("analytics_v2")
      .from("reg_jobs")
      .select("job_id, status")
      .eq("client_id", client_id)
      .eq("job_type", "csv_sync")
      .contains("input_params", { source_id })
      .in("status", ["pending", "running"])
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (existingJob?.job_id) {
      return json({
        error: "A CSV sync job is already in progress",
        existing_job_id: existingJob.job_id,
        status: existingJob.status,
      }, 409);
    }

    // ── 5. Persist confirmed column_mapping ───────────────────────────────────
    const now = new Date().toISOString();
    const autoMapping = (dataSource.auto_column_mapping ?? {}) as Record<string, string>;

    // auto_column_mapping is stored as { source → canonical } (match-columns format).
    // column_mapping from the frontend is { canonical → source } (flipped for ETL).
    // Invert autoMapping before diffing so both sides use the same direction.
    const autoInverted: Record<string, string> = {};
    for (const [src, can] of Object.entries(autoMapping)) {
      autoInverted[String(can)] = src;
    }

    // Diff: track what the user changed vs the auto-suggestion
    const userChanges: Record<string, { auto: string | null; confirmed: string }> = {};
    for (const [canonical, sourceCol] of Object.entries(column_mapping)) {
      if (autoInverted[canonical] !== sourceCol) {
        userChanges[canonical] = { auto: autoInverted[canonical] ?? null, confirmed: sourceCol };
      }
    }

    // Unmapped = canonical fields auto-matched but not confirmed by user.
    // autoInverted keys are canonical names, column_mapping keys are also canonical names.
    const unmapped = Object.keys(autoInverted).filter((canonical) => !(canonical in column_mapping));

    await svc
      .from("client_data_sources")
      .update({
        column_mapping,
        sync_status: "mapping_confirmed",
        unmapped_columns: unmapped,
        ignored_columns,
        user_column_changes: Object.keys(userChanges).length > 0 ? userChanges : null,
        reviewed_at: now,
        updated_at: now,
      })
      .eq("id", source_id);

    // ── 6. Download file and parse all rows ───────────────────────────────────
    const { data: fileData, error: downloadErr } = await svc.storage
      .from("csv_datasets")
      .download(dataSource.storage_location);

    if (downloadErr || !fileData) {
      console.error(`[run-csv-etl] ${requestId} Storage download failed:`, downloadErr);
      return json({ error: "Failed to download CSV file from storage" }, 500);
    }

    const storagePath: string = dataSource.storage_location ?? "";
    const isXlsx = /\.(xlsx|xls)$/i.test(storagePath);
    let rows: Record<string, string>[];

    if (isXlsx) {
      // Parse XLSX binary using same sheet-scoring + header-detection as upload-csv-source
      const XLSX = await import("https://esm.sh/xlsx@0.18.5");
      const buffer = await fileData.arrayBuffer();
      const workbook = XLSX.read(new Uint8Array(buffer), { type: "array", cellDates: true });

      const scored = workbook.SheetNames.map((name: string) => {
        const ref = workbook.Sheets[name]["!ref"] ?? "A1:A1";
        const range = XLSX.utils.decode_range(ref);
        return { name, score: scoreSheetName(name), rowCount: range.e.r - range.s.r + 1 };
      });
      scored.sort((a: { score: number; rowCount: number }, b: { score: number; rowCount: number }) =>
        b.score - a.score || b.rowCount - a.rowCount
      );
      const sheetName: string = scored[0]?.name ?? workbook.SheetNames[0];
      const data = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { header: 1, defval: "" }) as unknown[][];

      if (data.length < 2) {
        return json({ error: "XLSX file has no data rows" }, 400);
      }

      // Find header row: row with most non-empty cells in first 10 rows
      const searchRows = data.slice(0, 10);
      const headerIdx: number = searchRows.reduce((bestIdx: number, row: unknown, i: number) => {
        const count = (row as unknown[]).filter((c) => String(c ?? "").trim() !== "").length;
        const bestCount = (searchRows[bestIdx] as unknown[]).filter((c) => String(c ?? "").trim() !== "").length;
        return count > bestCount ? i : bestIdx;
      }, 0);

      // Preserve original column indices alongside header names so that empty
      // header cells don't shift the mapping for all subsequent columns.
      const headerEntries: Array<{ name: string; col: number }> = (data[headerIdx] as unknown[])
        .map((h, col) => ({ name: String(h ?? "").trim(), col }))
        .filter((e) => e.name !== "");

      rows = (data.slice(headerIdx + 1) as unknown[][])
        .filter((r) => (r as unknown[]).some((c) => String(c ?? "").trim() !== ""))
        .map((r) => {
          const obj: Record<string, string> = {};
          for (const { name, col } of headerEntries) {
            const v = (r as unknown[])[col];
            if (v instanceof Date) {
              obj[name] = v.toISOString().slice(0, 10);
            } else if (typeof v === "number" && Number.isInteger(v) && v > 25569 && v < 2958466) {
              // Excel date serial stored as a number-formatted cell (cellDates skips these).
              // 25569 = 1970-01-01; 2958466 = 9999-12-31.
              // Formula: days since 1899-12-30 (accounts for Excel's 1900 leap-year bug).
              const ms = (v - 25569) * 86400000;
              obj[name] = new Date(ms).toISOString().slice(0, 10);
            } else {
              obj[name] = String(v ?? "");
            }
          }
          return obj;
        });
    } else {
      const text = await fileData.text();
      const parsed = parseCSV(text);
      rows = parsed.rows.filter((row) =>
        Object.values(row).some((v) => v.trim() !== "")
      );
    }

    if (rows.length === 0) {
      return json({ error: "File has no data rows" }, 400);
    }

    // ── 7. Stage rows for DB processing ──────────────────────────────────────
    const { error: stageErr } = await svc
      .from("csv_import_staging")
      .insert({
        client_id,
        source_id,
        rows,
        row_count: rows.length,
        created_at: now,
      });

    if (stageErr) {
      console.error(`[run-csv-etl] ${requestId} Staging insert failed:`, stageErr);
      return json({ error: "Failed to stage CSV rows for processing" }, 500);
    }

    // ── 8. Create sync job — pg_cron dispatches within ~1 min ─────────────────
    const { data: job, error: jobErr } = await svc
      .schema("analytics_v2")
      .from("reg_jobs")
      .insert({
        client_id,
        job_type: "csv_sync",
        status: "pending",
        input_params: { source_id },
        progress_pct: 0,
      })
      .select("job_id")
      .single();

    if (jobErr || !job) {
      console.error(`[run-csv-etl] ${requestId} Job creation failed:`, jobErr);
      return json({ error: "Failed to create sync job" }, 500);
    }

    // ── 9. Execute ETL inline (pg_cron fallback) ──────────────────────────────
    const period = new Date().toISOString().slice(0, 7);
    try {
      const { error: rpcErr } = await svc.rpc("sincronizar_csv_cliente", {
        p_job_id: job.job_id,
      });
      if (rpcErr) {
        console.error("Inline RPC failed:", rpcErr);
        return json({ success: true, rows_inserted: 0, period: period }, 200);
      }
    } catch (rpcEx) {
      console.error("Inline RPC exception:", rpcEx);
      return json({ success: true, rows_inserted: 0, period: period }, 200);
    }

    const initDuration = Date.now() - startTime;
    console.log(
      `[run-csv-etl] ${requestId} Queued job=${job.job_id} rows=${rows.length} in ${initDuration}ms`,
    );

    return json({
      success: true,
      job_id: job.job_id,
      request_id: requestId,
      row_count: rows.length,
      message: "CSV sync job executed inline. Data is being processed.",
    }, 200, {
      "X-Request-Id": requestId,
      "X-Duration-Ms": String(initDuration),
    });
  } catch (err) {
    if (err instanceof AuthError) return json({ error: err.message }, err.status);
    console.error(`[run-csv-etl] ${requestId} Handler error:`, err);
    return json(
      { error: "Internal error", details: err instanceof Error ? err.message : String(err) },
      500,
    );
  }
});
