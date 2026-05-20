/**
 * upload-csv-source — CSV/XLSX file upload and schema matching
 *
 * 1. Parses file headers and infers column types from sample rows
 * 2. Uploads raw file to Supabase Storage (csv_uploads/{client_id}/{uuid}-{filename})
 * 3. INSERTs client_data_sources (source_type='csv', sync_status='columns_discovered')
 * 4. Calls match-columns edge function with extracted headers
 * 5. UPDATEs client_data_sources with auto_column_mapping, needs_review_columns,
 *    match_confidence, detected_entity_context, unmapped_columns
 * 6. Returns { source_id, columns, matched, unmatched, needs_review, confidence_scores, detected_context }
 */

import {
  AuthError,
  createServiceClient,
  requireAuth,
} from "../_shared/blu_auth.ts";
import { corsHeaders, json } from "../_shared/cors.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;

// =============================================================================
// Sheet selection helpers
// =============================================================================

const TRANSACTION_SHEET_KEYWORDS = [
  "lancamentos", "lancamento", "faturamento", "fatura", "faturas",
  "transacoes", "transacao", "entradas", "saidas", "movimentacao",
  "movimentacoes", "despesas", "receitas", "vendas", "compras",
  "financeiro", "pagamentos", "pagamento", "notas", "registros",
];

function scoreSheetName(name: string): number {
  const n = name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  return TRANSACTION_SHEET_KEYWORDS.some((kw) => n.includes(kw)) ? 1 : 0;
}

// =============================================================================
// Types
// =============================================================================

interface ColumnDef {
  name: string;
  type: "integer" | "numeric" | "date" | "text";
  sample: string[];
}

interface MatchResult {
  matched: Record<string, string>;
  unmatched: string[];
  needs_review: Array<{ source: string; candidates: Array<{ canonical: string; confidence: number }> }>;
  confidence_scores: Record<string, number>;
  detected_context?: string;
}

// =============================================================================
// CSV Parsing
// =============================================================================

function inferType(values: string[]): "integer" | "numeric" | "date" | "text" {
  const nonEmpty = values.filter((v) => v !== "");
  if (nonEmpty.length === 0) return "text";
  if (nonEmpty.every((v) => /^\d+$/.test(v.trim()))) return "integer";
  if (nonEmpty.every((v) => /^[\d.,]+$/.test(v.trim().replace(",", ".")))) return "numeric";
  if (
    nonEmpty.every((v) =>
      /^\d{4}-\d{2}-\d{2}/.test(v.trim()) ||
      /^\d{2}\/\d{2}\/\d{4}/.test(v.trim()) ||
      /^\d{2}-\d{2}-\d{4}/.test(v.trim())
    )
  ) return "date";
  return "text";
}

function parseLine(line: string, sep: string): string[] {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') { current += '"'; i++; }
      else inQuotes = !inQuotes;
    } else if (ch === sep && !inQuotes) {
      result.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  result.push(current.trim());
  return result;
}

function parseCSV(text: string): { headers: string[]; sampleRows: string[][] } {
  const lines = text.split(/\r?\n/).filter((l) => l.trim() !== "");
  if (lines.length === 0) throw new Error("Empty CSV file");

  // Detect separator using the line with the most delimiters
  const candidateLine = lines.slice(0, 10).reduce((best, l) =>
    l.length > best.length ? l : best, lines[0]);
  const sep = (candidateLine.match(/;/g) ?? []).length > (candidateLine.match(/,/g) ?? []).length ? ";" : ",";

  // Find the row with the most non-empty cells in the first 10 lines
  const searchLines = lines.slice(0, 10);
  const headerIdx = searchLines.reduce((bestIdx, line, i) => {
    const count = parseLine(line, sep).filter((c) => c.replace(/^"|"$/g, "").trim() !== "").length;
    const bestCount = parseLine(searchLines[bestIdx], sep).filter((c) => c.replace(/^"|"$/g, "").trim() !== "").length;
    return count > bestCount ? i : bestIdx;
  }, 0);

  const headers = parseLine(lines[headerIdx], sep).map((h) => h.replace(/^"|"$/g, "").trim()).filter(Boolean);
  const sampleRows = lines.slice(headerIdx + 1, headerIdx + 11).map((l) => parseLine(l, sep).map((v) => v.replace(/^"|"$/g, "")));

  return { headers, sampleRows };
}

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

    // ── 2. Parse multipart form ───────────────────────────────────────────────
    const contentType = req.headers.get("content-type") ?? "";
    if (!contentType.includes("multipart/form-data")) {
      return json({ error: "Content-Type must be multipart/form-data" }, 400);
    }

    const formData = await req.formData();
    const file = formData.get("file") as File | null;
    const clientId = formData.get("client_id") as string | null;
    const schemaType = (formData.get("schema_type") as string | null) ?? "invoices";
    const requestedSheet = (formData.get("sheet_name") as string | null) ?? "";

    if (!file) return json({ error: "file is required" }, 400);
    if (!clientId) return json({ error: "client_id is required" }, 400);

    // ── 3. Ownership check ────────────────────────────────────────────────────
    const { data: userClients } = await svc
      .from("clientes_blu")
      .select("client_id")
      .eq("external_user_id", ctx.userId);

    const ownsClient = (userClients ?? []).some(
      (r: { client_id: string }) => String(r.client_id) === String(clientId),
    );
    if (!ownsClient) return json({ error: "Unauthorized" }, 403);

    // ── 4. Validate file type ─────────────────────────────────────────────────
    const fileName = file.name;
    const isXlsx = fileName.endsWith(".xlsx") || fileName.endsWith(".xls");
    const isCsv = fileName.endsWith(".csv") || fileName.endsWith(".tsv");
    if (!isXlsx && !isCsv) {
      return json({ error: "Only CSV and XLSX files are supported" }, 400);
    }

    // ── 5. Parse headers and infer types ──────────────────────────────────────
    const fileBuffer = await file.arrayBuffer();
    let headers: string[];
    let sampleRows: string[][];

    if (isXlsx) {
      const XLSX = await import("https://esm.sh/xlsx@0.18.5");
      const workbook = XLSX.read(new Uint8Array(fileBuffer), { type: "array", cellDates: true });

      // Use the sheet name from the client if provided; otherwise score each sheet
      // by name keywords (transaction-like names win) then row count as tiebreaker.
      let sheetName = requestedSheet && workbook.SheetNames.includes(requestedSheet)
        ? requestedSheet
        : (() => {
            const scored = workbook.SheetNames.map((name) => {
              const ref = workbook.Sheets[name]["!ref"] ?? "A1:A1";
              const range = XLSX.utils.decode_range(ref);
              const rowCount = range.e.r - range.s.r + 1;
              return { name, score: scoreSheetName(name), rowCount };
            });
            scored.sort((a, b) => b.score - a.score || b.rowCount - a.rowCount);
            return scored[0]?.name ?? workbook.SheetNames[0];
          })();

      const sheet = workbook.Sheets[sheetName];
      const data = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: "" }) as unknown[][];
      if (data.length === 0) return json({ error: "Empty file" }, 400);
      // Find the row with the most non-empty cells in the first 10 rows — that's the header
      const searchRows = data.slice(0, 10) as unknown[][];
      const headerIdx = searchRows.reduce((bestIdx, row, i) => {
        const count = (row as unknown[]).filter((c) => String(c ?? "").trim() !== "").length;
        const bestCount = (searchRows[bestIdx] as unknown[]).filter((c) => String(c ?? "").trim() !== "").length;
        return count > bestCount ? i : bestIdx;
      }, 0);
      headers = (data[headerIdx] as unknown[]).map((h) => String(h ?? "").trim()).filter(Boolean);
      sampleRows = (data.slice(headerIdx + 1, headerIdx + 11) as unknown[][]).map((r) =>
        (r as unknown[]).map((v) => {
          if (v instanceof Date) return v.toISOString().slice(0, 10);
          // Excel number-formatted date cells (cellDates skips them): serial → ISO string.
          // 25569 = 1970-01-01; same range guard as run-csv-etl.
          if (typeof v === "number" && Number.isInteger(v) && v > 25569 && v < 2958466) {
            return new Date((v - 25569) * 86400000).toISOString().slice(0, 10);
          }
          return String(v ?? "");
        })
      );
    } else {
      const text = new TextDecoder().decode(fileBuffer);
      const parsed = parseCSV(text);
      headers = parsed.headers;
      sampleRows = parsed.sampleRows;
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

    // ── 6. Upload file to Supabase Storage ────────────────────────────────────
    const fileId = crypto.randomUUID();
    const storagePath = `csv_uploads/${clientId}/${fileId}-${fileName}`;
    const mimeType = isXlsx
      ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      : "text/csv";

    const { error: uploadErr } = await svc.storage
      .from("csv_datasets")
      .upload(storagePath, fileBuffer, { contentType: mimeType, upsert: false });

    if (uploadErr) {
      console.error(`[upload-csv-source] ${requestId} Storage upload failed:`, uploadErr);
      return json({ error: "Failed to upload file to storage" }, 500);
    }

    // ── 7. INSERT client_data_sources ─────────────────────────────────────────
    const now = new Date().toISOString();
    const { data: dataSource, error: insertErr } = await svc
      .from("client_data_sources")
      .insert({
        client_id: clientId,
        source_type: "csv",
        resource_type: "file",
        storage_type: "csv_file",
        storage_location: storagePath,
        source_columns: columns,
        sync_status: "columns_discovered",
        credential_id: null,
        created_at: now,
        updated_at: now,
      })
      .select("id")
      .single();

    if (insertErr || !dataSource) {
      console.error(`[upload-csv-source] ${requestId} DB insert failed:`, insertErr);
      return json({ error: "Failed to register data source" }, 500);
    }

    const sourceId = dataSource.id as string;

    // ── 8. Call match-columns (same function used for BigQuery) ───────────────
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
      console.warn(`[upload-csv-source] ${requestId} match-columns returned ${matchRes.status}`);
      return json({
        source_id: sourceId,
        columns,
        file_name: fileName,
        storage_path: storagePath,
        matched: {},
        unmatched: headers,
        needs_review: [],
        confidence_scores: {},
        detected_context: null,
      });
    }

    const matchResult = await matchRes.json() as MatchResult;

    // ── 9. UPDATE client_data_sources with full match result ──────────────────
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
      `[upload-csv-source] ${requestId} source=${sourceId} cols=${headers.length} matched=${Object.keys(matchResult.matched).length}`,
    );

    return json({
      source_id: sourceId,
      columns,
      file_name: fileName,
      storage_path: storagePath,
      matched: matchResult.matched,
      unmatched: matchResult.unmatched,
      needs_review: matchResult.needs_review,
      confidence_scores: matchResult.confidence_scores,
      detected_context: matchResult.detected_context ?? null,
    });
  } catch (err) {
    if (err instanceof AuthError) return json({ error: err.message }, err.status);
    console.error(`[upload-csv-source] ${requestId} Error:`, err);
    return json(
      { error: "Internal error", details: err instanceof Error ? err.message : String(err) },
      500,
    );
  }
});
