"""RED test for behavior B2 — ``signUp()`` sem ``signOut()`` previo em
``StepAuth.handleSubmit()`` quebra o segundo signup.

GOAL:
    Garantir que ``StepAuth.handleSubmit()`` em
    ``apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx`` chame
    ``signOut()`` (ou ``supabase.auth.signOut()``) ANTES de executar
    ``signUp(email, password)`` no branch ``else`` (signup).

    Sem esse ``signOut()`` previo, a sessao ativa de um signup/login
    anterior permanece viva no client Supabase, e o segundo ``signUp``
    retorna ``Auth session missing!`` (ou similar) ou herda o
    ``client_id`` do usuario anterior, quebrando o fluxo de onboarding
    para o segundo usuario.

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

HANDLESUBMIT_LINE_START = 316
HANDLESUBMIT_LINE_END = 336
STEPAUTH_USEAUTH_LINE = 298

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


# ── AC#1 — signOut() NAO e' chamado antes de signUp() no else branch ───


def test_b2_ac1_handleSubmit_else_nao_chama_signout_antes_de_signup():
    """AC#1: no branch ``else`` de ``StepAuth.handleSubmit()`` (linhas
    316-336 do ``OnboardingApp.tsx``), ``signOut()`` ou
    ``supabase.auth.signOut()`` NAO e' chamado antes de
    ``signUp(email, password)``.

    O estado RED e' exatamente este: ``signOut()`` esta' ausente do
    bloco ``else``, fazendo com que o segundo ``signUp`` herde a
    sessao anterior e quebre (erro ``Auth session missing!`` no
    backend, ou o novo signup acaba vinculado ao ``client_id`` do
    usuario anterior).
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

    # O bloco else NAO deve chamar ``signOut()`` nem
    # ``supabase.auth.signOut()`` antes de ``signUp(email, password)``.
    # Esta' e' a condicao RED: o signOut nao existe.
    signout_match = RE_SIGNOUT_CALL.search(else_block)
    assert not signout_match, (
        f"AC#1 violated: `signOut()` ou `supabase.auth.signOut()` "
        f"foi encontrado no bloco `else` de `handleSubmit()` em "
        f"{ONBOARDING_APP_PATH}, mas o AC#1 exige que NAO esteja "
        f"presente ate' a fase GREEN.\n"
        f"  - Bloco `else` atual: {else_block}\n"
        f"  - Match encontrado: {signout_match.group(0)}\n"
        f"  - Esperado (RED): nenhuma chamada a `signOut()` antes "
        f"de `signUp(email, password)` no `else`.\n"
        f"  - Correcao esperada (GREEN): adicionar "
        f"`await signOut()` (ou `await supabase.auth.signOut()`) "
        f"como primeira linha do `else`, antes de "
        f"`await signUp(email, password)`."
    )


# ── AC#2 — useAuth() desestrutura apenas signInWithEmail e signUp ───────


def test_b2_ac2_stepauth_useauth_nao_destructura_signout():
    """AC#2: em ``StepAuth`` linha 298 do ``OnboardingApp.tsx``,
    ``useAuth()`` desestrutura APENAS ``{ signInWithEmail, signUp }``,
    sem ``signOut``.

    Sem ``signOut`` no destructure, o componente NAO tem como chamar
    ``signOut()`` antes de ``signUp()`` — bug estrutural que precisa
    ser corrigido adicionando ``signOut`` ao destructure (e
    ``signOut`` na implementacao do hook ``useAuth()`` em
    ``apps/blu_v3/src/auth/AuthProvider.tsx`` ou similar).
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

    # O destructure NAO deve conter ``signOut`` (estado RED: bug
    # estrutural — o componente nao expoe a funcao necessaria).
    assert "signOut" not in destructured_names, (
        f"AC#2 violated: `signOut` esta' no destructure de "
        f"`useAuth()` na linha {STEPAUTH_USEAUTH_LINE} de "
        f"{ONBOARDING_APP_PATH}, mas o AC#2 exige que NAO esteja "
        f"presente ate' a fase GREEN.\n"
        f"  - Destructure atual: {{ {destructured.strip()} }}\n"
        f"  - Nomes encontrados: {destructured_names}\n"
        f"  - Esperado (RED): apenas `signInWithEmail` e `signUp`.\n"
        f"  - Correcao esperada (GREEN): adicionar `signOut` ao "
        f"destructure, e.g. "
        f"`const {{ signInWithEmail, signUp, signOut }} = useAuth()`, "
        f"e implementar `signOut` no hook `useAuth()` "
        f"(provavelmente em `apps/blu_v3/src/auth/AuthProvider.tsx` "
        f"ou equivalente) chamando `supabase.auth.signOut()`."
    )


# ── AC#3 — RED consolidado: pytest.fail() em pt-BR ──────────────────────


def test_b2_red_signup_sem_signout_quebra_segundo_signup():
    """RED consolidado para B2: falha explicitamente enquanto
    ``signOut()`` nao for chamado antes de ``signUp()`` em
    ``StepAuth.handleSubmit()``.

    Estado atual (RED): o destructure de ``useAuth()`` na linha 298
    expoe apenas ``{ signInWithEmail, signUp }``, e o branch ``else``
    de ``handleSubmit()`` (linhas 327-331) chama
    ``signUp(email, password)`` sem chamar ``signOut()`` antes.

    Consequencia: o segundo signup herda a sessao do primeiro
    usuario. Dependendo do estado de RLS e do backend Supabase, o
    segundo signup pode:
      (a) falhar com ``Auth session missing!`` ou erro similar
          retornado pelo backend, OU
      (b) ser concluido, mas o novo ``auth.users`` acaba vinculado
          ao ``client_id`` errado (do primeiro usuario), quebrando
          isolamento de dados e onboarding.

    A correcao (GREEN) deve:
      1. Adicionar ``signOut`` ao destructure de ``useAuth()`` na
         linha 298 de ``apps/blu_v3/src/pages/onboarding/
         OnboardingApp.tsx``.
      2. Implementar ``signOut`` no hook ``useAuth()`` (em
         ``apps/blu_v3/src/auth/AuthProvider.tsx`` ou arquivo
         equivalente) chamando ``supabase.auth.signOut()`` e
         limpando o estado local do provider.
      3. No branch ``else`` de ``handleSubmit()``, adicionar
         ``await signOut()`` como primeira linha, ANTES de
         ``await signUp(email, password)``.
    """
    assert ONBOARDING_APP_PATH.exists(), (
        f"Source file not found: {ONBOARDING_APP_PATH}. "
        "RED check requires OnboardingApp.tsx to exist."
    )

    source = ONBOARDING_APP_PATH.read_text(encoding="utf-8")
    lines = source.splitlines()

    # ── Avalia AC#1: signOut no else de handleSubmit ──
    handlesubmit_block = "\n".join(
        lines[HANDLESUBMIT_LINE_START - 1 : HANDLESUBMIT_LINE_END]
    )
    else_match = RE_ELSE_BLOCK.search(handlesubmit_block)
    else_block = else_match.group(1) if else_match else ""
    signup_in_else = bool(RE_SIGNUP_CALL.search(else_block))
    signout_in_else = bool(RE_SIGNOUT_CALL.search(else_block))

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

    # GREEN: a falha RED deixa de existir quando
    # (a) signOut() aparece no else de handleSubmit ANTES de signUp(), E
    # (b) signOut esta' no destructure de useAuth() na linha 298.
    green_already_applied = (
        signup_in_else
        and signout_in_else
        and signout_in_destructure
    )

    if green_already_applied:
        # Caso a fase GREEN ja' tenha sido aplicada em alguma iteracao
        # anterior, nao falhamos RED — deixamos os testes AC#1 e AC#2
        # validarem com mais detalhes.
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
