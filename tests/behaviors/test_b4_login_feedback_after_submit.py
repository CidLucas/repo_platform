"""RED test — B-3 (BATCH #215): Feedback visual apos login email/senha.

GOAL:
    Testar que o ``handleSubmit`` do ``StepAuth`` chama
    ``setSubmitting(false)`` APOS ``signInWithEmail`` completar,
    independentemente de erro ou sucesso, para que o botao ``Entrar``
    saia do estado ``Aguarde...`` e o usuario receba feedback visual.

BEHAVIOR:
    "B-3 — Feedback visual apos login email/senha: o handleSubmit do
    StepAuth chama setSubmitting(false) APOS signInWithEmail completar,
    independentemente de erro ou sucesso, para que o botao Entrar saia
    do estado 'Aguarde...' e o usuario receba feedback visual."

    O handleSubmit de OnboardingApp.tsx (funcao StepAuth) deve garantir
    que apos chamar ``signInWithEmail(email, password)``, o estado
    ``submitting`` seja resetado para ``false`` (saindo do spinner
    "Aguarde..." no botao Entrar), esteja o login em sucesso ou erro.
    Hoje, ``setSubmitting(false)`` so e chamado dentro do branch de
    erro (``if (error) { ... return }``), deixando o botao travado
    em "Aguarde..." apos um login bem-sucedido.

    Estado atual (BEFORE — RED):
        O codigo atual de handleSubmit tem:
          if (mode === login) {
            const { error } = await signInWithEmail(email, password)
            if (error) { setError(error.message); setSubmitting(false); return }
          }
        ``setSubmitting(false)`` so e chamado QUANDO ``error`` existe.
        Login bem-sucedido nunca chama ``setSubmitting(false)``.

    Estado esperado (AFTER — GREEN):
        if (mode === login) {
          const { error } = await signInWithEmail(email, password)
          setSubmitting(false)
          if (error) { setError(error.message); return }
        }

AC (Acceptance Criteria):

    AC#1: Existe um bloco ``if (mode === 'login') { ... }`` dentro de
          ``handleSubmit`` que trata o fluxo de login por email/senha.
          Evidencia: regex encontra o bloco.

    AC#2: ``setSubmitting(false)`` e chamado APOS ``signInWithEmail``
          no bloco de login, no mesmo escopo do bloco (antes do
          ``if (error) { ... return }``).  Evidencia: regex encontra
          ``signInWithEmail`` primeiro, depois ``setSubmitting(false)``,
          depois ``if (error)``, nessa ordem.

    AC#3: ``setSubmitting(false)`` NAO esta aninhado EXCLUSIVAMENTE
          dentro de ``if (error) { ... }`` no bloco de login.  Evidencia:
          existe uma chamada ``setSubmitting(false)`` em uma posicao
          que executa independentemente do resultado (antes ou fora do
          ``if (error)``).

    AC#4: O bloco de login garante que ``setSubmitting(false)`` sempre
          executa apos ``signInWithEmail``, seja antes do ``if (error)``
          ou em ambos os branches (if e else).  Evidencia: se
          ``setSubmitting(false)`` aparece apenas dentro do ``if
          (error)``, AC#4 e violado (caso atual).

Anti-Goals:
    1. NAO modificar codigo de producao (OnboardingApp.tsx).
    2. NAO executar/parsear JSX — somente inspecao textual com regex.
    3. NAO usar mocks, Supabase ou banco de dados.
    4. NAO quebrar funcionalidade existente.
    5. NAO relaxar o teste para que ele passe — precisa ser TRUE RED
       agora (AC#1 passa; AC#2, AC#3 e AC#4 falham).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

ONBOARDING_APP_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "onboarding"
    / "OnboardingApp.tsx"
)


# ── Override do root conftest (teste puramente estático) ──────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    pura inspeção textual, sem teardown no Supabase, sem rede,
    sem execução de JSX.
    """
    yield


# ── Helpers de inspeção textual ───────────────────────────────────────


def _read_source(path: Path) -> str:
    """Lê o arquivo como texto puro (sem parser)."""
    assert path.is_file(), (
        f"Source file not found: {path}.  "
        "O behavior B-3 (BATCH #215) exige que este arquivo exista no repo."
    )
    return path.read_text(encoding="utf-8")


# ── Teste principal (RED) — cobre todos os 4 ACs de B-3 ──────────────


@pytest.mark.behaviors
def test_b4_login_feedback_after_submit_red() -> None:
    """B-3 (BATCH #215) — RED.  Falha enquanto o handleSubmit do
    StepAuth nao chamar ``setSubmitting(false)`` APOS
    ``signInWithEmail`` completar, independentemente de erro ou
    sucesso.

    Agrega a verificacao de TODOS os 4 ACs em uma unica assercao:
    coleta todas as deficiencias e dispara ``pytest.fail`` com
    mensagem consolidada em pt-BR listando o que falta para GREEN.
    """
    problemas: list[str] = []

    # ── Preambulo: verifica existencia do arquivo ───────────────────

    onboarding_exists = ONBOARDING_APP_PATH.is_file()
    if not onboarding_exists:
        problemas.append(
            "[ARQUIVO AUSENTE] O arquivo "
            "`apps/blu_v3/src/pages/onboarding/OnboardingApp.tsx` "
            "NAO existe.  Sem ele, o fluxo de login nao pode ser "
            "verificado."
        )
        cabecalho = (
            "[RED] B-3 (BATCH #215) — Feedback visual apos login "
            f"email/senha — {len(problemas)} AC(s) violado(s):\n"
        )
        detalhes = "\n".join(f"  ✗ {p}" for p in problemas)
        pytest.fail(cabecalho + detalhes)
        return

    onboarding_source = _read_source(ONBOARDING_APP_PATH)

    # ── AC#1 — Existe um bloco if (mode === login) em handleSubmit ───

    # Extrai o conteudo do bloco `if (mode === 'login') { ... }` usando
    # o `} else {` (presente no if/else de login/signup) como ancora de
    # fechamento.  Isso permite localizar o bloco exato mesmo quando
    # ele contem `if (error) { ... }` aninhado.
    login_block_match = re.search(
        r"if\s*\(\s*mode\s*===\s*['\"]login['\"]\s*\)\s*\{(.*?)\}\s*else\s*\{",
        onboarding_source,
        re.DOTALL,
    )

    if login_block_match is None:
        problemas.append(
            "AC#1 — O bloco `if (mode === 'login') { ... }` NAO foi "
            "encontrado dentro de handleSubmit.  Sem este bloco, o "
            "fluxo de login por email/senha nao pode ser implementado."
        )
        cabecalho = (
            "[RED] B-3 (BATCH #215) — Feedback visual apos login "
            f"email/senha — {len(problemas)} AC(s) violado(s):\n"
        )
        detalhes = "\n".join(f"  ✗ {p}" for p in problemas)
        pytest.fail(cabecalho + detalhes)
        return

    login_block = login_block_match.group(1)

    # ── AC#2 — setSubmitting(false) APOS signInWithEmail, antes do if (error) ──

    # Evidencia exigida pelo AC#2: regex encontra, dentro do bloco de
    # login, a ordem `signInWithEmail` → `setSubmitting(false)` →
    # `if (error)`.  No codigo atual, a ordem e
    # `signInWithEmail` → `if (error)` → `setSubmitting(false)`
    # (aninhado dentro do if), entao este AC falha (RED).
    has_signin_then_setSubmitting_then_if_error = bool(
        re.search(
            r"signInWithEmail.*?setSubmitting\s*\(\s*false\s*\).*?if\s*\(\s*error\s*\)",
            login_block,
            re.DOTALL,
        )
    )

    if not has_signin_then_setSubmitting_then_if_error:
        problemas.append(
            "AC#2 — `setSubmitting(false)` NAO e chamado APOS "
            "`signInWithEmail` no escopo do bloco de login (antes do "
            "`if (error)`).  No codigo atual, `setSubmitting(false)` "
            "esta aninhado dentro de `if (error) { ... return }`, o "
            "que significa que o botao Entrar permanece em estado "
            "'Aguarde...' quando o login e bem-sucedido (error === "
            "null).  O codigo precisa chamar `setSubmitting(false)` "
            "em escopo de bloco, entre `signInWithEmail(...)` e "
            "`if (error)`."
        )

    # ── AC#3 — setSubmitting(false) NAO esta aninhado EXCLUSIVAMENTE em if (error) ──

    # Evidencia exigida pelo AC#3: existe uma chamada
    # `setSubmitting(false)` que esta FORA do `if (error) { ... }` no
    # bloco de login (em escopo de bloco, ou no branch else, etc).
    # Para isso, localizamos o primeiro `if (error) { ... }` no bloco
    # de login (considerando que ele nao tem chaves aninhadas) e
    # verificamos se ha `setSubmitting(false)` no texto FORA desse
    # trecho.
    if_error_block_match = re.search(
        r"if\s*\(\s*error\s*\)\s*\{[^{}]*\}",
        login_block,
    )
    if if_error_block_match is not None:
        outside_if_error = (
            login_block[: if_error_block_match.start()]
            + login_block[if_error_block_match.end():]
        )
        has_setSubmitting_outside_if_error = bool(
            re.search(r"setSubmitting\s*\(\s*false\s*\)", outside_if_error)
        )
    else:
        # Se nao ha `if (error)` no bloco, qualquer `setSubmitting(false)`
        # presente esta em escopo de bloco.
        has_setSubmitting_outside_if_error = bool(
            re.search(r"setSubmitting\s*\(\s*false\s*\)", login_block)
        )

    if not has_setSubmitting_outside_if_error:
        problemas.append(
            "AC#3 — `setSubmitting(false)` esta aninhado "
            "EXCLUSIVAMENTE dentro de `if (error) { ... }` no bloco "
            "de login.  Isto significa que `setSubmitting(false)` so "
            "executa quando ha erro; o login bem-sucedido NAO chama "
            "`setSubmitting(false)`, entao o botao Entrar permanece "
            "em estado 'Aguarde...' indefinidamente ate o usuario "
            "recarregar a pagina.  O codigo precisa chamar "
            "`setSubmitting(false)` em escopo de bloco (antes do "
            "`if (error)`) OU em ambos os branches (if e else)."
        )

    # ── AC#4 — setSubmitting(false) sempre executa apos signInWithEmail ──

    # Evidencia exigida pelo AC#4: o bloco de login deve garantir que
    # `setSubmitting(false)` sempre executa apos `signInWithEmail`,
    # seja antes do `if (error)` (escopo de bloco) ou em ambos os
    # branches.  Como o teste de "fora do if (error)" acima ja
    # captura ambos os casos (escopo de bloco OU else branch), usamos
    # a mesma evidencia.  Se `setSubmitting(false)` aparece apenas
    # dentro do `if (error)`, AC#4 e violado.
    if not has_setSubmitting_outside_if_error:
        problemas.append(
            "AC#4 — O bloco de login NAO garante que "
            "`setSubmitting(false)` sempre executa apos "
            "`signInWithEmail`.  No codigo atual, "
            "`setSubmitting(false)` so e chamado dentro de "
            "`if (error) { ... }`, o que NAO cobre o caminho de "
            "login bem-sucedido (error === null).  O codigo deve "
            "chamar `setSubmitting(false)` antes do `if (error)` "
            "(em escopo de bloco) OU em ambos os branches (if e else) "
            "para garantir que o feedback visual sempre ocorra."
        )

    # ── Agrega todas as deficiencias ─────────────────────────────────

    if problemas:
        cabecalho = (
            "[RED] B-3 (BATCH #215) — Feedback visual apos login "
            f"email/senha — {len(problemas)} AC(s) violado(s):\n"
        )
        detalhes = "\n".join(f"  ✗ {p}" for p in problemas)
        pytest.fail(cabecalho + detalhes)
