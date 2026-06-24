/**
 * upload-drive-source — Google Drive file intake
 *
 * POST { client_id, drive_file_id, schema_type? }
 *
 * 1. Auth + ownership check (same as upload-csv-source)
 * 2. Load Google access token from integration_tokens
 * 3. Fetch Drive file metadata, validate MIME type, check size
 * 4. Stream export/download into Supabase Storage (no full-buffer)
 * 5. Parse headers + samples from the downloaded XLSX/CSV
 * 6. INSERT client_data_sources (source_type='google_drive')
 * 7. Call match-columns
 * 8. Return same shape as upload-csv-source
 */

import {
  AuthError,
  createServiceClient,
  requireAuth,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";
import {
  driveExportOrDownload,
  driveMetadata,
  getAccessToken,
} from "../_shared/google_drive.ts";
import {
  type ColumnDef,
  type MatchResult,
  detectSeparator,
  inferType,
  parseLine,
  scoreSheetName,
} from "../_shared/sheet_intake.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

// 20 MB cap — Drive export for large Sheets can be slow and hit the 60s timeout.
const MAX_FILE_BYTES = 20 * 1024 * 1024;

// =============================================================================
// Sheet scoring — neutral patterns are Drive-specific (month names, versions)
// =============================================================================

// Month names and versioning patterns score 0 (neutral) — row count wins as tiebreaker.
const NEUTRAL_PATTERNS = [
  /^(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)/i,
  /^(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)/i,
  /rev\./i,
  /^v\d/i,
];

// =============================================================================
// Handler
// =============================================================================

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

  const requestId = crypto.randomUUID();

  try {
    // ── 1. Auth ───────────────────────────────────────────────────────────────
    const ctx = await requireAuth(req, SUPABASE_URL, SUPABASE_ANON_KEY);
    const svc = createServiceClient(SUPABASE_URL, SERVICE_ROLE_KEY);

    // ── 2. Parse body ─────────────────────────────────────────────────────────
    let body: { client_id?: string; drive_file_id?: string; schema_type?: string };
    try {
      body = await req.json();
    } catch {
      return json({ error: "Invalid JSON body" }, 400);
    }

    const { client_id: clientId, drive_file_id: driveFileId, schema_type: schemaType = "invoices" } = body;
    if (!clientId) return json({ error: "client_id is required" }, 400);
    if (!driveFileId) return json({ error: "drive_file_id is required" }, 400);

    // ── 3. Ownership check ────────────────────────────────────────────────────
    const { data: userClients } = await svc
      .from("clientes_blu")
      .select("client_id")
      .eq("external_user_id", ctx.userId);

    const ownsClient = (userClients ?? []).some(
      (r: { client_id: string }) => String(r.client_id) === String(clientId),
    );
    if (!ownsClient) return json({ error: "Unauthorized" }, 403);

    // ── 4. Get Google access token ────────────────────────────────────────────
    let accessToken: string;
    let integrationTokenId: string;
    try {
      ({ accessToken, integrationTokenId } = await getAccessToken(clientId, svc));
    } catch (e) {
      return json({ error: (e as Error).message }, 400);
    }

    // ── 5. Fetch Drive metadata + validate ────────────────────────────────────
    let metadata;
    try {
      metadata = await driveMetadata(accessToken, driveFileId);
    } catch (e) {
      return json({ error: (e as Error).message }, 400);
    }

    const { name: fileName, mimeType, modifiedTime } = metadata;

    // Size check — Drive reports quotaBytesUsed for native Sheets, size for uploaded files
    const reportedSize = metadata.size ? parseInt(metadata.size, 10) : null;
    if (reportedSize !== null && reportedSize > MAX_FILE_BYTES) {
      return json({
        error: `File too large (${Math.round(reportedSize / 1024 / 1024)} MB). Maximum is 20 MB. Please split the sheet into smaller files.`,
      }, 400);
    }

    // ── 6. Stream export/download from Drive ──────────────────────────────────
    let driveResponse: Response;
    try {
      driveResponse = await driveExportOrDownload(accessToken, driveFileId, mimeType);
    } catch (e) {
      return json({ error: (e as Error).message }, 400);
    }

    // Detect effective content type (export always produces XLSX)
    const isXlsx = mimeType === "application/vnd.google-apps.spreadsheet" ||
      mimeType === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
      mimeType === "application/vnd.ms-excel";
    const isCsv = mimeType === "text/csv";

    // Determine storage file name
    const baseName = isXlsx
      ? (fileName.endsWith(".xlsx") ? fileName : `${fileName}.xlsx`)
      : fileName;
    const storageName = `${driveFileId}-${baseName}`.replace(/[^a-zA-Z0-9._-]/g, "_");
    const storagePath = `drive_imports/${clientId}/${storageName}`;
    const storageMime = isXlsx
      ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      : "text/csv";

    // Buffer the response body (needed for both parsing and upload)
    // We do both in sequence to avoid holding two copies; parse after upload.
    const fileBuffer = await driveResponse.arrayBuffer();

    // Size check on actual body (native Sheets don't report size upfront)
    if (fileBuffer.byteLength > MAX_FILE_BYTES) {
      return json({
        error: `Exported file too large (${Math.round(fileBuffer.byteLength / 1024 / 1024)} MB). Maximum is 20 MB. Please reduce the sheet size.`,
      }, 400);
    }

    // ── 7. Parse headers + samples ────────────────────────────────────────────
    let headers: string[];
    let sampleRows: string[][];

    if (isXlsx) {
      const XLSX = await import("https://esm.sh/xlsx@0.18.5");
      const workbook = XLSX.read(new Uint8Array(fileBuffer), { type: "array", cellDates: true });

      // Score sheets by name keywords then row count (same logic as upload-csv-source)
      const scored = workbook.SheetNames.map((name: string) => {
        const ref = workbook.Sheets[name]["!ref"] ?? "A1:A1";
        const range = XLSX.utils.decode_range(ref);
        const rowCount = range.e.r - range.s.r + 1;
              return { name, score: scoreSheetName(name, NEUTRAL_PATTERNS), rowCount };
      });
      scored.sort((a: { score: number; rowCount: number }, b: { score: number; rowCount: number }) =>
        b.score - a.score || b.rowCount - a.rowCount
      );
      const sheetName = scored[0]?.name ?? workbook.SheetNames[0];

      const sheet = workbook.Sheets[sheetName];
      const data = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" }) as unknown[][];
      if (data.length === 0) return json({ error: "Empty file" }, 400);

      const searchRows = data.slice(0, 10) as unknown[][];
      const headerIdx = searchRows.reduce((bestIdx: number, row: unknown[], i: number) => {
        const count = (row as unknown[]).filter((c) => String(c ?? "").trim() !== "").length;
        const bestCount = (searchRows[bestIdx] as unknown[]).filter((c) => String(c ?? "").trim() !== "").length;
        return count > bestCount ? i : bestIdx;
      }, 0);

      headers = (data[headerIdx] as unknown[]).map((h) => String(h ?? "").trim()).filter(Boolean);
      sampleRows = (data.slice(headerIdx + 1, headerIdx + 11) as unknown[][]).map((r) =>
        (r as unknown[]).map((v) => {
          if (v instanceof Date) return v.toISOString().slice(0, 10);
          if (typeof v === "number" && Number.isInteger(v) && v > 25569 && v < 2958466) {
            return new Date((v - 25569) * 86400000).toISOString().slice(0, 10);
          }
          return String(v ?? "");
        })
      );
    } else if (isCsv) {
      const text = new TextDecoder().decode(fileBuffer);
      const lines = text.split(/\r?\n/).filter((l) => l.trim() !== "");
      if (lines.length === 0) return json({ error: "Empty CSV" }, 400);
      const sep = detectSeparator(lines[0]);
      headers = parseLine(lines[0], sep).map((h) => h.replace(/^"|"$/g, "").trim()).filter(Boolean);
      sampleRows = lines.slice(1, 11).map((l) =>
        parseLine(l, sep).map((v) => v.replace(/^"|"$/g, ""))
      );
    } else {
      return json({ error: "Unsupported MIME type" }, 400);
    }

    if (headers.length === 0) return json({ error: "No columns found in file" }, 400);

    const columns: ColumnDef[] = headers.map((name, i) => {
      const colValues = sampleRows.map((r) => r[i] ?? "");
      return {
        name,
        type: inferType(colValues),
        sample: colValues.slice(0, 3).filter((v) => v !== ""),
      };
    });

    // ── 8. Upload to Supabase Storage ─────────────────────────────────────────
    const { error: uploadErr } = await svc.storage
      .from("csv_datasets")
      .upload(storagePath, fileBuffer, { contentType: storageMime, upsert: true });

    if (uploadErr) {
      console.error(`[upload-drive-source] ${requestId} Storage upload failed:`, uploadErr);
      return json({ error: "Failed to upload file to storage" }, 500);
    }

    // ── 9. INSERT client_data_sources ─────────────────────────────────────────
    const now = new Date().toISOString();
    const { data: dataSource, error: insertErr } = await svc
      .from("client_data_sources")
      .insert({
        client_id: clientId,
        source_type: "google_drive",
        resource_type: "file",
        storage_type: "csv_file",
        storage_location: storagePath,
        source_columns: columns,
        sync_status: "columns_discovered",
        credential_id: null,
        drive_file_id: driveFileId,
        drive_modified_time: modifiedTime,
        integration_token_id: integrationTokenId,
        created_at: now,
        updated_at: now,
      })
      .select("id")
      .single();

    if (insertErr || !dataSource) {
      console.error(`[upload-drive-source] ${requestId} DB insert failed:`, insertErr);
      return json({ error: "Failed to register data source" }, 500);
    }

    const sourceId = dataSource.id as string;

    // ── 10. Call match-columns ─────────────────────────────────────────────────
    const matchRes = await fetch(`${SUPABASE_URL}/functions/v1/match-columns`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${SERVICE_ROLE_KEY}`,
        "apikey": SUPABASE_ANON_KEY,
      },
      body: JSON.stringify({ source_columns: headers, schema_type: schemaType }),
    });

    if (!matchRes.ok) {
      console.warn(`[upload-drive-source] ${requestId} match-columns returned ${matchRes.status}`);
      return json({
        source_id: sourceId,
        columns,
        file_name: baseName,
        storage_path: storagePath,
        matched: {},
        unmatched: headers,
        needs_review: [],
        confidence_scores: {},
        detected_context: null,
      });
    }

    const matchResult = await matchRes.json() as MatchResult;

    // ── 11. UPDATE client_data_sources with match result ──────────────────────
    await svc
      .from("client_data_sources")
      .update({
        auto_column_mapping: matchResult.matched,
        needs_review_columns: matchResult.needs_review,
        match_confidence: matchResult.confidence_scores,
        detected_entity_context: matchResult.detected_context ?? null,
        unmapped_columns: matchResult.unmatched,
        updated_at: new Date().toISOString(),
      })
      .eq("id", sourceId);

    console.log(
      `[upload-drive-source] ${requestId} source=${sourceId} file="${fileName}" cols=${headers.length} matched=${Object.keys(matchResult.matched).length}`,
    );

    return json({
      source_id: sourceId,
      columns,
      file_name: baseName,
      storage_path: storagePath,
      matched: matchResult.matched,
      unmatched: matchResult.unmatched,
      needs_review: matchResult.needs_review,
      confidence_scores: matchResult.confidence_scores,
      detected_context: matchResult.detected_context ?? null,
    });
  } catch (err) {
    if (err instanceof AuthError) return json({ error: err.message }, err.status);
    console.error(`[upload-drive-source] ${requestId} Error:`, err);
    return json(
      { error: "Internal error", details: err instanceof Error ? err.message : String(err) },
      500,
    );
  }
});
