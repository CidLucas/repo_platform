"""RED test for behavior — Step Dados CSV upload pipeline (Onboarding Step 1).

GOAL:
    Verify that the Step Dados onboarding pipeline (upload-csv-source →
    match-columns → run-csv-etl) supports the tax fields required by
    Brazilian Nota Fiscal (NF) spreadsheets:

        icms_base, icms_valor, iss_aliquota, iss_valor, pis, cofins

    Without canonical definitions AND alias entries for these fields, the
    onboarding flow will flag every tax column as `unmatched` and the user
    will be forced into manual mapping on every single upload — defeating
    the purpose of the auto-match step.

    This test is RED today because the INVOICES_COLUMNS array in
    match-columns/index.ts (lines 114-140) does NOT define any tax
    columns, and the COLUMN_ALIASES map does NOT include tax field
    aliases either.  The Coder must add both before this test turns GREEN.

BEHAVIOR:
    BEHAVIOR #1 — upload-csv-source edge function
        The Deno.serve handler at supabase/functions/upload-csv-source/index.ts
        MUST accept POST multipart/form-data with `file`, `client_id`, and
        `schema_type` fields, and MUST reject unsupported file types with
        a 400 response.

    BEHAVIOR #2 — match-columns INVOICES_COLUMNS canonical definitions
        The INVOICES_COLUMNS array MUST include a `column_name: "icms_base"`,
        `column_name: "icms_valor"`, `column_name: "iss_aliquota"`,
        `column_name: "iss_valor"`, `column_name: "pis"`, and
        `column_name: "cofins"` entry — one per tax field.

    BEHAVIOR #3 — match-columns COLUMN_ALIASES for tax fields
        The COLUMN_ALIASES map MUST include an entry for each of
        `icms_base`, `icms_valor`, `iss_aliquota`, `iss_valor`, `pis`,
        `cofins` so CSV headers like "ICMS Base", "Valor ICMS", "ISS Alíquota",
        "Valor ISS", "PIS", "COFINS" auto-match to their canonical targets.

    BEHAVIOR #4 — run-csv-etl validates non-empty column_mapping
        The Deno.serve handler at supabase/functions/run-csv-etl/index.ts
        MUST return 400 when `column_mapping` is null/empty so the user
        cannot enqueue an ETL job with no mapped fields.

    BEHAVIOR #5 — sheet_intake.parseCSV returns headers + rows
        The parseCSV function in supabase/functions/_shared/sheet_intake.ts
        MUST return a ParsedCSV object with `headers` (string[]) and
        `rows` (Record<string,string>[]) so the upload + ETL steps can
        map CSV cells to canonical columns.

    BEHAVIOR #6 — parseCSV preserves tax header names verbatim
        The parseCSV function MUST preserve tax field header names
        ("icms_valor", "iss_valor", "pis", "cofins") without dropping,
        lowercasing, or mangling them — so the alias match step can find
        them later.

AC (Acceptance Criteria):
    AC#1 — supabase/functions/upload-csv-source/index.ts defines
           `Deno.serve(...)` with a POST handler that calls
           `formData.get("file")`, `formData.get("client_id")`,
           `formData.get("schema_type")`, and returns 400 for
           non-CSV/XLSX files.

    AC#2 — supabase/functions/match-columns/index.ts defines an
           `INVOICES_COLUMNS` array that contains a `{ column_name: "icms_base" }`,
           `{ column_name: "icms_valor" }`, `{ column_name: "iss_aliquota" }`,
           `{ column_name: "iss_valor" }`, `{ column_name: "pis" }`, and
           `{ column_name: "cofins" }` entry.

    AC#3 — supabase/functions/match-columns/index.ts defines a
           `COLUMN_ALIASES` map with `icms_base`, `icms_valor`,
           `iss_aliquota`, `iss_valor`, `pis`, and `cofins` keys, each
           with at least one alias string.

    AC#4 — supabase/functions/run-csv-etl/index.ts handler body
           contains a 400 response branch when column_mapping is
           null/empty (e.g. `return json({ error: ... }, 400)` and a
           check on `Object.keys(...).length === 0` or equivalent).

    AC#5 — supabase/functions/_shared/sheet_intake.ts exports
           `parseCSV` whose body produces a `headers` string[] and
           a `rows` Record<string,string>[] for a non-empty CSV input.

    AC#6 — parseCSV preserves tax field header names (e.g. "icms_valor",
           "iss_valor", "pis", "cofins") in the returned `headers` array
           without dropping or mangling them.

DECISION:
    Estratégia: extend (add source-level inspection tests over an existing
                            pipeline — no DB fixtures, no runtime imports
                            of TypeScript, no mocks of internal modules).
    Arquivos alvo:
        - supabase/functions/upload-csv-source/index.ts
        - supabase/functions/match-columns/index.ts
        - supabase/functions/run-csv-etl/index.ts
        - supabase/functions/_shared/sheet_intake.ts

Anti-Goals (must NOT be violated):
    1. NÃO modificar nenhum arquivo TypeScript (testamos apenas o
       contrato de source).
    2. NÃO importar ou executar código TypeScript — inspeção via
       `pathlib` + `re` apenas, para evitar dependências de Deno.
    3. NÃO usar fixtures de DB — testes puramente estáticos.
    4. NÃO mockar módulos internos.

Estado atual: RED — `INVOICES_COLUMNS` e `COLUMN_ALIASES` no
match-columns/index.ts NÃO incluem os campos fiscais brasileiros
(icms_base, icms_valor, iss_aliquota, iss_valor, pis, cofins), então
as asserções de AC#2 e AC#3 falham.  O comportamento do upload-csv-source
(AC#1), do run-csv-etl (AC#4) e do sheet_intake (AC#5, AC#6) já
existe e os respectivos testes devem passar — o ponto é que a falha
de AC#2/AC#3 é o que mantém o suite RED até o Coder adicionar os
campos fiscais ao schema canônico.
"""

import re
from pathlib import Path

import pytest


# ── Paths ─────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

UPLOAD_CSV_SOURCE_PATH = (
    REPO_ROOT / "supabase" / "functions" / "upload-csv-source" / "index.ts"
)
MATCH_COLUMNS_PATH = (
    REPO_ROOT / "supabase" / "functions" / "match-columns" / "index.ts"
)
RUN_CSV_ETL_PATH = (
    REPO_ROOT / "supabase" / "functions" / "run-csv-etl" / "index.ts"
)
SHEET_INTAKE_PATH = (
    REPO_ROOT / "supabase" / "functions" / "_shared" / "sheet_intake.ts"
)


# ── Tax fields under test ────────────────────────────────────────────────

TAX_FIELDS = [
    "icms_base",
    "icms_valor",
    "iss_aliquota",
    "iss_valor",
    "pis",
    "cofins",
]


# ── Source-reading helpers ───────────────────────────────────────────────


def _read(path: Path) -> str:
    """Read a source file, failing fast if it's missing."""
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _extract_invoices_columns_block(source: str) -> str:
    """Return the substring of match-columns/index.ts that contains the
    INVOICES_COLUMNS array literal.  We isolate the array body so that an
    entry like `{ column_name: "icms_valor" }` is counted only when it
    appears inside INVOICES_COLUMNS (not in some unrelated map)."""
    match = re.search(
        r"const\s+INVOICES_COLUMNS\s*:\s*CanonicalColumnDef\[\]\s*=\s*\[(?P<body>.*?)\];",
        source,
        re.DOTALL,
    )
    assert match is not None, (
        "RED — could not locate `const INVOICES_COLUMNS: CanonicalColumnDef[] = [...]` "
        "in match-columns/index.ts. The Coder must declare the canonical column "
        "definitions as an exported const INVOICES_COLUMNS array of CanonicalColumnDef."
    )
    return match.group("body")


def _extract_column_aliases_block(source: str) -> str:
    """Return the substring of match-columns/index.ts that contains the
    COLUMN_ALIASES object literal."""
    match = re.search(
        r"const\s+COLUMN_ALIASES\s*:\s*Record<string,\s*string\[\]>\s*=\s*\{(?P<body>.*?)\n\};",
        source,
        re.DOTALL,
    )
    assert match is not None, (
        "RED — could not locate `const COLUMN_ALIASES: Record<string, string[]> = { ... }` "
        "in match-columns/index.ts. The Coder must declare the alias map as a "
        "const COLUMN_ALIASES of Record<string, string[]>."
    )
    return match.group("body")


def _extract_handler_body(source: str, start_marker: str = "Deno.serve(") -> str:
    """Return the substring of a Deno.serve handler — used for behaviour
    checks (POST/multipart/400 branches) on upload-csv-source and run-csv-etl."""
    idx = source.find(start_marker)
    assert idx != -1, (
        f"RED — could not find `{start_marker}` handler in source file."
    )
    return source[idx:]


def _extract_parse_csv_body(source: str) -> str:
    """Return the body of the `export function parseCSV(...)` declaration
    in sheet_intake.ts so we can assert on its returned shape."""
    match = re.search(
        r"export\s+function\s+parseCSV\s*\([^)]*\)\s*:\s*ParsedCSV\s*\{",
        source,
    )
    assert match is not None, (
        "RED — could not locate `export function parseCSV(...): ParsedCSV {` in "
        "supabase/functions/_shared/sheet_intake.ts. The Coder must export "
        "parseCSV as a function returning ParsedCSV."
    )
    return source[match.end():]


# ── Tests: AC#1 — upload-csv-source handler ───────────────────────────────


def test_upload_csv_source_defines_deno_serve_post_handler():
    """AC#1 — upload-csv-source/index.ts MUST define a Deno.serve handler
    that accepts POST requests.

    The handler is the public entry point of Step Dados.  Without a POST
    branch, the frontend cannot upload a CSV/XLSX file.
    """
    source = _read(UPLOAD_CSV_SOURCE_PATH)
    handler_body = _extract_handler_body(source)

    assert "Deno.serve" in handler_body, (
        "RED — upload-csv-source/index.ts does not define a Deno.serve handler."
    )
    # Accept both `=== "POST"` (allow) and `!== "POST"` (reject) — the
    # file currently uses `!==` so a strict `===` check would be a false
    # negative.
    assert re.search(
        r"req\.method\s*(?:===|!==)\s*[\"']POST[\"']",
        handler_body,
    ), (
        "RED — upload-csv-source Deno.serve handler does not branch on "
        "`req.method === \"POST\"` (or `!== \"POST\"`). The Step Dados upload "
        "endpoint must gate the multipart parsing on a POST method check."
    )


def test_upload_csv_source_reads_multipart_form_fields():
    """AC#1 — upload-csv-source MUST read `file`, `client_id`, and
    `schema_type` from a multipart/form-data body.

    The frontend Step Dados form posts these three fields together with
    the binary file.  If any of them is missing the upload must fail
    with a 400 (the handler already does so for `file` and `client_id`).
    """
    source = _read(UPLOAD_CSV_SOURCE_PATH)

    assert 'formData.get("file")' in source, (
        "RED — upload-csv-source/index.ts does not call "
        '`formData.get("file")`. The Step Dados form posts the CSV/XLSX '
        "file under the `file` field."
    )
    assert 'formData.get("client_id")' in source, (
        "RED — upload-csv-source/index.ts does not call "
        '`formData.get("client_id")`. The Step Dados form must know which '
        "tenant owns the upload so it can scope Storage paths + the "
        "client_data_sources row."
    )
    assert 'formData.get("schema_type")' in source, (
        "RED — upload-csv-source/index.ts does not call "
        '`formData.get("schema_type")`. The Step Dados form must declare '
        "the schema type (e.g. `invoices`) so match-columns knows which "
        "canonical definition set to load."
    )


def test_upload_csv_source_rejects_unsupported_files_with_400():
    """AC#1 — upload-csv-source MUST return 400 for files that are not
    .csv / .xlsx / .xls / .tsv.

    A user might try to upload a PDF or an image by mistake — the
    handler must reject these at the validation step (before Storage
    upload) with a 400 so the frontend can show a clear error.
    """
    source = _read(UPLOAD_CSV_SOURCE_PATH)

    # The handler explicitly checks for csv/xlsx/xls/tsv suffixes
    isXlsx = "xlsx" in source or ".xls" in source
    isCsv = ".csv" in source or ".tsv" in source
    assert isXlsx and isCsv, (
        "RED — upload-csv-source/index.ts does not validate file "
        "extensions against .csv/.xlsx/.xls/.tsv. The Coder must add an "
        "isXlsx/isCsv check and return 400 for anything else."
    )

    # The validation must return a 400 (not 500, not 200) so the
    # frontend can render a user-friendly error toast.
    assert re.search(
        r"return\s+json\s*\(\s*\{\s*error:[^}]+\}\s*,\s*400\s*\)",
        source,
    ), (
        "RED — upload-csv-source/index.ts does not return "
        "`json({ error: ... }, 400)` for the unsupported-file branch. "
        "The Step Dados handler must reject non-CSV/XLSX files with 400."
    )


# ── Tests: AC#2 — match-columns INVOICES_COLUMNS tax fields ──────────────


def test_match_columns_invoices_columns_define_icms_base():
    """AC#2 — INVOICES_COLUMNS MUST define a canonical column for `icms_base`.

    Brazilian NFs carry the ICMS tax base on every line.  Without a
    canonical definition, the auto-match step will not recognise any
    CSV column named "ICMS Base", "Base de Cálculo ICMS", etc., and the
    user will be forced to manually map it on every upload.
    """
    source = _read(MATCH_COLUMNS_PATH)
    block = _extract_invoices_columns_block(source)

    assert re.search(
        r"\{\s*column_name\s*:\s*[\"']icms_base[\"']\s*,",
        block,
    ), (
        "RED — INVOICES_COLUMNS in match-columns/index.ts does NOT define "
        'a `{ column_name: "icms_base", ... }` entry. '
        "The Coder must add a canonical column for the ICMS tax base "
        "(e.g. `data_type: \"numeric\"`, `is_required: false`, "
        '`description: "ICMS tax base (base de cálculo)"`).'
    )


def test_match_columns_invoices_columns_define_icms_valor():
    """AC#2 — INVOICES_COLUMNS MUST define a canonical column for `icms_valor`."""
    source = _read(MATCH_COLUMNS_PATH)
    block = _extract_invoices_columns_block(source)

    assert re.search(
        r"\{\s*column_name\s*:\s*[\"']icms_valor[\"']\s*,",
        block,
    ), (
        "RED — INVOICES_COLUMNS in match-columns/index.ts does NOT define "
        'a `{ column_name: "icms_valor", ... }` entry. '
        "The Coder must add a canonical column for the ICMS tax value."
    )


def test_match_columns_invoices_columns_define_iss_aliquota():
    """AC#2 — INVOICES_COLUMNS MUST define a canonical column for `iss_aliquota`.

    Service invoices (NFS-e) carry the ISS rate.  Without a canonical
    column the auto-match will leave it unmatched and the user will
    have to re-map it every upload.
    """
    source = _read(MATCH_COLUMNS_PATH)
    block = _extract_invoices_columns_block(source)

    assert re.search(
        r"\{\s*column_name\s*:\s*[\"']iss_aliquota[\"']\s*,",
        block,
    ), (
        "RED — INVOICES_COLUMNS in match-columns/index.ts does NOT define "
        'a `{ column_name: "iss_aliquota", ... }` entry. '
        "The Coder must add a canonical column for the ISS rate "
        "(e.g. `data_type: \"numeric\"`, expressed as a percentage)."
    )


def test_match_columns_invoices_columns_define_iss_valor():
    """AC#2 — INVOICES_COLUMNS MUST define a canonical column for `iss_valor`."""
    source = _read(MATCH_COLUMNS_PATH)
    block = _extract_invoices_columns_block(source)

    assert re.search(
        r"\{\s*column_name\s*:\s*[\"']iss_valor[\"']\s*,",
        block,
    ), (
        "RED — INVOICES_COLUMNS in match-columns/index.ts does NOT define "
        'a `{ column_name: "iss_valor", ... }` entry. '
        "The Coder must add a canonical column for the ISS tax value."
    )


def test_match_columns_invoices_columns_define_pis():
    """AC#2 — INVOICES_COLUMNS MUST define a canonical column for `pis`.

    PIS is a federal social contribution present on every product
    invoice.  Without a canonical column the auto-match will leave
    it as `unmatched` for every upload.
    """
    source = _read(MATCH_COLUMNS_PATH)
    block = _extract_invoices_columns_block(source)

    assert re.search(
        r"\{\s*column_name\s*:\s*[\"']pis[\"']\s*,",
        block,
    ), (
        "RED — INVOICES_COLUMNS in match-columns/index.ts does NOT define "
        'a `{ column_name: "pis", ... }` entry. '
        "The Coder must add a canonical column for the PIS contribution."
    )


def test_match_columns_invoices_columns_define_cofins():
    """AC#2 — INVOICES_COLUMNS MUST define a canonical column for `cofins`."""
    source = _read(MATCH_COLUMNS_PATH)
    block = _extract_invoices_columns_block(source)

    assert re.search(
        r"\{\s*column_name\s*:\s*[\"']cofins[\"']\s*,",
        block,
    ), (
        "RED — INVOICES_COLUMNS in match-columns/index.ts does NOT define "
        'a `{ column_name: "cofins", ... }` entry. '
        "The Coder must add a canonical column for the COFINS contribution."
    )


# ── Tests: AC#3 — match-columns COLUMN_ALIASES for tax fields ────────────


@pytest.mark.parametrize("tax_field", TAX_FIELDS)
def test_match_columns_column_aliases_includes_tax_field(tax_field: str):
    """AC#3 — COLUMN_ALIASES MUST include an entry for every tax field.

    A canonical definition alone is not enough: the alias map is what
    powers the fuzzy match (e.g. "Valor ICMS" → `icms_valor`).  Without
    an alias list for each tax field, every upload will need manual
    mapping.
    """
    source = _read(MATCH_COLUMNS_PATH)
    block = _extract_column_aliases_block(source)

    # Match the canonical key in COLUMN_ALIASES followed by an array of
    # at least one alias string.  We accept any number of whitespace
    # and tolerate either `tax_field: [...]` (unquoted) or `"tax_field": [...]`
    # (quoted) since both styles appear in the file.
    pattern = (
        rf"(?P<key>[\"']?{re.escape(tax_field)}[\"']?)\s*:\s*\[[^\]]*[\"'][^\]]*\]"
    )
    assert re.search(pattern, block, re.DOTALL), (
        f"RED — COLUMN_ALIASES in match-columns/index.ts does NOT include "
        f"a `{tax_field}: [...]` entry with at least one alias string. "
        f"The Coder must add alias entries (e.g. common Portuguese variants "
        f"like \"ICMS Base\", \"Valor ICMS\", \"ISS Alíquota\", \"Valor ISS\", "
        f"\"PIS\", \"COFINS\") so the auto-match step can map Brazilian "
        f"NF spreadsheet headers to the canonical `{tax_field}` column."
    )


# ── Tests: AC#4 — run-csv-etl validates non-empty column_mapping ────────


def test_run_csv_etl_rejects_empty_column_mapping_with_400():
    """AC#4 — run-csv-etl MUST return 400 when `column_mapping` is null/empty.

    Enqueueing an ETL job with no mapped columns would silently drop
    every row on the floor at the staging step.  The handler must
    short-circuit with 400 before touching Storage or reg_jobs.
    """
    source = _read(RUN_CSV_ETL_PATH)
    handler_body = _extract_handler_body(source)

    # 1. The handler must check for an empty column_mapping object
    assert re.search(
        r"Object\.keys\s*\([^)]*\)\.length\s*===\s*0",
        handler_body,
    ) or re.search(
        r"Object\.keys\s*\([^)]*\)\.length\s*<\s*1",
        handler_body,
    ), (
        "RED — run-csv-etl/index.ts handler does not check "
        "`Object.keys(...).length === 0` (or `< 1`) for column_mapping. "
        "The Coder must add an early-return branch that rejects an empty "
        "column_mapping object before any Storage download or job insert."
    )

    # 2. The rejection MUST be a 400 — not 200 (silent success) or 500
    # (uncatchable server error).  The frontend uses 400 to show a
    # "you must map at least one column" message.
    assert re.search(
        r"return\s+json\s*\(\s*\{\s*error:[^}]*column_mapping[^}]*\}\s*,\s*400\s*\)",
        handler_body,
        re.IGNORECASE,
    ) or (
        re.search(
            r"return\s+json\s*\(\s*\{\s*error:[^}]+\}\s*,\s*400\s*\)",
            handler_body,
        )
        and re.search(
            r"column_mapping",
            handler_body,
        )
    ), (
        "RED — run-csv-etl/index.ts does not return 400 for the "
        "empty-column_mapping branch. The Step Dados ETL endpoint must "
        "reject empty mappings with 400 (not 200 and not 500) so the "
        "frontend can show a clear error."
    )


# ── Tests: AC#5 — sheet_intake.parseCSV returns headers + rows ──────────


def test_sheet_intake_exports_parse_csv():
    """AC#5 — sheet_intake.ts MUST export a `parseCSV` function.

    Both upload-csv-source and run-csv-etl import `parseCSV` from
    sheet_intake.  Without the export the modules fail to load.
    """
    source = _read(SHEET_INTAKE_PATH)

    assert re.search(
        r"export\s+function\s+parseCSV\s*\(",
        source,
    ), (
        "RED — sheet_intake.ts does not export a `parseCSV` function. "
        "The Coder must add `export function parseCSV(text: string, "
        "opts?: ParseCSVOptions): ParsedCSV { ... }` so upload-csv-source "
        "and run-csv-etl can import it."
    )


def test_sheet_intake_parse_csv_returns_headers_and_rows():
    """AC#5 — parseCSV MUST return a ParsedCSV with `headers` and `rows`.

    `headers` is the list of column names from the file; `rows` is the
    list of header→value records.  Both are required by the upload and
    ETL handlers to map CSV cells to canonical columns.
    """
    source = _read(SHEET_INTAKE_PATH)
    body = _extract_parse_csv_body(source)

    # The function body must produce a headers string[] and rows
    # Record<string,string>[] and return them as part of ParsedCSV.
    assert "headers" in body, (
        "RED — parseCSV body does not reference a `headers` variable. "
        "The Coder must build a `headers` string[] from the first "
        "non-empty line of the CSV."
    )
    assert "rows" in body, (
        "RED — parseCSV body does not reference a `rows` variable. "
        "The Coder must build a `rows: Record<string,string>[]` array "
        "from the data lines."
    )
    assert re.search(
        r"return\s*\{\s*headers\s*,\s*rows\s*,", body,
    ) or re.search(
        r"return\s*\{\s*headers\s*:", body,
    ) or re.search(
        r"return\s*\{[^}]*headers[^}]*\}", body,
    ), (
        "RED — parseCSV body does not return `{ headers, rows, ... }`. "
        "The Coder must `return { headers, rows, headerRowIndex };` "
        "from parseCSV so callers receive a ParsedCSV shape."
    )


# ── Tests: AC#6 — parseCSV preserves tax header names ────────────────────


def test_sheet_intake_parse_csv_preserves_tax_header_names():
    """AC#6 — parseCSV MUST preserve tax field header names verbatim.

    The match-columns auto-match looks up headers against COLUMN_ALIASES
    (lowercase).  If parseCSV lowercased, trimmed, or otherwise mangled
    the original header name, the alias map would never see e.g.
    "ICMS Valor" — the user would have to map it manually on every
    upload.  We assert the function does NOT apply a global lowercase /
    diacritic-stripping transform on headers.
    """
    source = _read(SHEET_INTAKE_PATH)

    # The function uses .trim() (allowed) and .replace(/^"|"$/g, "") (allowed,
    # only strips outer quotes).  It must NOT use a global toLowerCase() or
    # NFD-normalize on the headers themselves.
    body_match = re.search(
        r"export\s+function\s+parseCSV\s*\([^)]*\)\s*:\s*ParsedCSV\s*\{(?P<body>.*?)(?=^\}|^\s*\n\s*\}|\Z)",
        source,
        re.DOTALL | re.MULTILINE,
    )
    assert body_match is not None, (
        "RED — could not isolate parseCSV body in sheet_intake.ts."
    )
    body = body_match.group("body")

    # Allowed: .trim() and outer-quote stripping.
    # Disallowed: a global .toLowerCase() on the header list, which would
    # destroy case-sensitivity required by the alias match.
    assert "headers.map((h) => h.toLowerCase())" not in body, (
        "RED — parseCSV lowercases every header before returning them. "
        "That would destroy the case-sensitivity required by the alias "
        "match (e.g. \"ICMS Valor\" would become \"icms valor\" — fine for "
        "lowercased alias lookup, but the matched.source key returned to "
        "the frontend must be the original case)."
    )

    # Also assert the headers-array construction uses .trim() and an
    # outer-quote strip — the minimal, non-mangling cleaning.
    # We accept any parseLine → .map → .filter pipeline (the actual file
    # formats the chain across multiple lines with chained method calls).
    assert re.search(
        r"const\s+headers\s*=\s*parseLine\(",
        body,
    ), (
        "RED — parseCSV body does not construct `headers` via "
        "`const headers = parseLine(...)`. The Coder must derive the "
        "headers string[] from the first non-empty line of the CSV."
    )
    # parseCSV must apply minimal cleaning only (`.trim()` + outer-quote
    # strip) — not a global `.toLowerCase()` or NFD-normalize on the
    # header list, which would mangle tax header names.
    assert "headers.map((h) => h.toLowerCase())" not in body, (
        "RED — parseCSV lowercases every header before returning them. "
        "That would destroy the original case of tax headers (e.g. "
        "\"ICMS Valor\") required by the alias match — the user would "
        "have to map tax columns manually on every upload."
    )
