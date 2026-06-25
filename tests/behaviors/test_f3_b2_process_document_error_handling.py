"""RED test for behavior F-3-B2 — Tratamento de erro com timeout no
``process-document`` EF: documentos simples nao devem ficar presos em
``'processing'`` se a EF falhar.

GOAL:
    AC#1 — ``supabase/functions/process-document/index.ts`` MUST validate
    the three required env vars (``CO_API_KEY``, ``SUPABASE_URL``,
    ``SUPABASE_SERVICE_ROLE_KEY``) at module top level and throw a clear
    error if any are missing — instead of relying on the
    ``Deno.env.get('...')!`` non-null assertion that silently produces
    ``undefined`` at runtime and causes the document to be stuck in
    ``status: 'processing'`` forever.

    AC#2 — Inside ``processDocument()`` the ``catch`` block MUST update
    ``vector_db.documents`` to ``status: 'failed'`` with ``error_message``
    populated, so the frontend can show the user that the document failed
    rather than polling forever.

    AC#3 — ``apps/blu_v3/src/services/knowledgeBaseService.ts``
    ``uploadSimpleFile()`` MUST catch errors from
    ``supabase.functions.invoke('process-document', ...)`` and re-throw
    with a Portuguese message, so the React UI surfaces a meaningful
    error to the user.

BEHAVIOR:
    F-3-B2 — Tratamento de erro com timeout no process-document EF.

    Symptom (from production): simple files get stuck in
    ``status: 'processing'`` indefinitely.  Two possible root causes:

    1. The EF never started (env var missing → ``undefined`` is used as
       a Bearer token → Cohere call returns 401 → exception → BUT the
       document is only marked ``failed`` inside the ``try`` block of
       ``processDocument()``; if the failure happens *before* the
       ``try`` (e.g. an undefined client construction), the document
       stays ``'processing'``).
    2. The EF ran, the document was marked ``completed`` server-side,
       but the frontend swallowed the error and never re-fetched.

    The fix is two-pronged: validate env vars at module top level (so
    failures happen BEFORE any DB record is created) AND ensure the
    ``catch`` block at the bottom of ``processDocument()`` is
    comprehensive (AC#2 — already in place, this test just pins the
    contract).  On the frontend side (AC#3 — already in place at
    lines 184-194, this test pins the contract), the error from the EF
    must be re-thrown with a Portuguese message.

AC (Acceptance Criteria):
    AC#1 — EF top-level validation of ``CO_API_KEY``, ``SUPABASE_URL``,
           ``SUPABASE_SERVICE_ROLE_KEY`` (throw clear error if missing).
    AC#2 — ``catch`` block in ``processDocument()`` UPDATEs the document
           to ``status: 'failed'`` with ``error_message`` populated.
    AC#3 — ``uploadSimpleFile()`` checks ``if (fnError) throw new Error(...)``
           after ``supabase.functions.invoke('process-document', ...)``.

Anti-Goals (must NOT be violated):
    1. NAO mover a validacao para dentro do handler HTTP — ela deve
       ocorrer no top-level do modulo para que erros de configuracao
       sejam detectados ANTES de qualquer chamada ao EF.
    2. NAO remover o ``catch`` de ``processDocument()`` — ele eh a rede
       de seguranca para falhas de runtime (Cohere, Ollama, postgres).
    3. NAO remover a checagem ``if (fnError)`` em ``uploadSimpleFile()``
       — sem ela a UI mostra "upload feito" mesmo quando o EF falhou.

Estado atual: RED — AC#1 validation is MISSING (only ``Deno.env.get(...)!``
non-null assertions exist at lines 19, 20, 72, 78).  AC#2 and AC#3 are
already implemented; the corresponding tests are expected to PASS
(False RED — they pin existing behavior so a regression breaks the
build).

The tests are pure source inspection (regex on the TypeScript text).
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

EF_PROCESS_DOCUMENT_PATH = (
    REPO_ROOT
    / "supabase"
    / "functions"
    / "process-document"
    / "index.ts"
)

KB_SERVICE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "services"
    / "knowledgeBaseService.ts"
)


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure source inspection, no DB teardown."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _load_ef_source() -> str:
    """Load ``supabase/functions/process-document/index.ts`` as plain text."""
    assert EF_PROCESS_DOCUMENT_PATH.exists(), (
        f"Source file not found: {EF_PROCESS_DOCUMENT_PATH}"
    )
    return EF_PROCESS_DOCUMENT_PATH.read_text()


def _load_kb_source() -> str:
    """Load ``knowledgeBaseService.ts`` as plain text."""
    assert KB_SERVICE_PATH.exists(), (
        f"Source file not found: {KB_SERVICE_PATH}"
    )
    return KB_SERVICE_PATH.read_text()


def _extract_function_body(source: str, func_name: str) -> str:
    """Return the body text of the first ``function <func_name>(...)``.

    Mirrors the brace-depth walker used in ``test_bkl_041`` so that the
    EF inspection logic and the KB-service inspection logic share the
    same primitives.  Strings (single, double, backtick) and comments
    (line ``//`` and block ``/* */``) are tracked so braces inside them
    are not miscounted.  Template-literal expressions (``${...}``) are
    tracked as nested brace contexts so they also don't break the depth
    count.

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
    # up to the next ``{`` (the start of the function body).  TypeScript
    # generics can contain ``<`` and ``>`` but no ``{`` inside.
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


# ── AC#1 — Top-level env var validation (RED — missing in source) ────────


# Env var tokens that must be explicitly validated at module top level.
# Reading them with ``Deno.env.get(...)!`` is NOT validation — the ``!``
# is erased at runtime and ``undefined`` propagates silently.
_REQUIRED_ENV_VARS = ("CO_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")


def _has_explicit_validation(source: str, env_var: str) -> bool:
    """Return True iff the source contains an explicit guard for ``env_var``.

    We accept any of these idiomatic patterns:

    * ``if (!<env_var>) throw ...``
    * ``if (!<env_var> || ...) throw ...``
    * ``if (<env_var> === undefined) throw ...``
    * ``if (<env_var> == null) throw ...``
    * ``if (typeof <env_var> !== "string") throw ...``

    The non-null assertion ``Deno.env.get('<env_var>')!`` does NOT
    count — at runtime it produces ``undefined`` when the var is
    missing, exactly the bug we are guarding against.
    """
    # Strip all non-null assertion reads so they don't pollute the match.
    # The pattern ``Deno.env.get("X")!`` or ``Deno.env.get('X')!`` is
    # removed entirely before searching.
    stripped = re.sub(
        r"Deno\.env\.get\(\s*['\"]" + re.escape(env_var) + r"['\"]\s*\)\s*!",
        "/* non-null read of " + env_var + " — does NOT count as validation */",
        source,
    )

    # Pattern 1: ``if (!X)`` / ``if (!X || ...)`` directly.
    if re.search(
        rf"if\s*\(\s*!\s*{re.escape(env_var)}\b",
        stripped,
    ):
        return True
    # Pattern 2: ``if (X === undefined)`` / ``==``.
    if re.search(
        rf"if\s*\(\s*{re.escape(env_var)}\s*={1,2}=\s*undefined\b",
        stripped,
    ):
        return True
    # Pattern 3: ``if (X == null)``.
    if re.search(
        rf"if\s*\(\s*{re.escape(env_var)}\s*==\s*null\b",
        stripped,
    ):
        return True
    # Pattern 4: ``if (typeof X !== "string")`` (or single quotes).
    if re.search(
        rf"if\s*\(\s*typeof\s+{re.escape(env_var)}\s*!==\s*['\"]string['\"]",
        stripped,
    ):
        return True
    return False


def test_f3_b2_ef_validates_co_api_key_at_module_top_level():
    """AC#1 — ``process-document`` MUST explicitly validate ``CO_API_KEY``.

    The current code only does
    ``const CO_API_KEY = Deno.env.get("CO_API_KEY")!;`` (line 72).  The
    ``!`` is a TypeScript non-null assertion: it is erased at runtime,
    so if ``CO_API_KEY`` is unset, ``CO_API_KEY`` becomes ``undefined``
    and is silently used as a Bearer token, producing a confusing 401
    from Cohere.  The EF must instead throw a clear error at module
    top level when ``CO_API_KEY`` is missing.
    """
    source = _load_ef_source()
    assert _has_explicit_validation(source, "CO_API_KEY"), (
        "AC#1 violada: `process-document` NAO valida `CO_API_KEY` no "
        "top-level do modulo. A unica referencia a `CO_API_KEY` no source "
        "eh `Deno.env.get(\"CO_API_KEY\")!` (linha 72), que eh apenas "
        "uma assercao de TypeScript e NAO validacao em runtime. "
        "Comportamento F-3-B2 exige que a EF lance um erro claro (ex.: "
        "`if (!CO_API_KEY) throw new Error(\"CO_API_KEY nao configurada\");`) "
        "no inicio do modulo, ANTES de qualquer chamada a API externa, "
        "para que erros de configuracao sejam detectados imediatamente "
        "em vez de produzirem documentos presos em `status: 'processing'`."
    )


def test_f3_b2_ef_validates_supabase_url_at_module_top_level():
    """AC#1 — ``process-document`` MUST explicitly validate ``SUPABASE_URL``.

    Same rationale as ``CO_API_KEY``: the non-null assertion at line 19
    is erased at runtime, so an unset ``SUPABASE_URL`` produces a
    client pointed at ``undefined`` and the document is never updated
    past ``'processing'``.
    """
    source = _load_ef_source()
    assert _has_explicit_validation(source, "SUPABASE_URL"), (
        "AC#1 violada: `process-document` NAO valida `SUPABASE_URL` no "
        "top-level do modulo. A unica referencia a `SUPABASE_URL` no "
        "source eh `Deno.env.get(\"SUPABASE_URL\")!` (linha 19), que NAO "
        "faz validacao em runtime. Comportamento F-3-B2 exige validacao "
        "explicita (ex.: `if (!SUPABASE_URL) throw new Error(...)`) para "
        "que a configuracao ausente seja detectada no startup da EF."
    )


def test_f3_b2_ef_validates_service_role_key_at_module_top_level():
    """AC#1 — ``process-document`` MUST explicitly validate
    ``SUPABASE_SERVICE_ROLE_KEY``.

    Same rationale as the other two.  Without the service-role key the
    supabase client cannot UPDATE ``vector_db.documents`` from inside
    the ``catch`` block (AC#2), so the document stays in
    ``'processing'`` forever — exactly the symptom F-3-B2 is about.
    """
    source = _load_ef_source()
    assert _has_explicit_validation(source, "SUPABASE_SERVICE_ROLE_KEY"), (
        "AC#1 violada: `process-document` NAO valida "
        "`SUPABASE_SERVICE_ROLE_KEY` no top-level do modulo. A unica "
        "referencia no source eh `Deno.env.get(\"SUPABASE_SERVICE_ROLE_KEY\")!` "
        "(linha 20), que NAO faz validacao em runtime. Comportamento "
        "F-3-B2 exige validacao explicita para detectar a ausencia dessa "
        "variavel — sem ela, o `catch` que faz `UPDATE status = 'failed' "
        "(AC#2) tambem falha, e o documento fica preso em "
        "`status: 'processing'`."
    )


def test_f3_b2_ef_validation_occurs_before_external_api_calls():
    """AC#1 — The env-var validation must run BEFORE any external call.

    The whole point of top-level validation is to fail fast at module
    load.  If the validation happens only inside the HTTP handler (or,
    worse, only after the document is already inserted in
    ``'processing'``), the symptom of the bug persists.

    This test ensures the validation is co-located with the ``const``
    declarations at the top of the module rather than buried inside
    ``Deno.serve`` or the catch block.
    """
    source = _load_ef_source()

    # Find the line number of the first `Deno.env.get` read for any of
    # the required vars.  That's where the validation must live (or
    # before, since multiple `const` declarations precede `Deno.serve`).
    first_read_line = None
    for line_no, line in enumerate(source.splitlines(), start=1):
        if re.search(
            r"Deno\.env\.get\(\s*['\"](?:CO_API_KEY|SUPABASE_URL|SUPABASE_SERVICE_ROLE_KEY)['\"]",
            line,
        ):
            first_read_line = line_no
            break
    assert first_read_line is not None, (
        "Sanity check failed: nao foi possivel localizar nenhum "
        "`Deno.env.get(...)` para CO_API_KEY, SUPABASE_URL ou "
        "SUPABASE_SERVICE_ROLE_KEY no source do `process-document`."
    )

    # Find any explicit validation lines for the required vars.
    validation_line_numbers = []
    for line_no, line in enumerate(source.splitlines(), start=1):
        for env_var in _REQUIRED_ENV_VARS:
            # Strip non-null reads of THIS specific var so they don't
            # count as "validation" for the test.
            cleaned = re.sub(
                r"Deno\.env\.get\(\s*['\"]" + re.escape(env_var) + r"['\"]\s*\)\s*!",
                "",
                line,
            )
            if _has_explicit_validation(cleaned, env_var):
                validation_line_numbers.append((line_no, env_var, line.strip()))
                break

    assert validation_line_numbers, (
        "AC#1 violada: nenhuma validacao explicita para "
        f"{', '.join(_REQUIRED_ENV_VARS)} foi encontrada no source do "
        "`process-document`. Comportamento F-3-B2 exige que essas "
        "variaveis sejam validadas no top-level do modulo."
    )

    # All validation lines must come BEFORE the first HTTP handler
    # (`Deno.serve`) — they must be module-load checks, not request
    # handlers.
    handler_match = re.search(r"^\s*Deno\.serve\s*\(", source, re.MULTILINE)
    assert handler_match is not None, (
        "Sanity check failed: nao foi possivel localizar `Deno.serve` no "
        "source do `process-document`."
    )
    handler_line = source[: handler_match.start()].count("\n") + 1

    for line_no, env_var, _stripped in validation_line_numbers:
        assert line_no < handler_line, (
            f"AC#1 violada: a validacao explicita de `{env_var}` na "
            f"linha {line_no} ocorre DEPOIS de `Deno.serve` (linha "
            f"{handler_line}). Comportamento F-3-B2 exige que a "
            "validacao ocorra no top-level do modulo, ANTES do HTTP "
            "handler, para falhar rapido no startup da EF."
        )


# ── AC#2 — catch block updates document to 'failed' (pins existing) ─────


def test_f3_b2_ef_catch_block_marks_document_as_failed():
    """AC#2 — ``processDocument()`` ``catch`` block UPDATEs the document
    to ``status: 'failed'`` with ``error_message`` populated.

    This is the safety net for runtime failures inside
    ``processDocument()`` (Cohere 5xx, Ollama timeout, postgres
    connection drop, etc.).  Without it the document sits in
    ``'processing'`` forever and the user never sees an error.

    This test pins the existing implementation (lines 629-641) so that
    a future refactor cannot silently remove this safety net.
    """
    source = _load_ef_source()

    # Locate the body of `processDocument` so we can scope the search to
    # the function that actually performs the work.
    body = _extract_function_body(source, "processDocument")
    assert body, (
        "Could not extract body of `processDocument` from "
        f"{EF_PROCESS_DOCUMENT_PATH}. The function may be missing, the "
        "pattern `function processDocument(` may not match (e.g. "
        "because of a rename), or the brace-counting failed "
        "(unbalanced braces)."
    )

    assert "catch" in body, (
        "AC#2 violada: `processDocument` nao possui bloco `catch`. "
        "Comportamento F-3-B2 exige que excecoes lancadas durante o "
        "processamento (chamada ao Cohere, chamada ao Ollama, insert no "
        "postgres, etc.) sejam capturadas e o documento seja marcado "
        "como `status: 'failed'` para que a UI possa informar o usuario."
    )

    assert "UPDATE" in body and "status = 'failed'" in body, (
        "AC#2 violada: o bloco `catch` de `processDocument` NAO executa "
        "`UPDATE vector_db.documents SET status = 'failed'`. "
        "Comportamento F-3-B2 exige que, quando uma excecao eh "
        "capturada, o documento correspondente seja atualizado para "
        "`status: 'failed'` para que a UI nao mostre o documento como "
        "ainda em processamento."
    )

    # The UPDATE must also populate `error_message` so the user (and
    # support team) can see WHY the document failed.
    assert "error_message" in body, (
        "AC#2 violada: o bloco `catch` de `processDocument` NAO "
        "popula `error_message` no UPDATE. Comportamento F-3-B2 exige "
        "que a mensagem da excecao (ou uma string derivada dela) seja "
        "gravada em `vector_db.documents.error_message` para que a UI "
        "possa exibir a causa da falha ao usuario."
    )


# ── AC#3 — Frontend catches EF invocation errors (pins existing) ─────────


def test_f3_b2_frontend_upload_simple_file_catches_function_error():
    """AC#3 — ``uploadSimpleFile()`` must check ``if (fnError) throw ...``
    after ``supabase.functions.invoke('process-document', ...)``.

    Without this check, a 4xx/5xx response from the EF (e.g. a missing
    env var returning 500) is silently ignored by the frontend, the
    insert was already done with ``status: 'processing'``, and the UI
    tells the user "upload feito" — even though the document will
    never be processed.  The check exists today (lines 184-194) and
    this test pins that contract.
    """
    source = _load_kb_source()
    body = _extract_function_body(source, "uploadSimpleFile")
    assert body, (
        "Could not extract body of `uploadSimpleFile` from "
        f"{KB_SERVICE_PATH}. The function may be missing, the pattern "
        "`function uploadSimpleFile(` may not match (e.g. because of a "
        "rename), or the brace-counting failed (unbalanced braces)."
    )

    # Step 1: the function must call the `process-document` EF.
    invoke_match = re.search(
        r"supabase\.functions\.invoke\s*\(\s*['\"]([^'\"]+)['\"]",
        body,
    )
    assert invoke_match is not None, (
        "AC#3 violada: `uploadSimpleFile` NAO chama "
        "`supabase.functions.invoke('...')`. Comportamento F-3-B2 "
        "exige que o upload de arquivos simples delegue o "
        "processamento para a Edge Function `process-document`."
    )
    assert invoke_match.group(1) == "process-document", (
        f"AC#3 violada: `uploadSimpleFile` chama "
        f"`supabase.functions.invoke('{invoke_match.group(1)}', ...)` "
        "mas o comportamento F-3-B2 exige que a EF invocada seja "
        "`process-document`."
    )

    # Step 2: the function must check the EF's `error` field. We
    # accept any of these idiomatic patterns (current code uses the
    # first one — lines 184-194):
    #
    #   const { error: fnError } = await supabase.functions.invoke(...)
    #   if (fnError) throw new Error(`Erro ao processar documento: ${fnError.message}`)
    #
    # or:
    #
    #   const { data, error: fnError } = await supabase.functions.invoke(...)
    #   if (fnError) { ... }
    assert re.search(
        r"(?:const|let)\s*\{\s*[^}]*\berror\s*:\s*fnError\b",
        body,
    ), (
        "AC#3 violada: `uploadSimpleFile` NAO extrai o campo `error` "
        "(renomeado para `fnError`) do retorno de "
        "`supabase.functions.invoke('process-document', ...)`. "
        "Comportamento F-3-B2 exige que esse erro seja capturado "
        "para que falhas da EF nao passem despercebidas pelo frontend."
    )

    assert re.search(
        r"if\s*\(\s*fnError\s*\)\s*throw\b",
        body,
    ), (
        "AC#3 violada: `uploadSimpleFile` NAO possui "
        "`if (fnError) throw ...` apos a invocacao da EF "
        "`process-document`. Comportamento F-3-B2 exige que o erro "
        "retornado pela EF seja re-lancado como `Error` (idealmente "
        "com mensagem em portugues, ex.: `Erro ao processar "
        "documento: ${fnError.message}`) para que a UI mostre a "
        "falha ao usuario em vez de silenciosamente deixar o "
        "documento preso em `status: 'processing'`."
    )
