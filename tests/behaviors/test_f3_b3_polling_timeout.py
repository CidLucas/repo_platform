"""RED test for behavior F-3-B3 — Timeout no polling do useKnowledgeBase com auto-fail.

GOAL:
    Documentos que ficam em "processing" por mais de 2 minutos devem ser
    tratados como falha desconhecida, com botão de reprocessar visível.

BEHAVIOR:
    F-3-B3 — Timeout no polling do useKnowledgeBase com auto-fail (2min).

    Em ``apps/blu_v3/src/hooks/useKnowledgeBase.ts`` o polling useEffect
    (linhas 53-65) atualmente:
        - Faz ``setInterval(load, 5_000)`` enquanto houver qualquer doc
          em status ``processing`` ou ``pending``.
        - NÃO possui nenhum mecanismo de timeout — o hook fica em polling
          infinito se o documento permanecer em ``processing`` para sempre.
        - Não detecta documentos "presos" (stuck).

    Em ``apps/blu_v3/src/pages/app/BibliotecaRoom.tsx``:
        - ``kbStatusBadge(status)`` (linhas 37-46) só conhece cinco status
          (``completed``/``processing``/``pending``/``failed``/``partially_failed``)
          e mapeia ``processing`` para "Processando…" sem checar idade.
        - ``DocCard`` (linhas 62-182) e ``DocRow`` (linhas 186-238) só
          mostram o botão "↻ Reprocessar" para ``failed`` e
          ``partially_failed`` — nunca para ``processing`` preso.

    Após o fix, o hook deve:
        (a) Rastrear quando cada documento entrou em "processing".
        (b) Parar o polling após 120_000ms (2 minutos) se nenhum
            documento mudou de status (sem progresso real).
        (c) ``clearInterval`` + ``clearTimeout`` no cleanup do effect.

    E a UI deve:
        (d) Mostrar badge "falha desconhecida" para docs em processing
            há mais de 2min.
        (e) Mostrar o botão "↻ Reprocessar" (DocCard e DocRow) também
            para docs cujo processing expirou (timed-out).

AC (Acceptance Criteria):
    AC#1 — useKnowledgeBase para de fazer polling após 2min se nenhum
           doc mudar de status. Implementa: tracking de start, corte em
           120000ms, clearInterval+clearTimeout no cleanup.
    AC#2 — Documentos presos em "processing" > 2min aparecem como
           "falha desconhecida" E exibem botão "↻ Reprocessar" no
           DocCard e no DocRow.
    AC#3 — Opcional (skip in RED, only if endpoint exists).

Anti-Goals (must NOT be violated):
    1. NÃO alterar a assinatura pública de ``useKnowledgeBase`` (mesmo
       retorno, mesmos campos). O fix pode adicionar um state interno
       (timedOutIds) e expor via um novo campo derivado, mas não pode
       quebrar consumidores existentes.
    2. NÃO alterar ``knowledgeBaseService.ts`` (apenas o hook e a UI).
    3. NÃO alterar o intervalo de polling de 5s — só adicionar o timeout
       máximo de 2min.

Estado atual: RED — o polling em ``useKnowledgeBase.ts`` não tem
nenhuma referência a ``120000``, ``setTimeout``, ``timeout``,
``stale`` ou ``processingStart``; e ``BibliotecaRoom.tsx`` não tem
"falha desconhecida" nem botão de reprocessar para processing
timed-out. Os testes parseiam o source TypeScript como texto puro
(source-inspection) e falham com AssertionError até que a feature
seja implementada na fase GREEN.
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

UI_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "BibliotecaRoom.tsx"
)


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure source inspection, no DB teardown."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _load(path: Path) -> str:
    """Load a TypeScript file and assert it exists."""
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text()


def _extract_use_effect_body(source: str, marker_comment_regex: str) -> str:
    """Return the body of the first useEffect that comes after a comment
    matching ``marker_comment_regex``.

    Walks from the comment to the ``useEffect(() => {`` call, then uses
    brace-depth counting to extract the callback body.
    """
    marker = re.search(marker_comment_regex, source)
    assert marker is not None, (
        f"Could not find marker comment matching {marker_comment_regex!r} "
        f"in source."
    )
    use_effect = re.search(
        r"useEffect\s*\(\s*\(\s*\)\s*=>\s*\{",
        source[marker.end():],
    )
    assert use_effect is not None, (
        f"Could not find `useEffect(() => {{ ... }})` after marker comment "
        f"matching {marker_comment_regex!r}."
    )
    body_start = marker.end() + use_effect.end()
    return _extract_balanced_braces(source, body_start)


def _extract_balanced_braces(source: str, start: int) -> str:
    """From position ``start`` (just after an opening ``{``), extract the
    matching closed-brace substring.  Tracks strings, comments, and
    template-literal expressions like ``_extract_function_body`` does.
    """
    brace_depth = 1
    k = start
    in_string = None
    in_line_comment = False
    in_block_comment = False
    while k < len(source) and brace_depth > 0:
        ch = source[k]
        nxt = source[k + 1] if k + 1 < len(source) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            k += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                k += 2
                continue
            k += 1
            continue
        if in_string is not None:
            if ch == "\\":
                k += 2
                continue
            if ch == in_string:
                in_string = None
                k += 1
                continue
            if in_string == "`":
                if ch == "$" and nxt == "{":
                    brace_depth += 1
                    k += 2
                    continue
                if ch == "}":
                    brace_depth -= 1
                    k += 1
                    continue
            k += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            k += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            k += 2
            continue
        if ch in ('"', "'", "`"):
            in_string = ch
            k += 1
            continue
        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
        k += 1
    if brace_depth != 0:
        return ""
    return source[start : k - 1]


def _extract_function_body(source: str, func_name: str) -> str:
    """Return the body of the first ``function <func_name>(...)`` (or arrow
    ``const <func_name> = ...``). Mirrors the pattern in
    ``test_bkl_041_upload_complex_to_process_document.py``.
    """
    pattern = rf"(?:export\s+)?(?:async\s+)?function\s+{re.escape(func_name)}\s*\("
    match = re.search(pattern, source)
    if match is None:
        const_pattern = rf"(?:export\s+)?const\s+{re.escape(func_name)}\s*="
        const_match = re.search(const_pattern, source)
        if const_match is None:
            return ""
        arrow_idx = source.find("=>", const_match.end())
        if arrow_idx == -1:
            return ""
        brace_idx = source.find("{", arrow_idx)
        if brace_idx == -1:
            return ""
        return _extract_balanced_braces(source, brace_idx + 1)

    start = match.end()
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        char = source[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        i += 1
    if depth != 0:
        return ""

    j = i
    while j < len(source) and source[j] != "{":
        j += 1
    if j >= len(source):
        return ""

    return _extract_balanced_braces(source, j + 1)


def _extract_component_body(source: str, component_name: str) -> str:
    """Return the body of a React component defined as
    ``function <ComponentName>({ ... }: { ... }) { ... }``.
    """
    pattern = rf"(?:export\s+)?function\s+{re.escape(component_name)}\s*\("
    match = re.search(pattern, source)
    if not match:
        return ""

    start = match.end()
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        char = source[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        i += 1
    if depth != 0:
        return ""

    j = i
    while j < len(source) and source[j] != "{":
        j += 1
    if j >= len(source):
        return ""

    return _extract_balanced_braces(source, j + 1)


# ── AC#1 — Polling timeout in useKnowledgeBase.ts ───────────────────────


def test_f3_b3_hook_contains_120000ms_timeout_constant():
    """AC#1 — O hook deve referenciar o timeout de 2 minutos (120_000ms).

    O polling useEffect precisa de um teto de 2 minutos para interromper
    a espera quando o documento não progride.  A forma mais simples
    (e mais comum em código React/TS) é uma constante ``120_000`` ou
    ``120000`` declarada no arquivo.  Atualmente o arquivo não contém
    nenhum timeout máximo — o ``setInterval`` roda indefinidamente.
    """
    source = _load(HOOK_PATH)
    assert "120000" in source or "120_000" in source, (
        "AC#1 violated: `useKnowledgeBase.ts` não contém a constante de "
        "timeout de 2 minutos (`120000` ou `120_000`). Behavior F-3-B3 "
        "requer que o polling useEffect pare de fazer polling após 2 "
        "minutos se nenhum documento mudar de status. Adicione um "
        "constante `POLLING_TIMEOUT_MS = 120_000` (ou similar) e use-a "
        "para agendar o cancelamento do `setInterval`."
    )


def test_f3_b3_hook_polling_use_effect_uses_settimeout_to_cut_polling():
    """AC#1 — O useEffect de polling deve usar ``setTimeout`` (além de
    ``setInterval``) para interromper o polling após 2min.

    Implementação esperada: ao montar o effect, agenda-se
    ``setTimeout(() => { clearInterval(interval); ... }, 120_000)``
    que para o polling se nenhum doc progrediu.
    """
    source = _load(HOOK_PATH)
    body = _extract_use_effect_body(
        source,
        r"//\s*Poll while any document is in a transient state",
    )
    assert body, (
        "Setup error: não foi possível extrair o corpo do useEffect de "
        "polling em `useKnowledgeBase.ts`. Verifique se o comentário "
        "'Poll while any document is in a transient state' ainda existe "
        "e precede o useEffect."
    )
    assert "setTimeout" in body, (
        "AC#1 violated: o useEffect de polling em `useKnowledgeBase.ts` "
        "não usa `setTimeout`. Behavior F-3-B3 requer que o polling seja "
        "interrompido após 2 minutos (120_000ms) se nenhum documento "
        "mudar de status. É necessário agendar um `setTimeout` que chame "
        "`clearInterval(interval)` após o timeout, e limpar esse "
        "timeout no cleanup do effect."
    )


def test_f3_b3_hook_polling_use_effect_clears_timeout_in_cleanup():
    """AC#1 — O useEffect de polling deve limpar o timeout no cleanup
    (junto com o clearInterval) para não deixar timers órfãos.

    O return do useEffect deve conter tanto ``clearInterval`` quanto
    ``clearTimeout`` (ou um helper que faça ambos).
    """
    source = _load(HOOK_PATH)
    body = _extract_use_effect_body(
        source,
        r"//\s*Poll while any document is in a transient state",
    )
    assert body, "Setup error: useEffect de polling não encontrado."
    assert "return" in body, (
        "Setup error: useEffect de polling não possui `return` de cleanup."
    )
    assert "clearInterval" in body, (
        "Setup error: useEffect de polling não chama `clearInterval`."
    )
    assert "clearTimeout" in body, (
        "AC#1 violated: o useEffect de polling em `useKnowledgeBase.ts` "
        "faz cleanup com `clearInterval` mas não limpa o `setTimeout` "
        "do timeout de 2 minutos. Behavior F-3-B3 requer que ambos os "
        "timers sejam liberados no cleanup para evitar vazamento de "
        "timers em re-renders."
    )


def test_f3_b3_hook_tracks_processing_start_for_staleness_check():
    """AC#1 — O hook deve rastrear quando o processing começou (timestamp
    de início) para identificar documentos "stuck" (presos por >2min).

    A presença de tracking é fundamental: sem saber há quanto tempo um
    doc está em "processing", não há como aplicar o auto-fail.  Padrões
    aceitáveis incluem refs (``processingStartRef``), useMemo, ou um
    state com timestamp de início do polling.
    """
    source = _load(HOOK_PATH)
    body = _extract_use_effect_body(
        source,
        r"//\s*Poll while any document is in a transient state",
    )
    assert body, "Setup error: useEffect de polling não encontrado."

    # Padrões aceitáveis para tracking de início do processing.
    has_timestamp_ref = bool(
        re.search(r"processingStart", body)
        or re.search(r"pollingStart", body)
        or re.search(r"stale", body)
    )
    has_date_now_call = "Date.now()" in body
    has_comparison = bool(
        re.search(r"Date\.now\(\)\s*-\s*\w+", body)
        or re.search(r"\w+\s*-\s*Date\.now\(\)", body)
        or re.search(r">\s*120", body)  # comparação com 120_000 / 120000
    )

    assert has_timestamp_ref or has_date_now_call, (
        "AC#1 violated: o useEffect de polling em `useKnowledgeBase.ts` "
        "não rastreia quando o processing começou. Behavior F-3-B3 "
        "requer tracking do timestamp de início (ex.: "
        "`const processingStart = Date.now()` ou um "
        "`useRef<number>`) para identificar docs 'presos' (stuck) há "
        "mais de 2 minutos."
    )
    assert has_comparison, (
        "AC#1 violated: o useEffect de polling em `useKnowledgeBase.ts` "
        "não compara o tempo decorrido com o timeout de 2 minutos. "
        "Behavior F-3-B3 requer uma comparação do tipo "
        "`Date.now() - processingStart > 120_000` (ou equivalente) "
        "para detectar docs stuck e acionar o auto-fail."
    )


# ── AC#2 — UI: "falha desconhecida" badge + botão reprocessar ──────────


def test_f3_b3_bibliotecaroom_kbstatusbadge_has_falha_desconhecida_label():
    """AC#2 — ``kbStatusBadge`` (ou a função que produz o badge label)
    deve incluir o rótulo "falha desconhecida" para documentos em
    processing há mais de 2min.

    A string exata esperada é "falha desconhecida" (case-insensitive).
    Atualmente a função só conhece os cinco status canônicos e mapeia
    ``processing`` para "Processando…", sem distinção de timeout.
    """
    source = _load(UI_PATH)
    assert "falha desconhecida" in source.lower(), (
        "AC#2 violated: `BibliotecaRoom.tsx` não contém o rótulo "
        "'falha desconhecida'. Behavior F-3-B3 requer que documentos "
        "presos em 'processing' por mais de 2 minutos sejam "
        "apresentados com o badge 'falha desconhecida' (em vez de "
        "'Processando…'). Adicione um caso timeout-aware em "
        "`kbStatusBadge` (ou função equivalente) que produza esse "
        "rótulo quando o processing exceder 2 minutos."
    )


def test_f3_b3_bibliotecaroom_doccard_shows_reprocess_for_timed_out_processing():
    """AC#2 — ``DocCard`` deve mostrar o botão "↻ Reprocessar" também
    para documentos cujo processing expirou (timed-out), não apenas
    para ``failed``/``partially_failed``.

    Atualmente a condição em ``DocCard`` (linhas 163-171) só renderiza
    o botão quando ``doc.status === 'failed' || doc.status === 'partially_failed'``.
    Após o fix, a condição deve também cobrir o caso
    ``processing-timed-out``.
    """
    source = _load(UI_PATH)
    body = _extract_component_body(source, "DocCard")
    assert body, (
        "Setup error: corpo do componente `DocCard` não encontrado em "
        "`BibliotecaRoom.tsx`."
    )
    assert "Reprocessar" in body, (
        "Setup error: `DocCard` não contém o texto 'Reprocessar' "
        "(verifique se o componente foi renomeado)."
    )
    # Extrair a condição que controla a renderização do botão.
    reprocess_match = re.search(
        r"\{[^{}]*(?:doc\.status\s*===\s*['\"]processing['\"]|\.status\s*===\s*['\"]processing['\"])[^{}]*Reprocessar",
        body,
    )
    # Padrão alternativo: presença de uma flag derivada como `isTimedOut`
    # ou `processingTimedOut` ao lado de "Reprocessar" dentro do DocCard.
    has_timedout_flag_near_reprocess = bool(
        re.search(
            r"(isTimedOut|processingTimedOut|isStuck|timedOut)\b[^{}]{0,200}Reprocessar",
            body,
            re.DOTALL,
        )
    )
    assert reprocess_match is not None or has_timedout_flag_near_reprocess, (
        "AC#2 violated: `DocCard` em `BibliotecaRoom.tsx` não mostra o "
        "botão '↻ Reprocessar' para documentos em 'processing' que "
        "expiraram (timed-out). Behavior F-3-B3 requer que a condição "
        "de renderização do botão cubra também o caso processing "
        "timed-out (ex.: `doc.status === 'processing' && isTimedOut(doc)`, "
        "ou uma flag derivada como `isTimedOut` que habilita o "
        "botão para processing preso)."
    )


def test_f3_b3_bibliotecaroom_docrow_shows_reprocess_for_timed_out_processing():
    """AC#2 — ``DocRow`` deve mostrar o botão "↻" (símbolo de retry)
    também para documentos cujo processing expirou, replicando o
    comportamento de ``DocCard`` (AC#2 simétrico).
    """
    source = _load(UI_PATH)
    body = _extract_component_body(source, "DocRow")
    assert body, (
        "Setup error: corpo do componente `DocRow` não encontrado em "
        "`BibliotecaRoom.tsx`."
    )
    # O DocRow usa apenas o símbolo "↻" no botão (linha 233). Verifica
    # se a condição cobre processing timed-out.
    has_processing_in_retry = bool(
        re.search(
            r"doc\.status\s*===\s*['\"]processing['\"]",
            body,
        )
    )
    has_timedout_flag_in_retry = bool(
        re.search(
            r"(isTimedOut|processingTimedOut|isStuck|timedOut)\b",
            body,
        )
    )
    assert has_processing_in_retry or has_timedout_flag_in_retry, (
        "AC#2 violated: `DocRow` em `BibliotecaRoom.tsx` não trata "
        "documentos em 'processing' timed-out na condição que renderiza "
        "o botão de retry (↻). Behavior F-3-B3 requer simetria com "
        "`DocCard`: o botão de retry deve aparecer também para "
        "documentos cujo processing expirou, não só para "
        "`failed`/`partially_failed`."
    )


def test_f3_b3_bibliotecaroom_exposes_timedout_info_to_components():
    """AC#2 — A tela ``BibliotecaRoom`` deve repassar informação de
    timeout (ex.: set ``isTimedOut`` no doc) para ``DocCard`` e
    ``DocRow``, de forma que ambos saibam quais docs estão presos.

    Padrões aceitáveis: doc derivado com flag, helper ``isTimedOut(doc)``,
    ou prop ``timedOutIds`` passada adiante.
    """
    source = _load(UI_PATH)
    has_helper = bool(re.search(r"isTimedOut\s*\(", source))
    has_timedout_field = bool(re.search(r"timedOut", source))
    assert has_helper or has_timedout_field, (
        "AC#2 violated: `BibliotecaRoom.tsx` não expõe nenhuma "
        "informação de timeout (sem helper `isTimedOut(doc)`, sem flag "
        "`timedOut`, sem `timedOutIds`). Behavior F-3-B3 requer que a "
        "tela saiba quais documentos estão presos em processing > 2min "
        "para renderizar 'falha desconhecida' e o botão de reprocessar "
        "em `DocCard` e `DocRow`."
    )
