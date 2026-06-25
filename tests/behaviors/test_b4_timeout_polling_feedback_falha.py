"""RED test for behavior B-4 (BKL-038) — Timeout de polling com feedback
de falha.

GOAL:
    Quando o polling de documentos na ``useKnowledgeBase.ts`` permanece
    monitorando um documento em estado transitorio (``processing`` ou
    ``pending``) por mais de ``POLLING_TIMEOUT_MS`` (120 segundos), o
    documento DEVE ser marcado como stalled (status virtual ``failed``
    local) e o ``error_message`` correspondente DEVE ser capturado via
    ``getDocumentProgress`` para que o usuario visualize a falha na
    ``BibliotecaRoom.tsx`` com a mensagem ``"Falha no processamento"``
    seguida do detalhe retornado pelo backend.

BEHAVIOR:
    B-4 — Timeout de polling com feedback de falha (BKL-038).

    Apos ``POLLING_TIMEOUT_MS`` (120 segundos), documentos que
    permanecerem em ``processing`` ou ``pending`` devem:

      1. Ser marcados como stalled (status virtual ``failed``).
      2. Capturar o ``error_message`` do registro via
         ``getDocumentProgress()``.
      3. Expor ``error_message`` para que possa ser exibido.
      4. Resetar quando ``retry`` for chamado.

AC (Acceptance Criteria):
    AC#1 — ``POLLING_TIMEOUT_MS = 120000`` constante em
           ``apps/blu_v3/src/hooks/useKnowledgeBase.ts``.

    AC#2 — ``startedAt`` tracking por ``documentId`` no polling effect.

    AC#3 — Timeout detection: pular docs stalled no ``load()`` usando
           ``getDocumentProgress(documentId)`` para capturar
           ``error_message``.

    AC#4 — Marcar stalled (status="failed" virtual) no estado local via
           ``setState``.

    AC#5 — ``error_message`` extraido de ``getDocumentProgress`` e
           integrado (em ``doc.error_message`` ou estado auxiliar).

    AC#6 — ``"Falha no processamento"`` seguido de ``error_message`` em
           ``BibliotecaRoom.tsx``.

    AC#7 — ``retry()`` reseta o stalled (limpa ``error_message`` e volta
           status para ``processing``) e remove ``documentId`` do
           ``startedAt`` tracking.

ESTADO ATUAL (RED):
    - ``apps/blu_v3/src/hooks/useKnowledgeBase.ts`` (146 linhas) faz
      polling de 5s enquanto ha doc ``processing``/``pending`` (linhas
      54-65), mas NAO define ``POLLING_TIMEOUT_MS``, NAO rastreia
      ``startedAt`` por documentId, NAO chama ``getDocumentProgress``
      dentro do interval, NAO detecta timeout, NAO marca stalled.
    - ``retry()`` (linhas 119-135) apenas faz ``status: 'processing'``
      no estado local — NAO limpa nenhum ``stalled`` (porque stalled
      nao existe).
    - ``apps/blu_v3/src/services/knowledgeBaseService.ts`` ja exporta
      ``getDocumentProgress`` (linhas 115-139) e ``KBDocument`` ja tem
      ``error_message: string | null`` (linha 21), e ``retryDocument``
      ja limpa ``error_message`` no banco.
    - ``apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`` NAO contem a
      string ``"Falha no processamento"`` em nenhum lugar.

ESTADO ALVO (GREEN):
    - Adicionar constante ``const POLLING_TIMEOUT_MS = 120_000`` (ou
      ``120000``) em ``useKnowledgeBase.ts``.
    - Adicionar ``Map<string, number>`` (ou ``Record<string, number>``)
      para ``startedAt`` por documentId no escopo do hook.
    - No effect de polling, registrar ``startedAt.set(docId, Date.now())``
      para cada doc que entra em estado transitorio e detectar
      ``Date.now() - startedAt.get(docId) > POLLING_TIMEOUT_MS``.
    - Ao detectar timeout, chamar ``await getDocumentProgress(docId)`` e
      (alternativamente) ler ``error_message`` do banco via Supabase
      client ou via response do RPC; armazenar no doc como
      ``error_message`` e setar ``status: 'failed'`` no estado local.
    - Em ``BibliotecaRoom.tsx``, renderizar ``"Falha no processamento"``
      seguido de ``doc.error_message`` para docs com status
      ``failed`` (incluindo stalled) que tenham ``error_message``.
    - No ``retry()``, remover o ``documentId`` do ``startedAt`` map e
      garantir ``error_message: null`` no estado local.

Anti-Goals (must NOT be violated):
    1. NAO modificar codigo de producao (useKnowledgeBase.ts,
       BibliotecaRoom.tsx, knowledgeBaseService.ts) — RED deve falhar.
    2. NAO importar / executar TypeScript — o teste e pura inspecao
       textual do arquivo .ts/.tsx.
    3. NAO usar fixtures de DB ou rede — sem Supabase, sem mocks.
    4. NAO usar ``ts-node``, ``tsx``, ``vitest`` ou qualquer runner TS.
    5. NAO relaxar o teste para que ele passe no estado atual — ele
       precisa ser TRUE RED agora.
    6. NAO remover nenhuma funcao ja exportada de
       ``knowledgeBaseService.ts``.
    7. NAO usar ``assert`` — usar ``pytest.fail()`` exclusivamente.
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
ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "BibliotecaRoom.tsx"
)
KB_SERVICE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "services"
    / "knowledgeBaseService.ts"
)


# ── Override do root conftest (teste puramente estatico) ──────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste e
    pura inspecao textual dos arquivos ``.ts``/``.tsx``, sem teardown
    no Supabase, sem rede, sem imports/execucao de TypeScript.
    """
    yield


# ── Helpers de inspecao textual ───────────────────────────────────────────


def _read_source(path: Path) -> str:
    """Le o codigo-fonte TS/TSX como texto puro (sem parser)."""
    assert path.exists(), (
        f"Source file not found: {path}.  "
        "O behavior B-4 (BKL-038) exige que o arquivo exista no repo."
    )
    return path.read_text(encoding="utf-8")


# ── AC#1 — POLLING_TIMEOUT_MS = 120000 constante ──────────────────────────


def test_b4_ac1_polling_timeout_ms_constante() -> None:
    """AC#1 — ``apps/blu_v3/src/hooks/useKnowledgeBase.ts`` DEVE definir
    uma constante ``POLLING_TIMEOUT_MS`` com valor ``120000``.

    Comportamento exigido:

        const POLLING_TIMEOUT_MS = 120_000
        // ou
        const POLLING_TIMEOUT_MS = 120000

    A constante deve ser declarada no escopo do modulo (top-level ou
    logo antes do polling effect) e referenciada no codigo de deteccao
    de timeout (ou seja, nao pode ser um literal orfao sem uso).

    Estado atual (RED):
      - O arquivo ``useKnowledgeBase.ts`` (146 linhas) NAO contem
        ``POLLING_TIMEOUT_MS`` em nenhum lugar.
      - O polling effect (linhas 54-65) usa ``5_000`` literal como
        intervalo, sem nenhum timeout maximo.

    GREEN deve, no minimo:
      1. Declarar ``const POLLING_TIMEOUT_MS = 120_000`` (ou
         ``120000``) no escopo do modulo.
      2. Usar essa constante na logica de deteccao de timeout
         (``Date.now() - startedAt.get(id) > POLLING_TIMEOUT_MS`` ou
         equivalente).
    """
    source = _read_source(HOOK_PATH)

    # ── 1. Procura por uma declaracao de POLLING_TIMEOUT_MS = 120000 ─
    timeout_const_pattern = re.compile(
        r"(?:const|let|var)\s+POLLING_TIMEOUT_MS\s*[:=]\s*"
        r"(?:120_?000|120000)\b",
    )
    if not timeout_const_pattern.search(source):
        pytest.fail(
            "AC#1 — RED.  A constante `POLLING_TIMEOUT_MS` com valor "
            "`120000` NAO esta definida em "
            "`apps/blu_v3/src/hooks/useKnowledgeBase.ts`.\n\n"
            "AC#1 exige que o modulo declare:\n"
            "  const POLLING_TIMEOUT_MS = 120_000  // 120 segundos\n\n"
            "O polling effect atual (linhas 54-65) apenas repete "
            "`load()` a cada 5s enquanto houver doc em "
            "`processing`/`pending`, sem nenhum timeout maximo.\n\n"
            "Implemente: declare a constante `POLLING_TIMEOUT_MS` no "
            "topo do arquivo (ou logo antes do polling effect) e "
            "use-a na logica de deteccao de timeout (ver AC#2 e "
            "AC#3)."
        )

    # ── 2. Verifica que a constante e usada em algum lugar do arquivo ─
    #        (nao pode ser declaracao orfa — precisa ser referenciada)
    if source.count("POLLING_TIMEOUT_MS") < 2:
        pytest.fail(
            "AC#1 — RED.  A constante `POLLING_TIMEOUT_MS` foi "
            "declarada mas NAO e referenciada em nenhum outro lugar "
            "de `useKnowledgeBase.ts`.\n\n"
            "AC#1 exige que a constante seja USADA na logica de "
            "deteccao de timeout (ex.: "
            "`Date.now() - startedAt.get(id) > POLLING_TIMEOUT_MS`).\n\n"
            "GREEN deve: alem de declarar a constante, compara-la com "
            "a diferenca de tempo no polling effect para detectar "
            "docs stalled."
        )


# ── AC#2 — startedAt tracking por documentId no polling effect ───────────


def test_b4_ac2_started_at_tracking_por_document_id() -> None:
    """AC#2 — O polling effect (linhas 54-65) DEVE rastrear
    ``startedAt`` (timestamp de inicio da observacao) por
    ``documentId``.

    Comportamento exigido:

        const startedAt = new Map<string, number>()
        // ou
        const startedAt: Record<string, number> = {}
        // ...
        startedAt.set(doc.id, Date.now())  // ao observar doc novo
        // ou
        if (!startedAt.has(doc.id)) {
            startedAt.set(doc.id, Date.now())
        }

    Estado atual (RED):
      - Nenhuma variavel ``startedAt`` (nem ``Map``, nem
        ``Record``) existe em ``useKnowledgeBase.ts``.
      - O polling effect apenas chama ``load()`` recursivamente sem
        nenhum rastreamento de quando cada doc comecou a ser
        monitorado.

    GREEN deve, no minimo:
      1. Declarar ``const startedAt = new Map<string, number>()``
         (ou ``Record<string, number>``) no escopo do hook.
      2. Para cada doc em estado transitorio que entra no effect,
         registrar ``startedAt.set(doc.id, Date.now())`` se ainda nao
         registrado.
      3. Usar ``Date.now() - startedAt.get(doc.id)`` no interval
         para detectar timeout (ver AC#3).
    """
    source = _read_source(HOOK_PATH)

    # ── 1. Procura por uma declaracao startedAt (Map ou Record) ──────
    started_at_declaration = re.search(
        r"(?:const|let|var)\s+startedAt\s*[:=]\s*"
        r"(?:new\s+Map<[^>]+>|new\s+Map\s*\(\s*\)|"
        r"Record<string\s*,\s*number>|\{\s*\})",
        source,
    )
    if started_at_declaration is None:
        pytest.fail(
            "AC#2 — RED.  Nenhum `startedAt` (Map<...> ou "
            "Record<string, number>) esta declarado em "
            "`apps/blu_v3/src/hooks/useKnowledgeBase.ts`.\n\n"
            "AC#2 exige que o polling effect rastreie, por "
            "`documentId`, o timestamp de inicio da observacao "
            "do doc em estado transitorio.\n\n"
            "Implemente uma das duas variantes:\n"
            "  a) const startedAt = new Map<string, number>()\n"
            "  b) const startedAt: Record<string, number> = {}\n\n"
            "E dentro do polling effect, para cada doc em "
            "`processing`/`pending`, registre "
            "`startedAt.set(doc.id, Date.now())` se ainda nao "
            "estiver registrado."
        )

    # ── 2. Procura por uso de .set() ou [doc.id] = no startedAt ──────
    has_set_call = bool(
        re.search(r"startedAt\.set\s*\(", source)
        or re.search(r"startedAt\s*\[\s*[a-zA-Z_.]+\.id\s*\]\s*=\s*Date\.now\(\)", source)
    )
    if not has_set_call:
        pytest.fail(
            "AC#2 — RED.  A variavel `startedAt` foi declarada mas "
            "NAO ha nenhuma chamada `startedAt.set(...)` (ou "
            "atribuicao `startedAt[doc.id] = ...`) em "
            "`useKnowledgeBase.ts`.\n\n"
            "AC#2 exige que, ao observar um doc em estado "
            "transitorio, o timestamp seja registrado:\n"
            "  startedAt.set(doc.id, Date.now())\n"
            "ou\n"
            "  startedAt[doc.id] = Date.now()\n\n"
            "GREEN deve: dentro do polling effect, para cada doc "
            "filtrado (status `processing` ou `pending`), chamar "
            "`startedAt.set(doc.id, Date.now())` se ainda nao "
            "registrado."
        )


# ── AC#3 — Timeout detection: getDocumentProgress chamado no interval ────


def test_b4_ac3_timeout_detection_get_document_progress() -> None:
    """AC#3 — Quando o polling detecta que um documento ultrapassou
    ``POLLING_TIMEOUT_MS`` sem sair de ``processing``/``pending``,
    DEVE chamar ``getDocumentProgress(documentId)`` para capturar o
    ``error_message`` do registro.

    Comportamento exigido:

        // dentro do setInterval do polling effect
        const elapsed = Date.now() - (startedAt.get(doc.id) ?? 0)
        if (elapsed > POLLING_TIMEOUT_MS) {
            const progress = await getDocumentProgress(doc.id)
            // ...
        }

    Estado atual (RED):
      - O interval (linha 60-62) so chama ``load()``.
      - Nenhuma comparacao com ``POLLING_TIMEOUT_MS`` existe.
      - ``getDocumentProgress`` NAO e chamado dentro do polling
        effect (ele e apenas re-exportado no return do hook na
        linha 144, mas nunca invocado).

    GREEN deve, no minimo:
      1. Dentro do ``setInterval`` (ou logo apos detectar um doc
         stalled), calcular o tempo decorrido desde
         ``startedAt.get(doc.id)``.
      2. Se ``elapsed > POLLING_TIMEOUT_MS``, chamar
         ``await getDocumentProgress(doc.id)`` para extrair o
         ``error_message`` retornado pelo backend.
    """
    source = _read_source(HOOK_PATH)

    # ── 1. Verifica que getDocumentProgress e invocado em algum lugar
    #        do hook (nao apenas importado ou re-exportado) ───────────
    # Procura chamada de getDocumentProgress(
    has_get_progress_call = bool(
        re.search(
            r"(?:await\s+)?getDocumentProgress\s*\(\s*[a-zA-Z_]+\.id\s*\)",
            source,
        )
    )
    if not has_get_progress_call:
        pytest.fail(
            "AC#3 — RED.  `getDocumentProgress(doc.id)` NAO e "
            "invocado em nenhum lugar de "
            "`apps/blu_v3/src/hooks/useKnowledgeBase.ts`.\n\n"
            "AC#3 exige que, ao detectar timeout "
            "(`Date.now() - startedAt.get(doc.id) > "
            "POLLING_TIMEOUT_MS`), o hook chame "
            "`getDocumentProgress(documentId)` para capturar o "
            "`error_message` do registro no banco.\n\n"
            "Estado atual: `getDocumentProgress` apenas aparece no "
            "import (linha 9) e no return do hook (linha 144, "
            "re-exportado para o consumidor), mas nunca e "
            "invocado internamente.\n\n"
            "GREEN deve: dentro do `setInterval` do polling effect, "
            "para cada doc que ultrapassou `POLLING_TIMEOUT_MS`, "
            "executar `const progress = await getDocumentProgress( "
            "doc.id )` e usar `progress.error_message` (ou buscar "
            "`error_message` no record retornado) para alimentar o "
            "estado local."
        )

    # ── 2. Verifica que POLLING_TIMEOUT_MS e usado em comparacao ─────
    timeout_check_pattern = re.compile(
        r"(?:POLLING_TIMEOUT_MS|120_?000|120000)"
    )
    if not timeout_check_pattern.search(source):
        pytest.fail(
            "AC#3 — RED.  Nenhuma comparacao com `POLLING_TIMEOUT_MS` "
            "(ou literal 120000) foi encontrada em "
            "`useKnowledgeBase.ts`.\n\n"
            "AC#3 exige que a logica de deteccao compare o tempo "
            "decorrido com o timeout, ex.:\n"
            "  if (Date.now() - startedAt.get(doc.id) > "
            "POLLING_TIMEOUT_MS) { ... }\n\n"
            "GREEN deve: introduzir essa comparacao dentro do "
            "`setInterval` (ou como condicional de chamada) e "
            "acionar a busca de `getDocumentProgress` apenas "
            "quando o limite for ultrapassado."
        )


# ── AC#4 — Marcar stalled (status="failed" virtual) no estado local ───────


def test_b4_ac4_marcar_stalled_status_failed_no_estado_local() -> None:
    """AC#4 — Apos timeout detectado, o documento DEVE ser marcado como
    ``"failed"`` no estado local (status virtual).

    Comportamento exigido:

        // dentro do setInterval, ao detectar timeout
        setState((prev) => ({
            ...prev,
            documents: prev.documents.map((d) =>
                d.id === doc.id
                    ? { ...d, status: 'failed' as const, error_message: ... }
                    : d,
            ),
        }))

    Estado atual (RED):
      - Nenhuma atribuicao ``status: 'failed'`` aparece dentro do
        polling effect.
      - O unico lugar onde status e setado como ``'failed'`` no
        estado local e inexistente (vem apenas do banco via
        ``load()``).

    GREEN deve, no minimo:
      1. Dentro do `setInterval`, ao detectar que um doc
         ultrapassou `POLLING_TIMEOUT_MS`, executar `setState`
         para marcar esse doc com `status: 'failed' as const`
         no array `documents` do estado local.
    """
    source = _read_source(HOOK_PATH)

    # ── 1. Procura por setState/setDocuments que atribui 'failed' ────
    # Pode ser:
    #   status: 'failed' as const
    #   status: 'failed'
    #   status: "failed"
    # Deve estar dentro de um setState/prev.documents.map (estado local)
    setstate_failed_pattern = re.compile(
        r"setState\s*\(\s*\([^)]*\)\s*=>\s*\(?\{[^}]*"
        r"status\s*:\s*['\"]failed['\"]",
        re.DOTALL,
    )
    if not setstate_failed_pattern.search(source):
        pytest.fail(
            "AC#4 — RED.  Nenhuma atribuicao "
            "`status: 'failed'` (ou `\"failed\"`) foi encontrada "
            "dentro de um `setState((prev) => ...)` em "
            "`useKnowledgeBase.ts`.\n\n"
            "AC#4 exige que, ao detectar timeout, o hook marque o "
            "doc como stalled com `status: 'failed'` no estado "
            "local (via `setState` + `prev.documents.map`).\n\n"
            "Estado atual: o status `'failed'` nunca e atribuido "
            "no estado local — o hook confia 100% no que vier do "
            "backend via `load()`. Para um doc stalled, o backend "
            "nunca retornara `failed` (ele ainda esta "
            "`processing`/`pending`), entao a marcacao local e "
            "essencial.\n\n"
            "GREEN deve: dentro do `setInterval`, apos confirmar "
            "timeout, executar algo como:\n"
            "  setState((prev) => ({\n"
            "    ...prev,\n"
            "    documents: prev.documents.map((d) =>\n"
            "      d.id === doc.id\n"
            "        ? { ...d, status: 'failed' as const, "
            "error_message: ... }\n"
            "        : d,\n"
            "    ),\n"
            "  }))"
        )


# ── AC#5 — error_message extraido do getDocumentProgress e integrado ─────


def test_b4_ac5_error_message_extraido_e_integrado() -> None:
    """AC#5 — O ``error_message`` retornado por ``getDocumentProgress``
    DEVE ser armazenado e acessivel.

    Pode ser:
      - integrado no doc como ``doc.error_message`` (mutacao local
        apos timeout), ou
      - em um estado auxiliar ``stalledMessages: Map<string, string>``
        ou ``Record<string, string>``.

    Estado atual (RED):
      - Nenhuma variavel ``stalledMessages`` (ou similar) existe.
      - Nenhuma atribuicao ``error_message: ...` (vinda de
        ``getDocumentProgress``) aparece no estado local.
      - O estado ``KBState`` nao tem campo nenhum para
        ``stalledMessages`` ou ``stalledErrorMessages``.

    GREEN deve, no minimo:
      1. Chamar `getDocumentProgress(doc.id)` no momento do timeout
         (ver AC#3).
      2. Extrair o `error_message` do retorno (o `EmbeddingProgress`
         atual retorna `status` mas nao `error_message` — pode ser
         necessario adicionar `error_message` ao `EmbeddingProgress`
         OU buscar o `error_message` via `select('error_message')`
         do `documents` no Supabase).
      3. Armazenar esse `error_message` no doc local (ou em estado
         auxiliar) para que `BibliotecaRoom.tsx` possa exibi-lo.
    """
    source = _read_source(HOOK_PATH)

    # ── 1. Procura por atribuicao de error_message vinda de progress ─
    #        (error_message: progress.error_message OU
    #         error_message: data.error_message OU
    #         error_message: ... em setState perto de getDocumentProgress)
    has_error_message_assignment = bool(
        re.search(
            r"error_message\s*:\s*[a-zA-Z_]+\.error_message",
            source,
        )
        or re.search(
            r"error_message\s*:\s*[a-zA-Z_]+\[['\"]error_message['\"]\]",
            source,
        )
    )
    # ── 2. Ou procura por um estado stalledMessages que armazene
    #        error_messages por documentId ────────────────────────────
    has_stalled_messages_state = bool(
        re.search(
            r"(?:const|let|var)\s+stalledMessages?\s*[:=]",
            source,
        )
        or re.search(
            r"stalledMessages?\s*:\s*(?:Map<string\s*,\s*string>|"
            r"Record<string\s*,\s*string>)",
            source,
        )
    )

    if not (has_error_message_assignment or has_stalled_messages_state):
        pytest.fail(
            "AC#5 — RED.  Nenhuma evidencia de extracao/integracao "
            "do `error_message` retornado por `getDocumentProgress` "
            "foi encontrada em `useKnowledgeBase.ts`.\n\n"
            "AC#5 exige que o `error_message` (capturado do backend) "
            "seja armazenado e acessivel. Duas alternativas "
            "equivalentes:\n\n"
            "  A) Integrar no doc local dentro do setState:\n"
            "     setState((prev) => ({\n"
            "       ...prev,\n"
            "       documents: prev.documents.map((d) =>\n"
            "         d.id === doc.id\n"
            "           ? { ...d, status: 'failed' as const, "
            "error_message: progress.error_message ?? "
            "data?.error_message ?? null }\n"
            "           : d,\n"
            "       ),\n"
            "     }))\n\n"
            "  B) Manter um estado auxiliar:\n"
            "     const [stalledMessages, setStalledMessages] = "
            "useState<Record<string, string>>({})\n"
            "     // ...\n"
            "     setStalledMessages((prev) => ({\n"
            "       ...prev,\n"
            "       [doc.id]: progress.error_message ?? '<erro>',\n"
            "     }))\n\n"
            "Estado atual: `useKnowledgeBase.ts` nao tem nenhum "
            "`stalledMessages` (nem Map, nem Record, nem useState "
            "com esse nome) e nao atribui `error_message` no "
            "setState do polling effect.\n\n"
            "GREEN deve: implementar a extracao do `error_message` "
            "e a integracao no estado (opcao A ou B)."
        )


# ── AC#6 — "Falha no processamento" com error_message em BibliotecaRoom ──


def test_b4_ac6_falha_no_processamento_com_error_message() -> None:
    """AC#6 — ``apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`` DEVE
    exibir ``"Falha no processamento"`` seguido do ``error_message``
    do documento.

    Comportamento exigido:

        // dentro do JSX de DocCard ou DocRow, quando
        // doc.status === 'failed' && doc.error_message
        <div>
            Falha no processamento: {doc.error_message}
        </div>

    O texto literal ``"Falha no processamento"`` DEVE aparecer no
    source.

    Estado atual (RED):
      - Nenhuma ocorrencia de ``"Falha no processamento"`` (com as
        aspas ou crases) foi encontrada em
        ``BibliotecaRoom.tsx``.
      - A bottom strip (linhas 566-574) so mostra a mensagem generica
        "X documento(s) com erro de processamento. Use ↻ para
        reprocessar." — sem o detalhe de ``error_message``.

    GREEN deve, no minimo:
      1. Renderizar ``"Falha no processamento"`` (literal) seguido de
         ``{doc.error_message}`` no JSX de ``DocCard`` ou ``DocRow``
         (ou em ambos) quando ``doc.status === 'failed'`` e
         ``doc.error_message`` estiver presente.
    """
    source = _read_source(ROOM_PATH)

    # ── 1. Procura pelo literal "Falha no processamento" ────────────
    failure_text_pattern = re.compile(
        r"Falha\s+no\s+processamento",
        re.IGNORECASE,
    )
    if not failure_text_pattern.search(source):
        pytest.fail(
            "AC#6 — RED.  O texto literal `\"Falha no processamento\"` "
            "NAO aparece em "
            "`apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`.\n\n"
            "AC#6 exige que a UI exiba `\"Falha no processamento\"` "
            "seguido do `error_message` retornado pelo backend "
            "para docs stalled (status `failed` com `error_message` "
            "preenchido).\n\n"
            "Estado atual: a bottom strip (linhas 566-574) so "
            "mostra a mensagem generica `\"X documento(s) com "
            "erro de processamento. Use ↻ para reprocessar.\"` "
            "— sem o detalhe especifico de `error_message`.\n\n"
            "GREEN deve: adicionar, dentro de `DocCard` (linhas "
            "62-182) ou `DocRow` (linhas 186-237), um bloco "
            "condicional do tipo:\n"
            "  {(doc.status === 'failed' && doc.error_message) && (\n"
            "    <div style={{...}}>\n"
            "      Falha no processamento: {doc.error_message}\n"
            "    </div>\n"
            "  )}\n\n"
            "O literal exato `\"Falha no processamento\"` precisa "
            "estar presente no source."
        )

    # ── 2. Verifica que error_message aparece perto do literal ───────
    #        (na mesma funcao/componente) ─────────────────────────────
    failure_match = failure_text_pattern.search(source)
    if failure_match is not None:
        # Pega 600 chars em torno do match para garantir contexto
        start = max(0, failure_match.start() - 400)
        end = min(len(source), failure_match.end() + 400)
        context = source[start:end]
        if "error_message" not in context and "errorMessage" not in context:
            pytest.fail(
                "AC#6 — RED.  O literal `\"Falha no processamento\"` "
                "foi encontrado, mas NAO esta acompanhado de "
                "`error_message` no mesmo contexto JSX em "
                "`BibliotecaRoom.tsx`.\n\n"
                "AC#6 exige que o `error_message` do doc seja "
                "renderizado junto (apos ou ao lado) do texto "
                "literal. Exemplo:\n"
                "  Falha no processamento: {doc.error_message}\n\n"
                "GREEN deve: garantir que o JSX que renderiza "
                "`\"Falha no processamento\"` tambem referencie "
                "`doc.error_message` na mesma expressao ou em "
                "um bloco adjacente."
            )


# ── AC#7 — Stalled reseta ao retry ────────────────────────────────────────


def test_b4_ac7_stalled_reseta_ao_retry() -> None:
    """AC#7 — A funcao ``retry()`` em ``useKnowledgeBase.ts`` DEVE
    resetar o stalled (limpar ``error_message`` e voltar status para
    ``processing``) e tambem remover o ``documentId`` do ``startedAt``
    tracking.

    Comportamento exigido:

        const retry = useCallback(async (doc) => {
            await retryDocument(doc)
            // remove do startedAt
            startedAt.delete(doc.id)  // ou
            delete startedAt[doc.id]
            // reseta estado local
            setState((prev) => ({
                ...prev,
                documents: prev.documents.map((d) =>
                    d.id === doc.id
                        ? { ...d, status: 'processing' as const,
                            error_message: null }
                        : d,
                ),
            }))
        }, [])

    Estado atual (RED):
      - O ``retry()`` atual (linhas 119-135) faz
        ``status: 'processing' as const`` mas NAO limpa
        ``error_message`` no estado local (o `error_message: null`
        vem do banco, mas se o doc esta stalled o estado local tem
        `error_message` proprio que nao e zerado).
      - Nenhum ``startedAt.delete(doc.id)`` ou
        ``delete startedAt[doc.id]`` aparece.
      - ``startedAt`` nem existe no source (ver AC#2).

    GREEN deve, no minimo:
      1. Dentro do `retry()`, apos `await retryDocument(doc)`,
         executar `startedAt.delete(doc.id)` (ou
         `delete startedAt[doc.id]`) para resetar o tracking.
      2. No setState do `retry()`, atribuir
         `error_message: null` (alem de `status: 'processing' as
         const`) para o doc correspondente.
    """
    source = _read_source(HOOK_PATH)

    # ── 1. Procura pelo corpo da funcao retry ────────────────────────
    retry_func_pattern = re.compile(
        r"const\s+retry\s*=\s*useCallback\s*\(\s*async\s*\([^)]*\)\s*=>\s*\{",
    )
    retry_match = retry_func_pattern.search(source)
    if retry_match is None:
        pytest.fail(
            "AC#7 — RED.  A funcao `retry` (declarada com "
            "`useCallback`) NAO foi encontrada em "
            "`useKnowledgeBase.ts`.\n\n"
            "AC#7 exige que `retry()` resete o stalled. "
            "Esperava-se encontrar:\n"
            "  const retry = useCallback(async (doc) => { ... }, "
            "[...])\n\n"
            "Estado atual: existe `const retry = useCallback(...)` "
            "nas linhas 119-135 — mas o teste nao conseguiu "
            "combinar com o padrao acima. Verifique se a sintaxe "
            "foi alterada."
        )

    retry_start = retry_match.end()
    # Pega o corpo ate a proxima }, ou ate 80 linhas (o que vier antes)
    retry_body = source[retry_start : retry_start + 4000]

    # ── 2. Verifica que error_message: null aparece no setState do
    #        retry ────────────────────────────────────────────────────
    if "error_message" not in retry_body:
        pytest.fail(
            "AC#7 — RED.  O corpo da funcao `retry` em "
            "`useKnowledgeBase.ts` NAO faz referencia a "
            "`error_message`.\n\n"
            "AC#7 exige que `retry()` LIMPE o `error_message` no "
            "estado local (alem de voltar status para "
            "`processing`).\n\n"
            "Estado atual: o `retry()` atual (linhas 119-135) so "
            "faz `status: 'processing' as const` no `setState` "
            "— nenhum `error_message: null` e atribuido. Para "
            "um doc stalled (status local `failed` com "
            "`error_message` proprio, ver AC#5), apos `retry` o "
            "doc permaneceria com `error_message` antigo no "
            "estado ate o proximo `load()` resolver.\n\n"
            "GREEN deve: dentro do setState do `retry()`, mapear "
            "o doc correspondente para:\n"
            "  { ...d, status: 'processing' as const, "
            "error_message: null }\n"
        )
    elif not re.search(
        r"error_message\s*:\s*null",
        retry_body,
    ):
        pytest.fail(
            "AC#7 — RED.  O corpo do `retry()` referencia "
            "`error_message`, mas NAO o atribui para `null`.\n\n"
            "AC#7 exige que `retry()` LIMPE o `error_message` no "
            "estado local:\n"
            "  error_message: null\n\n"
            "GREEN deve: garantir que o setState do `retry()` "
            "atribua explicitamente `error_message: null` ao doc "
            "correspondente."
        )

    # ── 3. Verifica que ha limpeza do startedAt (delete) ────────────
    has_started_at_delete = bool(
        re.search(
            r"startedAt\.delete\s*\(\s*[a-zA-Z_]+\.id\s*\)",
            source,
        )
        or re.search(
            r"delete\s+startedAt\s*\[\s*[a-zA-Z_]+\.id\s*\]",
            source,
        )
    )
    if not has_started_at_delete:
        pytest.fail(
            "AC#7 — RED.  Nenhuma evidencia de que o "
            "`documentId` e removido do `startedAt` tracking "
            "durante o `retry()` foi encontrada em "
            "`useKnowledgeBase.ts`.\n\n"
            "AC#7 exige que `retry()` remova o doc do `startedAt` "
            "(para que o proximo ciclo de observacao comece "
            "do zero):\n"
            "  startedAt.delete(doc.id)\n"
            "ou\n"
            "  delete startedAt[doc.id]\n\n"
            "Estado atual: `startedAt` nem existe no source (ver "
            "AC#2), e o `retry()` atual (linhas 119-135) nao faz "
            "nenhuma manipulacao de `startedAt`.\n\n"
            "GREEN deve: alem de criar o `startedAt` map (AC#2), "
            "chamar `startedAt.delete(doc.id)` (ou `delete "
            "startedAt[doc.id]`) dentro do `retry()`, antes ou "
            "logo apos o `setState` que reseta o status."
        )
