"""RED test for behavior BKL-039/040 — process-document EF: XLSX/PPTX parsers + hardening ACs.

GOAL:
    AC#1 / AC#2 — ``getParser()`` in ``supabase/functions/process-document/index.ts``
    must handle ``xlsx`` and ``pptx`` file types (returning real parser functions),
    not just fall through to the ``default: return null`` branch.

    AC#3 — AC#8 — Hardening contracts that the EF must respect today and that
    serve as living documentation: embedding failure must not insert chunks,
    embedding failure must mark the document ``failed``, the request must be
    raced against ``catchUnload`` (isolate termination), metadata enrichment
    must be non-fatal via ``Promise.allSettled``, the existing parsers must
    continue to work, and the chunk INSERT must always include the
    ``embedding`` column (no insert-without-embedding path).

BEHAVIOR:
    BKL-039 — process-document Edge Function hardening: embed failure
    surfaces as failed status, Promise.race with catchUnload, metadata
    enrichment is non-fatal.

    BKL-040 — Add XLSX / PPTX parsers to ``getParser()`` so the EF can
    ingest Excel workbooks and PowerPoint decks directly (today they fall
    through to the ``default: return null`` branch and the handler returns
    422 "Unsupported file type for direct processing").

    Today, ``getParser()`` (lines 378-401 of ``index.ts``) only handles:

        - txt / md   -> parseTxtMd
        - csv        -> parseCsv
        - json       -> parseJson
        - xml, html,
          htm        -> parseXmlHtml
        - pdf        -> parsePdf
        - docx       -> parseDocx
        - default    -> return null

    There is NO ``xlsx`` or ``pptx`` case. The 8 tests below inspect the
    source text and assert these contracts; the first two are RED because
    the new parsers don't exist yet.

AC (Acceptance Criteria):
    AC#1 — ``getParser()`` has a case for ``"xlsx"`` returning a parser.
    AC#2 — ``getParser()`` has a case for ``"pptx"`` returning a parser.
    AC#3 — If ``generateEmbeddings()`` throws, the chunk INSERT inside
           ``sql.begin(...)`` is NOT reached (the catch handler at line 629
           marks the document ``failed`` instead).
    AC#4 — The catch handler at line 629 sets ``status = 'failed'`` and
           writes ``error_message`` for embedding API failures.
    AC#5 — The HTTP handler uses ``Promise.race([processDocument(...),
           catchUnload()])`` so a Deno isolate unload fails the document
           instead of silently leaving it in ``processing``.
    AC#6 — Metadata enrichment uses ``Promise.allSettled`` and only logs
           ``console.warn`` on failure — it never throws out of the loop.
    AC#7 — The existing parsers (txt, md, csv, json, xml, html, htm, pdf,
           docx) continue to work after the XLSX/PPTX cases are added.
    AC#8 — The INSERT in ``sql.begin(...)`` always includes the
           ``embedding`` column — no code path inserts chunks without an
           embedding vector.

Anti-Goals (must NOT be violated):
    1. NÃO alterar ``generateEmbeddings()`` (lines 80-112) to silently
       swallow errors — the throw on !response.ok is the contract.
    2. NÃO mover o ``sql.begin`` insert block para fora do ``try``
       que contém ``generateEmbeddings()``.
    3. NÃO substituir ``Promise.allSettled`` por ``Promise.all`` no
       enrichment loop.
    4. NÃO remover o ``Promise.race`` com ``catchUnload`` no handler.

Estado atual: RED — ``xlsx`` and ``pptx`` cases are missing from
``getParser()``. ACs 3-8 currently PASS but are still asserted here as
regression guards. The test parses the source TypeScript as plain text
(source-inspection puro) and uses regex/string matching, just like
``tests/behaviors/test_bkl_041_upload_complex_to_process_document.py``.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

PROCESS_DOC_PATH = (
    REPO_ROOT
    / "supabase"
    / "functions"
    / "process-document"
    / "index.ts"
)


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure source inspection, no DB teardown."""
    yield


# ── Helpers: extract a function body using brace-depth counting ──────────


def _extract_function_body(source: str, func_name: str) -> str:
    """Return the body text of the first ``function <func_name>(...)``.

    The function is located by matching the keyword ``function`` followed
    by ``<func_name>(``.  The body is then identified by walking past the
    parameter list's closing ``)``, skipping the optional return-type
    annotation up to the opening ``{`` of the body, and then counting
    braces to find the matching ``}``.

    Strings (single, double, backtick) and comments (line ``//`` and block
    ``/* */``) are tracked so braces inside them are not miscounted.
    Template-literal expressions (``${...}``) are tracked as nested brace
    contexts so they also don't break the depth count.

    Returns an empty string if the function is not found.
    """
    pattern = rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(func_name)}\s*\("
    match = re.search(pattern, source)
    if not match:
        return ""

    # Walk past the matching ')' of the parameter list.
    start = match.end()
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        char = source[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        i += 1
    if depth != 0:
        return ""

    # Skip the optional return-type annotation (e.g., ``: Promise<string>``)
    # up to the next ``{`` (the start of the function body).
    j = i
    while j < len(source) and source[j] != "{":
        j += 1
    if j >= len(source):
        return ""

    body_start = j + 1

    # Brace-depth counting to find the matching closing ``}``.
    brace_depth = 1
    k = body_start
    in_string = None  # None | '"' | "'" | "`"
    in_line_comment = False
    in_block_comment = False
    while k < len(source) and brace_depth > 0:
        ch = source[k]
        nxt = source[k + 1] if k + 1 < len(source) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            k += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                k += 2
                continue
            k += 1
            continue
        if in_string is not None:
            if ch == "\\":
                k += 2
                continue
            if ch == in_string:
                in_string = None
                k += 1
                continue
            if in_string == "`":
                if ch == "$" and nxt == "{":
                    brace_depth += 1
                    k += 2
                    continue
                if ch == "}":
                    brace_depth -= 1
                    k += 1
                    continue
            k += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            k += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            k += 2
            continue
        if ch in ('"', "'", "`"):
            in_string = ch
            k += 1
            continue
        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
        k += 1

    if brace_depth != 0:
        return ""
    return source[body_start : k - 1]


def _find_matching_close(source: str, start: int, open_ch: str, close_ch: str) -> int:
    """Return the index of the ``close_ch`` that matches the ``open_ch``
    at ``start``.  Tracks strings and comments the same way as
    ``_extract_function_body`` so brackets inside them are ignored.
    """
    assert source[start] == open_ch, (
        f"_find_matching_close called with start={start!r} "
        f"but source[start]={source[start]!r} (expected {open_ch!r})."
    )
    depth = 1
    k = start + 1
    in_string = None
    in_line_comment = False
    in_block_comment = False
    while k < len(source) and depth > 0:
        ch = source[k]
        nxt = source[k + 1] if k + 1 < len(source) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            k += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                k += 2
                continue
            k += 1
            continue
        if in_string is not None:
            if ch == "\\":
                k += 2
                continue
            if ch == in_string:
                in_string = None
                k += 1
                continue
            k += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            k += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            k += 2
            continue
        if ch in ('"', "'", "`"):
            in_string = ch
            k += 1
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
        k += 1
    return k - 1


def _load_source() -> str:
    """Load ``process-document/index.ts`` as text and assert it exists."""
    assert PROCESS_DOC_PATH.exists(), (
        f"Source file not found: {PROCESS_DOC_PATH}"
    )
    return PROCESS_DOC_PATH.read_text()


def _load_function_body(func_name: str) -> str:
    """Load the source and return the body of ``func_name``."""
    source = _load_source()
    body = _extract_function_body(source, func_name)
    assert body, (
        f"Could not extract body of `{func_name}` from "
        f"{PROCESS_DOC_PATH}. The function may be missing or the "
        "brace-counting may have failed (unbalanced braces)."
    )
    return body


# ── Tests ────────────────────────────────────────────────────────────────


def test_bkl_039_getParser_handles_xlsx():
    """AC#1 — ``getParser()`` must handle the ``xlsx`` file type.

    XLSX is a first-class document type for the knowledge base (spreadsheets
    are a major source of business data — folha, dre, fluxo de caixa, etc.).
    The EF must dispatch ``"xlsx"`` to a real parser function, not return
    ``null`` from the default branch.

    Today the case is missing, so this test is RED.
    """
    body = _load_function_body("getParser")

    # The switch must have an explicit case for "xlsx" returning a parser
    # (or an arrow / function expression).  We accept any of the forms:
    #   case "xlsx":
    #       return parseXlsx;
    #   case "xlsx": return parseXlsx;
    # and we reject fall-throughs that leave the type unhandled.
    case_match = re.search(
        r'case\s+["\']xlsx["\']\s*:\s*return\s+([A-Za-z_$][\w$]*)\s*;',
        body,
    )
    assert case_match is not None, (
        "AC#1 violated: `getParser()` has NO `case \"xlsx\": return <parser>;` "
        "branch. Behavior BKL-040 requires the EF to ingest XLSX workbooks "
        "directly. Add a `case \"xlsx\":` branch that returns a parser "
        "function (e.g. `parseXlsx` backed by SheetJS / xlsx npm package)."
    )

    # And the parser it returns must exist as a function defined in the file,
    # otherwise the case is a dangling reference that will throw at runtime.
    parser_name = case_match.group(1)
    source = _load_source()
    parser_def = re.search(
        rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(parser_name)}\s*\(",
        source,
    )
    assert parser_def is not None, (
        f"AC#1 violated: `getParser()` returns `{parser_name}` for xlsx, but "
        f"no `function {parser_name}(...)` is defined anywhere in "
        f"{PROCESS_DOC_PATH}. The xlsx case must point to a real parser."
    )


def test_bkl_039_getParser_handles_pptx():
    """AC#2 — ``getParser()`` must handle the ``pptx`` file type.

    PPTX presentations are a knowledge source (treinamentos, políticas
    internas, decks comerciais). The EF must dispatch ``"pptx"`` to a real
    parser, not return ``null`` from the default branch.

    Today the case is missing, so this test is RED.
    """
    body = _load_function_body("getParser")

    case_match = re.search(
        r'case\s+["\']pptx["\']\s*:\s*return\s+([A-Za-z_$][\w$]*)\s*;',
        body,
    )
    assert case_match is not None, (
        "AC#2 violated: `getParser()` has NO `case \"pptx\": return <parser>;` "
        "branch. Behavior BKL-040 requires the EF to ingest PPTX decks "
        "directly. Add a `case \"pptx\":` branch that returns a parser "
        "function (e.g. `parsePptx` backed by jszip + xml extraction)."
    )

    parser_name = case_match.group(1)
    source = _load_source()
    parser_def = re.search(
        rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(parser_name)}\s*\(",
        source,
    )
    assert parser_def is not None, (
        f"AC#2 violated: `getParser()` returns `{parser_name}` for pptx, but "
        f"no `function {parser_name}(...)` is defined anywhere in "
        f"{PROCESS_DOC_PATH}. The pptx case must point to a real parser."
    )


def test_bkl_039_embedding_failure_no_chunk_insert():
    """AC#3 — If ``generateEmbeddings()`` throws, the chunk INSERT inside
    ``sql.begin(...)`` is NOT reached.

    The pipeline order is:

        1. parse
        2. chunk
        3. generateEmbeddings  <-- throws on Cohere API error (line 103)
        4. enrich metadata
        5. sql.begin { INSERT INTO vector_db.document_chunks ... }

    Because the INSERT is in the same ``try`` block as the
    ``generateEmbeddings`` call (and the catch handler at line 629 marks
    the document ``failed`` and ``return``s), an embedding failure must
    short-circuit before any chunk is inserted.

    This is a hardening contract — it must hold both before and after the
    XLSX/PPTX parsers are added.
    """
    source = _load_source()

    # (a) generateEmbeddings must `throw` on a non-OK response — this is the
    # signal that fails the document.  Look for the throw inside the
    # function body.
    gen_body = _extract_function_body(source, "generateEmbeddings")
    assert gen_body, "Could not extract `generateEmbeddings` body."
    assert "throw" in gen_body, (
        "AC#3 violated: `generateEmbeddings()` does not `throw` on Cohere "
        "API errors. Behavior BKL-039 requires the function to throw so the "
        "outer `try { ... } catch { mark failed }` handler can fail the "
        "document instead of silently inserting chunks without embeddings."
    )

    # (b) The INSERT must live strictly INSIDE the same `try` block that
    # contains the `generateEmbeddings` call.  We assert this by checking
    # that the literal string "INSERT INTO vector_db.document_chunks"
    # appears BEFORE the `} catch (` that owns the failure path.
    insert_idx = source.find("INSERT INTO vector_db.document_chunks")
    assert insert_idx >= 0, (
        "AC#3 violated: no `INSERT INTO vector_db.document_chunks` found "
        "in `process-document/index.ts`. The pipeline must insert chunks "
        "exactly once per document."
    )

    # Locate the `} catch (` for the outer try.  We pick the FIRST one
    # after the `try {` that opens the pipeline (the outer try, not a
    # nested one inside the insert loop's ON CONFLICT clause).
    try_idx = source.find("try {", source.find("async function processDocument"))
    assert try_idx >= 0, "AC#3 violated: outer `try {` not found in processDocument."

    catch_idx = source.find("} catch (", try_idx)
    assert catch_idx >= 0, (
        "AC#3 violated: no `} catch (` found after the outer `try {` in "
        "`processDocument()`. The catch handler that marks the document "
        "failed must be present so embedding failures don't crash the EF."
    )

    assert insert_idx < catch_idx, (
        "AC#3 violated: the `INSERT INTO vector_db.document_chunks` block "
        "appears AFTER the `} catch (` that owns the embedding-failure "
        "handler. The insert must be INSIDE the try block so an embedding "
        "throw short-circuits the insert. Move the `sql.begin(...)` insert "
        "block above the catch handler."
    )


def test_bkl_039_embedding_failure_sets_status_failed():
    """AC#4 — The catch handler at line 629 sets ``status = 'failed'`` and
    writes ``error_message`` for embedding API failures.

    This is the contract that makes a Cohere outage or rate-limit visible
    in the UI: the document row is updated to ``failed`` with the error
    reason, instead of being stuck in ``processing`` forever.
    """
    source = _load_source()

    # Locate the catch block of processDocument (the one that owns the
    # pipeline failures).  We look for the FIRST `} catch (` after the
    # outer `try {` opened inside processDocument.
    proc_idx = source.find("async function processDocument")
    assert proc_idx >= 0, "`async function processDocument` not found."
    try_idx = source.find("try {", proc_idx)
    assert try_idx >= 0, "outer `try {` not found in processDocument."
    catch_start = source.find("} catch (", try_idx)
    assert catch_start >= 0, "outer `} catch (` not found in processDocument."

    # The catch body is the text from the `} catch (err) {` open-brace
    # up to the matching close-brace.  Find the open brace.
    open_brace = source.find("{", catch_start)
    assert open_brace >= 0, "Could not find open brace of catch block."

    # Walk braces to find the matching close.
    depth = 1
    k = open_brace + 1
    in_string = None
    in_line_comment = False
    in_block_comment = False
    while k < len(source) and depth > 0:
        ch = source[k]
        nxt = source[k + 1] if k + 1 < len(source) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            k += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                k += 2
                continue
            k += 1
            continue
        if in_string is not None:
            if ch == "\\":
                k += 2
                continue
            if ch == in_string:
                in_string = None
                k += 1
                continue
            k += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            k += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            k += 2
            continue
        if ch in ('"', "'", "`"):
            in_string = ch
            k += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        k += 1

    catch_body = source[open_brace + 1 : k - 1]

    assert "status = 'failed'" in catch_body or 'status = "failed"' in catch_body, (
        "AC#4 violated: the catch handler in `processDocument()` does NOT "
        "set `status = 'failed'`. Behavior BKL-039 requires the catch "
        "block to UPDATE the document row to `status = 'failed'` so that "
        "embedding / parsing / chunking failures are visible in the UI."
    )
    assert "error_message" in catch_body, (
        "AC#4 violated: the catch handler in `processDocument()` does NOT "
        "write `error_message`. Behavior BKL-039 requires the catch block "
        "to set `error_message = ${err.message}` (or equivalent) so that "
        "operators can see WHY the document failed."
    )


def test_bkl_039_timeout_fails_document():
    """AC#5 — The HTTP handler must race ``processDocument(...)`` against
    ``catchUnload()`` so that a Deno isolate unload fails the document
    instead of leaving it stuck in ``processing``.

    ``catchUnload()`` registers a ``beforeunload`` listener that rejects
    with ``"Deno isolate terminated (beforeunload) ..."`` — that rejection
    propagates up to the handler's outer ``catch (err)`` which returns 500
    AND, because the throw originated inside ``processDocument``'s try
    block, the catch handler at line 629 marks the document ``failed``.

    Without the ``Promise.race``, a stuck chunk loop would freeze the
    isolate and the document would never transition out of ``processing``.
    """
    source = _load_source()

    # (a) catchUnload must exist and reject with a clear error.
    catch_unload_body = _extract_function_body(source, "catchUnload")
    assert catch_unload_body, (
        "AC#5 violated: `catchUnload()` is not defined in "
        f"{PROCESS_DOC_PATH}. The function is required so the HTTP handler "
        "can race the processing pipeline against isolate termination."
    )
    assert "beforeunload" in catch_unload_body, (
        "AC#5 violated: `catchUnload()` does not register a `beforeunload` "
        "listener. The whole point of the function is to reject on "
        "`beforeunload` so the document is marked failed."
    )
    assert "reject" in catch_unload_body, (
        "AC#5 violated: `catchUnload()` does not call `reject(...)`. "
        "Without a reject, the race has no loser and a Deno unload would "
        "not fail the document."
    )

    # (b) The HTTP handler must use Promise.race with both processDocument
    # AND catchUnload.  We look for the literal pattern.
    assert "Promise.race" in source, (
        "AC#5 violated: `Promise.race` is not used in "
        f"{PROCESS_DOC_PATH}. The HTTP handler must race the processing "
        "pipeline against `catchUnload()` so an isolate unload fails the "
        "document."
    )
    race_match = re.search(
        r"Promise\.race\s*\(\s*\[",
        source,
    )
    assert race_match is not None, (
        "AC#5 violated: `Promise.race([` not found. The handler must race "
        "the processing pipeline against `catchUnload()` so an isolate "
        "unload fails the document."
    )
    # Walk brackets to find the matching `]` of the array literal.  This
    # correctly handles the nested parens inside `processDocument(...)`.
    race_section = source[ race_match.start() : _find_matching_close(
        source, race_match.end() - 1, "[", "]",
    ) + 1 ]
    assert "processDocument(" in race_section, (
        "AC#5 violated: `Promise.race([...])` does not include "
        "`processDocument(` as a slot. The first slot must be the "
        "`processDocument` call so the race times out the pipeline."
    )
    assert "catchUnload()" in race_section, (
        "AC#5 violated: `Promise.race([...])` does not include "
        "`catchUnload()` as a slot. The race must pair the pipeline with "
        "`catchUnload()` so an isolate unload rejects the race and the "
        "document is marked failed."
    )


def test_bkl_039_metadata_enrichment_non_fatal():
    """AC#6 — Metadata enrichment must use ``Promise.allSettled`` and only
    log a warning on failure — it must never throw out of the enrichment
    loop.

    A flaky Ollama Cloud call must NOT fail the whole document — the chunk
    is still valuable without enrichment (theme/word_cloud/usage_context
    are nice-to-have, not correctness-critical).
    """
    source = _load_source()

    # The enrichment loop must use Promise.allSettled — not Promise.all.
    # We search for the call site to be sure it's the right one.
    all_settled_match = re.search(
        r"Promise\.allSettled\s*\(",
        source,
    )
    assert all_settled_match is not None, (
        "AC#6 violated: `Promise.allSettled` is not used in "
        f"{PROCESS_DOC_PATH}. Behavior BKL-039 requires the metadata "
        "enrichment loop to use `Promise.allSettled` so that a single "
        "LLM failure does not reject the whole batch and fail the document."
    )

    # The `.forEach` after allSettled must inspect `result.status` and log
    # a warning (NOT throw) on rejection.
    # Look at the forEach body that lives right after the allSettled call.
    after = source[ all_settled_match.end() : all_settled_match.end() + 1500 ]
    assert "result.status" in after, (
        "AC#6 violated: the forEach after `Promise.allSettled` does not "
        "check `result.status`. The handler must distinguish fulfilled "
        "from rejected results so failures are downgraded to a warning."
    )
    assert 'console.warn' in after, (
        "AC#6 violated: the enrichment failure path does not call "
        "`console.warn`. Behavior BKL-039 requires failures to be logged "
        "as warnings, not errors, and crucially NOT to throw."
    )
    # And the failure branch must NOT re-throw.  We assert there's no
    # `throw` inside the `else` (or `status === \"rejected\"`) branch.
    # Simple heuristic: between the forEach's `=> {` and the next `});`
    # there must be no bare `throw `.
    foreach_open = after.find("results.forEach")
    assert foreach_open >= 0, "AC#6 violated: `results.forEach` not found after allSettled."
    foreach_close = after.find(");", foreach_open)
    assert foreach_close >= 0, "AC#6 violated: could not find end of forEach after allSettled."
    foreach_body = after[ foreach_open : foreach_close ]
    # Strip the `console.warn` line before checking for throws so we don't
    # trip on substrings inside log messages.
    cleaned = re.sub(r"console\.warn\([^;]*", "", foreach_body)
    assert "throw " not in cleaned, (
        "AC#6 violated: the enrichment forEach body contains a `throw`. "
        "A metadata enrichment failure must be swallowed (logged as a "
        "warning) so the document can still complete without enrichment."
    )


def test_bkl_039_existing_parsers_still_work():
    """AC#7 — Adding xlsx/pptx must not regress the existing parsers.

    Today ``getParser()`` handles: txt, md, csv, json, xml, html, htm, pdf,
    docx.  All nine must continue to be dispatched correctly after the
    XLSX/PPTX cases land.
    """
    body = _load_function_body("getParser")

    expected_parsers = {
        "txt": "parseTxtMd",
        "md": "parseTxtMd",
        "csv": "parseCsv",
        "json": "parseJson",
        "xml": "parseXmlHtml",
        "html": "parseXmlHtml",
        "htm": "parseXmlHtml",
        "pdf": "parsePdf",
        "docx": "parseDocx",
    }

    missing = []
    for ext, parser_name in expected_parsers.items():
        # Match `case "txt":` (or `case 'txt':`) possibly followed by
        # whitespace/newline and then `return parseTxtMd;`.
        pattern = (
            rf'case\s+["\']' + re.escape(ext) + rf'["\']\s*:'
            rf'[\s\S]{{0,80}}return\s+' + re.escape(parser_name) + r'\s*;'
        )
        if not re.search(pattern, body):
            missing.append((ext, parser_name))

    assert not missing, (
        "AC#7 violated: the following existing parser cases are missing "
        "or no longer dispatch to the right parser function in "
        "`getParser()`: "
        + ", ".join(f"`{ext}` -> `{parser_name}`" for ext, parser_name in missing)
        + ". Behavior BKL-040 must not regress the 9 existing file types "
        "(txt, md, csv, json, xml, html, htm, pdf, docx)."
    )


def test_bkl_039_chunks_without_embedding_never_inserted():
    """AC#8 — The chunk INSERT in ``sql.begin(...)`` must always include
    the ``embedding`` column.

    There must be NO code path that inserts a row into
    ``vector_db.document_chunks`` without a populated ``embedding`` column.
    The whole point of the synchronous pipeline is that every chunk is
    searchable the moment the EF returns 200 — a row with a NULL
    ``embedding`` would silently break semantic search for that chunk.

    We assert this two ways:

        1. The single INSERT statement in the file must list ``embedding``
           in its column list.
        2. There must be NO ``INSERT INTO vector_db.document_chunks`` that
           omits the word ``embedding`` (no second INSERT elsewhere, no
           fallback path).
    """
    source = _load_source()

    # Find every INSERT into document_chunks and check each one includes
    # the `embedding` column.  We use a tolerant search for the column
    # list: it must contain the bare identifier `embedding` somewhere
    # between the opening paren of the column list and the matching close.
    insert_blocks = list(
        re.finditer(
            r"INSERT\s+INTO\s+vector_db\.document_chunks\b[\s\S]*?\)",
            source,
        )
    )
    assert insert_blocks, (
        "AC#8 violated: no `INSERT INTO vector_db.document_chunks` block "
        "found in `process-document/index.ts`. The pipeline must insert "
        "chunks exactly once per document."
    )

    bad_blocks = []
    for match in insert_blocks:
        block = match.group(0)
        if "embedding" not in block:
            bad_blocks.append(block[:120].replace("\n", " "))

    assert not bad_blocks, (
        "AC#8 violated: at least one `INSERT INTO vector_db.document_chunks` "
        "block does not list the `embedding` column. A chunk inserted "
        "without an embedding is invisible to semantic search, which is "
        "a silent correctness bug. The offending block(s):\n  - "
        + "\n  - ".join(bad_blocks)
    )
