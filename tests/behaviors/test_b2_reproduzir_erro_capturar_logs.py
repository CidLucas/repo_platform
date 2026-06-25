"""RED test for behavior B2 — Captura de logs no pipeline de Auth.

GOAL:
    Garantir que o pipeline de Auth ("segundo cadastro de email falha")
    tenha **observabilidade mínima** para que se consiga diagnosticar em
    qual camada o erro está acontecendo quando um segundo signup em
    sequência (<5s, mesmo browser) falha.

    O bug atual: o código de AuthContext.signUp(),
    useOnboardingDraft.bootstrap() e a trigger DB handle_new_auth_user()
    **engolem erros silenciosamente** — não há ``console.warn``,
    ``console.error`` ou ``RAISE NOTICE`` registrando o estado da sessão
    prévia, o contexto do erro da edge function, nem conflitos na trigger
    de auto-criação de tenant. Sem isso, o operador não tem como saber se
    a falha é no frontend, na edge function ou no DB.

BEHAVIOR:
    B2 — Capturar logs: tornar o pipeline de Auth observável.
    Issue: "segundo cadastro de email falha" (parent batch #202).
    Pré-requisito: B-1 (limpar sessão existente antes do signUp).

    Cadeia investigada:
        OnboardingApp.StepAuth.handleSubmit()
            └─> useAuth().signUp()            [packages/blu-auth/src/useAuth.ts]
                └─> AuthContext.signUp()      [packages/blu-auth/src/AuthContext.tsx:233-240]
                    └─> supabase.auth.signUp()        ← AC#1: logar sessão prévia
                        └─> trigger handle_new_auth_user()  ← AC#3: RAISE NOTICE conflito
                            └─> webhook/edge function onboarding-bootstrap  ← AC#2: logar erro

AC (Acceptance Criteria):
    AC#1 — ``AuthContext.signUp()`` (linhas 233-240) deve registrar via
           ``console.warn`` / ``console.error`` / ``console.log`` o
           estado da sessão Auth existente ANTES de chamar
           ``supabase.auth.signUp()``. Sem isso, é impossível saber se
           havia sessão do usuário A contaminando o cadastro de B.

    AC#2 — ``useOnboardingDraft.bootstrap()`` (linhas 92-107) deve
           registrar via ``console.error`` / ``console.log`` /
           ``console.warn`` o erro retornado por
           ``supabase.functions.invoke('onboarding-bootstrap', ...)``
           com contexto completo (body enviado, error.message,
           error.details, status code). Hoje o código apenas faz
           ``throw new Error(error.message ?? 'Bootstrap failed')``.

    AC#3 — A trigger ``public.handle_new_auth_user()`` (migration
           ``20260523999999_baseline_v2.sql``, linhas 2961-3018) deve
           emitir ``RAISE NOTICE`` ou ``RAISE LOG`` quando o
           ``INSERT ... ON CONFLICT (external_user_id) DO NOTHING``
           detecta um conflito (ou seja, o ``RETURNING client_id INTO
           v_client_id`` retorna NULL). Hoje o conflito é silencioso.

DECISÃO:
    Estratégia: source_inspection (testes leem arquivos .tsx/.ts/.sql como
    texto puro). Sem DB, sem mocks. Arquivos alvo:
        - packages/blu-auth/src/AuthContext.tsx
        - apps/blu_v3/src/hooks/useOnboardingDraft.ts
        - supabase/migrations/20260523999999_baseline_v2.sql

Estado atual: RED — todas as ACs falham porque o código fonte ainda não
implementa nenhum dos três pontos de logging. Os testes servem como
contrato executável do comportamento que a fase GREEN deve introduzir.
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

USE_ONBOARDING_DRAFT_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "hooks"
    / "useOnboardingDraft.ts"
)

BASELINE_SQL_PATH = (
    REPO_ROOT
    / "supabase"
    / "migrations"
    / "20260523999999_baseline_v2.sql"
)


# ── Override root conftest cleanup (no real Supabase needed) ───────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — pure source-inspection tests, no DB teardown."""
    yield


# ── Helpers: extract the body of a named function from a source file ────


def _extract_function_body(source: str, marker: str) -> str:
    """Given a TS/TSX source string and a marker that uniquely appears on
    the first line of a function, return the body of that function as a
    string — from the line with the marker up to (but excluding) the next
    line that closes the surrounding block.

    This is intentionally loose: we just want a substring that includes
    the whole function so we can search inside it for console calls,
    RAISE statements, etc.
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

    Declared as:

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


def _extract_bootstrap_function_body(source: str) -> str:
    """Return the body of the ``bootstrap`` callback in useOnboardingDraft.ts.

    Declared as:

        const bootstrap = useCallback(async (finalPatch?: Partial<OnboardingDraft>) => {
            ...
        }, [draft, userEmail])
    """
    return _extract_function_body(source, "const bootstrap = useCallback")


def _extract_handle_new_auth_user_body(source: str) -> str:
    """Return the body of the ``handle_new_auth_user`` function from the
    baseline migration SQL.

    Declared as:

        CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        ...
        $function$;

    We grab from the AS $function$ marker up to the closing $function$;
    marker (which lives on its own line at column 0).
    """
    start_marker = "CREATE OR REPLACE FUNCTION public.handle_new_auth_user()"
    start_idx = source.find(start_marker)
    if start_idx == -1:
        return ""
    # Find the $function$ that opens the function body
    body_open = source.find("$function$", start_idx)
    if body_open == -1:
        return ""
    # Find the $function$ that closes the function body (column 0)
    body_close = source.find("\n$function$;\n", body_open)
    if body_close == -1:
        body_close = source.find("\n$function$", body_open)
    if body_close == -1:
        return ""
    return source[body_open:body_close]


# ══════════════════════════════════════════════════════════════════════════
# AC#1 — AuthContext.signUp() must log the existing session state
# ══════════════════════════════════════════════════════════════════════════


def test_b2_ac1_auth_context_signup_logs_existing_session_state():
    """AC#1: ``AuthContext.signUp()`` deve registrar (via ``console.warn``,
    ``console.error`` ou ``console.log``) o estado da sessão Auth
    existente ANTES de chamar ``supabase.auth.signUp()``.

    Hoje, o código em AuthContext.tsx (linhas 233-240) faz:

        const signUp = async (email, password, metadata) => {
            const { error } = await supabase.auth.signUp({
                email, password, options: { data: metadata },
            })
            return { error }
        }

    Sem nenhum ``console.*`` que registre:
      - Se já existe ``session`` ou ``user`` autenticado
      - Se é o segundo cadastro em sequência (mesmo browser, <5s)
      - O email/erro original retornado com contexto

    Sem essa observabilidade mínima, quando o "segundo cadastro de email
    falha" acontece em produção, o operador não tem como distinguir:
      (a) o frontend tentou cadastrar sem limpar a sessão
      (b) o frontend limpou a sessão mas o DB rejeitou
      (c) a edge function falhou

    O teste falha RED até a fase GREEN introduzir o logging.
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

    # The pre-signup block must contain at least one console.* logging call
    # that references the existing session/user state.
    has_console_log = (
        "console.warn(" in pre_signup_block
        or "console.error(" in pre_signup_block
        or "console.log(" in pre_signup_block
    )

    # The logging must reference the existing session/user, not be a
    # generic log without context.
    references_session_state = (
        "session" in pre_signup_block
        or "user" in pre_signup_block
        or "state." in pre_signup_block
    )

    if not has_console_log:
        pytest.fail(
            "AC#1 violada (RED): AuthContext.signUp() NÃO registra/loga "
            "o estado da sessão existente ANTES de chamar "
            "`supabase.auth.signUp()`.\n\n"
            "Sem esse logging, é impossível diagnosticar o bug "
            "'segundo cadastro de email falha' em produção — o operador "
            "não consegue distinguir se a falha é por sessão prévia "
            "contaminada, erro do Supabase Auth, ou falha da trigger DB.\n\n"
            "Contrato esperado: o signUp() deve conter, ANTES de "
            "`supabase.auth.signUp(...)`, pelo menos um:\n"
            "  - console.warn(`[AuthContext.signUp] sessão prévia detectada`, "
            "{ hasSession: !!session, hasUser: !!user, email })\n"
            "  - console.error(`[AuthContext.signUp] estado pré-signup`, state)\n"
            "  - console.log(`[AuthContext.signUp] segundo signup em sequência`, "
            "{ email, prevUserId: user?.id })\n\n"
            "Trecho atual do signUp() (linhas aproximadas 233-240):\n"
            f"```\n{body.strip()}\n```"
        )

    if not references_session_state:
        pytest.fail(
            "AC#1 violada (RED): AuthContext.signUp() tem um console.* "
            "no bloco pré-signup, mas ele NÃO referencia o estado da "
            "sessão (session/user/state) que é exatamente o que precisa "
            "ser loggado.\n\n"
            "Contrato esperado: o console.* deve mencionar pelo menos "
            "um de: `session`, `user`, `state` — variáveis que "
            "representam o estado Auth singleton.\n\n"
            f"Bloco pré-signup atual:\n```\n{pre_signup_block.rstrip()}\n```"
        )


# ══════════════════════════════════════════════════════════════════════════
# AC#2 — useOnboardingDraft.bootstrap() must log edge function errors
# ══════════════════════════════════════════════════════════════════════════


def test_b2_ac2_bootstrap_logs_edge_function_errors_with_context():
    """AC#2: ``useOnboardingDraft.bootstrap()`` (linhas 92-107) deve
    registrar via ``console.error`` / ``console.warn`` / ``console.log``
    o erro retornado por ``supabase.functions.invoke('onboarding-bootstrap')``
    com contexto completo: o ``body`` enviado, ``error.message``,
    ``error.details`` e o status code HTTP (se disponível).

    Hoje, o código faz:

        const { data, error } = await supabase.functions.invoke(
            'onboarding-bootstrap', { body: state },
        )
        if (error) throw new Error(error.message ?? 'Bootstrap failed')

    O ``throw`` apenas encapsula ``error.message`` e perde:
      - o ``body`` que foi enviado (impossível reproduzir o erro)
      - o ``error.context`` (status code, response body da edge function)
      - o email do usuário e o timestamp do request
      - a stack original do erro (porque ``new Error(...)`` cria uma
        stack vazia, sem o local original da falha)

    Sem esse logging, quando o "segundo cadastro de email falha" acontece
    na fase de bootstrap, o operador não consegue saber se o erro veio:
      (a) validação server-side (HTTP 400/422)
      (b) timeout da edge function (HTTP 504)
      (c) erro de DB na trigger handle_new_auth_user
      (d) conflito de external_user_id (mesmo cenário do B-1)

    O teste falha RED.
    """
    assert USE_ONBOARDING_DRAFT_PATH.exists(), (
        f"Source file not found: {USE_ONBOARDING_DRAFT_PATH}. "
        "AC#2 requires inspecting useOnboardingDraft.ts."
    )

    source = USE_ONBOARDING_DRAFT_PATH.read_text()
    body = _extract_bootstrap_function_body(source)
    assert body, (
        "Could not locate `const bootstrap = useCallback(...)` in "
        "useOnboardingDraft.ts. AC#2 requires inspecting the bootstrap() "
        "callback body."
    )

    # Locate the supabase.functions.invoke() call.
    invoke_idx = body.find("supabase.functions.invoke(")
    assert invoke_idx != -1, (
        "AC#2 violated: could not find `supabase.functions.invoke(` "
        "inside the bootstrap() callback body. Expected bootstrap() to "
        "call the onboarding-bootstrap edge function."
    )

    # Locate the error throw — we want to verify that BEFORE the throw,
    # there is logging of the error context.
    throw_idx = body.find("throw new Error(")
    if throw_idx == -1:
        # The error might be propagated differently (e.g. return)
        # but for this test we specifically look for a log block
        # between the invoke() and the end of the function / first
        # post-invoke statement.
        throw_idx = len(body)

    # The post-invoke block (between invoke() and throw/end) must contain
    # at least one console.* call that references the error variable.
    post_invoke_block = body[invoke_idx:throw_idx]

    has_console_log = (
        "console.error(" in post_invoke_block
        or "console.warn(" in post_invoke_block
        or "console.log(" in post_invoke_block
    )

    # The logging must reference the error object/variable — not a
    # generic log without context.
    references_error = "error" in post_invoke_block

    if not has_console_log:
        pytest.fail(
            "AC#2 violada (RED): useOnboardingDraft.bootstrap() NÃO "
            "registra/loga o erro retornado por "
            "`supabase.functions.invoke('onboarding-bootstrap', ...)`.\n\n"
            "O código atual apenas faz `throw new Error(error.message ?? "
            "'Bootstrap failed')`, o que descarta todo o contexto "
            "do erro (body enviado, error.context com HTTP status, "
            "error.details, stack original).\n\n"
            "Sem esse logging, é impossível diagnosticar em qual camada "
            "o 'segundo cadastro de email falha' está quebrando — se é "
            "validação da edge function, timeout, ou erro da trigger DB.\n\n"
            "Contrato esperado: bootstrap() deve conter, ANTES do "
            "`throw new Error(...)`, um bloco similar a:\n"
            "  console.error('[bootstrap] onboarding-bootstrap falhou', {\n"
            "    email: state.email,\n"
            "    errorMessage: error.message,\n"
            "    errorContext: error.context,\n"
            "    errorDetails: error.details,\n"
            "    body: state,\n"
            "  })\n\n"
            "Trecho atual do bootstrap() entre invoke() e throw:\n"
            f"```\n{post_invoke_block.strip()}\n```"
        )

    if not references_error:
        pytest.fail(
            "AC#2 violada (RED): useOnboardingDraft.bootstrap() tem um "
            "console.* no bloco pós-invoke, mas ele NÃO referencia a "
            "variável `error` retornada pelo "
            "`supabase.functions.invoke(...)`.\n\n"
            "Contrato esperado: o console.* deve mencionar `error` "
            "(a variável desestruturada do invoke) para que o "
            "contexto do erro (message, details, context) seja logado.\n\n"
            f"Bloco pós-invoke atual:\n```\n{post_invoke_block.rstrip()}\n```"
        )


# ══════════════════════════════════════════════════════════════════════════
# AC#3 — handle_new_auth_user() must RAISE NOTICE on conflict
# ══════════════════════════════════════════════════════════════════════════


def test_b2_ac3_handle_new_auth_user_raises_notice_on_conflict():
    """AC#3: A trigger ``public.handle_new_auth_user()`` (migration
    ``20260523999999_baseline_v2.sql``, linhas 2961-3018) deve emitir
    ``RAISE NOTICE`` ou ``RAISE LOG`` quando o
    ``INSERT ... ON CONFLICT (external_user_id) DO NOTHING`` detecta
    um conflito.

    O bloco atual é:

        INSERT INTO public.clientes_blu (
            external_user_id, api_key, nome_empresa, created_at, updated_at
        ) VALUES (
            NEW.id::text, v_api_key, COALESCE(NEW.email, 'Empresa'),
            now(), now()
        )
        ON CONFLICT (external_user_id) DO NOTHING
        RETURNING client_id INTO v_client_id;

        -- If row already existed (conflict), get its client_id
        IF v_client_id IS NULL THEN
            SELECT client_id INTO v_client_id FROM public.clientes_blu
            WHERE external_user_id = NEW.id::text;
        END IF;

    O conflito é silencioso. Quando o "segundo cadastro de email falha"
    acontece (B-1 scenario), a trigger executa com o mesmo
    ``external_user_id`` (porque é o mesmo ``auth.users.id`` reusado
    pelo Supabase) e o INSERT conflita. O operador não tem como
    detectar isso pelos logs do Postgres.

    O teste verifica que existe pelo menos um ``RAISE NOTICE`` ou
    ``RAISE LOG`` dentro da função (de preferência no ramo do
    conflito, i.e. dentro do ``IF v_client_id IS NULL THEN``).

    O teste falha RED porque o código atual não tem nenhum RAISE.
    """
    assert BASELINE_SQL_PATH.exists(), (
        f"Source file not found: {BASELINE_SQL_PATH}. "
        "AC#3 requires inspecting the baseline_v2 migration SQL."
    )

    source = BASELINE_SQL_PATH.read_text()
    body = _extract_handle_new_auth_user_body(source)
    assert body, (
        "Could not extract the body of `public.handle_new_auth_user()` "
        "from the baseline migration. AC#3 requires inspecting that "
        "function's body (lines 2961-3018 in "
        "supabase/migrations/20260523999999_baseline_v2.sql)."
    )

    # The function body must contain at least one RAISE NOTICE, RAISE LOG,
    # or RAISE EXCEPTION (we accept all three forms).
    has_raise_notice = "RAISE NOTICE" in body
    has_raise_log = "RAISE LOG" in body
    has_raise_exception = "RAISE EXCEPTION" in body
    has_raise_info = "RAISE INFO" in body
    has_raise_debug = "RAISE DEBUG" in body

    if not (has_raise_notice or has_raise_log or has_raise_exception
            or has_raise_info or has_raise_debug):
        pytest.fail(
            "AC#3 violada (RED): a trigger `public.handle_new_auth_user()` "
            "NÃO emite nenhum `RAISE NOTICE` / `RAISE LOG` / `RAISE "
            "EXCEPTION` para registrar conflitos de "
            "`external_user_id`.\n\n"
            "O código atual faz:\n"
            "  INSERT INTO public.clientes_blu (...)\n"
            "  VALUES (NEW.id::text, v_api_key, ...)\n"
            "  ON CONFLICT (external_user_id) DO NOTHING\n"
            "  RETURNING client_id INTO v_client_id;\n\n"
            "  IF v_client_id IS NULL THEN\n"
            "      SELECT client_id INTO v_client_id FROM public.clientes_blu\n"
            "      WHERE external_user_id = NEW.id::text;\n"
            "  END IF;\n\n"
            "Quando o 'segundo cadastro de email falha' acontece, o "
            "mesmo auth.users.id tenta inserir em clientes_blu duas "
            "vezes em <5s. A segunda inserção conflita silenciosamente "
            "e o operador não tem como saber pelo log do Postgres que "
            "houve conflito de tenant auto-criado.\n\n"
            "Contrato esperado: a função deve emitir um `RAISE NOTICE` "
            "(ou `RAISE LOG`) no ramo do conflito, por exemplo:\n"
            "  IF v_client_id IS NULL THEN\n"
            "      RAISE NOTICE 'handle_new_auth_user: conflito em "
            "external_user_id=%, email=%', NEW.id, NEW.email;\n"
            "      SELECT client_id INTO v_client_id FROM public.clientes_blu\n"
            "      WHERE external_user_id = NEW.id::text;\n"
            "  END IF;\n\n"
            f"Corpo atual da função (trecho extraído da migration):\n"
            f"```\n{body.strip()[:2000]}\n```"
        )


# ══════════════════════════════════════════════════════════════════════════
# Bonus cross-check: ensure the call chain is the documented one
# ══════════════════════════════════════════════════════════════════════════


def test_b2_call_chain_invariant_signup_to_bootstrap_to_trigger():
    """Sanity check (também RED-driven): garante que a cadeia investigada
    (signUp → trigger → bootstrap) é exatamente a documentada. Se
    algum refactor mover o nome de alguma peça, este teste força a
    atenção para o ponto exato onde o logging precisa ser inserido.

    Especificamente verifica:
      1. ``AuthContext.signUp()`` chama ``supabase.auth.signUp(...)``
         (call site onde AC#1 insere o logging).
      2. ``useOnboardingDraft.bootstrap()`` chama
         ``supabase.functions.invoke('onboarding-bootstrap', ...)``
         (call site onde AC#2 insere o logging).
      3. A migration baseline declara a função
         ``public.handle_new_auth_user()`` e ela tem
         ``ON CONFLICT (external_user_id) DO NOTHING`` (o ponto onde
         AC#3 insere o RAISE NOTICE).
    """
    assert AUTH_CONTEXT_PATH.exists(), (
        f"Source file not found: {AUTH_CONTEXT_PATH}."
    )
    auth_source = AUTH_CONTEXT_PATH.read_text()
    assert "supabase.auth.signUp" in auth_source, (
        "Invariant: AuthContext.tsx deve chamar `supabase.auth.signUp` "
        "— esse é o call site onde o AC#1 logging precisa ser inserido."
    )

    assert USE_ONBOARDING_DRAFT_PATH.exists(), (
        f"Source file not found: {USE_ONBOARDING_DRAFT_PATH}."
    )
    bootstrap_source = USE_ONBOARDING_DRAFT_PATH.read_text()
    assert "supabase.functions.invoke" in bootstrap_source, (
        "Invariant: useOnboardingDraft.ts deve chamar "
        "`supabase.functions.invoke` — esse é o call site onde o AC#2 "
        "logging precisa ser inserido."
    )
    assert "'onboarding-bootstrap'" in bootstrap_source, (
        "Invariant: useOnboardingDraft.ts deve invocar a edge function "
        "nomeada 'onboarding-bootstrap' — o logging do AC#2 deve "
        "acontecer especificamente aqui."
    )

    assert BASELINE_SQL_PATH.exists(), (
        f"Source file not found: {BASELINE_SQL_PATH}."
    )
    sql_source = BASELINE_SQL_PATH.read_text()
    assert "CREATE OR REPLACE FUNCTION public.handle_new_auth_user()" in sql_source, (
        "Invariant: a migration baseline deve declarar "
        "`public.handle_new_auth_user()` — esse é o call site onde o "
        "AC#3 RAISE NOTICE precisa ser inserido."
    )
    assert "ON CONFLICT (external_user_id) DO NOTHING" in sql_source, (
        "Invariant: a trigger handle_new_auth_user() deve usar "
        "`ON CONFLICT (external_user_id) DO NOTHING` — o RAISE NOTICE "
        "do AC#3 deve ser inserido especificamente no ramo onde este "
        "conflito ocorre (i.e. quando `RETURNING client_id INTO "
        "v_client_id` resulta em NULL)."
    )
