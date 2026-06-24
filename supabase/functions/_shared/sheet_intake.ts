/**
 * sheet_intake — Shared helpers for CSV/XLSX/Sheets ingestion edge functions.
 *
 * Consolidates logic that was duplicated across:
 *   - run-csv-etl
 *   - upload-csv-source
 *   - upload-drive-source
 *
 * Exports:
 *   - TRANSACTION_SHEET_KEYWORDS   (canonical list, used for sheet/file scoring)
 *   - scoreSheetName               (1 if name matches a transaction keyword, 0 otherwise)
 *   - inferColumnType              (best-effort type from a column's sample values)
 *   - parseLine                    (single-line CSV parser with quoted-field support)
 *   - detectSeparator              (';' or ',' from a sample line)
 *   - parseCSV                     (full CSV -> { headers, rows, headerRowIndex })
 *   - ColumnDef, MatchResult, InferredType, ParsedCSV (shared types)
 */

const TRANSACTION_SHEET_KEYWORDS_LIST = [
  "lancamentos", "lancamento", "faturamento", "fatura", "faturas",
  "transacoes", "transacao", "entradas", "saidas", "movimentacao",
  "movimentacoes", "despesas", "receitas", "vendas", "compras",
  "financeiro", "pagamentos", "pagamento", "notas", "registros",
] as const;

export const TRANSACTION_SHEET_KEYWORDS: ReadonlySet<string> = new Set(
  TRANSACTION_SHEET_KEYWORDS_LIST,
);

/** Lowercase + strip diacritics for accent-insensitive keyword matching. */
function _normalizeSheetName(name: string): string {
  return name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/**
 * Score a sheet/file name by how likely it is to be a transactions sheet.
 *
 * Returns 1 if the normalized name contains a known transaction keyword;
 * returns 0 otherwise. If `neutralPatterns` is provided, any name matching
 * those patterns also scores 0 (e.g. month names, "rev.", "v1").
 */
export function scoreSheetName(
  name: string,
  neutralPatterns?: readonly RegExp[],
): number {
  const n = _normalizeSheetName(name);
  if (TRANSACTION_SHEET_KEYWORDS_LIST.some((kw) => n.includes(kw))) return 1;
  if (neutralPatterns?.some((p) => p.test(name))) return 0;
  return 0;
}

export type InferredType = "integer" | "numeric" | "date" | "text";

/** Best-effort type inference for a single column from a sample of its values. */
export function inferColumnType(
  rows: ReadonlyArray<Readonly<Record<string, string>>>,
  columnName: string,
): InferredType {
  const values = rows.map((r) => r[columnName] ?? "");
  return inferType(values);
}

/**
 * Infer the type of a homogeneous list of string values.
 * Exposed for callers that already have a column-shaped array.
 */
export function inferType(values: readonly string[]): InferredType {
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

/** Parse a single CSV line, handling quoted fields and `""` escape. */
export function parseLine(line: string, sep: string): string[] {
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

/** Detect the most likely separator (';' or ',') from a sample line. */
export function detectSeparator(sampleLine: string): ";" | "," {
  return (sampleLine.match(/;/g) ?? []).length >
    (sampleLine.match(/,/g) ?? []).length
    ? ";"
    : ",";
}

export interface ColumnDef {
  name: string;
  type: InferredType;
  sample: string[];
}

export interface MatchResult {
  matched: Record<string, string>;
  unmatched: string[];
  needs_review: Array<{
    source: string;
    candidates: Array<{ canonical: string; confidence: number }>;
  }>;
  confidence_scores: Record<string, number>;
  detected_context?: string;
}

export interface ParsedCSV {
  headers: string[];
  /** Each row is a record mapping header -> cell value. */
  rows: Record<string, string>[];
  /** 0-based line index of the header row (post-`split(/\r?\n/)`). */
  headerRowIndex: number;
}

export interface ParseCSVOptions {
  /**
   * If set, return at most this many data rows after the header row.
   * Used by upload-csv-source to preview the first ~10 rows.
   * Omit (or undefined) to return all rows.
   */
  maxSampleRows?: number;
}

/**
 * Parse full CSV text into headers + rows.
 *
 * - Detects separator (';' wins ties over ',').
 * - Picks the header row as the row with the most non-empty cells within the
 *   first 10 lines (mirrors upload-csv-source behaviour).
 * - Strips surrounding quotes from headers and cell values.
 * - Drops empty header columns.
 */
export function parseCSV(text: string, opts?: ParseCSVOptions): ParsedCSV {
  const lines = text.split(/\r?\n/).filter((l) => l.trim() !== "");
  if (lines.length === 0) throw new Error("Empty CSV file");

  const longestInHead = lines.slice(0, 10).reduce(
    (best, l) => (l.length > best.length ? l : best),
    lines[0],
  );
  const sep = detectSeparator(longestInHead);

  const searchLines = lines.slice(0, 10);
  const headerIdx = searchLines.reduce((bestIdx, line, i) => {
    const count = parseLine(line, sep).filter(
      (c) => c.replace(/^"|"$/g, "").trim() !== "",
    ).length;
    const bestCount = parseLine(searchLines[bestIdx], sep).filter(
      (c) => c.replace(/^"|"$/g, "").trim() !== "",
    ).length;
    return count > bestCount ? i : bestIdx;
  }, 0);

  const headers = parseLine(lines[headerIdx], sep)
    .map((h) => h.replace(/^"|"$/g, "").trim())
    .filter(Boolean);

  const dataLines = lines.slice(
    headerIdx + 1,
    opts?.maxSampleRows !== undefined
      ? headerIdx + 1 + opts.maxSampleRows
      : undefined,
  );

  const rows: Record<string, string>[] = dataLines.map((l) => {
    const values = parseLine(l, sep).map((v) => v.replace(/^"|"$/g, ""));
    const row: Record<string, string> = {};
    headers.forEach((h, i) => {
      row[h] = values[i] ?? "";
    });
    return row;
  });

  return { headers, rows, headerRowIndex: headerIdx };
}
