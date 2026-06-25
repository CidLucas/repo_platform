"""RED test for B-4 (BKL-038) — No false positive: completed docs NOT
marked stalled.

GOAL:
    Quando um documento em estado transitorio (``processing`` ou
    ``pending``) completa (muda para ``"completed"``) antes de
    ``POLLING_TIMEOUT_MS`` (120s) expirar, o polling effect DEVE
    reconhecer que o doc nao esta mais em estado transitorio e NAO
    deve marca-lo como stalled/failed localmente.

BEHAVIOR:
    B-4 — Timeout de polling com feedback de falha (BKL-038).
    Sub-behavior: No false positive — completed docs skipped from
    stalled detection.

AC (Acceptance Criteria):
    AC#1 — O polling effect em ``useKnowledgeBase.ts`` DEVE existir
           (ja existe, com ``setInterval`` e ``load()`` no estado
           atual — esse AC e pre-requisito).

    AC#2 — O polling effect DEVE ter uma CONDICAO GUARDA explicita
           que exclui docs ja finalizados (``status === 'completed'``,
           ``status === 'failed'``, ou seja, ``status !==
           'processing' && status !== 'pending'``) da deteccao de
           stalled. Exemplos validos:

             a) ``const active = docs.filter(d => d.status === 'processing' || d.status === 'pending')``
                // so percorre `active` na deteccao de stalled

             b) ``if (doc.status !== 'processing' && doc.status !== 'pending') continue``
                // guarda dentro do loop de deteccao

             c) ``.filter(d => d.status === 'processing' || d.status === 'pending')``
                // aplicado antes da verificacao de elapsed > timeout

ESTADO ATUAL (RED):
    ``apps/blu_v3/src/hooks/useKnowledgeBase.ts`` (146 linhas) tem o
    polling effect (linhas 54-65) que:

      1. Filtra ``state.documents`` para ``processing``/``pending``
         (linhas 55-57) — mas isso e para DECIDIR se o polling deve
         continuar rodando, NAO para guardar a deteccao de stalled.

      2. Se ``processing.length === 0``, retorna (sem polling).

      3. Caso contrario, faz ``setInterval(() => load(), 5_000)``.

    NAO existe ``POLLING_TIMEOUT_MS`` (AC#1 de
    test_b4_timeout_polling_feedback_falha.py), NAO existe
    ``startedAt``, NAO existe deteccao de stalled, e — crucialmente
    para este teste — NAO existe uma CONDICAO GUARDA que exclua docs
    completed/failed da deteccao de stalled.

    Como NAO ha nem mesmo deteccao de stalled, tambem nao ha guarda
    de false-positive. O teste FALHA TRUE RED apontando que essa
    guarda nao existe.

GREEN deve, no minimo:
    1. Implementar deteccao de stalled (ver
       test_b4_timeout_polling_feedback_falha.py).
    2. Antes de aplicar a marcacao ``status: 'failed'`` em um doc,
       verificar explicitamente se o doc ja saiu de estado
       transitorio (``status !== 'processing' && status !==
       'pending'``) — se sim, pular (continue / filter).
    3. A guarda deve aparecer de forma inequivoca no source, nao
       implicitamente.

Anti-Goals (must NOT be violated):
    1. NAO modificar codigo de producao (useKnowledgeBase.ts,
       BibliotecaRoom.tsx, knowledgeBaseService.ts) — RED deve
       falhar.
    2. NAO importar / executar TypeScript — o teste e pura inspecao
       textual do arquivo .ts.
    3. NAO usar fixtures de DB ou rede — sem Supabase, sem mocks.
    4. NAO usar ``ts-node``, ``tsx``, ``vitest`` ou qualquer runner
       TS.
    5. NAO relaxar o teste para que ele passe no estado atual — ele
       precisa ser TRUE RED agora.
    6. NAO usar ``assert`` — usar ``pytest.fail()`` exclusivamente,
       com mensagem em pt-BR.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "hooks"
    / "useKnowledgeBase.ts"
)


# ── Override do root conftest (teste puramente estatico) ──────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste e
    pura inspecao textual do arquivo ``.ts``, sem teardown no
    Supabase, sem rede, sem imports/execucao de TypeScript.
    """
    yield


# ── Helpers de inspecao textual ───────────────────────────────────────────


def _read_source(path: Path) -> str:
    """Le o codigo-fonte TS como texto puro (sem parser)."""
    assert path.exists(), (
        f"Source file not found: {path}.  "
        "O behavior B-4 (BKL-038) exige que o arquivo exista no repo."
    )
    return path.read_text(encoding="utf-8")


# ── AC#1 — Pre-requisito: polling effect existe ──────────────────────────


def test_b4_ac1_polling_effect_existe() -> None:
    """AC#1 (pre-requisito) — O polling effect com ``setInterval``
    DEVE existir em ``useKnowledgeBase.ts``.

    Comportamento exigido:

        useEffect(() => {
            // ...filtra docs em estado transitorio...
            const interval = setInterval(() => { ... }, 5_000)
            return () => clearInterval(interval)
        }, [...])

    Estado atual (RED mas pre-existente):
      - O polling effect existe nas linhas 54-65 com
        ``setInterval(() => load(), 5_000)``. Este AC deve passar
        no estado atual — ele so estabelece o pre-requisito.

    Este teste serve como gate: se o polling effect nao existir,
    os outros ACs nao fazem sentido.
    """
    source = _read_source(HOOK_PATH)

    # ── 1. Procura por setInterval no arquivo ────────────────────────
    has_set_interval = bool(re.search(r"\bsetInterval\s*\(", source))
    if not has_set_interval:
        pytest.fail(
            "AC#1 — RED.  Nenhum `setInterval` foi encontrado em "
            "`apps/blu_v3/src/hooks/useKnowledgeBase.ts`.\n\n"
            "Pre-requisito: o polling effect DEVE existir para que "
            "a deteccao de stalled seja possivel.  GREEN deve: "
            "introduzir o polling effect com `setInterval` e "
            "`clearInterval` no cleanup."
        )

    # ── 2. Procura por clearInterval (cleanup) ──────────────────────
    has_clear_interval = bool(re.search(r"\bclearInterval\s*\(", source))
    if not has_clear_interval:
        pytest.fail(
            "AC#1 — RED.  O `setInterval` foi encontrado, mas NAO "
            "ha `clearInterval` correspondente em "
            "`useKnowledgeBase.ts`.\n\n"
            "Pre-requisito: o polling effect DEVE ter cleanup "
            "(`return () => clearInterval(interval)`) para nao "
            "vazar handles."
        )


# ── AC#2 — Guarda explicita exclui docs completed da deteccao de stalled


def test_b4_ac2_guarda_exclui_docs_completed_da_deteccao_stalled() -> None:
    """AC#2 — No false-positive: o polling effect DEVE ter uma
    CONDICAO GUARDA explicita que exclui docs ja finalizados
    (``status === 'completed'`` ou ``status === 'failed'``) de
    serem marcados como stalled.

    Comportamento exigido (qualquer uma das variantes):

        // Variante A — filter ANTES da deteccao de stalled:
        const stalledCandidates = state.documents.filter(
            (d) => d.status === 'processing' || d.status === 'pending',
        )
        for (const doc of stalledCandidates) {
            // ... deteccao de stalled ...
        }

        // Variante B — guarda `continue` DENTRO do loop:
        for (const doc of state.documents) {
            if (doc.status !== 'processing' && doc.status !== 'pending') {
                continue  // ← guarda explicita de no-false-positive
            }
            // ... deteccao de stalled ...
        }

        // Variante C — `.filter` aplicado a `startedAt` ou ao array
        // de docs a verificar:
        const active = state.documents.filter(
            (d) => d.status === 'processing' || d.status === 'pending',
        )
        for (const doc of active) {
            if (Date.now() - (startedAt.get(doc.id) ?? 0) > POLLING_TIMEOUT_MS) {
                // stalled
            }
        }

    A chave e: DEVE haver, no source, um pattern inequivoco que
    restrinja a deteccao de stalled a docs com status
    ``processing`` ou ``pending`` (excluindo ``completed`` e
    ``failed``).

    Estado atual (RED):
      - O polling effect (linhas 54-65) tem um `filter` em
        ``state.documents`` para ``processing``/``pending`` (linhas
        55-57), mas esse filter e usado apenas para DECIDIR se o
        setInterval deve rodar. NAO ha:
          * nenhuma deteccao de stalled
          * nenhum `POLLING_TIMEOUT_MS`
          * nenhum `startedAt`
          * nenhuma iteracao sobre docs candidatos a stalled
          * nenhuma guarda `continue` ou `filter` explicito para
            exclui-los
      - Como nao ha nem deteccao de stalled, tambem nao ha guarda
        de false-positive. O teste FALHA TRUE RED.

    GREEN deve, no minimo:
      1. Implementar deteccao de stalled
         (test_b4_timeout_polling_feedback_falha.py).
      2. Antes de marcar um doc como stalled, garantir que ele
         AINDA esta em estado transitorio. Isso pode ser feito
         via:
         a) `.filter(d => d.status === 'processing' || d.status === 'pending')`
            aplicado ao array que sera percorrido na deteccao de
            stalled.
         b) `if (doc.status !== 'processing' && doc.status !== 'pending') continue`
            dentro do loop de deteccao.
         c) `if (active.some(d => d.id === doc.id)) { ... }` — equivalente.
      3. A guarda deve ser VISIVEL no source (regex matchavel),
         nao implicita.
    """
    source = _read_source(HOOK_PATH)

    # ── 1. Confirma que o polling effect existe (pre-requisito) ────
    if not re.search(r"\bsetInterval\s*\(", source):
        pytest.fail(
            "AC#2 — RED.  Nao foi possivel avaliar a guarda de "
            "false-positive porque o polling effect "
            "(`setInterval`) NAO existe em "
            "`useKnowledgeBase.ts`.  Resolva AC#1 primeiro."
        )

    # ── 2. Procura por uma das tres variantes de guarda ────────────
    # Variante A — filter que restringe a docs processing/pending
    #              E que aparece junto a uma variavel que sugere
    #              deteccao de stalled (candidatos, active, etc).
    filter_stalled_pattern = re.compile(
        r"\.(?:filter|some|every|find)\s*\(\s*"
        r"[\(]?\s*"
        r"(?:d|doc|document)\s*=>\s*"
        r"(?:d|doc|document)\.status\s*===\s*['\"]processing['\"]"
        r"\s*\|\|\s*"
        r"(?:d|doc|document)\.status\s*===\s*['\"]pending['\"]"
        r"\s*[\)]?",
    )

    # Variante B — guarda `continue` com checagem explicita de
    #              status diferente de processing/pending
    continue_guard_pattern = re.compile(
        r"if\s*\(\s*"
        r"(?:d|doc|document)\.status\s*!==\s*['\"]processing['\"]"
        r"\s*&&\s*"
        r"(?:d|doc|document)\.status\s*!==\s*['\"]pending['\"]"
        r"\s*\)\s*\{?\s*continue\b",
    )

    # Variante C — `!== 'processing' && !== 'pending'` (qualquer
    #              forma, nao apenas `continue`)
    not_processing_not_pending_pattern = re.compile(
        r"\.status\s*!==\s*['\"]processing['\"]"
        r"\s*&&\s*"
        r"(?:d|doc|document|\w+)\.status\s*!==\s*['\"]pending['\"]",
    )

    # Variante D — variavel nomeada que sugira "candidatos a stalled"
    #              combinada com iteracao
    stalled_candidates_pattern = re.compile(
        r"(?:const|let|var)\s+"
        r"(?:stalledCandidates|activeDocs|active|"
        r"stalledDocs|candidates|pendingDocs)"
        r"\s*[:=]",
    )

    has_filter_guard = bool(filter_stalled_pattern.search(source))
    has_continue_guard = bool(continue_guard_pattern.search(source))
    has_status_not_guard = bool(not_processing_not_pending_pattern.search(source))
    has_named_variable = bool(stalled_candidates_pattern.search(source))

    # O filter existente no polling effect (linhas 55-57) E
    # correspondente a filter_stalled_pattern.  Entao precisamos
    # EXCLUIR esse match se ele for o unico e nao estiver
    # relacionado a deteccao de stalled.

    # Para fazer isso, procuramos o filter perto de `POLLING_TIMEOUT_MS`
    # ou `startedAt` ou `stalled` ou `elapsed`.  Se o filter nao
    # tiver nenhum desses vizinhos, ele e o do polling effect
    # original (linhas 55-57) e nao conta como guarda de
    # false-positive.

    if has_filter_guard and not (
        re.search(r"POLLING_TIMEOUT_MS", source)
        or re.search(r"\bstartedAt\b", source)
        or re.search(r"\bstalled\b", source)
        or re.search(r"\belapsed\b", source)
    ):
        # O filter matchado e o do polling effect original
        # (linhas 55-57), NAO uma guarda de false-positive na
        # deteccao de stalled.
        has_filter_guard = False

    # ── 3. Decide se alguma variante foi encontrada ────────────────
    if not (
        has_filter_guard
        or has_continue_guard
        or has_status_not_guard
        or has_named_variable
    ):
        pytest.fail(
            "AC#2 — RED.  Nenhuma CONDICAO GUARDA explicita "
            "excluindo docs ja finalizados (`status === 'completed'` "
            "ou `status === 'failed'`) da deteccao de stalled foi "
            "encontrada em `apps/blu_v3/src/hooks/useKnowledgeBase.ts`.\n\n"
            "AC#2 (no false-positive) exige que, ao implementar a "
            "deteccao de stalled, o polling effect pule "
            "explicitamente docs que ja nao estao em estado "
            "transitorio (`processing` ou `pending`), para evitar "
            "marcar um doc que acabou de completar como stalled.\n\n"
            "Variantes validas (escolha uma):\n\n"
            "  A) Filter explicito aplicado aos candidatos a stalled:\n"
            "     const stalledCandidates = state.documents.filter(\n"
            "       (d) => d.status === 'processing' || d.status === 'pending',\n"
            "     )\n"
            "     for (const doc of stalledCandidates) {\n"
            "       // ... deteccao de stalled ...\n"
            "     }\n\n"
            "  B) Guarda `continue` dentro do loop:\n"
            "     for (const doc of state.documents) {\n"
            "       if (doc.status !== 'processing' && doc.status !== 'pending') {\n"
            "         continue\n"
            "       }\n"
            "       // ... deteccao de stalled ...\n"
            "     }\n\n"
            "  C) Variavel nomeada (`active`, `stalledCandidates`, etc) "
            "que carrega apenas docs processing/pending.\n\n"
            "Estado atual: o polling effect (linhas 54-65) filtra "
            "`processing`/`pending` (linhas 55-57), mas isso e "
            "usado APENAS para decidir se o `setInterval` deve "
            "rodar. Nao ha deteccao de stalled, nao ha `startedAt`, "
            "nao ha `POLLING_TIMEOUT_MS`, e nao ha guarda de "
            "false-positive.\n\n"
            "GREEN deve: alem de implementar a deteccao de stalled "
            "(ver test_b4_timeout_polling_feedback_falha.py), "
            "adicionar uma das tres variantes acima para garantir "
            "que docs ja finalizados NAO sejam marcados como "
            "stalled."
        )

    # ── 4. Refinamento: se a unica evidencia e o filter do polling
    #        effect original (linhas 55-57), falha.  Esse filter
    #        NAO protege contra false-positive na deteccao de
    #        stalled, porque ele so e usado para decidir se o
    #        setInterval deve existir.
    if has_filter_guard and not (
        has_continue_guard or has_status_not_guard or has_named_variable
    ):
        # Confirma se o filter matchado esta perto de deteccao de stalled
        match = filter_stalled_pattern.search(source)
        assert match is not None  # type safety
        # Pega 400 chars em torno do match
        start = max(0, match.start() - 400)
        end = min(len(source), match.end() + 400)
        context = source[start:end]
        has_stalled_context = bool(
            re.search(r"\bstalled\b", context)
            or re.search(r"\bPOLLING_TIMEOUT_MS\b", context)
            or re.search(r"\bstartedAt\b", context)
            or re.search(r"\belapsed\b", context)
        )
        if not has_stalled_context:
            pytest.fail(
                "AC#2 — RED.  Foi encontrado um `.filter` que "
                "restringe a `processing`/`pending`, mas ele "
                "NAO esta em contexto de deteccao de stalled — "
                "e o filter do polling effect original "
                "(linhas 55-57), que apenas decide se o "
                "`setInterval` deve rodar.\n\n"
                "AC#2 exige que a guarda esteja na deteccao de "
                "stalled, nao na decisao de polling.  GREEN deve: "
                "adicionar um filter/guarda NO LUGAR onde o "
                "stalled e detectado, garantindo que docs "
                "completed/failed sejam pulados.\n\n"
                "Variantes validas (escolha uma):\n\n"
                "  A) const stalledCandidates = state.documents.filter(\n"
                "       (d) => d.status === 'processing' || d.status === 'pending',\n"
                "     )\n"
                "     // ... usar stalledCandidates na deteccao ...\n\n"
                "  B) for (const doc of state.documents) {\n"
                "       if (doc.status !== 'processing' && doc.status !== 'pending') {\n"
                "         continue\n"
                "       }\n"
                "       // ... deteccao de stalled ...\n"
                "     }\n"
            )

    # ── 5. Se chegamos aqui, alguma guarda foi encontrada E ela esta
    #        em contexto de deteccao de stalled.  GREEN achieved.
