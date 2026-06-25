"""RED test for behavior B1 — Fluxo de Signup deve limpar sessão existente.

GOAL:
    Garantir que ao cadastrar um SEGUNDO email no fluxo de onboarding
    ("segundo cadastro de email falha"), a sessão Auth pré-existente seja
    limpa ANTES da chamada ``supabase.auth.signUp()``.

    O bug atual: ``AuthContext.signUp()`` (em
    ``packages/blu-auth/src/AuthContext.tsx``, linhas 233-240) chama
    ``supabase.auth.signUp()`` diretamente, sem ``signOut()`` prévio nem
    reset do state React (singleton ``session``, ``user``, ``clientId``,
    ``tier``). Resultado: o segundo cadastro é poluído pela sessão do
    primeiro usuário.

BEHAVIOR:
    B1 — Fluxo de Signup: limpar sessão existente antes de signUp.
    Issue: "segundo cadastro de email falha" (parent batch #202).

    Cadeia investigada:
        OnboardingApp.StepAuth.handleSubmit()
            └─> useAuth().signUp()        [packages/blu-auth/src/useAuth.ts]
                └─> AuthContext.signUp()  [packages/blu-auth/src/AuthContext.tsx:233-240]
                    └─> supabase.auth.signUp()

AC (Acceptance Criteria):
    AC#1 — AuthContext.signUp() deve chamar ``supabase.auth.signOut()`` OU
           resetar ``setState`` (session/user/clientId/tier) ANTES de
           ``supabase.auth.signUp()``. Sem isso, a sessão do usuário
           anterior vaza no segundo cadastro.
    AC#2 — StepAuth.handleSubmit() (OnboardingApp.tsx ~linhas 316-336) deve
           checar sessão existente antes de chamar ``signUp()``. Hoje, a
           função vai direto para ``signUp(email, password)`` sem nenhuma
           guarda.
    AC#3 — O pacote ``@blu/auth`` deve exportar um hook de ciclo de vida
           ``onSignUp`` (callback executado após signUp bem-sucedido, usado
           para observabilidade/telemetria/limpeza). Hoje o
           ``packages/blu-auth/src/index.ts`` não exporta nada desse tipo.

DECISÃO:
    Estratégia: source_inspection (testes leem arquivos .tsx como texto).
    Arquivos alvo:
        - packages/blu-auth/src/AuthContext.tsx
        - apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
        - packages/blu-auth/src/index.ts

Estado atual: RED — todas as ACs falham porque o código fonte ainda não
implementa nenhuma das três correções. Os testes servem como contrato
executável do comportamento que a fase GREEN deve introduzir.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ── Constants: paths to source files under test ──────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

AUTH_CONTEXT_PATH = (
    REPO_ROOT
    / "packages"
    / "blu-auth"
    / "src"
    / "AuthContext.tsx"
)

ONBOARDING_APP_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "onboarding"
    / "OnboardingApp.tsx"
)

BLU_AUTH_INDEX_PATH = (
    REPO_ROOT
    / "packages"
    / "blu-auth"
    / "src"
    / "index.ts"
)


# ── Override root conftest cleanup (no real Supabase needed) ───────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — pure source-inspection tests, no DB teardown."""
    yield


# ── Helpers: extract the body of a named function from a TS source file ──


def _extract_function_body(source: str, marker: str) -> str:
    """Given a TS source string and a marker that uniquely appears on the
    first line of a function (e.g. ``const signUp = async (email: ...``),
    return the body of that function as a string — from the line with the
    marker up to (but excluding) the next line that closes the surrounding
    block.

    This is intentionally loose: we just want a substring that includes the
    whole ``signUp`` (or ``handleSubmit``) function so we can search inside
    it for ``supabase.auth.signOut``, ``setState``, ``signUp(`` etc.
    """
    idx = source.find(marker)
    if idx == -1:
        return ""
    # Walk forward and try to find the next line whose indent is 0 and
    # which doesn't look like a continuation of the function body.
    lines = source[idx:].split("\n")
    body_lines = [lines[0]]
    # The opening line defines the starting indent.
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
            # Likely end of the function.
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
    # Find any of the possible declarations.
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


def _extract_handle_submit_body(source: str) -> str:
    """Return the body of ``handleSubmit`` in OnboardingApp.tsx.

    Declared as:

        async function handleSubmit() {
            ...
        }
    """
    return _extract_function_body(source, "async function handleSubmit()")


# ══════════════════════════════════════════════════════════════════════════
# AC#1 — AuthContext.signUp() must clear existing session before signUp
# ══════════════════════════════════════════════════════════════════════════


def test_ac1_auth_context_signup_clears_existing_session_before_calling_supabase():
    """AC#1: ``AuthContext.signUp()`` deve limpar a sessão atual (via
    ``supabase.auth.signOut()`` ou ``setState({ session: null, ... })``)
    ANTES de chamar ``supabase.auth.signUp()``.

    Hoje, o código em AuthContext.tsx (linhas 233-240) faz:

        const signUp = async (email, password, metadata) => {
            const { error } = await supabase.auth.signUp({
                email, password, options: { data: metadata },
            })
            return { error }
        }

    Sem ``signOut()`` prévio nem ``setState`` reset, a sessão singleton
    (``session``, ``user``, ``clientId``, ``tier``) do usuário anterior
    vaza no segundo cadastro. O teste falha RED até a fase GREEN.
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

    # Locate the position of the supabase.auth.signUp() call within the body.
    signup_call_idx = body.find("supabase.auth.signUp(")
    assert signup_call_idx != -1, (
        "AC#1 violated: could not find `supabase.auth.signUp(` inside the "
        "signUp() function body. Expected the AuthContext to call "
        "supabase.auth.signUp() to create the new user."
    )

    # Slice everything BEFORE the signUp() call.
    pre_signup_block = body[:signup_call_idx]

    # The pre-signup block must contain either:
    #   (a) a call to supabase.auth.signOut(), OR
    #   (b) a setState call that resets session/user/clientId/tier.
    has_signout = "supabase.auth.signOut(" in pre_signup_block
    has_state_reset = (
        "setState(" in pre_signup_block
        and (
            "session: null" in pre_signup_block
            or "session:null" in pre_signup_block
            or "user: null" in pre_signup_block
            or "user:null" in pre_signup_block
        )
    )

    assert has_signout or has_state_reset, (
        "AC#1 violated (RED): AuthContext.signUp() NÃO limpa a sessão "
        "existente antes de chamar `supabase.auth.signUp()`. "
        "Isso causa o bug 'segundo cadastro de email falha': o singleton "
        "React (session, user, clientId, tier) mantém o estado do "
        "primeiro usuário e polui o segundo cadastro.\n\n"
        "Contrato esperado (escolher uma das duas formas):\n"
        "  1. Chamar `await supabase.auth.signOut()` ANTES de "
        "`supabase.auth.signUp(...)`.\n"
        "  2. Chamar `setState({ session: null, user: null, "
        "clientId: null, tier: null, loading: false })` ANTES de "
        "`supabase.auth.signUp(...)`.\n\n"
        "Trecho atual do signUp() (linhas aproximadas 233-240):\n"
        f"```\n{body.strip()}\n```"
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#2 — StepAuth.handleSubmit() must check existing session before signUp
# ══════════════════════════════════════════════════════════════════════════


def test_ac2_step_auth_handle_submit_checks_existing_session_before_signup():
    """AC#2: ``StepAuth.handleSubmit()`` em OnboardingApp.tsx
    (linhas ~316-336) deve checar a sessão existente antes de chamar
    ``signUp()``. Sem essa guarda, o componente assume que nunca há
    usuário logado, e delega 100% da limpeza para o AuthContext — o que
    hoje não acontece (ver AC#1).

    Formas aceitáveis de "existing-session check":
      - leitura de ``session``/``user`` do useAuth()
      - leitura de ``state.session``
      - chamada explícita a ``signOut()`` antes de ``signUp()``
      - um ``if (session)`` ou ``if (user)`` que faça guard

    Hoje a função faz apenas:

        const { error } = await signUp(email, password)
        if (error) { setError(...); return }
        onNext()

    O teste falha RED.
    """
    assert ONBOARDING_APP_PATH.exists(), (
        f"Source file not found: {ONBOARDING_APP_PATH}. "
        "AC#2 requires inspecting OnboardingApp.tsx."
    )

    source = ONBOARDING_APP_PATH.read_text()

    # The handleSubmit() function body must be extractable.
    body = _extract_handle_submit_body(source)
    assert body, (
        "Could not locate `async function handleSubmit()` in "
        "OnboardingApp.tsx. AC#2 requires inspecting handleSubmit() "
        "inside StepAuth."
    )

    # Locate the signUp() call within the body.
    signup_call_idx = body.find("signUp(email, password)")
    assert signup_call_idx != -1, (
        "AC#2 violated: could not find `signUp(email, password)` inside "
        "StepAuth.handleSubmit(). Expected the call to destructure the "
        "useAuth().signUp() function with two positional args."
    )

    # Slice everything BEFORE the signUp() call.
    pre_signup_block = body[:signup_call_idx]

    # Acceptable forms of "existing session check" before signUp().
    has_session_variable = "session" in pre_signup_block
    has_user_variable = "user" in pre_signup_block
    has_signout_call = "signOut(" in pre_signup_block
    has_explicit_guard = (
        "if (session" in pre_signup_block
        or "if (user" in pre_signup_block
        or "if (state.session" in pre_signup_block
        or "if (state.user" in pre_signup_block
    )
    has_use_auth_state_destructure = (
        "useAuth" in pre_signup_block
        and ("session" in pre_signup_block or "user" in pre_signup_block)
    )

    assert (
        has_signout_call
        or has_explicit_guard
        or has_session_variable
        or has_user_variable
        or has_use_auth_state_destructure
    ), (
        "AC#2 violated (RED): StepAuth.handleSubmit() NÃO checa a sessão "
        "existente antes de chamar `signUp(email, password)`. Isso "
        "significa que se um usuário A terminou o onboarding e um "
        "segundo email B é cadastrado no mesmo browser, o estado "
        "singleton do usuário A (session, user, clientId, tier) "
        "permanece vivo e contamina o cadastro de B.\n\n"
        "Contrato esperado: o handleSubmit() deve fazer uma das "
        "seguintes guardas antes do `signUp(email, password)`:\n"
        "  - Destrurar `session` ou `user` do `useAuth()` e checar\n"
        "    `if (session)` ou `if (user)`.\n"
        "  - Chamar explicitamente `await signOut()` antes do signUp().\n"
        "  - Qualquer combinação que garanta que o estado Auth "
        "    esteja limpo antes do novo cadastro.\n\n"
        f"Trecho atual do handleSubmit() até o signUp():\n"
        f"```\n{body[:signup_call_idx].rstrip()}\n```\n"
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#3 — @blu/auth must export an onSignUp lifecycle hook
# ══════════════════════════════════════════════════════════════════════════


def test_ac3_blu_auth_exports_onsignup_lifecycle_hook():
    """AC#3: O pacote ``@blu/auth`` deve exportar um hook de ciclo de
    vida ``onSignUp`` — callback executado após um signUp bem-sucedido.
    Esse hook serve para observabilidade/telemetria/limpeza externa
    (analytics identify, reset de cache, etc.).

    Hoje, ``packages/blu-auth/src/index.ts`` exporta apenas:

        supabase, resolveClientId, getAuthToken, buildAuthHeaders,
        AuthContext, AuthProvider, useAuth, tipos.

    Não há nenhum ``onSignUp`` (nem como prop do AuthProvider, nem como
    função exportada). O teste falha RED.
    """
    assert BLU_AUTH_INDEX_PATH.exists(), (
        f"Source file not found: {BLU_AUTH_INDEX_PATH}. "
        "AC#3 requires inspecting packages/blu-auth/src/index.ts."
    )

    source = BLU_AUTH_INDEX_PATH.read_text()

    # The index must export an identifier named onSignUp (case-sensitive).
    # Acceptable forms:
    #   export const onSignUp = ...
    #   export { onSignUp } from '...'
    #   export function onSignUp(...)
    #   export { useSignUp } ...     (alternative hook name)
    # We accept any identifier that contains "onSignUp" or "useSignUp"
    # in an export statement.
    has_onsignup_export = (
        "onSignUp" in source
        and (
            "export { onSignUp" in source
            or "export const onSignUp" in source
            or "export function onSignUp" in source
            or "export type onSignUp" in source
            or "export { useSignUp" in source
            or "export const useSignUp" in source
            or "export function useSignUp" in source
        )
    )

    assert has_onsignup_export, (
        "AC#3 violated (RED): o pacote `@blu/auth` NÃO exporta um hook "
        "de ciclo de vida `onSignUp` (nem `useSignUp`).\n\n"
        "Contrato esperado: o `packages/blu-auth/src/index.ts` deve "
        "exportar um identificador `onSignUp` (ou `useSignUp` para "
        "estilo hook) para que consumers possam reagir ao evento de "
        "signup bem-sucedido. Esse hook é usado para:\n"
        "  - Identificar o novo usuário em analytics/telemetria\n"
        "  - Resetar caches dependentes da sessão anterior\n"
        "  - Disparar fluxos de pós-cadastro (welcome email, etc.)\n\n"
        "Exemplo de export esperado:\n"
        "  export { onSignUp } from './AuthContext'\n"
        "  // ou\n"
        "  export const useSignUp = () => { ... }\n\n"
        f"Conteúdo atual de {BLU_AUTH_INDEX_PATH.relative_to(REPO_ROOT)}:\n"
        f"```\n{source}\n```"
    )


# ══════════════════════════════════════════════════════════════════════════
# Bonus cross-check: ensure the call chain really is the documented one
# ══════════════════════════════════════════════════════════════════════════


def test_call_chain_invariant_stepauth_to_supabase_signup():
    """Sanity check (also RED-driven): a chamada ``signUp(email, password)``
    em OnboardingApp.tsx deve resolver para ``AuthContext.signUp`` (e
    portanto para ``supabase.auth.signUp``), e não para alguma função
    paralela que mascarasse a falta da limpeza.

    Se em algum refactor futuro alguém trocar o caminho do signUp(), este
    teste força a atenção sobre isso.
    """
    assert ONBOARDING_APP_PATH.exists(), (
        f"Source file not found: {ONBOARDING_APP_PATH}."
    )
    source = ONBOARDING_APP_PATH.read_text()

    # OnboardingApp imports useAuth from @blu/auth.
    assert "from '@blu/auth'" in source, (
        "Invariant: OnboardingApp.tsx deve importar de '@blu/auth' para "
        "ter acesso a useAuth() e signUp()."
    )
    assert "useAuth" in source, (
        "Invariant: OnboardingApp.tsx deve chamar useAuth() para obter "
        "signUp()."
    )
    # StepAuth must destructure signUp from useAuth().
    assert "signUp } = useAuth()" in source or "signUp, " in source or ", signUp " in source, (
        "Invariant: StepAuth deve destrurar `signUp` de useAuth() (e não "
        "importar signUp diretamente de outro lugar)."
    )

    # AuthContext must contain supabase.auth.signUp() inside a signUp
    # function — esse é o call site que o fix da AC#1 vai alterar.
    assert AUTH_CONTEXT_PATH.exists(), (
        f"Source file not found: {AUTH_CONTEXT_PATH}."
    )
    auth_source = AUTH_CONTEXT_PATH.read_text()
    assert "supabase.auth.signUp" in auth_source, (
        "Invariant: AuthContext.tsx deve chamar supabase.auth.signUp() "
        "dentro do signUp() — esse é o ponto exato onde o signOut "
        "precisa ser inserido."
    )
