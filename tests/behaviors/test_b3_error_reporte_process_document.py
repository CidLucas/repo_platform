"""RED test for behavior B-3 / AC-3 — ``process-document`` EF: outer
handler catch MUST mark the document as ``failed`` on timeout.

GOAL:
    AC-3 — ``supabase/functions/process-document/index.ts`` outer
    ``catch (err) { ... }`` block (the one wrapping the HTTP handler
    body, AFTER the ``Promise.race([processDocument(...), catchUnload()])``)
    MUST execute an ``UPDATE vector_db.documents SET status = 'failed',
    error_message = ...`` when the race is lost or any other unexpected
    error propagates out of the request pipeline.  This guarantees that
    every failure path — download, parse, embed, enrich, timeout — ends
    with a persisted ``status='failed'`` row that the frontend can show
    to the user, instead of leaving the document stuck in
    ``status='processing'`` forever.

BEHAVIOR:
    B-3 / AC-3 — Toda falha no EF ``process-document`` (download, parse,
    embed, enrich, timeout) resulta em ``status='failed'`` com
    ``error_message`` no DB.

    The HTTP handler at the bottom of ``index.ts`` is structured as:

        Deno.serve(async (req: Request) => {
            if (req.method === "OPTIONS") { ... }
            try {
                ...
                await Promise.race([
                    processDocument(...),
                    catchUnload(),
                ]);
                return json({ ... status: "completed" ... });
            } catch (err) {
                console.error("[process-document] Handler error:", err);
                return json(
                    { error: "Internal error", details: ... },
                    500,
                );
            }
        });

    The INNER catch inside ``processDocument()`` (around line 668-674)
    already updates the document to ``status='failed'`` — that covers
    failures that happen INSIDE the function (Cohere 5xx, Ollama timeout,
    postgres connection drop, etc.).  But the OUTER catch (lines 744-750)
    is the safety net for failures that escape the inner try: most
    importantly, when ``catchUnload()`` wins the race (Deno isolate
    being terminated / timeout), the rejection propagates straight to
    this outer catch.  Today the outer catch only ``console.error``s
    and returns HTTP 500 — it does NOT touch the database.

    The gap (RED): if the isolate is terminated mid-processing, the
    document is left at ``status='processing'`` forever.  The frontend
    keeps polling, the user never sees an error, and the document is
    effectively orphaned.

AC (Acceptance Criteria):
    AC-3 — The outer ``catch (err) { ... }`` block in the ``Deno.serve``
           handler (the one AFTER the ``Promise.race([processDocument(...),
           catchUnload()])``) MUST:
             1. Execute an ``UPDATE`` on ``vector_db.documents`` that sets
                ``status = 'failed'``.
             2. Populate ``error_message`` in that UPDATE so operators
                and the UI can see WHY the document failed.

Anti-Goals (must NOT be violated):
    1. NAO remover o ``Promise.race([processDocument(...), catchUnload()])``
       — ele garante que o handler nao trava em loops infinitos quando
       o isolate do Deno precisa ser terminado.
    2. NAO duplicar o try/catch interno de ``processDocument()`` — ele
       ja cobre falhas de runtime (Cohere, Ollama, postgres).  O catch
       externo eh a REDE DE SEGURANCA para o que ESCAPA desse try
       interno, em particular o ``catchUnload()``.
    3. NAO usar ``console.error`` como unica acao de tratamento no catch
       externo — sem o UPDATE o documento fica travado em
       ``status='processing'`` e o usuario nunca recebe feedback.

Estado atual: RED — o catch externo do handler (linhas 744-750 de
``index.ts``) NAO faz UPDATE. Apenas faz ``console.error`` e retorna
HTTP 500.  Quando o ``catchUnload()`` vence a race (timeout), o
documento fica preso em ``status='processing'`` para sempre.  Este
teste pin o contrato esperado: o catch externo PRECISA persistir
``status='failed'`` + ``error_message`` antes de retornar 500.

The test is pure source inspection (regex on the TypeScript text).
Nothing is mocked, nothing is executed.
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


# ── Helpers (pattern copied from test_bkl_039_040) ───────────────────────


def _extract_function_body(source: str, func_name: str) -> str:
    """Return the body text of the first ``function <func_name>(...)``.

    Mirrors the brace-depth walker used in
    ``test_bkl_039_040_process_document_parsers_and_hardening.py`` so the
    EF inspection primitives are shared across the behavior test suite.
    Strings (single, double, backtick) and comments (line ``//`` and
    block ``/* */``) are tracked so braces inside them are not
    miscounted.  Template-literal expressions (``${...}``) are tracked
    as nested brace contexts.

    Returns an empty string if the function is not found or the
    brace-counting fails.
    """
    pattern = rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(func_name)}\s*\("
    match = re.search(pattern, source)
    if not match:
        return ""

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

    j = i
    while j < len(source) and source[j] != "{":
        j += 1
    if j >= len(source):
        return ""

    body_start = j + 1

    brace_depth = 1
    k = body_start
    in_string = None
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
    at ``start``.

    Tracks strings and comments the same way as
    ``_extract_function_body`` so brackets inside them are ignored.
    Template-literal expressions (``${...}``) are NOT tracked here —
    callers that need it should use ``_extract_function_body`` instead.
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
    """Load ``supabase/functions/process-document/index.ts`` as text and
    assert it exists."""
    assert PROCESS_DOC_PATH.exists(), (
        f"Source file not found: {PROCESS_DOC_PATH}"
    )
    return PROCESS_DOC_PATH.read_text()


# ── Helpers specific to this test (Deno.serve handler + outer catch) ─────


def _extract_deno_serve_handler_body(source: str) -> str:
    """Return the body text of the arrow function passed to
    ``Deno.serve(async (req: Request) => { ... })``.

    ``Deno.serve`` is not a ``function`` declaration, so
    ``_extract_function_body`` cannot locate it.  This helper finds the
    call site with a regex and then uses ``_find_matching_close`` to
    locate the matching ``}`` of the arrow function body.
    """
    match = re.search(
        r"Deno\.serve\s*\(\s*async\s*\([^)]*\)\s*=>\s*\{",
        source,
    )
    if not match:
        return ""
    brace_pos = match.end() - 1  # position of the opening '{'
    close_pos = _find_matching_close(source, brace_pos, "{", "}")
    if close_pos <= brace_pos:
        return ""
    return source[brace_pos + 1 : close_pos]


def _extract_outer_catch_in_handler(source: str) -> str:
    """Return the body of the OUTER ``catch (err) { ... }`` block in the
    ``Deno.serve`` handler.

    The handler has exactly one outer catch (the one that wraps the
    entire request processing including the ``Promise.race`` with
    ``catchUnload()``).  This is the catch that fires when the race
    is lost (timeout) or when any other unexpected error escapes the
    inner ``processDocument()`` try/catch.

    The function returns the text inside that catch block, or an empty
    string if the handler / outer catch cannot be located.
    """
    handler_body = _extract_deno_serve_handler_body(source)
    if not handler_body:
        return ""

    # The outer catch is the LAST 'catch' in the handler body: the
    # inner ``try { ... }`` block closes with ``} catch (err) { ... }``
    # and there are no other catches in the handler body.
    catch_matches = list(re.finditer(r"\}\s*catch\s*\(", handler_body))
    if not catch_matches:
        return ""
    last = catch_matches[-1]

    # The opening '{' of the catch block comes right after the
    # ``catch (err)`` parameter list.
    after_catch = handler_body[last.end() :]
    open_brace_match = re.search(r"\{", after_catch)
    if not open_brace_match:
        return ""
    brace_start = last.end() + open_brace_match.start()

    close_pos = _find_matching_close(handler_body, brace_start, "{", "}")
    if close_pos <= brace_start:
        return ""
    return handler_body[brace_start + 1 : close_pos]


# ── AC-3 — Outer handler catch must mark document as failed ──────────────


def test_b3_handler_catch_fails_document_on_timeout():
    """AC-3 do B-3 — O ``catch (err) { ... }`` externo do handler
    ``Deno.serve`` (em ``supabase/functions/process-document/index.ts``,
    DEPOIS do ``Promise.race([processDocument(...), catchUnload()])``)
    PRECISA executar ``UPDATE vector_db.documents SET status = 'failed'``
    e popular ``error_message`` quando o ``catchUnload()`` vence a race
    (timeout) ou quando qualquer outro erro escapa do try interno de
    ``processDocument()``.

    HOJE (RED): o catch externo (linhas 744-750) so faz
    ``console.error(...)`` e retorna HTTP 500.  Nao toca no banco.
    Resultado: quando o isolate do Deno eh terminado (timeout, deploy,
    cold start ruim), o documento fica TRAVADO em
    ``status='processing'`` para sempre — o frontend faz polling
    infinito, o usuario nunca ve a falha, e o documento vira orfao.

    Para fechar AC-3, o catch externo precisa:
      1. Executar ``UPDATE vector_db.documents SET status = 'failed',
         error_message = <msg> WHERE id = <document_id>`` antes de
         retornar 500.
      2. Usar o ``document_id`` extraido do body da request (linha 703)
         para identificar qual linha atualizar.
    """
    source = _load_source()

    # Sanity: the handler must use Promise.race with catchUnload.
    # Without the race, this test's gap is moot (the document would
    # be stuck for a different reason — infinite chunk loop), so we
    # pin that contract here too.
    assert "Promise.race" in source and "catchUnload()" in source, (
        "Sanity check failed: o handler `Deno.serve` em "
        f"{PROCESS_DOC_PATH} NAO usa `Promise.race([processDocument(...), "
        "catchUnload()])`. Sem essa race, um loop travado no pipeline "
        "deixa o documento preso em 'processing' por motivo diferente, "
        "entao este teste (AC-3 do B-3) so faz sentido se a race existir."
    )

    # Extract the OUTER catch block (the one that wraps the request
    # processing including the Promise.race with catchUnload).
    catch_body = _extract_outer_catch_in_handler(source)
    assert catch_body, (
        "Could not extract the outer `catch (err) { ... }` block from "
        f"the `Deno.serve` handler in {PROCESS_DOC_PATH}. The handler "
        "must be of the form `Deno.serve(async (req: Request) => { ... "
        "})` with an outer `try { ... } catch (err) { ... }` that wraps "
        "the entire request processing, including the "
        "`Promise.race([processDocument(...), catchUnload()])`."
    )

    # (1) The outer catch must execute an UPDATE that sets status='failed'.
    # If this assertion fails, the document is left in 'processing' on
    # timeout — the exact gap AC-3 is about.
    assert "UPDATE" in catch_body and "status = 'failed'" in catch_body, (
        "AC-3 do B-3 violada (RED): o catch externo do handler "
        "`Deno.serve` em `supabase/functions/process-document/index.ts` "
        "(o catch DEPOIS do `Promise.race([processDocument(...), "
        "catchUnload()])`) NAO executa "
        "`UPDATE vector_db.documents SET status = 'failed'`. "
        "\n\n"
        "Hoje o catch externo so faz `console.error(...)` e retorna "
        "HTTP 500, sem tocar no banco. Quando o `catchUnload()` vence "
        "a race (Deno isolate sendo terminado / timeout), a rejeicao "
        "sobe ate esse catch externo e o documento fica TRAVADO em "
        "`status='processing'` para sempre — o frontend fica em loop "
        "de polling e o usuario nunca ve a falha. "
        "\n\n"
        "Para fechar AC-3, o catch externo precisa fazer algo como:\n"
        "  await supabase\n"
        "    .from('documents')\n"
        "    .update({ status: 'failed', error_message: err.message })\n"
        "    .eq('id', document_id);\n"
        "antes de retornar `json({ error: 'Internal error', ... }, 500)`."
    )

    # (2) The outer catch must populate `error_message` so the UI /
    # operators can see WHY the document failed (otherwise the user
    # sees a generic 'processamento falhou' with no root cause).
    assert "error_message" in catch_body, (
        "AC-3 do B-3 violada (RED): o catch externo do handler "
        "`Deno.serve` NAO popula `error_message` no UPDATE do documento. "
        "Sem isso, o frontend mostra apenas 'processamento falhou' sem "
        "causa raiz e a equipe de suporte nao consegue diagnosticar a "
        "falha. O catch externo precisa gravar "
        "`error_message = err.message` (ou string equivalente derivada "
        "do erro) para que operadores e usuarios consigam ver POR QUE "
        "o documento falhou."
    )
