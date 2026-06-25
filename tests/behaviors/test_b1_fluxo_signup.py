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


# ══════════════════════════════════════════════════════════════════════════
# AC#4 — handle_new_auth_user() trigger exists in migration SQL
# ══════════════════════════════════════════════════════════════════════════

BASELINE_MIGRATION_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)

ONBOARDING_DRAFT_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "hooks"
    / "useOnboardingDraft.ts"
)

EDGE_FN_BOOTSTRAP_PATH = (
    REPO_ROOT
    / "supabase"
    / "functions"
    / "onboarding-bootstrap"
    / "index.ts"
)


def _read_source(path: Path) -> str:
    assert path.exists(), f"Arquivo nao encontrado: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════════
# AC#4 — ensure_tenant_row() must be called BEFORE onboarding_bootstrap_tx
# ══════════════════════════════════════════════════════════════════════════


def test_ac4_edge_fn_calls_ensure_tenant_row_before_rpc():
    """AC#4: Na edge function ``onboarding-bootstrap/index.ts``, a chamada
    ``ensure_tenant_row`` DEVE ocorrer ANTES da chamada ao RPC
    ``onboarding_bootstrap_tx``.

    A ordem importa: primeiro a edge function garante que o tenant
    (clientes_blu) existe via ``userClient.rpc('ensure_tenant_row')``,
    e SÓ ENTÃO chama o RPC de bootstrap com o payload completo.

    Hoje (RED), a edge function tem a ordem:
        rpc('ensure_tenant_row')
        rpc('onboarding_bootstrap_tx', { p_payload: payload })

    O teste verifica que ensure_tenant_row aparece primeiro no arquivo.
    """
    source = _read_source(EDGE_FN_BOOTSTRAP_PATH)

    # ensure_tenant_row deve existir
    assert "ensure_tenant_row" in source, (
        "AC#4 violated (RED): onboarding-bootstrap/index.ts NAO chama "
        "ensure_tenant_row. Esperado:\n"
        "  userClient.rpc('ensure_tenant_row')\n"
        "Essa chamada garante que o tenant existe antes do bootstrap."
    )

    # onboarding_bootstrap_tx deve existir (pode ser multi-line)
    assert "onboarding_bootstrap_tx" in source, (
        "AC#4 violated (RED): onboarding-bootstrap/index.ts NAO chama "
        "onboarding_bootstrap_tx RPC. Esperado:\n"
        "  userClient.rpc('onboarding_bootstrap_tx', { p_payload: payload })"
    )

    # ensure_tenant_row DEVE aparecer ANTES de onboarding_bootstrap_tx
    # Pular a seção de comentários/header — procurar a partir de "Deno.serve"
    code_body = source[source.find("Deno.serve"):]
    idx_ensure = code_body.find("ensure_tenant_row")
    idx_rpc = code_body.find("onboarding_bootstrap_tx")

    assert idx_ensure < idx_rpc, (
        "AC#4 violated (RED): ensure_tenant_row DEVE ser chamado ANTES "
        "de onboarding_bootstrap_tx, mas no codigo (posicao relativa "
        "ao handler Deno.serve):\n"
        "  ensure_tenant_row em posicao: {}, "
        "onboarding_bootstrap_tx em posicao: {}\n\n"
        "A chamada ensure_tenant_row garante que o tenant existe "
        "antes do bootstrap atomico, evitando race conditions."
        .format(idx_ensure, idx_rpc)
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#5 — bootstrap_knowledge_from_onboarding is called after tx RPC
# ══════════════════════════════════════════════════════════════════════════


def test_ac5_knowledge_bootstrap_called_after_tx_rpc():
    """AC#5: Na edge function, ``bootstrap_knowledge_from_onboarding``
    DEVE ser chamado DEPOIS de ``onboarding_bootstrap_tx``, pois precisa
    do ``client_id`` retornado pela transacao atomica.

    Hoje (RED), a funcao tem:
        rpc('onboarding_bootstrap_tx', ...)
        ...
        rpc('bootstrap_knowledge_from_onboarding', { p_client_id })

    O teste verifica que a chamada tx RPC aparece antes.
    """
    source = _read_source(EDGE_FN_BOOTSTRAP_PATH)

    has_knowledge_rpc = "bootstrap_knowledge_from_onboarding" in source

    assert has_knowledge_rpc, (
        "AC#5 violated (RED): onboarding-bootstrap/index.ts NAO chama "
        "bootstrap_knowledge_from_onboarding. Esperado:\n"
        "  svc.rpc('bootstrap_knowledge_from_onboarding', { p_client_id })"
    )

    # knowledge DEVE aparecer DEPOIS de onboarding_bootstrap_tx
    tx_idx = source.find('onboarding_bootstrap_tx')
    kb_idx = source.find('bootstrap_knowledge_from_onboarding')

    assert tx_idx < kb_idx, (
        "AC#5 violated (RED): bootstrap_knowledge_from_onboarding DEVE "
        "ser chamado DEPOIS de onboarding_bootstrap_tx, pois precisa "
        "do client_id retornado pela transacao.\n\n"
        "Ordem atual: tx={}, knowledge={}"
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#6 — website-context-builder fire-and-forget via EdgeRuntime.waitUntil
# ══════════════════════════════════════════════════════════════════════════


def test_ac6_website_context_builder_fire_and_forget():
    """AC#6: Na edge function, o disparo do ``website-context-builder``
    DEVE ser fire-and-forget via ``EdgeRuntime.waitUntil``, e NAO um
    await síncrono que bloquearia a resposta HTTP.

    A edge function deve responder rapido (redirect do wizard), entao
    a chamada para website-context-builder nao pode travar a resposta.

    O teste falha RED se:
      - website-context-builder nao for chamado (ausente)
      - OU for chamado com await síncrono (nao usa waitUntil)
    """
    source = _read_source(EDGE_FN_BOOTSTRAP_PATH)

    assert "website-context-builder" in source, (
        "AC#6 violated (RED): onboarding-bootstrap/index.ts NAO "
        "referencia website-context-builder. Esperado: fire-and-forget "
        "fetch para /functions/v1/website-context-builder."
    )

    # website-context-builder deve estar dentro de EdgeRuntime.waitUntil
    # Verificar que existe um waitUntil que contem website-context-builder
    wait_until_blocks = [p for p in source.split("EdgeRuntime.waitUntil(") if "website-context-builder" in p]
    assert len(wait_until_blocks) >= 1, (
        "AC#6 violated (RED): website-context-builder NAO esta dentro de "
        "EdgeRuntime.waitUntil(). Esperado:\n"
        "  EdgeRuntime.waitUntil(\n"
        "    fetch(`${SUPABASE_URL}/functions/v1/website-context-builder`, ...)\n"
        "  )\n\n"
        "Sem waitUntil, o fetch blocaria a resposta HTTP da edge function, "
        "atrasando o redirect do wizard de onboarding."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#7 — onboarding_bootstrap_tx(p_payload jsonb) RPC exists in SQL
# ══════════════════════════════════════════════════════════════════════════


def test_ac7_onboarding_bootstrap_tx_rpc_exists():
    """AC#7: O RPC ``onboarding_bootstrap_tx(p_payload jsonb)``
    DEVE existir na migration SQL como funcao PL/pgSQL
    que chama ``public.get_my_client_id()`` e retorna jsonb.

    Este RPC é o coracao do provisionamento atomico pós-signup:
    ele recebe o payload completo do wizard de onboarding,
    cria/atualiza o tenant e retorna { client_id, agents, routines }.

    O teste falha RED enquanto a funcao SQL nao existir com
    a assinatura correta e chamadas internas esperadas.
    """
    source = _read_source(BASELINE_MIGRATION_PATH)

    assert "onboarding_bootstrap_tx" in source, (
        "AC#7 violated (RED): onboarding_bootstrap_tx NAO encontrado "
        "na migration baseline. Esperado:\n"
        "  CREATE OR REPLACE FUNCTION public.onboarding_bootstrap_tx(p_payload jsonb)\n"
        "  RETURNS jsonb"
    )

    # Extrair o bloco da funcao (do nome ate o $function$)
    func_header = source.split("onboarding_bootstrap_tx")[1][:300]

    assert 'p_payload' in func_header, (
        "AC#7 violated (RED): onboarding_bootstrap_tx NAO tem parametro "
        "p_payload na assinatura. Esperado:\n"
        "  onboarding_bootstrap_tx(p_payload jsonb)"
    )

    assert 'RETURNS jsonb' in func_header, (
        "AC#7 violated (RED): onboarding_bootstrap_tx NAO retorna jsonb. "
        "Esperado: RETURNS jsonb para retornar { client_id, agents, routines }."
    )

    # Verificar corpo da funcao
    tx_body = source.split("onboarding_bootstrap_tx")[1][:2000]
    assert 'get_my_client_id()' in tx_body, (
        "AC#7 violated (RED): onboarding_bootstrap_tx NAO chama "
        "public.get_my_client_id(). Esperado:\n"
        "  v_client_id := public.get_my_client_id()"
    )

    assert 'UPDATE public.clientes_blu' in tx_body, (
        "AC#7 violated (RED): onboarding_bootstrap_tx NAO faz "
        "UPDATE em public.clientes_blu com company_profile, "
        "team_structure, etc. Essa atualizacao eh o core "
        "do provisionamento."
    )


# ══════════════════════════════════════════════════════════════════════════
# AC#8 — bootstrap_knowledge_from_onboarding(p_client_id uuid) seeds docs
# ══════════════════════════════════════════════════════════════════════════


def test_ac8_bootstrap_knowledge_from_onboarding_seeds_documents():
    """AC#8: O RPC ``bootstrap_knowledge_from_onboarding(p_client_id uuid)``
    DEVE existir na migration SQL e fazer INSERT INTO
    ``public.client_knowledge_documents`` com status='partial',
    source='onboarding'.

    Esta funcao sementa documentos de conhecimento iniciais
    (ficha_cadastral, perfil_empresarial, etc) para que os scores
    de cobertura nao sejam zero desde o primeiro dia.

    O teste falha RED enquanto a funcao SQL nao existir com os
    inserts corretos.
    """
    source = _read_source(BASELINE_MIGRATION_PATH)

    assert "bootstrap_knowledge_from_onboarding" in source, (
        "AC#8 violated (RED): bootstrap_knowledge_from_onboarding "
        "NAO encontrado na migration baseline. Esperado:\n"
        "  CREATE OR REPLACE FUNCTION "
        "public.bootstrap_knowledge_from_onboarding(p_client_id uuid)\n"
        "  RETURNS jsonb"
    )

    # Verificar assinatura
    kb_header = source.split("bootstrap_knowledge_from_onboarding")[1][:200]
    assert 'p_client_id' in kb_header, (
        "AC#8 violated (RED): bootstrap_knowledge_from_onboarding "
        "NAO tem parametro p_client_id. Esperado:\n"
        "  bootstrap_knowledge_from_onboarding(p_client_id uuid)"
    )

    # Verificar corpo (INSERT em client_knowledge_documents)
    kb_body = source.split("bootstrap_knowledge_from_onboarding")[1][:2000]
    assert 'client_knowledge_documents' in kb_body, (
        "AC#8 violated (RED): bootstrap_knowledge_from_onboarding "
        "NAO insere em client_knowledge_documents. Esperado:\n"
        "  INSERT INTO public.client_knowledge_documents\n"
        "    (client_id, document_type_id, status, source)\n"
        "  VALUES (p_client_id, 'ficha_cadastral', 'partial', 'onboarding')"
    )

    assert "source" in kb_body and "onboarding" in kb_body, (
        "AC#8 violated (RED): bootstrap_knowledge_from_onboarding "
        "NAO usa source='onboarding' no INSERT. Esperado:\n"
        "  source = 'onboarding' para rastrear a origem do documento."
    )

    assert "INSERT" in kb_body and "ON CONFLICT" in kb_body, (
        "AC#8 violated (RED): bootstrap_knowledge_from_onboarding "
        "NAO tem ON CONFLICT DO NOTHING. Esperado: upsert que "
        "nao duplica documentos se o mesmo document_type_id ja existir."
    )
