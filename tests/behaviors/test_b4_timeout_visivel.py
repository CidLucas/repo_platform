"""RED test for behavior B-4 — Timeout visível BKL-038 (NAO implementado).

GOAL:
    Validar que a feature de "timeout visível" para documentos da
    Biblioteca de Conhecimento (BKL-038) **NAO esta implementada** no
    estado atual do repositório.  O behavior B-4 (a ser entregue em
    fase GREEN) deve tornar visível para o usuário da Biblioteca
    quando um documento está travado em ``processing`` ha mais de
    2 minutos (120 000 ms), exibindo um badge "Falha no
    processamento" e a mensagem de erro do documento.

BEHAVIOR:
    B-4 — Timeout visível BKL-038: quando um doc fica em
    ``processing``/``pending`` por mais de ``POLLING_TIMEOUT_MS`` (120s),
    a UI da Biblioteca deve:
      1) marcar o doc localmente como ``status: 'failed'`` +
         ``error_message`` (ciclo de polling do ``useKnowledgeBase``);
      2) exibir um badge "Falha no processamento" no card/row;
      3) exibir a ``error_message`` do documento na UI.

    **Estado atual (RED):** nenhum desses pontos está implementado.
    O polling em ``useKnowledgeBase.ts`` apenas chama ``load()`` a cada
    5s sem nenhuma checagem de elapsed, e ``BibliotecaRoom.tsx`` nao
    tem helper ``isTimedOut``, nao estende ``kbStatusBadge`` com um
    case de timeout, e nao renderiza ``doc.error_message``.

    Estes 5 testes sao TRUE RED — falham com ``pytest.fail`` em
    pt-BR enquanto a feature nao existir no código-fonte.  Quando
    a feature for implementada (fase GREEN), os testes passam.

AC (Acceptance Criteria):
    AC#1 — ``useKnowledgeBase.ts`` define ``const POLLING_TIMEOUT_MS
            = 120_000`` (ou literal equivalente ``120000``) — limite
            de tempo que um doc pode ficar em processing.
    AC#2 — O ``useEffect`` de polling (``setInterval(..., 5_000)``)
            em ``useKnowledgeBase.ts`` compara ``Date.now() -
            startTime`` (ou ``elapsed``) contra ``POLLING_TIMEOUT_MS``
            e marca o doc com ``status: 'failed'`` + ``error_message``
            quando excede o limite.
    AC#3 — ``BibliotecaRoom.tsx`` estende ``kbStatusBadge`` com um
            case para o estado de timeout e exibe o texto "Falha no
            processamento" como label do badge.
    AC#4 — ``BibliotecaRoom.tsx`` define uma função ``isTimedOut(doc)``
            que retorna ``true`` quando o doc está em
            ``processing``/``pending`` ha mais de 2 min.
    AC#5 — ``BibliotecaRoom.tsx`` exibe ``doc.error_message`` (ou
            ``errorMessage``) na UI para documentos com falha.

DECISAO:
    Estratégia: source_inspection (regex sobre os arquivos .ts/.tsx).
    Arquivos alvos:
      - apps/blu_v3/src/hooks/useKnowledgeBase.ts
      - apps/blu_v3/src/pages/app/BibliotecaRoom.tsx
      - apps/blu_v3/src/services/knowledgeBaseService.ts (contexto)

    Arquivos INTOCADOS (fora do escopo do B-4):
      - apps/blu_v3/src/hooks/useStandaloneAgent.ts (irrelevante)

Anti-Goals (must NOT be violated):
    1. NAO modificar código de produção — o teste é puramente
       estático.  A implementação da feature será feita na fase GREEN.
    2. NAO importar ou executar código TypeScript/React — o teste
       apenas lê os arquivos como texto e usa regex.
    3. NAO usar fixtures de DB ou rede — o teste é determinístico
       e roda sem rede.
    4. NAO inspecionar ``useStandaloneAgent.ts`` — esse arquivo é
       irrelevante para o behavior B-4.
    5. NAO exigir mudanca em ``process-document/index.ts`` — ele
       já propaga ``error_message`` em caso de erro, mas o timeout
       (BKL-038) é uma feature client-side, nao server-side.

Estado atual: RED — nenhum dos 5 acceptance criteria está
implementado.  Os testes falham com ``pytest.fail`` em pt-BR
apontando o que precisa ser adicionado em cada arquivo.
"""

import re
from pathlib import Path

import pytest


# ── Constants: paths da interface pública sob teste ──────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

USE_KNOWLEDGE_BASE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "hooks"
    / "useKnowledgeBase.ts"
)

BIBLIOTECA_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "BibliotecaRoom.tsx"
)

KNOWLEDGE_BASE_SERVICE_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "services"
    / "knowledgeBaseService.ts"
)


# ── Override do root conftest (teste puramente estático) ────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    pura inspeção de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspeção do TypeScript ───────────────────────────────


def _read_text(path: Path) -> str:
    """Lê o arquivo e devolve o conteúdo como string única."""
    assert path.exists(), (
        f"Arquivo nao encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-4 (timeout visivel BKL-038) exige que este "
        f"arquivo exista no repositório."
    )
    return path.read_text(encoding="utf-8")


# ── AC#1 — useKnowledgeBase.ts: POLLING_TIMEOUT_MS = 120_000 ────────


def test_b4_ac1_polling_timeout_ausente():
    """AC#1: ``useKnowledgeBase.ts`` DEVE definir a constante
    ``POLLING_TIMEOUT_MS = 120_000`` (ou literal ``120000``) que
    limita o tempo que um doc pode ficar em ``processing``/``pending``
    antes de ser considerado travado.

    Falha (RED) enquanto a constante nao existir.  Quando
    implementada, o teste passa.
    """
    content = _read_text(USE_KNOWLEDGE_BASE_PATH)

    # Aceita tanto ``120_000`` quanto ``120000`` (separador de milhar
    # opcional).  Tambem aceita ``= 120_000`` ou ``=120000`` etc.
    pattern = re.compile(
        r"\bPOLLING_TIMEOUT_MS\s*=\s*120[_\s]?000\b",
        re.IGNORECASE,
    )

    if not pattern.search(content):
        pytest.fail(
            "AC#1 violada — RED.  A constante ``POLLING_TIMEOUT_MS = "
            "120_000`` nao existe em "
            f"{USE_KNOWLEDGE_BASE_PATH.relative_to(REPO_ROOT)}.\n\n"
            "O behavior B-4 (timeout visivel BKL-038) precisa de um "
            "limite de tempo explícito (120 000 ms = 2 min) para "
            "definir quando um documento em ``processing``/``pending`` "
            "deve ser considerado travado e marcado como ``failed``.\n\n"
            "GREEN deve adicionar ao topo do hook (logo após os "
            "imports, antes do ``useState``):\n\n"
            "  const POLLING_TIMEOUT_MS = 120_000\n\n"
            "Variantes aceitas: ``120_000``, ``120000``.  Outros "
            "valores (ex.: 60_000, 180_000) nao satisfazem este AC."
        )


# ── AC#2 — useKnowledgeBase.ts: lógica de timeout no setInterval ────


def test_b4_ac2_timeout_logic_ausente():
    """AC#2: O ``useEffect`` de polling em ``useKnowledgeBase.ts``
    (aquele que tem ``setInterval(..., 5_000)``) DEVE ter lógica de
    timeout: a cada ciclo, calcular ``Date.now() - startTime`` (ou
    variável ``elapsed`` equivalente) e, quando exceder
    ``POLLING_TIMEOUT_MS``, marcar o doc localmente com
    ``status: 'failed'`` e ``error_message``.

    Falha (RED) enquanto a lógica de timeout nao existir dentro
    do ``setInterval``.  Quando implementada, o teste passa.
    """
    content = _read_text(USE_KNOWLEDGE_BASE_PATH)

    # Pré-condição de sanidade: o setInterval(..., 5_000) precisa
    # existir no arquivo, caso contrário este teste nao faria
    # sentido (a AC é "dentro deste setInterval").
    interval_match = re.search(
        r"setInterval\s*\(",
        content,
    )
    assert interval_match, (
        "Pré-condição violada: nao encontrei ``setInterval(`` em "
        f"{USE_KNOWLEDGE_BASE_PATH.relative_to(REPO_ROOT)}.  O "
        "behavior B-4 pressupõe que já existe um useEffect de "
        "polling com setInterval(..., 5_000)."
    )

    # Fatia o conteúdo APÓS o setInterval (janela generosa de 3000
    # chars cobre o callback inteiro do setInterval + o useEffect).
    after_interval = content[interval_match.start() : interval_match.start() + 3000]

    # Detecta a presença de cálculo de elapsed/tempo decorrido.
    # Aceita padrões comuns:
    #   Date.now() - startTime
    #   Date.now() - startedAt
    #   Date.now() - processingStartedAt
    #   const elapsed = ...
    elapsed_patterns = [
        r"Date\.now\s*\(\s*\)\s*-\s*start[A-Za-z_]*",
        r"elapsed\s*=",
        r"const\s+elapsed\b",
    ]
    elapsed_found = any(
        re.search(p, after_interval, re.IGNORECASE)
        for p in elapsed_patterns
    )

    # Detecta a presença de comparação com o timeout.
    timeout_compare_patterns = [
        r"elapsed\s*>\s*POLLING_TIMEOUT_MS",
        r"elapsed\s*>=\s*POLLING_TIMEOUT_MS",
        r"POLLING_TIMEOUT_MS\s*<\s*elapsed",
        r"POLLING_TIMEOUT_MS\s*<=\s*elapsed",
        r"Date\.now\s*\(\s*\)\s*-\s*\w+\s*>\s*POLLING_TIMEOUT_MS",
    ]
    timeout_compare_found = any(
        re.search(p, after_interval, re.IGNORECASE)
        for p in timeout_compare_patterns
    )

    # Detecta a marcação do doc como failed com error_message
    # dentro do setInterval (ou próximo a ele).
    fail_mark_patterns = [
        r"status:\s*['\"]failed['\"]",
        r"error_message\s*:",
    ]
    fail_mark_found = any(
        re.search(p, after_interval, re.IGNORECASE)
        for p in fail_mark_patterns
    )

    if not (elapsed_found and timeout_compare_found and fail_mark_found):
        missing = []
        if not elapsed_found:
            missing.append("calculo de elapsed (Date.now() - startTime)")
        if not timeout_compare_found:
            missing.append("comparacao elapsed > POLLING_TIMEOUT_MS")
        if not fail_mark_found:
            missing.append("marcacao do doc como status:'failed' + error_message")

        pytest.fail(
            "AC#2 violada — RED.  O ``useEffect`` de polling em "
            f"{USE_KNOWLEDGE_BASE_PATH.relative_to(REPO_ROOT)} "
            "(linhas ~54-65) chama ``load()`` a cada 5s mas NAO "
            "implementa a lógica de timeout do BKL-038.\n\n"
            "Estao faltando os seguintes elementos dentro do callback "
            "do ``setInterval(..., 5_000)``:\n\n"
            "  - " + "\n  - ".join(missing) + "\n\n"
            "GREEN deve substituir o corpo simples ``load()`` por "
            "uma lógica que, a cada ciclo:\n\n"
            "  1) Calcule ``const elapsed = Date.now() - startTime`` "
            "(onde ``startTime`` é quando o doc entrou em "
            "``processing``/``pending``).\n"
            "  2) Se ``elapsed > POLLING_TIMEOUT_MS``, marque o doc "
            "localmente com ``status: 'failed'`` e "
            "``error_message: 'Timeout: documento em processamento "
            "ha mais de 2 minutos.'``.\n"
            "  3) Caso contrário, chame ``load()`` normalmente.\n\n"
            "Variaveis de tempo aceitas: ``startTime``, ``startedAt``, "
            "``processingStartedAt``.  A variável ``elapsed`` é "
            "recomendada para clareza."
        )


# ── AC#3 — BibliotecaRoom.tsx: badge "Falha no processamento" ──────


def test_b4_ac3_falha_processamento_ausente():
    """AC#3: ``BibliotecaRoom.tsx`` DEVE estender ``kbStatusBadge``
    (a funcao ``switch(status)`` que define ``label``/``color`` dos
    badges da Biblioteca) com um case que reconheça o estado de
    timeout e exiba o label literal "Falha no processamento".

    Falha (RED) enquanto o label "Falha no processamento" nao
    aparecer em nenhum lugar do arquivo.
    """
    content = _read_text(BIBLIOTECA_ROOM_PATH)

    # Procura pelo label literal "Falha no processamento" no arquivo.
    pattern = re.compile(r"Falha\s+no\s+processamento", re.IGNORECASE)

    if not pattern.search(content):
        # Verifica se a funcao kbStatusBadge existe (pre-condicao).
        assert "kbStatusBadge" in content, (
            "Pré-condição violada: a funcao ``kbStatusBadge`` nao "
            f"foi encontrada em "
            f"{BIBLIOTECA_ROOM_PATH.relative_to(REPO_ROOT)}.  O "
            "behavior B-4 pressupõe que esta funcao já existe e "
            "precisa ser estendida com um case de timeout."
        )

        pytest.fail(
            "AC#3 violada — RED.  O label ``'Falha no "
            "processamento'`` nao aparece em "
            f"{BIBLIOTECA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            "O behavior B-4 (timeout visivel BKL-038) exige que "
            "``kbStatusBadge`` (funcao ``switch(status)`` que mapeia "
            "``status`` → ``{label, color}``) seja estendida com um "
            "case para o estado de timeout.  Atualmente o switch "
            "cobre apenas ``'completed'``, ``'processing'``, "
            "``'pending'``, ``'failed'``, ``'partially_failed'`` — "
            "nenhum trata o caso de timeout (doc travado em "
            "``processing`` por mais de 2 min).\n\n"
            "GREEN deve adicionar ao switch de ``kbStatusBadge`` "
            "(em BibliotecaRoom.tsx, ~linha 37-46) um case adicional "
            "para o status de timeout.  Como o hook "
            "``useKnowledgeBase`` já marca o doc com "
            "``status: 'failed'`` quando há timeout, a abordagem "
            "mais limpa é distinguir visualmente os ``failed`` "
            "normais dos ``failed`` por timeout, exibindo o label "
            "literal ``'Falha no processamento'`` quando o doc "
            "atingiu ``POLLING_TIMEOUT_MS``.\n\n"
            "Padrão esperado (variáveis podem variar):\n\n"
            "  case 'timed_out':\n"
            "    return { label: 'Falha no processamento', "
            "color: 'var(--urg)' }\n\n"
            "ou, equivalentemente, uma checagem do tipo "
            "``doc.error_message?.includes('Timeout')`` no "
            "``kbStatusBadge``."
        )


# ── AC#4 — BibliotecaRoom.tsx: funcao isTimedOut() ──────────────────


def test_b4_ac4_is_timed_out_ausente():
    """AC#4: ``BibliotecaRoom.tsx`` DEVE definir uma função
    ``isTimedOut(doc)`` que retorna ``true`` quando o documento está
    em estado de timeout (ex.: ``processing``/``pending`` por mais
    de 2 min, ou ``status === 'timed_out'``).

    Falha (RED) enquanto a funcao nao existir.  Quando implementada,
    o teste passa.
    """
    content = _read_text(BIBLIOTECA_ROOM_PATH)

    # Procura pela declaracao de funcao ``isTimedOut``.
    pattern = re.compile(
        r"\bfunction\s+isTimedOut\s*\(",
        re.IGNORECASE,
    )

    if not pattern.search(content):
        # Variantes aceitas: arrow function atribuída a const, ou
        # const isTimedOut = (doc) => ...  (também checamos).
        arrow_pattern = re.compile(
            r"\b(?:const|let|var)\s+isTimedOut\s*=",
            re.IGNORECASE,
        )
        if not arrow_pattern.search(content):
            pytest.fail(
                "AC#4 violada — RED.  A funcao ``isTimedOut(doc)`` "
                f"nao existe em "
                f"{BIBLIOTECA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
                "O behavior B-4 (timeout visivel BKL-038) precisa de "
                "um helper que receba um ``KBDocument`` e retorne "
                "``true`` quando o doc está travado em "
                "``processing``/``pending`` por mais de "
                "``POLLING_TIMEOUT_MS`` (120 000 ms = 2 min), ou "
                "alternativamente quando ``doc.status === "
                "'timed_out'``.\n\n"
                "GREEN deve adicionar ao arquivo (sugestao: próximo "
                "à funcao ``kbStatusBadge``, ~linha 37):\n\n"
                "  function isTimedOut(doc: KBDocument): boolean {\n"
                "    // Implementacao 1: checa status dedicado\n"
                "    if (doc.status === 'timed_out') return true\n"
                "    // Implementacao 2: calcula elapsed desde o "
                "início do processing\n"
                "    if (doc.status === 'processing' || "
                "doc.status === 'pending') {\n"
                "      const startedAt = new Date("
                "doc.processing_started_at ?? doc.created_at)"
                ".getTime()\n"
                "      return Date.now() - startedAt > "
                "POLLING_TIMEOUT_MS\n"
                "    }\n"
                "    return false\n"
                "  }\n\n"
                "Variantes aceitas: ``function isTimedOut(`` ou "
                "``const isTimedOut = (doc) => ...``."
            )


# ── AC#5 — BibliotecaRoom.tsx: exibicao de doc.error_message ────────


def test_b4_ac5_error_message_ausente():
    """AC#5: ``BibliotecaRoom.tsx`` DEVE exibir ``doc.error_message``
    (ou ``errorMessage``) na UI para documentos com falha.

    Falha (RED) enquanto nenhuma referencia a ``error_message`` /
    ``errorMessage`` aparecer no JSX/return da funcao principal.
    """
    content = _read_text(BIBLIOTECA_ROOM_PATH)

    # Procura por qualquer referencia a ``doc.error_message`` ou
    # ``errorMessage`` no arquivo.  Aceita camelCase (``errorMessage``)
    # e snake_case (``error_message``), ambos com ou sem prefixo
    # ``doc.``.
    patterns = [
        r"\bdoc\.error_message\b",
        r"\bdoc\.errorMessage\b",
        r"\{error_message\}",
        r"\{errorMessage\}",
    ]

    if not any(re.search(p, content, re.IGNORECASE) for p in patterns):
        pytest.fail(
            "AC#5 violada — RED.  Nao encontrei nenhuma exibicao de "
            "``doc.error_message`` (ou ``errorMessage``) no JSX de "
            f"{BIBLIOTECA_ROOM_PATH.relative_to(REPO_ROOT)}.\n\n"
            "O behavior B-4 (timeout visivel BKL-038) exige que, "
            "para documentos com falha (especialmente os que "
            "atingiram o timeout), a ``error_message`` retornada "
            "pelo backend (ou gerada client-side em "
            "``useKnowledgeBase``) seja exibida na UI — tanto no "
            "card (grid view) quanto na row (list view), ou em um "
            "bloco de erro destacado ao lado do badge.\n\n"
            "GREEN deve adicionar um bloco de erro no ``DocCard`` e "
            "no ``DocRow`` (ou em um painel de detalhes) que "
            "renderize ``doc.error_message`` quando ele estiver "
            "preenchido.  Exemplo:\n\n"
            "  {doc.error_message && (\n"
            "    <div style={{ fontSize: 10, color: 'var(--urg)', "
            "marginTop: 4 }}>\n"
            "      {doc.error_message}\n"
            "    </div>\n"
            "  )}\n\n"
            "Variantes aceitas: ``doc.error_message``, "
            "``doc.errorMessage``, ``error_message``, "
            "``errorMessage``."
        )
