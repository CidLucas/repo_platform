"""tests/integration/test_sequential_signups.py

B-4: 3 signups sequenciais no mesmo browser — RED.

Este teste é baseado em inspeção de fonte (.tsx/.ts) e verifica que os
mecanismos de proteção contra reuso de sessão estão AUSENTES no estado
atual do código. Todos os 4 ACs devem falhar (RED) hoje; quando o bug for
corrigido, devem passar (GREEN).

Sequência-alvo: carolina@test.blu.sh → lucia@test.blu.sh → joao@test.blu.sh
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

AUTH_CONTEXT = REPO_ROOT / "packages" / "blu-auth" / "src" / "AuthContext.tsx"
ONBOARDING_APP = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "onboarding" / "OnboardingApp.tsx"
AUTH_INDEX = REPO_ROOT / "packages" / "blu-auth" / "src" / "index.ts"

SIGNUP_SEQUENCE = (
    "carolina@test.blu.sh",
    "lucia@test.blu.sh",
    "joao@test.blu.sh",
)


def _extract_function_body(source: str, start_marker: str) -> str:
    """Extrai o corpo de uma função a partir do start_marker.

    Faz um scan por contagem de chaves para localizar o `}` de fechamento
    correspondente ao primeiro `{` após o start_marker. Suporta arrow
    functions e `function` declarations. Levanta ValueError se não encontrar.
    """
    idx = source.find(start_marker)
    if idx == -1:
        raise ValueError(f"start_marker não encontrado: {start_marker!r}")
    brace_open = source.find("{", idx)
    if brace_open == -1:
        raise ValueError(f"chave de abertura não encontrada após {start_marker!r}")
    depth = 0
    for i in range(brace_open, len(source)):
        ch = source[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[brace_open + 1 : i]
    raise ValueError(f"chave de fechamento não encontrada para {start_marker!r}")


def _has_signout_before_signup(signup_body: str) -> bool:
    """Verifica se há uma chamada a supabase.auth.signOut( no corpo de signUp."""
    return "supabase.auth.signOut(" in signup_body


def _has_session_guard(handle_submit_body: str) -> bool:
    """Verifica se há um session/user guard antes do signUp(email, password).

    Critério: o corpo precisa referenciar `session` ou `user` (variáveis do
    useAuth) com um early-return/conditional antes do bloco de signup.
    """
    body = handle_submit_body
    has_session_or_user_ref = bool(
        re.search(r"\b(session|user)\b", body)
    )
    signup_call_match = re.search(r"signUp\s*\(\s*email\s*,\s*password", body)
    if signup_call_match is None:
        return False
    before_signup = body[: signup_call_match.start()]
    has_early_return_before = bool(
        re.search(r"\breturn\b", before_signup)
    )
    return has_session_or_user_ref and has_early_return_before


def _has_onsignup_export(index_source: str) -> bool:
    """Verifica se onSignUp ou useSignUp é exportado pelo @blu/auth."""
    return bool(
        re.search(r"export\s+(?:\{[^}]*\b(onSignUp|useSignUp)\b|const\s+(?:onSignUp|useSignUp)\b)",
                  index_source)
    )


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override do _cleanup_test_data do root conftest.

    Estes testes não tocam no Supabase real — fazem apenas inspeção de
    fonte. Não há nada para limpar.
    """
    yield


def test_ac4_1_authcontext_signup_limpa_sessao_antes_de_signup():
    """AC4.1: AuthContext.signUp() deve chamar signOut() antes de signUp().

    Hoje, o segundo signup herda a sessão do primeiro. RED: a chamada a
    supabase.auth.signOut( está AUSENTE no corpo de signUp.
    """
    assert AUTH_CONTEXT.exists(), f"arquivo não encontrado: {AUTH_CONTEXT}"
    source = AUTH_CONTEXT.read_text(encoding="utf-8")

    start_marker = "const signUp = async"
    signup_body = _extract_function_body(source, start_marker)

    assert _has_signout_before_signup(signup_body), (
        "B-4 / AC4.1 RED: AuthContext.signUp() não chama supabase.auth.signOut( "
        "antes de supabase.auth.signUp(. Sem isso, o segundo signup sequencial "
        "(carolina@test.blu.sh → lucia@test.blu.sh) reusa a sessão do primeiro "
        "e o email do signup em andamento fica vinculado ao client_id errado."
    )


def test_ac4_2_stepauth_handlesubmit_tem_session_guard():
    """AC4.2: StepAuth.handleSubmit() deve checar sessão/usuário antes de
    chamar signUp(email, password).

    Hoje, o guard está AUSENTE — qualquer um pode tentar cadastrar um novo
    email mesmo já estando logado, o que gera o terceiro signup inconsistente
    (joao@test.blu.sh). RED: nenhum early-return baseado em session/user antes
    do signUp.
    """
    assert ONBOARDING_APP.exists(), f"arquivo não encontrado: {ONBOARDING_APP}"
    source = ONBOARDING_APP.read_text(encoding="utf-8")

    start_marker = "async function handleSubmit"
    handle_submit_body = _extract_function_body(source, start_marker)

    assert _has_session_guard(handle_submit_body), (
        "B-4 / AC4.2 RED: StepAuth.handleSubmit() em OnboardingApp.tsx não "
        "possui session/user guard antes de signUp(email, password). Sem o "
        "guard, o fluxo de onboarding aceita um novo signup mesmo com sessão "
        "ativa, e a sequência carolina → lucia → joao fica inconsistente."
    )


def test_ac4_3_blu_auth_exporta_onsignup_ou_usesignup():
    """AC4.3: @blu/auth deve exportar onSignUp ou useSignUp.

    Esses são os hooks que o StepAuth deveria consumir para orquestrar o
    signup "limpo" (signOut → signUp). Hoje o pacote só exporta useAuth.
    RED: nenhum dos dois símbolos está presente em packages/blu-auth/src/index.ts.
    """
    assert AUTH_INDEX.exists(), f"arquivo não encontrado: {AUTH_INDEX}"
    source = AUTH_INDEX.read_text(encoding="utf-8")

    assert _has_onsignup_export(source), (
        "B-4 / AC4.3 RED: @blu/auth (packages/blu-auth/src/index.ts) não "
        "exporta onSignUp nem useSignUp. Sem esses hooks, o consumidor "
        "(OnboardingApp) não tem como garantir que o signOut acontece antes "
        "do signUp na sequência de 3 cadastros."
    )


def test_ac4_4_tres_mecanismos_protecao_ausentes_sequencia_falha():
    """AC4.4: AC4.1 ∧ AC4.2 ∧ AC4.3 — nenhum dos 3 mecanismos existe.

    Combinação: se QUALQUER das 3 proteções existir, a sequência pode
    sobreviver. RED combinado: as 3 proteções estão ausentes ao mesmo
    tempo, então carolina → lucia → joao quebra garantidamente.
    """
    assert AUTH_CONTEXT.exists(), f"arquivo não encontrado: {AUTH_CONTEXT}"
    assert ONBOARDING_APP.exists(), f"arquivo não encontrado: {ONBOARDING_APP}"
    assert AUTH_INDEX.exists(), f"arquivo não encontrado: {AUTH_INDEX}"

    auth_source = AUTH_CONTEXT.read_text(encoding="utf-8")
    onboarding_source = ONBOARDING_APP.read_text(encoding="utf-8")
    index_source = AUTH_INDEX.read_text(encoding="utf-8")

    signup_body = _extract_function_body(auth_source, "const signUp = async")
    handle_submit_body = _extract_function_body(onboarding_source, "async function handleSubmit")

    ac41_ok = _has_signout_before_signup(signup_body)
    ac42_ok = _has_session_guard(handle_submit_body)
    ac43_ok = _has_onsignup_export(index_source)

    assert ac41_ok and ac42_ok and ac43_ok, (
        "B-4 / AC4.4 RED combinado: nenhum dos 3 mecanismos de proteção "
        f"existe — sequência {SIGNUP_SEQUENCE} sempre quebra. "
        f"AC4.1 (signOut no AuthContext.signUp)={ac41_ok}; "
        f"AC4.2 (session guard no StepAuth.handleSubmit)={ac42_ok}; "
        f"AC4.3 (onSignUp/useSignUp exportado por @blu/auth)={ac43_ok}. "
        "Para GREEN, é preciso implementar os 3."
    )
