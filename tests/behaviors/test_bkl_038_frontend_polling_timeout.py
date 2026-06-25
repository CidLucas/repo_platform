"""RED test for behavior BKL-038 — Frontend polling stops after 2 minutes.

GOAL:
    AC#1 — Polling for knowledge-base document status in
    ``apps/blu_v3/src/hooks/useKnowledgeBase.ts`` must stop after 2
    minutes and surface the user-facing error message
    'Falha no processamento'.

BEHAVIOR:
    BKL-038 — Timeout do polling: para após 2 minutos com mensagem
    'Falha no processamento'.

    In ``apps/blu_v3/src/hooks/useKnowledgeBase.ts`` the polling
    ``useEffect`` (lines 54-65) currently:
        - Filters ``state.documents`` to transient states
          ('processing' or 'pending') (lines 55-57).
        - Spawns ``setInterval(load, 5_000)`` (lines 60-62).
        - Clears the interval on unmount or dep change
          (``return () => clearInterval(interval)`` at line 64).

    There is NO upper bound on how long this polling runs. If the
    backend never reports the document as ready, the polling continues
    forever, the user sees an indefinite 'processing' state, and no
    error is surfaced.

    After the fix, the polling effect must:
        - Define a constant ``POLLING_TIMEOUT_MS = 120_000`` (2 minutes).
        - Track elapsed time inside the polling useEffect (e.g. via a
          local ``elapsed`` counter, a parallel ``setTimeout``, or
          comparing ``Date.now() - start`` to the timeout).
        - When the timeout is reached, ``clearInterval(interval)`` and
          surface the user-facing message 'Falha no processamento' —
          typically via ``setState({ error: 'Falha no processamento' })``
          or a similar mechanism.
        - Preserve the existing early-cleanup behavior: polling must
          still stop when ``state.documents`` changes or the component
          unmounts.

AC (Acceptance Criteria):
    AC#1 — Polling para APÓS 2 minutos com mensagem
           'Falha no processamento'.

Anti-Goals (must NOT be violated):
    1. NÃO alterar a primeira ``useEffect`` (linhas 49-51) — ela
       continua responsável por carregar os documentos na montagem.
    2. NÃO remover o cleanup de ``clearInterval(interval)`` — o
       polling ainda deve parar quando ``state.documents`` mudar ou
       o componente desmontar (early-stop continua obrigatório).
    3. NÃO introduzir dependências novas (ex.: bibliotecas de
       timer) — usar APIs nativas do browser (``setTimeout``,
       ``clearTimeout``, ``Date.now()``).
    4. NÃO alterar a interface pública do hook
       (``useKnowledgeBase()``) — apenas o corpo do ``useEffect``
       de polling.

Estado atual: RED — o polling atual no ``useEffect`` (linhas 54-65)
não tem limite de tempo, não define a constante ``POLLING_TIMEOUT_MS``,
não contém a string 'Falha no processamento' e não tem tracking de
tempo decorrido. O teste parseia o source TypeScript como texto
(source-inspection puro) e valida as 4 asserções de AC#1, falhando
com AssertionError até que a feature seja implementada na fase GREEN.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

HOOK_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "hooks"
    / "useKnowledgeBase.ts"
)


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure source inspection, no DB teardown."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_hook_source() -> str:
    """Return the full text of ``useKnowledgeBase.ts``.

    Raises an ``AssertionError`` if the file is missing — the test should
    fail loudly with a clear message rather than silently passing on a
    missing file.
    """
    assert HOOK_PATH.exists(), f"Source file not found: {HOOK_PATH}"
    return HOOK_PATH.read_text(encoding="utf-8")


def _extract_polling_effect(source: str) -> str:
    """Return the body of the polling ``useEffect`` (the one containing ``setInterval``).

    Walks every ``useEffect(`` in ``source``, locates the body of its
    effect callback — the arrow function between ``useEffect(() => {``
    and the matching ``}, [...]`` — using brace-depth counting that
    ignores braces inside strings (single, double, backtick), line
    comments, and block comments, and returns the first body whose
    contents reference ``setInterval``.

    Returns an empty string if no such useEffect is found, which lets
    the caller distinguish "no polling effect" from "polling effect
    exists but lacks the timeout feature".
    """
    for match in re.finditer(r"useEffect\s*\(", source):
        arrow_idx = source.find("=>", match.end())
        if arrow_idx == -1:
            continue
        brace_open_idx = source.find("{", arrow_idx)
        if brace_open_idx == -1:
            continue
        depth = 1
        j = brace_open_idx + 1
        in_string = None  # None | '"' | "'" | "`"
        in_line_comment = False
        in_block_comment = False
        while j < len(source) and depth > 0:
            ch = source[j]
            nxt = source[j + 1] if j + 1 < len(source) else ""
            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
                j += 1
                continue
            if in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    j += 2
                    continue
                j += 1
                continue
            if in_string is not None:
                if ch == "\\":
                    j += 2
                    continue
                if ch == in_string:
                    in_string = None
                    j += 1
                    continue
                j += 1
                continue
            if ch == "/" and nxt == "/":
                in_line_comment = True
                j += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                j += 2
                continue
            if ch in ('"', "'", "`"):
                in_string = ch
                j += 1
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            j += 1
        if depth != 0:
            continue
        body = source[brace_open_idx + 1 : j - 1]
        if "setInterval" in body:
            return body
    return ""


# ── Tests ────────────────────────────────────────────────────────────────


def test_bkl_038_polling_has_no_timeout_limit():
    """AC#1 — Polling deve parar APÓS 2 minutos com mensagem 'Falha no processamento'.

    BKL-038 currently has NO timeout limit. The polling ``useEffect``
    (lines 54-65 of ``useKnowledgeBase.ts``) spawns
    ``setInterval(load, 5_000)`` and only stops when ``state.documents``
    changes or the component unmounts — never based on elapsed time.

    This RED test asserts that the timeout feature MUST be present
    (so it FAILS today). Once the feature is implemented in the GREEN
    phase, all 4 assertions below will pass.
    """
    source = _read_hook_source()
    polling_effect = _extract_polling_effect(source)

    # Sanity check: we must be able to locate the polling useEffect.
    # If this fails, the hook was refactored in a way that no longer
    # exposes a setInterval-based polling effect, which means the
    # BKL-038 target moved or was rewritten.
    assert polling_effect, (
        f"Não foi possível extrair o corpo do `useEffect` de polling de "
        f"{HOOK_PATH}. O hook pode ter sido refatorado, o padrão "
        "`useEffect(() => { ... }, [deps])` pode não estar mais presente, "
        "ou não há nenhum `useEffect` que referencie `setInterval` "
        "(que é o efeito de polling que BKL-038 visa limitar a 2 minutos)."
    )

    # 1) A constante POLLING_TIMEOUT_MS = 120_000 (2 minutos) deve ser
    #    definida no arquivo. Sem essa constante nomeada, o polling não
    #    tem como expressar/declarar seu limite de tempo.
    timeout_const_re = re.compile(
        r"(?:const|let|var)\s+POLLING_TIMEOUT_MS\s*=\s*120_?000\b"
    )
    assert timeout_const_re.search(source), (
        "AC#1 violada: o arquivo `useKnowledgeBase.ts` NÃO define a "
        "constante `POLLING_TIMEOUT_MS = 120_000` (2 minutos). Behavior "
        "BKL-038 requer que o polling tenha um limite explícito de 2 "
        "minutos, expresso por uma constante `POLLING_TIMEOUT_MS` igual "
        "a `120_000` (ou `120000`). Sem essa constante, o polling atual "
        "roda indefinidamente e nenhum erro é exibido ao usuário após "
        "o timeout."
    )

    # 2) A string 'Falha no processamento' deve estar presente no
    #    arquivo. É a mensagem de erro user-facing que deve aparecer
    #    quando o timeout de 2 minutos expira.
    assert "Falha no processamento" in source, (
        "AC#1 violada: a string 'Falha no processamento' NÃO está "
        "presente em `useKnowledgeBase.ts`. Behavior BKL-038 requer "
        "que, ao atingir o timeout de 2 minutos, o hook exiba a "
        "mensagem de erro 'Falha no processamento' para o usuário "
        "(tipicamente via "
        "`setState({ error: 'Falha no processamento' })` ou um "
        "`setTimeout(() => setError('Falha no processamento'), "
        "POLLING_TIMEOUT_MS)` no efeito de polling)."
    )

    # 3) O `useEffect` de polling deve conter lógica de timeout. Hoje
    #    ele só tem `setInterval` + `clearInterval`, sem nenhum
    #    mecanismo de limite superior baseado em tempo.
    has_set_timeout = "setTimeout" in polling_effect
    has_clear_timeout = "clearTimeout" in polling_effect
    has_elapsed = re.search(r"\belapsed\b", polling_effect, re.IGNORECASE) is not None
    assert has_set_timeout or has_clear_timeout or has_elapsed, (
        "AC#1 violada: o `useEffect` de polling (linhas 54-65) NÃO "
        "contém lógica de timeout. Behavior BKL-038 requer que o "
        "polling tenha algum mecanismo para limitar sua duração a 2 "
        "minutos — seja via `setTimeout`/`clearTimeout` (ex.: um timer "
        "paralelo que dispara o erro 'Falha no processamento' após "
        "`POLLING_TIMEOUT_MS`) ou via tracking de tempo decorrido "
        "(ex.: variável `elapsed` incrementada a cada tick e "
        "comparada com `POLLING_TIMEOUT_MS`). Hoje o polling só tem "
        "`setInterval` e `clearInterval`, sem nenhum limite superior."
    )

    # 4) O `useEffect` de polling deve referenciar `POLLING_TIMEOUT_MS`
    #    para acionar a parada. Isso garante que o timeout não é só
    #    declarado em algum lugar do arquivo, mas de fato USADO dentro
    #    do efeito que precisa parar.
    assert "POLLING_TIMEOUT_MS" in polling_effect, (
        "AC#1 violada: o `useEffect` de polling não referencia a "
        "constante `POLLING_TIMEOUT_MS`. Behavior BKL-038 requer que o "
        "polling USE a constante de timeout para decidir quando parar "
        "(ex.: `if (elapsed >= POLLING_TIMEOUT_MS) { "
        "clearInterval(interval); setState({ error: 'Falha no "
        "processamento' }); }` ou `setTimeout(stop, "
        "POLLING_TIMEOUT_MS)`). Apenas definir a constante no topo "
        "do arquivo não basta — ela precisa ser consumida dentro do "
        "`useEffect` de polling. Hoje o polling nunca para por tempo "
        "decorrido, apenas por mudança de `state.documents` ou "
        "desmontagem do componente."
    )
