"""GREEN test for behavior B2 — ``signUp()`` com ``signOut()`` previo em
``StepAuth.handleSubmit()`` para evitar contaminacao de sessao.

Validates the GREEN phase: ``StepAuth.handleSubmit()`` em
``apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx`` DEVE chamar
``signOut()`` (ou ``supabase.auth.signOut()``) ANTES de executar
``signUp(email, password)`` no branch ``else`` (signup), e ``signOut``
DEVE estar no destructure de ``useAuth()``.

Phase 0.1 (commit 1f60c82e) shipped this fix. These tests are now
GREEN: they verify the fix is in place and would FAIL if someone
regressed the bug back. The previous RED assertion was inverted
(it asserted the bug existed, which was wrong once the fix landed).

BEHAVIOR:
    B2 — ``signUp()`` em ``StepAuth.handleSubmit()`` deve ser precedido
    de ``signOut()`` (ou ``supabase.auth.signOut()``) para garantir
    que cada signup comeca de uma sessao limpa.

    Cadeia do fluxo de signup:
        user clica "Criar conta"
            -> handleSubmit() (mode === 'signup')
                -> signOut()                     <-- OBRIGATORIO
                -> signUp(email, password)       <-- so' funciona apos signOut
                    -> onNext()                  -> proxima step do onboarding

AC (Acceptance Criteria):
    AC#1 — No branch ``else`` de ``StepAuth.handleSubmit()`` (linhas
            316-336 do ``OnboardingApp.tsx``), ``signOut()`` ou
            ``supabase.auth.signOut()`` NAO e' chamado antes de
            ``signUp(email, password)``.
    AC#2 — Em ``StepAuth`` linha 298, ``useAuth()`` desestrutura
            APENAS ``{ signInWithEmail, signUp }`` — ``signOut`` NAO
            esta' disponivel no escopo do componente.
    AC#3 — RED consolidado: ``pytest.fail()`` em pt-BR enquanto a
            correcao (adicionar ``signOut()`` antes de ``signUp()``)
            nao existir.

DECISAO:
    Estrategia: source_inspection (leitura do arquivo .tsx como texto).
    Arquivo alvo:
        - apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx
    Sem mock, sem DB, sem fixtures de runtime.

Estado atual: RED — ``StepAuth`` (linha 298) desestrutura
``useAuth()`` em ``{ signInWithEmail, signUp }`` apenas, e o
``handleSubmit()`` (linhas 316-336) chama ``signUp(email, password)``
sem chamar ``signOut()`` antes. O teste falha via ``pytest.fail()``
em pt-BR ate' que a correcao seja aplicada na fase GREEN para
satisfazer os AC#1..AC#3 do comportamento B2.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Constants: the public interface under test ──────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ONBOARDING_APP_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "onboarding"
    / "OnboardingApp.tsx"
)

HANDLESUBMIT_LINE_START = 324
HANDLESUBMIT_LINE_END = 352
STEPAUTH_USEAUTH_LINE = 306

# Regex para extrair o bloco ``else`` de handleSubmit.
# Aceita variantes como:
#       } else {
#         const { error } = await signUp(email, password)
#         if (error) { setError(error.message); setSubmitting(false); return }
#         onNext()
#       }
RE_ELSE_BLOCK = re.compile(
    r"\}\s*else\s*\{(.*?)\n\s*\}",
    re.DOTALL,
)

# Regex para identificar chamada ``signUp(email, password)`` no
# contexto do handleSubmit.
RE_SIGNUP_CALL = re.compile(
    r"\bsignUp\s*\(\s*email\s*,\s*password\s*\)",
)

# Regex para identificar chamada ``signOut()`` ou
# ``supabase.auth.signOut()`` no contexto do handleSubmit.
RE_SIGNOUT_CALL = re.compile(
    r"\b(?:supabase\.auth\.signOut\s*\(\s*\)|signOut\s*\(\s*\))",
)

# Regex para identificar o destructure do ``useAuth()``.
# Aceita variantes como:
#   const { signInWithEmail, signUp } = useAuth()
#   const { signInWithEmail, signUp, signOut } = useAuth()
RE_USEAUTH_DESTRUCTURE = re.compile(
    r"const\s*\{([^}]*)\}\s*=\s*useAuth\s*\(\s*\)",
)


# ── Override root conftest cleanup (no real Supabase needed) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file I/O, no DB teardown."""
    yield


# ── AC#1 — signOut() DEVE ser chamado antes de signUp() no else branch ───


def test_b2_ac1_handleSubmit_else_chama_signout_antes_de_signup():
    """AC#1 (GREEN): no branch ``else`` de ``StepAuth.handleSubmit()``
    (linhas 316-336 do ``OnboardingApp.tsx``), ``signOut()`` ou
    ``supabase.auth.signOut()`` DEVE ser chamado antes de
    ``signUp(email, password)``.

    Validates the Phase 0.1 fix (commit 1f60c82e): a sessao ativa de
    um signup/login anterior e' limpa antes do novo signup, evitando
    contaminacao entre usuarios no mesmo browser. Sem esse ``signOut``
    previo, o segundo ``signUp`` herdaria a sessao anterior e
    quebraria (erro ``Auth session missing!`` no backend, ou o novo
    signup acabaria vinculado ao ``client_id`` do usuario anterior).
    """
    assert ONBOARDING_APP_PATH.exists(), (
        f"Source file not found: {ONBOARDING_APP_PATH}. "
        "AC#1 requires inspecting OnboardingApp.tsx."
    )

    source = ONBOARDING_APP_PATH.read_text(encoding="utf-8")

    # Particiona o arquivo em linhas para extrair o handleSubmit().
    lines = source.splitlines()
    handlesubmit_block = "\n".join(
        lines[HANDLESUBMIT_LINE_START - 1 : HANDLESUBMIT_LINE_END]
    )

    # Localiza o bloco ``else { ... }`` dentro de handleSubmit.
    else_match = RE_ELSE_BLOCK.search(handlesubmit_block)
    assert else_match, (
        f"AC#1 violated: bloco `else {{ ... }}` nao encontrado em "
        f"`handleSubmit()` (linhas {HANDLESUBMIT_LINE_START}-"
        f"{HANDLESUBMIT_LINE_END}) de {ONBOARDING_APP_PATH}. "
        f"Nao foi possivel avaliar a presenca de `signOut()` antes "
        f"de `signUp()`."
    )

    else_block = else_match.group(1)

    # O bloco else DEVE conter ``signUp(email, password)``.
    assert RE_SIGNUP_CALL.search(else_block), (
        f"AC#1 violated: `signUp(email, password)` nao encontrado no "
        f"bloco `else` de `handleSubmit()` em {ONBOARDING_APP_PATH}. "
        f"O teste pressupoe que o `else` faz o signup; sem ele, o "
        f"AC#1 nao faz sentido."
    )

    # AC#1 (GREEN): `signOut()` DEVE ser chamado em handleSubmit ANTES
    # do `signUp(email, password)`. O fix do Phase 0.1 evoluiu de
    # `signOut` dentro do `else` (versao inicial) para um guard no
    # topo de handleSubmit: `if (mode === 'signup') { await signOut() }`
    # seguido do signup no `else` (defense in depth). Esta assertion
    # valida qualquer das duas patterns: signOut no escopo de
    # handleSubmit ANTES do signUp call.
    signout_match = RE_SIGNOUT_CALL.search(handlesubmit_block)
    signup_pos = handlesubmit_block.find("signUp(email, password)")
    signout_pos = handlesubmit_block.find("signOut()")
    signout_before_signup = (
        signout_match is not None
        and signup_pos != -1
        and signout_pos != -1
        and signout_pos < signup_pos
    )
    assert signout_before_signup, (
        f"AC#1 REGRESSED: `signOut()` NAO foi chamado em `handleSubmit()` "
        f"ANTES de `signUp(email, password)` em {ONBOARDING_APP_PATH}. "
        f"O Phase 0.1 (commit 1f60c82e) fixou a contaminacao de sessao "
        f"adicionando `await signOut()` como guard antes do signup. "
        f"Se este teste falha, alguem removeu a linha — REVERTER "
        f"imediatamente.\n"
        f"  - handleSubmit block (linhas "
        f"{HANDLESUBMIT_LINE_START}-{HANDLESUBMIT_LINE_END}): "
        f"{handlesubmit_block}\n"
        f"  - Esperado (GREEN): `await signOut()` (ou "
        f"`await supabase.auth.signOut()`) em algum lugar de "
        f"handleSubmit ANTES de `await signUp(email, password)`."
    )


# ── AC#2 — useAuth() DEVE destructurar signOut (fix Phase 0.1) ──────────


def test_b2_ac2_stepauth_useauth_destructura_signout():
    """AC#2 (GREEN): em ``StepAuth`` linha 298 do ``OnboardingApp.tsx``,
    ``useAuth()`` DEVE destructurar ``signOut`` alem de
    ``signInWithEmail`` e ``signUp``.

    Sem ``signOut`` no destructure, o componente NAO tem como chamar
    ``signOut()`` antes de ``signUp()`` — bug estrutural que foi
    corrigido no Phase 0.1 (commit 1f60c82e) adicionando ``signOut``
    ao destructure e implementando a funcao no hook ``useAuth()`` em
    ``packages/blu-auth/src/AuthContext.tsx``.
    """
    assert ONBOARDING_APP_PATH.exists(), (
        f"Source file not found: {ONBOARDING_APP_PATH}. "
        "AC#2 requires inspecting OnboardingApp.tsx."
    )

    source = ONBOARDING_APP_PATH.read_text(encoding="utf-8")
    lines = source.splitlines()

    assert STEPAUTH_USEAUTH_LINE <= len(lines), (
        f"AC#2 violated: linha {STEPAUTH_USEAUTH_LINE} nao existe em "
        f"{ONBOARDING_APP_PATH} (arquivo tem {len(lines)} linhas). "
        f"Nao foi possivel inspecionar o destructure de `useAuth()` "
        f"em `StepAuth`."
    )

    useauth_line = lines[STEPAUTH_USEAUTH_LINE - 1]

    # A linha 298 deve conter o destructure do useAuth.
    match = RE_USEAUTH_DESTRUCTURE.search(useauth_line)
    assert match, (
        f"AC#2 violated: `const {{ ... }} = useAuth()` nao "
        f"encontrado na linha {STEPAUTH_USEAUTH_LINE} de "
        f"{ONBOARDING_APP_PATH}.\n"
        f"  - Linha atual: {useauth_line!r}\n"
        f"  - O teste pressupoe que `StepAuth` desestrutura "
        f"`useAuth()` na linha {STEPAUTH_USEAUTH_LINE}; sem essa "
        f"linha, AC#2 nao pode ser avaliado."
    )

    destructured = match.group(1)
    destructured_names = [
        name.strip()
        for name in destructured.split(",")
        if name.strip()
    ]

    # O destructure deve conter ``signInWithEmail`` e ``signUp``.
    assert "signInWithEmail" in destructured_names, (
        f"AC#2 violated: `signInWithEmail` nao esta' no destructure "
        f"de `useAuth()` na linha {STEPAUTH_USEAUTH_LINE} de "
        f"{ONBOARDING_APP_PATH}.\n"
        f"  - Destructure atual: {{ {destructured.strip()} }}\n"
        f"  - Esperado: `signInWithEmail` e `signUp`."
    )

    assert "signUp" in destructured_names, (
        f"AC#2 violated: `signUp` nao esta' no destructure de "
        f"`useAuth()` na linha {STEPAUTH_USEAUTH_LINE} de "
        f"{ONBOARDING_APP_PATH}.\n"
        f"  - Destructure atual: {{ {destructured.strip()} }}\n"
        f"  - Esperado: `signInWithEmail` e `signUp`."
    )

    # O destructure DEVE conter ``signOut`` (fix Phase 0.1).
    # Esta assertion e' GREEN: valida que o fix esta' em vigor.
    assert "signOut" in destructured_names, (
        f"AC#2 REGRESSED: `signOut` NAO esta' no destructure de "
        f"`useAuth()` na linha {STEPAUTH_USEAUTH_LINE} de "
        f"{ONBOARDING_APP_PATH}. Phase 0.1 (commit 1f60c82e) "
        f"adicionou `signOut` ao destructure para permitir o "
        f"pattern de defesa em profundidade "
        f"(`if (mode === 'signup') await signOut()` antes do "
        f"signup). Se este teste falha, alguem removeu `signOut` do "
        f"destructure — REVERTER imediatamente.\n"
        f"  - Destructure atual: {{ {destructured.strip()} }}\n"
        f"  - Nomes encontrados: {destructured_names}\n"
        f"  - Esperado (GREEN): "
        f"`const {{ signInWithEmail, signUp, signOut }} = useAuth()`."
    )


# ── AC#3 — RED consolidado: pytest.fail() em pt-BR ──────────────────────


def test_b2_red_signup_sem_signout_quebra_segundo_signup():
    """GREEN consolidado para B2: passa enquanto o fix Phase 0.1 estiver
    em vigor — ``signOut()`` chamado antes de ``signUp()`` em
    ``StepAuth.handleSubmit()``.

    Phase 0.1 (commit 1f60c82e) shipped the fix:

      1. Adicionado ``signOut`` ao destructure de ``useAuth()`` em
         ``apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx``.
      2. ``signOut`` implementado no hook ``useAuth()`` (em
         ``packages/blu-auth/src/AuthContext.tsx``) chamando
         ``supabase.auth.signOut()`` e limpando o estado local.
      3. ``await signOut()`` adicionado no topo de ``handleSubmit()``
         como guard (``if (mode === 'signup') await signOut()``),
         antes do branch que chama ``await signUp(email, password)``.

    Este teste so' falha se o fix for REVERTIDO — nesse caso, o
    segundo signup herda a sessao do primeiro usuario e quebra
    (erro ``Auth session missing!`` no backend, ou o novo
    ``auth.users`` acaba vinculado ao ``client_id`` errado,
    quebrando isolamento de dados e onboarding).
    """
    assert ONBOARDING_APP_PATH.exists(), (
        f"Source file not found: {ONBOARDING_APP_PATH}. "
        "GREEN check requires OnboardingApp.tsx to exist."
    )

    source = ONBOARDING_APP_PATH.read_text(encoding="utf-8")
    lines = source.splitlines()

    # ── Avalia AC#1: signOut em handleSubmit ANTES de signUp() ──
    handlesubmit_block = "\n".join(
        lines[HANDLESUBMIT_LINE_START - 1 : HANDLESUBMIT_LINE_END]
    )
    else_match = RE_ELSE_BLOCK.search(handlesubmit_block)
    else_block = else_match.group(1) if else_match else ""
    signup_in_else = bool(RE_SIGNUP_CALL.search(else_block))
    signup_pos = handlesubmit_block.find("signUp(email, password)")
    signout_pos = handlesubmit_block.find("signOut()")
    signout_in_handlesubmit_before_signup = (
        signup_in_else
        and signout_pos != -1
        and signup_pos != -1
        and signout_pos < signup_pos
    )

    # ── Avalia AC#2: signOut no destructure de useAuth ──
    useauth_line = (
        lines[STEPAUTH_USEAUTH_LINE - 1]
        if STEPAUTH_USEAUTH_LINE <= len(lines)
        else ""
    )
    useauth_match = RE_USEAUTH_DESTRUCTURE.search(useauth_line)
    destructured_names: list[str] = []
    if useauth_match:
        destructured_names = [
            name.strip()
            for name in useauth_match.group(1).split(",")
            if name.strip()
        ]
    signout_in_destructure = "signOut" in destructured_names

    # GREEN: o fix esta' em vigor quando
    # (a) signOut() aparece em handleSubmit ANTES de signUp(), E
    # (b) signOut esta' no destructure de useAuth() na linha 298.
    green_in_place = (
        signout_in_handlesubmit_before_signup
        and signout_in_destructure
    )

    if green_in_place:
        # Fix em vigor. Passa silenciosamente.
        return

    pytest.fail(
        f"B2 RED: `signUp()` em `StepAuth.handleSubmit()` NAO e' "
        f"precedido de `signOut()` em "
        f"{ONBOARDING_APP_PATH.relative_to(REPO_ROOT)}, quebrando o "
        f"segundo signup.\n\n"
        f"  - AC#1 violado: branch `else` de `handleSubmit()` "
        f"(linhas {HANDLESUBMIT_LINE_START}-{HANDLESUBMIT_LINE_END}) "
        f"NAO chama `signOut()` (nem `supabase.auth.signOut()`) "
        f"antes de `signUp(email, password)`.\n"
        f"      - signUp() presente no else: {signup_in_else}\n"
        f"      - signOut() presente no else: {signout_in_else}\n"
        f"  - AC#2 violado: destructure de `useAuth()` na linha "
        f"{STEPAUTH_USEAUTH_LINE} expoe apenas "
        f"{{ {', '.join(destructured_names) if destructured_names else '(nao encontrado)'} }}"
        f" — `signOut` NAO esta' disponivel no escopo de `StepAuth`.\n\n"
        f"Estado atual (RED):\n"
        f"  - Usuario A faz signup/login -> sessao A persiste no "
        f"client Supabase.\n"
        f"  - Usuario B tenta fazer signup em outra aba/janela -> "
        f"`signUp()` e' chamado sem `signOut()` previo.\n"
        f"  - Backend Supabase pode retornar erro "
        f"`Auth session missing!`, OU o novo `auth.users` acaba "
        f"vinculado ao `client_id` do Usuario A.\n"
        f"  - Resultado: onboarding do Usuario B quebra "
        f"(isolamento de dados violado, ou signup falha em "
        f"silencio).\n\n"
        f"Comportamento desejado (GREEN):\n"
        f"  1. Adicionar `signOut` ao destructure de `useAuth()` "
        f"na linha {STEPAUTH_USEAUTH_LINE} de "
        f"{ONBOARDING_APP_PATH.relative_to(REPO_ROOT)}:\n"
        f"         const {{ signInWithEmail, signUp, signOut }} = "
        f"useAuth()\n"
        f"  2. Implementar `signOut` no hook `useAuth()` "
        f"(provavelmente em "
        f"apps/blu_v3/src/auth/AuthProvider.tsx ou arquivo "
        f"equivalente), chamando `supabase.auth.signOut()` e "
        f"limpando o estado local do provider.\n"
        f"  3. No branch `else` de `handleSubmit()` (linha ~327), "
        f"adicionar `await signOut()` como PRIMEIRA acao, ANTES "
        f"de `await signUp(email, password)`:\n"
        f"         }} else {{\n"
        f"           await signOut()\n"
        f"           const {{ error }} = await signUp(email, "
        f"password)\n"
        f"           if (error) {{ setError(error.message); "
        f"setSubmitting(false); return }}\n"
        f"           onNext()\n"
        f"         }}\n\n"
        f"Risco:\n"
        f"  - 100% dos signups subsequentes ao primeiro em uma "
        f"sessao ativa quebram.\n"
        f"  - Risco de cross-client data leak se o backend nao "
        f"validar o `external_user_id` (cliente B ve' dados do "
        f"cliente A durante o signup).\n"
        f"  - UX ruim: usuario B nao consegue criar conta sem "
        f"antes deslogar manualmente.\n\n"
        f"Proximo passo (fase GREEN):\n"
        f"  - Editar "
        f"{ONBOARDING_APP_PATH.relative_to(REPO_ROOT)} seguindo "
        f"os 3 passos descritos acima, e implementar `signOut` "
        f"no hook `useAuth()` caso ainda nao exista."
    )
