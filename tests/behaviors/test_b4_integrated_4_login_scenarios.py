"""RED test integrado para B-4 — Os 4 cenarios de login.

GOAL:
    Validar de forma INTEGRADA (i.e. atravessando todas as camadas do
    pipeline) que os 4 cenarios canonicos de login/onboarding do batch
    #202 ("segundo cadastro de email falha") satisfazem o contrato
    executavel da correcao estrutural.

    Os 4 cenarios sob teste sao:

      Cenario 1 — Primeiro signup (estado limpo, sem sessao previa)
        Cadeia: handleSubmit() -> signUp() -> supabase.auth.signUp()
                -> trigger handle_new_auth_user() -> ensure_tenant_row()
                -> onboarding_bootstrap_tx()
        Estado esperado GREEN: tudo funciona de primeira.

      Cenario 2 — Segundo signup (sessao residual do usuario A vaza)
        Cadeia: mesmo handleSubmit() chamado num browser que JA tem
                sessao ativa de um signup anterior (logout + novo
                signup rapido, troca de conta no mesmo browser).
        Bug atual (RED): sessao de A vaza para o signup de B
                (AuthContext.signUp nao chama signOut() nem setState
                 reset; trigger DB faz ON CONFLICT DO NOTHING em vez
                 de DO UPDATE; useOnboardingDraft nao reseta draft).
        Estado esperado GREEN: cada signup comeca de sessao limpa,
                updated_at e nome_empresa refletem o novo signup.

      Cenario 3 — Login de usuario existente (signInWithEmail)
        Cadeia: handleSubmit() (mode='login') -> signInWithEmail()
                -> supabase.auth.signInWithPassword()
                -> onAuthStateChange listener -> initClientId()
                -> get_my_client_id() -> navigate('/app') se onboarding
                   completo, ou restaurar step do wizard se incompleto.
        Estado esperado GREEN: login de usuario existente nao
                dispara fluxo de bootstrap; redireciona corretamente.

      Cenario 4 — Login OAuth (Google) — signInWithOAuth
        Cadeia: handleGoogle() -> supabase.auth.signInWithOAuth()
                -> redirect para /onboarding?mode=login
                -> onAuthStateChange listener -> initClientId()
                -> get_my_client_id() -> ensure_tenant_row() (se novo)
                -> setStep('info') OU navigate('/app')
        Estado esperado GREEN: OAuth signup/login de novo usuario
                provisiona tenant via ensure_tenant_row; OAuth de
                usuario existente redireciona para /app.

BEHAVIOR:
    B-4 (parent batch #202) — Cenarios integrados de login/onboarding.
    Documentos de referencia:
        - docs/observability/auth-signup-flow.md
        - docs/observability/auth-second-signup-root-cause.md
        - docs/root-cause-segundo-cadastro-email.md

DECISAO:
    Estrategia: source_inspection (regex/texto sobre os arquivos
    .tsx/.ts/.sql). Sem React runtime, sem Supabase client, sem
    mocks, sem DB. O teste falha RED com ``pytest.fail()`` em pt-BR
    ate' que TODAS as correcoes estruturais estejam aplicadas.

    Arquivos sob inspecao:
        - packages/blu-auth/src/AuthContext.tsx
        - apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
        - apps/blu_v3/src/hooks/useOnboardingDraft.ts
        - supabase/functions/onboarding-bootstrap/index.ts
        - supabase/migrations/20260523999999_baseline_v2.sql

Estado atual: RED — varios ACs ja foram cobertos por testes
individuais (B-1, B-2, B-3a, B-3b, B-3c) mas este teste e' o
**integrador**: falha se QUALQUER das correcoes estiver ausente,
servindo como gate de saida da fase RED para a fase GREEN.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Constants: paths to source files under test ──────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

AUTH_CONTEXT_PATH = (
    REPO_ROOT / "packages" / "blu-auth" / "src" / "AuthContext.tsx"
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
USE_DRAFT_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "hooks" / "useOnboardingDraft.ts"
)
EDGE_FN_BOOTSTRAP_PATH = (
    REPO_ROOT
    / "supabase"
    / "functions"
    / "onboarding-bootstrap"
    / "index.ts"
)
BASELINE_MIGRATION_PATH = (
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


# ── Helpers ─────────────────────────────────────────────────────────────


def _read_source(path: Path) -> str:
    assert path.exists(), f"Arquivo nao encontrado: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def _extract_function_body(source: str, marker: str) -> str:
    """Extract a TS function body (from marker line to next top-level
    closing). Mirrors the helper used in test_b1_fluxo_signup.py."""
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


def _plsql_function_body(source: str, func_name: str) -> str:
    """Extract the body of a PL/pgSQL function by name (delimited by
    $function$ ... $function$;). Mirrors the helper in
    test_b1_fluxo_signup.py."""
    marker = f"CREATE OR REPLACE FUNCTION public.{func_name}"
    marker_idx = source.find(marker)
    if marker_idx == -1:
        return ""
    body_start = source.find("$function$", marker_idx)
    if body_start == -1:
        return ""
    body_start = source.find("\n", body_start) + 1
    body_end = source.find("$function$;", body_start)
    if body_end == -1:
        return ""
    return source[body_start:body_end]


# ══════════════════════════════════════════════════════════════════════════
# CENARIO 1 — Primeiro signup (estado limpo, sem sessao previa)
# ══════════════════════════════════════════════════════════════════════════


def test_cenario_1_primeiro_signup_sem_sessao_previa():
    """Cenario 1 (happy path): um usuario cadastra seu PRIMEIRO email
    num browser limpo (sem sessao previa). O fluxo deve funcionar
    ponta-a-ponta sem nenhum vazamento de estado.

    Componentes verificados:
      1. handleSubmit() no branch else (signup) chama signUp().
      2. signUp() chega ate supabase.auth.signUp() sem pre-consultas
         problematicas.
      3. O frontend chama supabase.rpc('ensure_tenant_row') para
         provisionar a linha inicial do tenant (clientes_blu).
      4. A edge function onboarding-bootstrap chama
         ensure_tenant_row ANTES de onboarding_bootstrap_tx.

    Estrategia: source-inspection, sem runtime.

    Estado atual: GREEN para este cenario (browser limpo, sem
    sessao anterior). O teste serve como REGRESSAO — se algum
    refactor futuro quebrar o cenario 1, este teste pega.
    """
    # (1) handleSubmit() deve ter o branch signup (else) com signUp(...)
    app_src = _read_source(ONBOARDING_APP_PATH)
    handle_submit_body = _extract_function_body(
        app_src, "async function handleSubmit()"
    )
    assert handle_submit_body, "StepAuth.handleSubmit() nao encontrada"
    assert "signUp(email, password)" in handle_submit_body, (
        "Cenario 1 violado: handleSubmit() no branch signup NAO chama "
        "`signUp(email, password)`. Esperado: o branch else (mode !== "
        "'login') executa o signup via useAuth().signUp()."
    )
    assert "signInWithEmail(email, password)" in handle_submit_body, (
        "Cenario 1 violado: handleSubmit() NAO tem o branch de login "
        "chamando signInWithEmail(email, password). O fluxo de login "
        "tambem faz parte do cenario feliz de primeiro acesso."
    )

    # (2) AuthContext.signUp() deve existir e chamar supabase.auth.signUp
    auth_src = _read_source(AUTH_CONTEXT_PATH)
    assert "supabase.auth.signUp" in auth_src, (
        "Cenario 1 violado: AuthContext NAO chama supabase.auth.signUp(). "
        "Esperado: arrow function signUp() delega para o SDK Supabase."
    )

    # (3) O effect de redirect no OnboardingApp deve chamar ensure_tenant_row
    # quando o get_my_client_id() retorna null (novo usuario).
    assert "ensure_tenant_row" in app_src, (
        "Cenario 1 violado: OnboardingApp NAO chama supabase.rpc("
        "'ensure_tenant_row'). Sem isso, o tenant (clientes_blu) NAO e' "
        "criado para o novo usuario, e o bootstrap falha."
    )

    # (4) A edge function deve chamar ensure_tenant_row ANTES de
    # onboarding_bootstrap_tx.
    edge_src = _read_source(EDGE_FN_BOOTSTRAP_PATH)
    code_body = edge_src[edge_src.find("Deno.serve"):]
    idx_ensure = code_body.find("ensure_tenant_row")
    idx_rpc = code_body.find("onboarding_bootstrap_tx")
    assert idx_ensure != -1 and idx_rpc != -1, (
        "Cenario 1 violado: edge function NAO chama ensure_tenant_row e/ou "
        "onboarding_bootstrap_tx."
    )
    assert idx_ensure < idx_rpc, (
        "Cenario 1 violado: ensure_tenant_row DEVE ser chamado ANTES de "
        "onboarding_bootstrap_tx na edge function. Ordem atual:\n"
        f"  ensure_tenant_row em posicao: {idx_ensure}\n"
        f"  onboarding_bootstrap_tx em posicao: {idx_rpc}"
    )


# ══════════════════════════════════════════════════════════════════════════
# CENARIO 2 — Segundo signup (sessao residual vaza) — O BUG DO BATCH
# ══════════════════════════════════════════════════════════════════════════


def test_cenario_2_segundo_signup_limpa_sessao_antes_signup():
    """Cenario 2 (o bug do batch): o usuario A terminou o onboarding
    (sessao ativa, client_id resolvido). Em seguida, o mesmo browser
    faz logout e inicia um novo signup com email B. O fluxo DEVE
    comecar de uma sessao limpa — sem o singleton React (session,
    user, clientId, tier) do usuario A vazando para o cadastro de B.

    Componentes verificados (gate RED -> GREEN):
      2.1. AuthContext.signUp() chama signOut() OU setState reset
            ANTES de supabase.auth.signUp().
      2.2. A trigger DB handle_new_auth_user() usa
            ON CONFLICT (external_user_id) DO UPDATE (atualiza
            updated_at, nome_empresa) — NAO DO NOTHING.
      2.3. O hook useOnboardingDraft reseta o draft quando o
            userEmail muda (segundo signup nao herda o draft de A).
      2.4. O OnboardingApp reseta o ref clientIdChecked quando
            user.id muda (senao o guarda bloqueia o routing do 2o user).

    Estado atual: RED — todos os 4 sub-ACs acima estao ausentes.
    Este teste e' o gate integrado do cenario 2: falha enquanto
    qualquer uma das correcoes nao for aplicada.
    """
    # ── 2.1: AuthContext.signUp() deve limpar sessao antes de signUp ──
    auth_src = _read_source(AUTH_CONTEXT_PATH)
    signup_body = _extract_function_body(auth_src, "const signUp = async")
    assert signup_body, "AuthContext.signUp() nao encontrada"

    signup_call_idx = signup_body.find("supabase.auth.signUp(")
    assert signup_call_idx != -1, (
        "Cenario 2.1 violado: signUp() NAO chama supabase.auth.signUp()."
    )
    pre_signup = signup_body[:signup_call_idx]
    has_signout = "supabase.auth.signOut(" in pre_signup
    has_state_reset = (
        "setState(" in pre_signup
        and ("session: null" in pre_signup or "user: null" in pre_signup)
    )
    assert has_signout or has_state_reset, (
        "Cenario 2.1 violado (RED): AuthContext.signUp() NAO limpa a "
        "sessao existente antes de chamar supabase.auth.signUp().\n"
        "Sintoma: o segundo cadastro herda o singleton React (session, "
        "user, clientId, tier) do primeiro usuario, fazendo o "
        "get_my_client_id() retornar o client_id de A no cadastro de B.\n\n"
        "Correcao esperada (escolher uma):\n"
        "  1. await supabase.auth.signOut() ANTES de supabase.auth.signUp(...)\n"
        "  2. setState({ session: null, user: null, clientId: null,\n"
        "                tier: null, loading: false }) ANTES de signUp\n\n"
        f"Trecho atual do signUp() (pre-signup):\n```\n{pre_signup.strip()}\n```"
    )

    # ── 2.2: Trigger DB deve usar ON CONFLICT DO UPDATE (B-3a) ──
    baseline_src = _read_source(BASELINE_MIGRATION_PATH)
    trigger_body = _plsql_function_body(baseline_src, "handle_new_auth_user()")
    assert trigger_body, (
        "Cenario 2.2 violado: funcao handle_new_auth_user() NAO encontrada "
        "na migration baseline_v2.sql."
    )
    has_do_update = "ON CONFLICT (external_user_id) DO UPDATE" in trigger_body
    has_do_nothing = "ON CONFLICT (external_user_id) DO NOTHING" in trigger_body
    assert has_do_update and not has_do_nothing, (
        "Cenario 2.2 violado (RED): trigger handle_new_auth_user() NAO usa "
        "`ON CONFLICT (external_user_id) DO UPDATE` (B-3a). Atualmente "
        "usa DO NOTHING, que descarta o INSERT no re-signup com o mesmo "
        "external_user_id. Consequencia: updated_at NAO e' atualizado, "
        "nome_empresa NAO reflete o novo email, e o operador nao tem "
        "rastreio do re-signup.\n\n"
        "Correcao esperada:\n"
        "  ON CONFLICT (external_user_id) DO UPDATE SET\n"
        "    updated_at = now(),\n"
        "    nome_empresa = COALESCE(EXCLUDED.nome_empresa,\n"
        "                           clientes_blu.nome_empresa)\n"
        "  RETURNING client_id INTO v_client_id;\n\n"
        f"Trecho atual do trigger:\n```\n{trigger_body.strip()[:500]}\n```"
    )

    # ── 2.3: useOnboardingDraft deve resetar draft quando userEmail muda ──
    draft_src = _read_source(USE_DRAFT_PATH)
    has_useremail_dep = bool(
        re.search(r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*setDraft", draft_src)
        and re.search(r"\[\s*userEmail\s*\]", draft_src)
    )
    has_remount_key = bool(re.search(r"key=\{user\?\.id\}", draft_src))
    assert has_useremail_dep or has_remount_key, (
        "Cenario 2.3 violado (RED): hook useOnboardingDraft NAO reseta o "
        "draft quando o userEmail muda (B-3c). O initializer de useState "
        "roda apenas no mount; o draft do usuario A permanece em memoria "
        "e no localStorage quando o usuario B faz signup.\n\n"
        "Correcao esperada (escolher uma):\n"
        "  1. Adicionar useEffect que observa userEmail e chama "
        "setDraft(initialDraft(userEmail)).\n"
        "  2. No consumidor (OnboardingApp), usar key={user?.id} no "
        "componente-raiz para forcar remount.\n\n"
        f"Trecho atual do hook (primeiras 60 linhas):\n"
        f"```\n{draft_src.split(chr(10))[:60]}\n```"
    )

    # ── 2.4: OnboardingApp deve resetar clientIdChecked quando user.id muda ──
    app_src = _read_source(ONBOARDING_APP_PATH)
    has_reset_ref = bool(
        re.search(
            r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*clientIdChecked\.current\s*=\s*false",
            app_src,
        )
    )
    has_reset_key = bool(
        re.search(
            r"clientIdChecked\s*=\s*useRef<Record<string,\s*boolean>>",
            app_src,
        )
    )
    assert has_reset_ref or has_reset_key, (
        "Cenario 2.4 violado (RED): OnboardingApp NAO reseta o ref "
        "clientIdChecked quando user.id muda (B-3c). O useEffect re-dispara "
        "(porque user?.id mudou), mas o early-return "
        "`if (clientIdChecked.current) return` bloqueia a checagem de "
        "perfil para o segundo usuario.\n\n"
        "Correcao esperada (escolher uma):\n"
        "  1. useEffect(() => { clientIdChecked.current = false }, [user?.id])\n"
        "  2. Trocar para useRef<Record<string, boolean>> e indexar por user.id\n\n"
        f"Trecho relevante do OnboardingApp:\n"
        f"```\n"
        f"{[l for l in app_src.split(chr(10)) if 'clientIdChecked' in l][:8]}\n"
        f"```"
    )


# ══════════════════════════════════════════════════════════════════════════
# CENARIO 3 — Login de usuario existente (signInWithEmail)
# ══════════════════════════════════════════════════════════════════════════


def test_cenario_3_login_usuario_existente_respeita_sessao():
    """Cenario 3: um usuario JA cadastrado (com onboarding completo ou
    incompleto) faz login via email/senha. O fluxo DEVE:

      3.1. handleSubmit() no branch 'login' chama signInWithEmail()
            e NAO chama signUp() (senao cria usuario novo em vez de logar).
      3.2. signInWithEmail() chega ate supabase.auth.signInWithPassword
            (ou signInWithEmail do SDK antigo).
      3.3. O OnboardingApp, apos detectar sessao, consulta
            get_my_client_id(). Se o cliente existe, le o
            onboarding_completed_at e decide entre navigate('/app') ou
            setStep('info'/'data').
      3.4. Nenhuma chamada a supabase.auth.signUp() deve ser disparada
            em modo 'login' — isso e' o que diferencia login de signup.

    Estado atual: GREEN esperado. Teste serve como REGRESSAO para
    garantir que refactors futuros nao quebrem o cenario de login.
    """
    app_src = _read_source(ONBOARDING_APP_PATH)
    handle_submit_body = _extract_function_body(
        app_src, "async function handleSubmit()"
    )
    assert handle_submit_body, "StepAuth.handleSubmit() nao encontrada"

    # (3.1) Branch 'login' chama signInWithEmail
    assert "signInWithEmail(email, password)" in handle_submit_body, (
        "Cenario 3.1 violado: handleSubmit() NAO tem branch 'login' "
        "chamando signInWithEmail(email, password). O fluxo de login "
        "deve ser distinto do fluxo de signup."
    )

    # (3.2) AuthContext deve implementar signInWithEmail
    auth_src = _read_source(AUTH_CONTEXT_PATH)
    assert (
        "supabase.auth.signInWithPassword" in auth_src
        or "supabase.auth.signInWithEmail" in auth_src
    ), (
        "Cenario 3.2 violado: AuthContext NAO implementa signInWithEmail. "
        "Esperado: arrow function signInWithEmail() que delega para "
        "supabase.auth.signInWithPassword() (ou signInWithEmail no SDK "
        "antigo)."
    )

    # (3.3) OnboardingApp consulta get_my_client_id e decide routing
    assert "get_my_client_id" in app_src, (
        "Cenario 3.3 violado: OnboardingApp NAO consulta get_my_client_id "
        "no effect de redirect. Sem isso, o login de usuario existente "
        "nao consegue decidir entre restaurar o wizard ou ir para /app."
    )
    assert "onboarding_completed_at" in app_src, (
        "Cenario 3.3 violado: OnboardingApp NAO checa "
        "onboarding_completed_at apos get_my_client_id(). Sem essa "
        "checagem, usuarios com onboarding completo NAO sao "
        "redirecionados para /app — ficam presos no wizard."
    )
    assert "navigate('/app'" in app_src, (
        "Cenario 3.3 violado: OnboardingApp NAO chama navigate('/app') "
        "no ramo de onboarding completo. Usuarios com onboarding ja "
        "concluido seriam forçados a refazer o wizard."
    )

    # (3.4) Em modo 'login', NAO deve haver chamada a signUp()
    # Procura dentro do branch "if (mode === 'login')" — garante que
    # so' signInWithEmail e' chamado, NAO signUp().
    login_branch_match = re.search(
        r"if\s*\(\s*mode\s*===\s*['\"]login['\"]\s*\)\s*\{(.*?)\}",
        handle_submit_body,
        re.DOTALL,
    )
    assert login_branch_match, (
        "Cenario 3.4 violado: branch 'if (mode === \"login\")' NAO "
        "encontrado em handleSubmit()."
    )
    login_branch = login_branch_match.group(1)
    assert "signInWithEmail(" in login_branch, (
        "Cenario 3.4 violado: branch de login NAO chama signInWithEmail()."
    )
    assert "signUp(" not in login_branch, (
        "Cenario 3.4 violado: branch de login CHAMA signUp() — isso "
        "criaria um usuario novo em vez de autenticar o existente. "
        "Esperado: o branch 'login' so' chama signInWithEmail()."
    )


# ══════════════════════════════════════════════════════════════════════════
# CENARIO 4 — Login OAuth (Google) — signInWithOAuth
# ══════════════════════════════════════════════════════════════════════════


def test_cenario_4_oauth_google_garante_provisionamento_e_redirect():
    """Cenario 4: o usuario clica em 'Continuar com Google' (signup OU
    login). O fluxo DEVE:

      4.1. handleGoogle() chama supabase.auth.signInWithOAuth com
            provider 'google' e redirectTo para /onboarding (modo
            signup ou login).
      4.2. O OnboardingApp, apos o redirect de volta com sessao OAuth,
            consulta get_my_client_id e:
            - Se cliente NAO existe: chama ensure_tenant_row() e
              setStep('info') (novo usuario OAuth).
            - Se cliente existe: navega para /app (usuario OAuth
              retornando).
      4.3. O hook useAuth expõe onAuthStateChange que detecta o
            evento SIGNED_IN vindo do OAuth e atualiza session/user.
      4.4. O handleGoogle NAO chama signUp() (OAuth nao usa
            signUp/password — apenas signInWithOAuth).

    Estado atual: GREEN para o caminho feliz do OAuth (novo usuario
    em browser limpo). O teste serve como REGRESSAO.
    """
    # (4.1) handleGoogle() com signInWithOAuth
    app_src = _read_source(ONBOARDING_APP_PATH)
    handle_google_body = _extract_function_body(
        app_src, "async function handleGoogle()"
    )
    assert handle_google_body, (
        "Cenario 4.1 violado: funcao handleGoogle() NAO encontrada no "
        "OnboardingApp. Esperado: handler do botao 'Continuar com Google'."
    )
    assert "supabase.auth.signInWithOAuth" in handle_google_body, (
        "Cenario 4.1 violado: handleGoogle() NAO chama "
        "supabase.auth.signInWithOAuth. Esperado: chamada com "
        "provider='google' e redirectTo para /onboarding."
    )
    assert "google" in handle_google_body.lower(), (
        "Cenario 4.1 violado: handleGoogle() NAO referencia o provider "
        "'google'. Esperado: provider: 'google' nas options do "
        "signInWithOAuth."
    )
    assert "/onboarding" in handle_google_body, (
        "Cenario 4.1 violado: handleGoogle() NAO define redirectTo para "
        "/onboarding. Sem isso, o usuario OAuth e' redirecionado para "
        "outra rota e perde o wizard."
    )

    # (4.2) OnboardingApp trata sessao OAuth via get_my_client_id
    # + ensure_tenant_row (novo) ou navigate('/app') (existente).
    assert "get_my_client_id" in app_src, (
        "Cenario 4.2 violado: OnboardingApp NAO consulta get_my_client_id "
        "no effect de redirect pos-OAuth. Sem isso, nao consegue "
        "distinguir novo usuario OAuth (criar tenant) de usuario "
        "existente (ir para /app)."
    )
    assert "ensure_tenant_row" in app_src, (
        "Cenario 4.2 violado: OnboardingApp NAO chama ensure_tenant_row "
        "para provisionar tenant de novo usuario OAuth. Sem isso, o "
        "novo usuario OAuth fica sem client_id e o bootstrap falha."
    )
    assert "setStep('info')" in app_src or 'setStep("info")' in app_src, (
        "Cenario 4.2 violado: OnboardingApp NAO chama setStep('info') "
        "como destino pos-auth OAuth para novo usuario."
    )
    assert "navigate('/app'" in app_src, (
        "Cenario 4.2 violado: OnboardingApp NAO redireciona para /app "
        "no caso de usuario OAuth existente."
    )

    # (4.3) AuthContext deve registrar onAuthStateChange para detectar
    # o evento SIGNED_IN vindo do OAuth.
    auth_src = _read_source(AUTH_CONTEXT_PATH)
    assert "onAuthStateChange" in auth_src, (
        "Cenario 4.3 violado: AuthContext NAO registra "
        "supabase.auth.onAuthStateChange. Sem esse listener, a sessao "
        "criada pelo OAuth NAO e' detectada no estado React — o usuario "
        "fica preso em 'loading=true'."
    )
    assert "SIGNED_IN" in auth_src, (
        "Cenario 4.3 violado: onAuthStateChange NAO trata o evento "
        "SIGNED_IN. Esperado: setState({ session, user }) no callback."
    )

    # (4.4) handleGoogle NAO chama signUp() (OAuth puro)
    assert "signUp(" not in handle_google_body, (
        "Cenario 4.4 violado: handleGoogle() CHAMA signUp() — isso esta "
        "errado. OAuth NAO usa o fluxo de signUp com senha; ele usa "
        "signInWithOAuth() que cria o usuario via provider externo."
    )


# ══════════════════════════════════════════════════════════════════════════
# GATE INTEGRADOR — todas as correcoes de log e lock presentes
# ══════════════════════════════════════════════════════════════════════════


def test_gate_integrador_logs_e_concorrencia_presentes():
    """Gate integrador: alem das correcoes dos 4 cenarios de login,
    o batch #202 exige tambem:

      G.1 — AuthContext.signUp() tem console.warn|error|log ANTES de
            supabase.auth.signUp() (B-2/AC#1).
      G.2 — useOnboardingDraft.bootstrap() tem console.error ANTES
            do throw new Error (B-2/AC#2).
      G.3 — Trigger handle_new_auth_user() emite RAISE NOTICE no
            ramo de conflito (B-2/AC#3).
      G.4 — onboarding_bootstrap_tx() faz SELECT ... FOR UPDATE
            antes do UPDATE SET (B-3b).

    Estado atual: RED — nenhum dos 4 sub-ACs esta implementado.
    O gate so' vira GREEN quando TODOS estiverem presentes — esse e'
    o criterio de aceitacao final do batch #202.
    """
    # ── G.1: AuthContext.signUp() com log pre-signup ──
    auth_src = _read_source(AUTH_CONTEXT_PATH)
    signup_body = _extract_function_body(auth_src, "const signUp = async")
    signup_call_idx = signup_body.find("supabase.auth.signUp(")
    pre_signup = signup_body[:signup_call_idx]
    has_console_log = bool(
        re.search(r"console\.(warn|error|log|info|debug)\s*\(", pre_signup)
    )
    assert has_console_log, (
        "G.1 violado (RED): AuthContext.signUp() NAO tem "
        "console.warn|error|log antes de supabase.auth.signUp(). "
        "Sem esse log, e' impossivel saber se havia sessao previa "
        "contaminando o cadastro (B-2/AC#1).\n\n"
        f"Trecho atual (pre-signup):\n```\n{pre_signup.strip()}\n```"
    )

    # ── G.2: useOnboardingDraft.bootstrap() com log pre-throw ──
    draft_src = _read_source(USE_DRAFT_PATH)
    bootstrap_match = re.search(
        r"async\s+function\s+bootstrap\s*\([^)]*\)\s*\{(.*?)(?=\n\s*(?:async\s+function|function|const\s+\w+\s*=\s*|\}|export\s))",
        draft_src,
        re.DOTALL,
    )
    assert bootstrap_match, (
        "G.2 violado: funcao bootstrap() nao encontrada no "
        "useOnboardingDraft."
    )
    bootstrap_body = bootstrap_match.group(1)
    throw_idx = bootstrap_body.find("throw new Error")
    if throw_idx == -1:
        # Pode estar em outro formato (throw new ErrorInline)
        has_console_in_bootstrap = bool(
            re.search(r"console\.(error|warn|log)\s*\(", bootstrap_body)
        )
    else:
        pre_throw = bootstrap_body[:throw_idx]
        has_console_in_bootstrap = bool(
            re.search(r"console\.(error|warn|log)\s*\(", pre_throw)
        )
    assert has_console_in_bootstrap, (
        "G.2 violado (RED): useOnboardingDraft.bootstrap() NAO tem "
        "console.error/warn/log antes do throw new Error(error.message). "
        "Sem esse log, erros da edge function onboarding-bootstrap sao "
        "engolidos silenciosamente (B-2/AC#2).\n\n"
        f"Trecho atual do bootstrap():\n```\n{bootstrap_body[:400]}\n```"
    )

    # ── G.3: Trigger com RAISE NOTICE no ramo de conflito ──
    baseline_src = _read_source(BASELINE_MIGRATION_PATH)
    trigger_body = _plsql_function_body(baseline_src, "handle_new_auth_user()")
    assert trigger_body, (
        "G.3 violado: trigger handle_new_auth_user() nao encontrado."
    )
    has_raise_notice = bool(
        re.search(
            r"RAISE\s+(NOTICE|LOG)\s+['\"](?:handle_new_auth_user|conflito)",
            trigger_body,
            re.IGNORECASE,
        )
    )
    assert has_raise_notice, (
        "G.3 violado (RED): trigger handle_new_auth_user() NAO emite "
        "RAISE NOTICE ou RAISE LOG no ramo de conflito (B-2/AC#3). "
        "Sem isso, o conflito ON CONFLICT DO UPDATE e' invisivel para "
        "o operador — impossivel auditar re-signups.\n\n"
        "Correcao esperada (dentro do IF v_client_id IS NULL THEN ou "
        "equivalente):\n"
        "  RAISE NOTICE 'handle_new_auth_user: conflito em "
        "external_user_id=%, email=%', NEW.id, NEW.email;\n\n"
        f"Trecho atual do trigger:\n```\n{trigger_body.strip()[:500]}\n```"
    )

    # ── G.4: onboarding_bootstrap_tx com SELECT FOR UPDATE ──
    bootstrap_tx_body = _plsql_function_body(
        baseline_src, "onboarding_bootstrap_tx(p_payload jsonb)"
    )
    assert bootstrap_tx_body, (
        "G.4 violado: funcao onboarding_bootstrap_tx(p_payload jsonb) "
        "NAO encontrada na migration baseline."
    )
    has_for_update = bool(
        re.search(
            r"SELECT[^;]*\bclient_id\b[^;]*\bFOR\s+UPDATE\b",
            bootstrap_tx_body,
            re.IGNORECASE | re.DOTALL,
        )
    )
    assert has_for_update, (
        "G.4 violado (RED): onboarding_bootstrap_tx() NAO faz "
        "SELECT ... FOR UPDATE em public.clientes_blu antes do "
        "UPDATE SET (B-3b). Sem o row-level lock, dois submits "
        "simultaneos (duplo clique, retry de rede) podem causar "
        "lost-update em clientes_blu, com nome_empresa, "
        "company_profile, team_structure, policies e "
        "onboarding_completed_at sendo sobrescritos por uma "
        "transacao mais antiga.\n\n"
        "Correcao esperada (antes do UPDATE SET):\n"
        "  SELECT client_id FROM public.clientes_blu\n"
        "  WHERE client_id = v_client_id\n"
        "  FOR UPDATE;\n\n"
        f"Trecho atual do bootstrap_tx() (primeiros 800 chars):\n"
        f"```\n{bootstrap_tx_body.strip()[:800]}\n```"
    )


# ══════════════════════════════════════════════════════════════════════════
# INVARIANTE — o call chain StepAuth -> useAuth -> AuthContext -> supabase
# ══════════════════════════════════════════════════════════════════════════


def test_invariante_call_chain_stepauth_ate_supabase():
    """Invariante cross-cutting: a chamada de signup em
    StepAuth.handleSubmit() DEVE resolver para
    AuthContext.signUp() -> supabase.auth.signUp() (e nao para alguma
    funcao paralela que mascarasse as correcoes de B-1/B-2).

    Este teste e' um guard contra refactors futuros que poderiam
    trocar o caminho do signUp e silenciar os fixes de limpeza de
    sessao / logging.
    """
    app_src = _read_source(ONBOARDING_APP_PATH)
    auth_src = _read_source(AUTH_CONTEXT_PATH)

    # OnboardingApp importa useAuth de @blu/auth
    assert "from '@blu/auth'" in app_src, (
        "Invariante violado: OnboardingApp.tsx NAO importa de '@blu/auth'. "
        "O caminho canonico de signup DEVE passar pelo pacote @blu/auth."
    )
    assert "useAuth" in app_src, (
        "Invariante violado: OnboardingApp NAO chama useAuth()."
    )

    # AuthContext tem o call site supabase.auth.signUp que B-1/B-2 vao patchar
    assert "supabase.auth.signUp" in auth_src, (
        "Invariante violado: AuthContext NAO chama supabase.auth.signUp(). "
        "Esse e' o call site exato que o signOut() pre-signup deve ser "
        "inserido (AC#1) e onde o console.warn pre-signup deve aparecer "
        "(B-2/AC#1)."
    )

    # O @blu/auth expoe o signUp para o consumidor
    blu_auth_index = REPO_ROOT / "packages" / "blu-auth" / "src" / "index.ts"
    index_src = blu_auth_index.read_text() if blu_auth_index.exists() else ""
    assert "signUp" in index_src or "useAuth" in index_src, (
        "Invariante violado: packages/blu-auth/src/index.ts NAO expoe "
        "signUp/useAuth. Sem essa exportacao, OnboardingApp nao consegue "
        "chamar o signUp via useAuth()."
    )
