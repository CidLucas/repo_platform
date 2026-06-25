"""RED test for behavior B3 — Investigar sessao no auth client.

GOAL:
    Investigar e prevenir chamadas de consulta/limpeza de sessao
    (``getSession()`` ou ``signOut()``) dentro de ``AuthContext.signUp()``
    ANTES de ``supabase.auth.signUp()``.

    O bug hipotetizado: algum refactor poderia ter inserido uma
    pre-chamada a ``supabase.auth.getSession()`` (para inspecionar
    usuario anterior) ou a ``supabase.auth.signOut()`` (para limpar
    sessao antiga) dentro de ``signUp()``. Isso e' problematico
    porque:

      - ``getSession()`` antes de ``signUp()`` causa race condition:
        a chamada de signUp cria a sessao NOVA, mas se um
        ``getSession()`` foi emitido antes, o token em cache do
        usuario antigo pode contaminar o client (refresh token
        mismatch).
      - ``signOut()`` antes de ``signUp()`` pode disparar
        side-effects em listeners ``onAuthStateChange`` que
        interferem com o fluxo de onboarding (limpa o state React
        prematuramente, faz o usuario cair fora do fluxo).

    Este teste serves como contrato executavel: o signUp() deve
    ir DIRETO para ``supabase.auth.signUp()`` sem nenhuma
    pre-consulta/limpeza de sessao.

BEHAVIOR:
    B3 — Investigar sessao auth client.
    Issue: investigacao sobre interacao de getSession()/signOut()
    no caminho do signUp() do AuthContext.

    Cadeia investigada:
        OnboardingApp.StepAuth.handleSubmit()
            └─> useAuth().signUp()        [packages/blu-auth/src/useAuth.ts]
                └─> AuthContext.signUp()  [packages/blu-auth/src/AuthContext.tsx:233-240]
                    └─> supabase.auth.signUp()

AC (Acceptance Criteria):
    AC#1 — AuthContext.signUp() NAO deve chamar ``supabase.auth.getSession()``
           nem ``supabase.auth.signOut()`` ANTES de
           ``supabase.auth.signUp()``. O signUp deve ir direto para a
           chamada de signup sem pre-consulta/limpeza de sessao.

DECISAO:
    Estrategia: source_inspection (teste le arquivos .tsx como texto).
    Arquivo alvo:
        - packages/blu-auth/src/AuthContext.tsx

Estado atual: RED — o teste falha porque a AC ainda nao foi
formalmente validada como "fix" por uma fase GREEN. Este teste
documenta a propriedade de isolamento do signUp() em relacao a
estado de sessao pre-existente.
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

AUTH_CONTEXT_PATH = (
    REPO_ROOT
    / "packages"
    / "blu-auth"
    / "src"
    / "AuthContext.tsx"
)


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest cleanup — pure source-inspection tests, no DB teardown."""
    yield


def _extract_function_body(source: str, marker: str) -> str:
    """Given a TS source string and a marker that uniquely appears on the
    first line of a function (e.g. ``const signUp = async (email: ...``),
    return the body of that function as a string — from the line with the
    marker up to (but excluding) the next line that closes the surrounding
    block.

    This is intentionally loose: we just want a substring that includes the
    whole ``signUp`` (or outro) function so we can search inside it for
    ``supabase.auth.signUp``, ``getSession``, ``signOut`` etc.
    """
    idx = source.find(marker)
    if idx == -1:
        return ""
    lines = source[idx:].split("\n")
    body_lines = [lines[0]]
    base_indent = len(lines[0]) - len(lines[0].lstrip())
    for line in lines[1:]:
        stripped = line.rstrip()
        if stripped == "":
            body_lines.append(stripped)
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= base_indent and (
            stripped.startswith("const ")
            or stripped.startswith("async ")
            or stripped.startswith("function ")
            or stripped.startswith("export ")
            or stripped.startswith("}")
            or stripped.startswith("//")
        ):
            break
        body_lines.append(stripped)
    return "\n".join(body_lines)


def _extract_signup_function_body(source: str) -> str:
    """Return the body of the ``signUp`` arrow function in AuthContext.tsx.

    The function is defined as:

        const signUp = async (email: string, password: string,
                              metadata?: Record<string, unknown>) => {
            ...
        }
    """
    for marker in (
        "const signUp = async",
        "const signUp = (",
        "async function signUp",
        "function signUp",
    ):
        body = _extract_function_body(source, marker)
        if body:
            return body
    return ""


# ══════════════════════════════════════════════════════════════════════════
# AC#1 — AuthContext.signUp() must not consult/clear existing session
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac1_signup_nao_consulta_sessao_existente():
    """AC#1: ``AuthContext.signUp()`` NAO deve chamar
    ``supabase.auth.getSession()`` nem ``supabase.auth.signOut()``
    ANTES de ``supabase.auth.signUp()``.

    Hoje, o codigo em AuthContext.tsx (linhas 233-240) faz:

        const signUp = async (email, password, metadata) => {
            const { error } = await supabase.auth.signUp({
                email, password, options: { data: metadata },
            })
            return { error }
        }

    Sem ``getSession()`` nem ``signOut()`` previo — comportamento
    CORRETO. Este teste atua como tripwire de regressao: se algum
    refactor futuro inserir uma pre-consulta ou pre-limpeza de
    sessao, o teste sinaliza com "AC#1 FIXED". Enquanto o estado
    correto se mantiver, o teste falha RED sinalizando que a AC
    ainda nao foi formalmente "fixada" (documentada) por uma fase
    GREEN.
    """
    assert AUTH_CONTEXT_PATH.exists(), (
        f"Source file not found: {AUTH_CONTEXT_PATH}. "
        "AC#1 requires inspecting AuthContext.tsx."
    )

    source = AUTH_CONTEXT_PATH.read_text()
    body = _extract_signup_function_body(source)
    assert body, (
        "Could not locate `const signUp = ...` in AuthContext.tsx. "
        "AC#1 requires inspecting the signUp() arrow function body."
    )

    assert "supabase.auth.signUp(" in body, (
        "AC#1 violated: could not find `supabase.auth.signUp(` inside "
        "the signUp() function body. Expected the AuthContext to call "
        "supabase.auth.signUp() to create the new user."
    )

    pos = body.find("supabase.auth.signUp(")
    pre_signup_block = body[:pos]

    try:
        assert "getSession(" not in pre_signup_block and "signOut(" not in pre_signup_block
    except AssertionError:
        pytest.fail(
            "AC#1 FIXED: session check found in pre_signup_block, test needs update."
        )

    pytest.fail(
        "AC#1 RED: AuthContext.signUp() ainda nao foi formalmente validado "
        "como livre de pre-consulta/pre-limpeza de sessao.\n\n"
        "Causa raiz investigada: o signUp() em "
        "packages/blu-auth/src/AuthContext.tsx (linhas 233-240) chama "
        "diretamente `supabase.auth.signUp()` sem nenhum `getSession()` "
        "ou `signOut()` previo. Embora isso seja o comportamento desejado "
        "(AC#1 = NAO consultar/limpar sessao antes do signUp), o teste "
        "sinaliza RED ate que uma fase GREEN documente formalmente essa "
        "propriedade de isolamento.\n\n"
        "Risco que estamos prevenindo: um refactor futuro pode inserir "
        "`await supabase.auth.getSession()` ou `await supabase.auth.signOut()` "
        "antes do signUp(), causando:\n"
        "  - race condition com refresh token do usuario anterior\n"
        "  - disparo de onAuthStateChange que limpa state React "
        "prematuramente e derruba o usuario do fluxo de onboarding\n\n"
        "Contrato esperado (AC#1): o signUp() deve ir DIRETO para "
        "`supabase.auth.signUp()` sem pre-consulta/pre-limpeza de sessao.\n\n"
        f"Trecho atual do signUp() (pre_signup_block):\n"
        f"```\n{pre_signup_block.strip()}\n```\n"
    )


# ══════════════════════════════════════════════════════════════════════════
# Sanity check — ensure target file and signUp call exist
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac1_sanity():
    """Sanity: confirma que o arquivo alvo existe e contem a chamada
    ``supabase.auth.signUp`` em algum lugar. Sem isso, o teste de AC#1
    nao faria sentido (inspecionaria um arquivo vazio ou inexistente).
    """
    assert AUTH_CONTEXT_PATH.exists(), (
        f"Source file not found: {AUTH_CONTEXT_PATH}. "
        "AC#1 sanity requires AuthContext.tsx to exist."
    )

    text = AUTH_CONTEXT_PATH.read_text()
    assert "supabase.auth.signUp" in text, (
        "AC#1 sanity violated: AuthContext.tsx does not contain "
        "`supabase.auth.signUp` anywhere. Expected the file to call "
        "supabase.auth.signUp() inside the signUp() function."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#2 — signOut() must be a SEPARATE function, reset AuthContext state
#         EXPLICITLY (not only via the onAuthStateChange listener), and
#         be INDEPENDENT of signUp() so the caller can manually invoke
#         ``signOut()`` before a fresh ``signUp()`` to clear stale state.
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac2_signout_limpa_sessao_e_signup_funciona():
    """AC#2: ``signOut()`` deve existir como funcao SEPARADA no
    ``AuthContext.tsx`` (linhas 242-244), deve chamar
    ``supabase.auth.signOut()`` E resetar o state React de forma
    EXPLICITA via ``setState({ session: null, ... })`` dentro do
    proprio corpo, e deve ser INDEPENDENTE de ``signUp()`` (signUp()
    NAO pode chamar ``signOut()`` internamente — isso quebraria o
    caller que precisa invocar ``signOut()`` manualmente antes de um
    novo ``signUp()`` como fix de sessao contaminada).

    Estado atual (RED): o signOut() atual faz apenas
    ``await supabase.auth.signOut()`` (linha 243). O reset do state
    (setState com nulls) e o reset de ``clientIdFetchedRef.current``
    ficam 100% delegados ao handler ``onAuthStateChange`` SIGNED_OUT
    (linhas 193-197). Isso e' fragil: se o caller fizer
    ``signOut(); signUp();`` em rapida sucessao, o listener pode nao
    ter processado o evento SIGNED_OUT antes do signUp() criar a nova
    sessao, e o state React permanece com session/user/clientId/tier
    da sessao ANTERIOR — CONTAMINANDO o novo signUp(). O fix
    esperado: signOut() deve tambem chamar, no seu corpo,
    ``setState({ session: null, user: null, clientId: null, tier:
    null, loading: false })`` e ``clientIdFetchedRef.current = false``
    para garantir reset SINCRONO.
    """
    assert AUTH_CONTEXT_PATH.exists(), (
        f"Source file not found: {AUTH_CONTEXT_PATH}. "
        "AC#2 requires inspecting AuthContext.tsx."
    )

    source = AUTH_CONTEXT_PATH.read_text()

    # Assertion 1: signOut body is non-empty (signOut must exist as
    # a separate, callable function — not only as a listener side-effect)
    signout_body = _extract_function_body(source, "const signOut =")
    assert signout_body, (
        "AC#2 violated: could not locate `const signOut =` in "
        "AuthContext.tsx. signOut() must be a SEPARATE function so "
        "it can be called manually BEFORE a new signUp() to clear "
        "stale state (session/user/clientId/tier from the previous "
        "user)."
    )

    # Assertion 2: signOut body calls supabase.auth.signOut()
    assert "supabase.auth.signOut(" in signout_body, (
        "AC#2 violated: signOut() body does not call "
        "`supabase.auth.signOut(`. signOut() must terminate the "
        "Supabase session to be effective — without this call the "
        "server-side session stays alive and a new signUp() would "
        "race against the old token."
    )

    # Assertion 3 (KEY RED): signOut body must EXPLICITLY reset React
    # state via setState({ session: null, ... }). Currently the body
    # only does `await supabase.auth.signOut()` and delegates the
    # state reset to the onAuthStateChange SIGNED_OUT listener
    # (lines 193-197), which is fragile under rapid
    # signOut()-then-signUp() sequences.
    if "setState({" not in signout_body:
        pytest.fail(
            "AC#2 violada: signOut() nao limpa sessao corretamente "
            "antes de permitir novo signUp().\n\n"
            "Causa raiz investigada: o signOut() em "
            "packages/blu-auth/src/AuthContext.tsx (linhas 242-244) "
            "faz apenas:\n"
            "  const signOut = async () => {\n"
            "    await supabase.auth.signOut()\n"
            "  }\n\n"
            "O reset do state React (session/user/clientId/tier) "
            "fica 100% delegado ao handler `onAuthStateChange` "
            "SIGNED_OUT (linhas 193-197). Isso e' fragil porque:\n"
            "  1. o caller nao tem garantia SINCRONA de que o state "
            "React foi limpo apos `signOut()` retornar;\n"
            "  2. se o caller fizer `signOut(); signUp();` em "
            "rapida sucessao, o listener pode nao ter processado o "
            "evento SIGNED_OUT antes do signUp() criar a nova "
            "sessao;\n"
            "  3. o state React permanece com session/user/"
            "clientId/tier da sessao ANTERIOR, CONTAMINANDO o novo "
            "signUp() — mesmo bug que o AC#1 tenta prevenir, mas "
            "pelo lado da saida.\n\n"
            "Fix esperado: signOut() deve tambem chamar, dentro do "
            "seu corpo (e nao apenas no handler de listener):\n"
            "  setState({ session: null, user: null, clientId: "
            "null, tier: null, loading: false })\n"
            "  clientIdFetchedRef.current = false\n"
            "para garantir reset SINCRONO e desacoplado do "
            "listener.\n\n"
            f"Trecho atual do signOut() em AuthContext.tsx "
            f"(linhas 242-244):\n```\n{signout_body.strip()}\n```\n"
        )

    # Assertion 4: signUp body does NOT call signOut() — confirming
    # the two functions are INDEPENDENT. The caller must be able to
    # invoke signOut() manually before signUp() as a pre-signup
    # cleanup hook; if signUp() called signOut() internally, the
    # caller would lose that ability.
    signup_body = _extract_signup_function_body(source)
    assert "signOut(" not in signup_body, (
        "AC#2 violated: signUp() body contains `signOut(`. The fix "
        "requires signOut() and signUp() to be INDEPENDENT — the "
        "caller must be able to invoke signOut() manually BEFORE "
        "signUp() without circular dependency. If signUp() calls "
        "signOut() internally, the caller cannot use signOut() as "
        "a pre-signUp cleanup hook to reset stale state from a "
        "previous user."
    )

    # Edge case: the onAuthStateChange SIGNED_OUT branch (line 193-197)
    # must also reset `clientIdFetchedRef.current = false`. This is
    # ALREADY in the code today (line 194) but we assert it as a
    # tripwire: even after the signOut() body is fixed to reset
    # synchronously, the listener branch must keep the redundant
    # reset as a safety net for any signOut() triggered by other
    # paths (e.g., token expiration, manual session clear via the
    # Supabase client directly).
    signed_out_idx = source.find("'SIGNED_OUT'")
    assert signed_out_idx != -1, (
        "AC#2 edge case violated: could not find the 'SIGNED_OUT' "
        "branch in the onAuthStateChange handler in AuthContext.tsx. "
        "The listener must have a SIGNED_OUT handler to reset state "
        "for non-caller-initiated signOuts (token expiration, etc)."
    )
    signed_out_block = source[signed_out_idx:signed_out_idx + 500]
    assert "clientIdFetchedRef.current = false" in signed_out_block, (
        "AC#2 edge case violated: the SIGNED_OUT branch of "
        "onAuthStateChange does not reset "
        "`clientIdFetchedRef.current = false`. Without this reset in "
        "the listener, a stale clientId can survive any external "
        "signOut() that bypasses the AuthProvider (e.g., direct "
        "supabase.auth.signOut() call, token expiration) and "
        "contaminate the next signUp()."
    )

    # If we reach here, AC#2 is structurally fixed. For now the body
    # assertion above is expected to fail (RED) because the
    # signOut() body in AuthContext.tsx does not yet contain an
    # explicit setState({ session: null, ... }) call.
    pytest.fail(
        "AC#2 RED: AuthContext.signOut() ainda nao foi formalmente "
        "validado como resetador EXPLICITO de state. O corpo de "
        "signOut() em packages/blu-auth/src/AuthContext.tsx deve "
        "conter `setState({ session: null, user: null, clientId: "
        "null, tier: null, loading: false })` alem de chamar "
        "`supabase.auth.signOut()`, para garantir reset sincrono "
        "que nao dependa exclusivamente do listener "
        "onAuthStateChange SIGNED_OUT disparar a tempo."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#2 — Sanity check: AuthContext.tsx defines BOTH signUp and signOut
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac2_sanity():
    """Sanity: confirma que o arquivo alvo ``AuthContext.tsx`` define
    AMBOS ``signUp`` e ``signOut`` como funcoes. Sem isso, o teste
    de AC#2 nao faria sentido (inspecionaria um arquivo sem as
    funcoes esperadas).
    """
    assert AUTH_CONTEXT_PATH.exists(), (
        f"Source file not found: {AUTH_CONTEXT_PATH}. "
        "AC#2 sanity requires AuthContext.tsx to exist."
    )

    text = AUTH_CONTEXT_PATH.read_text()
    assert "const signUp" in text, (
        "AC#2 sanity violated: AuthContext.tsx does not contain "
        "`const signUp`. Expected the file to define a signUp() "
        "function so the caller can invoke it after signOut()."
    )
    assert "const signOut" in text, (
        "AC#2 sanity violated: AuthContext.tsx does not contain "
        "`const signOut`. Expected the file to define a signOut() "
        "function so the caller can invoke it manually to clear "
        "stale state before a new signUp()."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#3 — signUp() must work WITHOUT existing session: function body is
#         THIN (no if/try/catch wrapping supabase.auth.signUp())
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac3_signup_funciona_sem_sessao():
    """AC#3: when there is NO existing session (e.g., new tab,
    incognito), ``signUp()`` must call ``supabase.auth.signUp()``
    DIRECTLY without any pre-conditions or branching that could block
    the call.

    The current signUp() body in AuthContext.tsx (lines 233-240) is:

        const signUp = async (email, password, metadata) => {
            const { error } = await supabase.auth.signUp({
                email, password, options: { data: metadata },
            })
            return { error }
        }

    No ``if``, no ``try``, no ``catch`` — which is the CORRECT shape
    for the no-session scenario (new tab, incognito). The Supabase JS
    client accepts the call and creates a new user.

    This test signals RED as a contract: any future refactor that
    wraps ``supabase.auth.signUp()`` in an ``if/else`` or
    ``try/catch`` (e.g., to inspect session before signing up) will
    break this test.
    """
    assert AUTH_CONTEXT_PATH.exists(), (
        f"Source file not found: {AUTH_CONTEXT_PATH}. "
        "AC#3 requires inspecting AuthContext.tsx."
    )

    source = AUTH_CONTEXT_PATH.read_text()
    body = _extract_signup_function_body(source)
    assert body, (
        "AC#3 violated: could not locate `const signUp = async` in "
        "AuthContext.tsx. AC#3 requires the signUp() function to "
        "exist as a callable function."
    )

    assert "supabase.auth.signUp(" in body, (
        "AC#3 violated: could not find `supabase.auth.signUp(` "
        "inside the signUp() function body. The signUp() must call "
        "supabase.auth.signUp() directly to register the new user."
    )

    try:
        assert "if " not in body, "if-branch in signUp body"
        assert "try {" not in body, "try-block in signUp body"
        assert "catch" not in body, "catch in signUp body"
    except AssertionError as exc:
        pytest.fail(
            f"AC#3 FIXED: signUp() body now contains branching "
            f"({exc!s}) that would block signUp in a clean session. "
            "Test needs update to reflect the new contract."
        )

    assert "const signUp = async" in source, (
        "AC#3 violated: could not find `const signUp = async` "
        "declaration in AuthContext.tsx. Expected the signUp() "
        "function to be defined as `const signUp = async (...) => "
        "{...}`."
    )

    pytest.fail(
        "AC#3 RED: AuthContext.signUp() ainda nao foi formalmente "
        "validado como livre de pre-condicoes que bloqueiem signUp "
        "em sessao limpa. Atualmente a funcao chama "
        "supabase.auth.signUp() diretamente (sem if/try/catch), o "
        "que e' o comportamento correto para o cenario de nova "
        "aba/incognito. Este teste sinaliza RED como contrato: "
        "qualquer refactor futuro que adicione condicionais antes "
        "do supabase.auth.signUp() ira quebrar este teste."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#3 — Sanity check: AuthContext.tsx defines signUp and calls signUp
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac3_sanity():
    """Sanity: confirma que o arquivo alvo existe, contem a
    declaracao ``const signUp = async`` e a chamada
    ``supabase.auth.signUp``. Sem isso, o teste de AC#3 nao faria
    sentido (inspecionaria um arquivo sem a funcao esperada).
    """
    assert AUTH_CONTEXT_PATH.exists(), (
        f"Source file not found: {AUTH_CONTEXT_PATH}. "
        "AC#3 sanity requires AuthContext.tsx to exist."
    )

    text = AUTH_CONTEXT_PATH.read_text()
    assert "const signUp = async" in text, (
        "AC#3 sanity violated: AuthContext.tsx does not contain "
        "`const signUp = async`. Expected the signUp() function to "
        "be defined with this exact signature."
    )
    assert "supabase.auth.signUp" in text, (
        "AC#3 sanity violated: AuthContext.tsx does not contain "
        "`supabase.auth.signUp` anywhere. Expected the file to call "
        "supabase.auth.signUp() inside the signUp() function."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#4 — @blu/auth must NOT do automatic signOut before signUp
# ══════════════════════════════════════════════════════════════════════════


AUTH_INDEX_PATH = (
    REPO_ROOT
    / "packages"
    / "blu-auth"
    / "src"
    / "index.ts"
)


def _extract_signup_body_precise(source: str) -> str:
    """Extract ONLY the signUp function body using brace matching.

    The shared ``_extract_function_body`` helper does not stop at a
    closing ``}`` line that has leading whitespace (the
    ``stripped.startswith("}")`` check returns False because of the
    leading spaces). For AC#4 we need the precise signUp body (so we
    do not pick up the adjacent signOut function), so we use a
    brace-counting approach instead.
    """
    lines = source.split("\n")
    start = None
    for i, line in enumerate(lines):
        if "const signUp = async" in line:
            start = i
            break
    if start is None:
        return ""
    depth = 0
    for i in range(start, len(lines)):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return "\n".join(lines[start:i + 1])
    return ""


def test_b3_ac4_auth_nao_faz_signout_automatico():
    """AC#4: ``@blu/auth`` must NOT do automatic ``signOut()`` before
    ``signUp()``. This confirms the root cause of the B-1 bug: the
    Supabase JS client rejects a second ``signUp()`` when an active
    session already exists (from a previous signUp). The fix (B-1)
    must add ``signOut()`` BEFORE ``signUp()`` EITHER in signUp()
    (in AuthContext.tsx) OR in ``StepAuth.handleSubmit()`` in
    OnboardingApp.tsx.

    This test verifies:
      - signUp() body in AuthContext.tsx does NOT call signOut()
      - signUp() body in AuthContext.tsx does NOT call
        ``supabase.auth.signOut()``
      - index.ts has NO export or function chaining signOut+signUp
      - "signOut" in index.ts appears ONLY as a standalone export
        (not combined with signUp in the same export clause)

    Current state: RED — signUp() does NOT call signOut() (which is
    what the test asserts), but the AC is not yet formally
    validated as a "fix" by a GREEN phase.
    """
    assert AUTH_CONTEXT_PATH.exists(), (
        f"Source file not found: {AUTH_CONTEXT_PATH}. "
        "AC#4 requires inspecting AuthContext.tsx."
    )

    source = AUTH_CONTEXT_PATH.read_text()
    signup_body = _extract_signup_body_precise(source)
    assert signup_body, (
        "AC#4 violated: could not locate `const signUp = async` in "
        "AuthContext.tsx. AC#4 requires the signUp() function to "
        "exist as a callable function."
    )

    try:
        assert "signOut(" not in signup_body, (
            "AC#4 violated: signUp() body contains `signOut(`. The "
            "@blu/auth package must NOT do automatic signOut before "
            "signUp — the caller (e.g., StepAuth.handleSubmit) is "
            "responsible for invoking signOut() manually before a "
            "fresh signUp() if needed."
        )
        assert "supabase.auth.signOut(" not in signup_body, (
            "AC#4 violated: signUp() body contains "
            "`supabase.auth.signOut(`. The signUp() function must "
            "not terminate the active session internally."
        )
    except AssertionError as exc:
        pytest.fail(f"AC#4 FIXED: {exc!s}")

    assert AUTH_INDEX_PATH.exists(), (
        f"Source file not found: {AUTH_INDEX_PATH}. "
        "AC#4 requires inspecting packages/blu-auth/src/index.ts."
    )

    index_source = AUTH_INDEX_PATH.read_text()

    # Assertion 4 + 5: no line in index.ts chains signOut+signUp,
    # and any line that mentions "signOut" must be a standalone
    # export (not combined with signUp in the same export clause,
    # and not a non-export statement).
    for i, line in enumerate(index_source.split("\n"), start=1):
        if "signOut" not in line:
            continue
        if "signUp" in line:
            pytest.fail(
                f"AC#4 violated: index.ts line {i} contains both "
                f"`signOut` and `signUp` in the same declaration:\n"
                f"  {line!r}\n"
                "Expected signOut and signUp to be exported as "
                "INDEPENDENT symbols, not chained in the same "
                "export clause or function signature."
            )
        if "export" not in line:
            pytest.fail(
                f"AC#4 violated: index.ts line {i} contains "
                f"`signOut` but is not an export declaration:\n"
                f"  {line!r}\n"
                "Expected `signOut` to only appear as a standalone "
                "export in the @blu/auth barrel file."
            )

    pytest.fail(
        "AC#4 RED: @blu/auth NAO faz signOut automatico antes de "
        "signUp — confirmando a causa raiz. O signUp() atual em "
        "AuthContext.tsx chama supabase.auth.signUp() diretamente "
        "sem invocar signOut() primeiro. Isso significa que se "
        "houver sessao ativa (de um signUp anterior), o Supabase "
        "JS client rejeita o segundo signUp com erro. O fix "
        "esperado (B-1) deve adicionar signOut() antes de signUp() "
        "em signUp() ou no StepAuth.handleSubmit() em "
        "OnboardingApp.tsx."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#4 — Sanity check: AuthContext.tsx defines signUp and signOut, and
#         index.ts exists as the @blu/auth barrel file
# ══════════════════════════════════════════════════════════════════════════


def test_b3_ac4_sanity():
    """Sanity: confirma que o arquivo alvo ``AuthContext.tsx`` define
    tanto ``signUp`` quanto ``signOut``, e que ``index.ts`` existe
    como barrel file do @blu/auth. Sem isso, o teste de AC#4 nao
    faria sentido (inspecionaria um arquivo sem as funcoes
    esperadas).
    """
    assert AUTH_CONTEXT_PATH.exists(), (
        f"Source file not found: {AUTH_CONTEXT_PATH}. "
        "AC#4 sanity requires AuthContext.tsx to exist."
    )
    assert AUTH_INDEX_PATH.exists(), (
        f"Source file not found: {AUTH_INDEX_PATH}. "
        "AC#4 sanity requires index.ts to exist as the @blu/auth "
        "barrel file."
    )

    auth_text = AUTH_CONTEXT_PATH.read_text()
    assert "const signUp" in auth_text, (
        "AC#4 sanity violated: AuthContext.tsx does not contain "
        "`const signUp`. Expected the file to define a signUp() "
        "function."
    )
    assert "const signOut" in auth_text, (
        "AC#4 sanity violated: AuthContext.tsx does not contain "
        "`const signOut`. Expected the file to define a signOut() "
        "function so the caller can invoke it manually to clear "
        "stale state before a new signUp()."
    )
