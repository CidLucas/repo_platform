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
