"""RED test for behavior B-5 — Correção estrutural consolidada.

GOAL:
    Garantir que TODAS as correções estruturais descritas no root-cause doc
    ``docs/observability/auth-second-signup-root-cause.md`` NÃO estão
    implementadas ainda (TRUE RED).

    O teste falha provando que o pipeline de correção ainda não foi aplicado
    — cada Acceptance Criteria (AC) passa (assert True) confirmando que o
    bug ainda existe no código fonte.

BEHAVIOR:
    B-5 — Correção estrutural consolidada do pipeline de Auth
    (Batch #202: "segundo cadastro de email falha").

    Consolida 5 ACs, cada um confirmando que uma correção específica AINDA
    NÃO EXISTE no código:

    AC#1 — AuthContext.signUp() carece de ``signOut()`` antes de ``signUp()``
    AC#2 — Trigger ``handle_new_auth_user`` usa ``DO NOTHING`` em vez de ``DO UPDATE``
    AC#3 — ``onboarding_bootstrap_tx`` carece de ``SELECT FOR UPDATE``
    AC#4 — ``clientIdChecked`` ref nunca é resetado entre signups
    AC#5 — ``useOnboardingDraft`` carece de ``useEffect([userEmail])``

ESTADO ATUAL:
    RED — todas as ACs confirmam que o bug ainda existe.
    Uma vez que as correções forem implementadas (fase GREEN), cada AC
    deve falhar com pytest.fail(), sinalizando FALSE RED (correção já
    aplicada). Por ora, todas passam = TRUE RED.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ── Constants ──────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

AUTH_CONTEXT_PATH = (
    REPO_ROOT / "packages" / "blu-auth" / "src" / "AuthContext.tsx"
)

BASELINE_SQL_PATH = (
    REPO_ROOT / "supabase" / "migrations" / "20260523999999_baseline_v2.sql"
)

ONBOARDING_APP_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "onboarding" / "OnboardingApp.tsx"
)

ONBOARDING_DRAFT_PATH = (
    REPO_ROOT / "apps" / "blu_v3" / "src" / "hooks" / "useOnboardingDraft.ts"
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _read_file(path: Path) -> str:
    assert path.exists(), f"Arquivo não encontrado: {path}"
    return path.read_text(encoding="utf-8")


# ── AC#1: AuthContext.signUp carece de signOut() antes de signUp() ────────

def test_b5_ac1_auth_context_signup_sem_signout() -> None:
    """
    AC#1 — RED: AuthContext.signUp() NÃO chama supabase.auth.signOut() antes
    de supabase.auth.signUp().

    Lógica:
        - Se o arquivo contém ".signOut(" → a correção JÁ FOI APLICADA
          → pytest.fail("FALSE RED: correção já implementada")
        - Caso contrário → assert True → TRUE RED confirmado
    """
    content = _read_file(AUTH_CONTEXT_PATH)

    import re

    # Extrai o corpo da função signUp: entre "const signUp = async" e "  }"
    # (a função tem indentação de 2 espaços, termina com "  }")
    sign_up_match = re.search(
        r"const signUp\s*=\s*async\s*\([^)]*\)\s*=>\s*\{"
        r"(.*?)\n  \}",
        content,
        re.DOTALL,
    )
    assert sign_up_match, (
        "Não foi possível localizar o corpo da função signUp() em AuthContext.tsx"
    )

    sign_up_body = sign_up_match.group(1)

    # Procura por signOut() dentro do corpo da função signUp
    if ".signOut(" in sign_up_body:
        pytest.fail(
            "FALSE RED — AC#1: AuthContext.signUp() já contém "
            "supabase.auth.signOut() antes de signUp(). "
            "Correção já implementada — este teste deveria falhar na fase GREEN."
        )

    # Se chegou aqui, a correção NÃO existe → TRUE RED
    assert True, (
        "TRUE RED confirmado — AC#1: AuthContext.signUp() ainda chama "
        "supabase.auth.signUp() sem signOut() prévio. "
        "A sessão do usuário anterior vaza no segundo cadastro."
    )


# ── AC#2: Trigger handle_new_auth_user usa DO NOTHING, não DO UPDATE ─────

def test_b5_ac2_trigger_handle_new_auth_user_do_nothing() -> None:
    """
    AC#2 — RED: Trigger ``handle_new_auth_user`` usa ``ON CONFLICT DO NOTHING``
    em vez de ``ON CONFLICT DO UPDATE SET updated_at``.

    Lógica:
        - Se o arquivo contém "ON CONFLICT (external_user_id) DO UPDATE SET"
          → pytest.fail (correção já implementada)
        - Caso contrário, e contém "DO NOTHING" → TRUE RED confirmado
    """
    content = _read_file(BASELINE_SQL_PATH)

    if "ON CONFLICT (external_user_id) DO UPDATE SET" in content:
        pytest.fail(
            "FALSE RED — AC#2: handle_new_auth_user já usa "
            "ON CONFLICT DO UPDATE SET em vez de DO NOTHING. "
            "Correção já implementada."
        )

    # Confirma que ainda usa DO NOTHING (TRUE RED)
    assert (
        "ON CONFLICT (external_user_id) DO NOTHING" in content
        and "DO UPDATE SET" not in content.split("ON CONFLICT (external_user_id)")[1:][0]
        if "ON CONFLICT (external_user_id)" in content
        else False
    ), (
        "TRUE RED confirmado — AC#2: trigger handle_new_auth_user ainda usa "
        "ON CONFLICT DO NOTHING. O re-signup com mesmo external_user_id "
        "descartará o INSERT silenciosamente sem atualizar updated_at."
    )


# ── AC#3: onboarding_bootstrap_tx carece de SELECT FOR UPDATE ─────────────

def test_b5_ac3_onboarding_bootstrap_tx_sem_for_update() -> None:
    """
    AC#3 — RED: ``onboarding_bootstrap_tx`` NÃO faz ``SELECT ... FOR UPDATE``
    antes de ``UPDATE public.clientes_blu SET``.

    Lógica:
        - Se "FOR UPDATE" aparece antes de "UPDATE public.clientes_blu SET"
          dentro da função → pytest.fail (correção já implementada)
        - Caso contrário → TRUE RED (lost-update possível)
    """
    content = _read_file(BASELINE_SQL_PATH)

    # Encontra o início da função onboarding_bootstrap_tx
    func_start = content.find("onboarding_bootstrap_tx")
    if func_start == -1:
        pytest.fail("FALSE RED — AC#3: função onboarding_bootstrap_tx não encontrada no SQL.")

    func_body = content[func_start:]

    # Verifica se FOR UPDATE aparece antes do UPDATE SET
    for_update_pos = func_body.find("FOR UPDATE")
    update_pos = func_body.find("UPDATE public.clientes_blu SET")

    if for_update_pos != -1 and for_update_pos < update_pos:
        pytest.fail(
            "FALSE RED — AC#3: onboarding_bootstrap_tx já contém "
            "SELECT FOR UPDATE antes do UPDATE SET. "
            "Correção já implementada — lost-update prevenido."
        )

    assert True, (
        "TRUE RED confirmado — AC#3: onboarding_bootstrap_tx ainda carece "
        "de SELECT FOR UPDATE antes do UPDATE SET. "
        "Dois submits simultâneos podem causar lost-update em clientes_blu."
    )


# ── AC#4: clientIdChecked ref nunca resetado entre signups ────────────────

def test_b5_ac4_clientid_checked_ref_nao_resetado() -> None:
    """
    AC#4 — RED: ``clientIdChecked`` ref em OnboardingApp.tsx NUNCA é resetado
    quando ``user.id`` muda.

    Lógica:
        - Se existe ``useEffect`` com ``user?.id`` que reseta
          ``clientIdChecked.current = false`` → pytest.fail
        - Caso contrário → TRUE RED (guarda permanente bloqueia novo signup)
    """
    content = _read_file(ONBOARDING_APP_PATH)

    # Procura por um useEffect que reseta clientIdChecked com user?.id
    # Padrão esperado (GREEN): useEffect(() => { clientIdChecked.current = false }, [user?.id])
    import re

    green_pattern = re.compile(
        r"useEffect\s*\(\s*\(\)\s*=>\s*[^}]*clientIdChecked\s*\.\s*current\s*=\s*false",
        re.DOTALL,
    )

    if green_pattern.search(content):
        pytest.fail(
            "FALSE RED — AC#4: OnboardingApp.tsx já implementa reset de "
            "clientIdChecked ref via useEffect([user?.id]). "
            "Correção já implementada."
        )

    # Verifica se o ref ainda existe (bug presente)
    ref_pattern = re.compile(r"const\s+clientIdChecked\s*=\s*useRef\s*\(\s*false\s*\)")
    set_pattern = re.compile(r"clientIdChecked\s*\.\s*current\s*=\s*true")

    assert ref_pattern.search(content) and set_pattern.search(content), (
        "TRUE RED — Mas o ref clientIdChecked não foi encontrado "
        "no formato esperado. Verificar se a estrutura mudou."
    )

    if set_pattern.search(content) and ref_pattern.search(content):
        assert True, (
            "TRUE RED confirmado — AC#4: clientIdChecked.current = true "
            "permanece entre signups. Nenhum useEffect([user?.id]) reseta "
            "o ref para false. A guarda bloqueia o fetch de client_id "
            "no segundo cadastro."
        )


# ── AC#5: useOnboardingDraft carece de useEffect([userEmail]) ────────────

def test_b5_ac5_onboarding_draft_sem_useffect_user_email() -> None:
    """
    AC#5 — RED: ``useOnboardingDraft`` NÃO tem ``useEffect([userEmail])`` para
    resetar o draft quando o email do usuário muda.

    Lógica:
        - Se existe ``useEffect`` com ``userEmail`` na dependência e
          ``setDraft(initialDraft(...))`` no callback → pytest.fail
        - Caso contrário → TRUE RED (draft do usuário A contamina B)
    """
    content = _read_file(ONBOARDING_DRAFT_PATH)

    import re

    # Padrão esperado (GREEN): useEffect com userEmail na dependência e
    # setDraft(initialDraft) ou similar resetando o draft
    green_pattern = re.compile(
        r"useEffect\s*\(\s*\(\)\s*=>\s*\{[^}]*"
        r"(?:setDraft|initialDraft)"
        r"[^}]*\}?\s*,\s*\[userEmail\]",
        re.DOTALL,
    )

    if green_pattern.search(content):
        pytest.fail(
            "FALSE RED — AC#5: useOnboardingDraft.ts já implementa "
            "useEffect([userEmail]) para resetar o draft. "
            "Correção já implementada."
        )

    assert True, (
        "TRUE RED confirmado — AC#5: useOnboardingDraft ainda carece de "
        "useEffect([userEmail]) para resetar o draft. "
        "Quando userEmail muda, o hook continua retornando dados "
        "do usuário anterior (draft A contamina B)."
    )
