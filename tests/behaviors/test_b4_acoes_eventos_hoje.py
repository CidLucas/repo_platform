"""RED test for behavior B-4 — Ações e detalhes nos eventos da aba Hoje (AgendaRoom).

GOAL:
    Cada evento renderizado no tab "hoje" (id="ag-hoje") da AgendaRoom deve ter
    (1) toggle para expandir detalhes, (2) botão "Confirmar" e (3) botão
    "Remarcar", (4) exibir dados de contato/observação ao expandir, (5) usar
    estado de expansão INDEPENDENTE do tab "pendentes" (que usa
    `expandedId` + `toggleDc`), e (6) seguir o mesmo padrão visual `dc-row`
    usado nas aprovações.

BEHAVIOR:
    B-4 — Eventos "hoje" da agenda devem ter expandir detalhes (toggle) +
    ações (Confirmar / Remarcar) + dados de contato/observação visíveis ao
    expandir, com expansão isolada (não conflita com a expansão dos approvals
    da aba "pendentes").

AC (Acceptance Criteria):
    AC#1 — Cada `ev-row` no tab "hoje" deve ter onClick de toggle para
           expandir/recolher detalhes (usando um state próprio, não o mesmo
           `expandedId` do pendentes).
    AC#2 — Cada evento expandido deve ter botão "Confirmar" que chama
           `openChatWith(...)` com contexto de presença/confirmar.
    AC#3 — Cada evento expandido deve ter botão "Remarcar" que chama
           `openChatWith(...)` com contexto de remarcar/reagendar.
    AC#4 — Ao expandir, devem aparecer dados de contato (`ev.contact`) e
           observação (`ev.observation`) do evento.
    AC#5 — A expansão dos eventos "hoje" deve usar `expandedId` DIFERENTE do
           `expandedId` usado pelas aprovações da aba "pendentes" — ou seja,
           uma variável/estado novo (ex: `hojeExpandedId`, `eventExpandedId`,
           etc.) e/ou um toggle próprio (ex: `toggleHojeDc`, `toggleEvent`).
    AC#6 — Deve usar o mesmo padrão visual `dc-row` (classes `dc-row`,
           `dc-chev`, `dc-expand`) já usado nas aprovações.

ESTADO ATUAL (RED):
    - AgendaRoom.tsx (linhas 171-193): o tab "hoje" (id="ag-hoje") renderiza
      eventos com `<div key={ev.id} className="ev-row">`, sem onClick, sem
      toggle, sem botões "Confirmar" / "Remarcar", sem seção de detalhes
      com `ev.contact` / `ev.observation`.
    - AgendaRoom.tsx (linhas 196-224): a aba "pendentes" já usa o padrão
      `expandedId === approval.id` + `toggleDc(approval.id)` + classes
      `dc-row`, `dc-chev`, `dc-expand` (modelo a ser replicado).

ESTADO ALVO (GREEN):
    - O tab "hoje" deve ter:
        * um state próprio (ex: `hojeExpandedId`) + toggle próprio
          (ex: `toggleHojeDc`),
        * `onClick` na linha do evento chamando o toggle,
        * classes `dc-row`, `dc-chev`, `dc-expand` (mesmas dos approvals),
        * um bloco `dc-expand` com `ev.contact`, `ev.observation` e dois
          botões: "Confirmar" e "Remarcar", ambos chamando `openChatWith`
          com contexto adequado.

Anti-Goals (must NOT be violated):
    1. NAO remover o tab "hoje" (id="ag-hoje") nem o map de `todayEvents`.
    2. NAO remover o tab "pendentes" (id="ag-pendentes") nem o padrão
       `expandedId` / `toggleDc` dos approvals.
    3. NAO reusar o mesmo `expandedId` e/ou `toggleDc` para os eventos
       "hoje" (isso causaria conflito de expansão entre tabs).
    4. NAO quebrar as queries/estados existentes da AgendaRoom
       (integrations, scheduleQ, approvals, etc.).
    5. NAO introduzir mocks, dependências de DB ou imports do módulo React
       no teste — o teste é puramente source-inspection.
    6. NAO alterar a coluna lateral (rcol) que lista os eventos "hoje"
       em formato compacto (esta é uma lista resumida, não a lista
       detalhada da aba).

Estratégia de teste (source-inspection):
    - Lê o AgendaRoom.tsx como texto puro (Path.read_text).
    - Aplica regex para localizar o bloco do tab "hoje" (id="ag-hoje").
    - Verifica a presença de onClick de toggle, dos botões "Confirmar" /
       "Remarcar", do uso de `ev.contact` / `ev.observation`, da existência
       de um state próprio de expansão (≠ `expandedId`/`toggleDc`) e das
       classes visuais `dc-row` / `dc-chev` / `dc-expand`.
    - Não toca DB, não monta mocks, não importa o módulo React.
    - Falha com pytest.fail() / assert em pt-BR enquanto não implementado
       (RED) e passa quando o Coder implementar (GREEN).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

AGENDA_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "AgendaRoom.tsx"


# ── Source-level helpers ───────────────────────────────────────────────────


def _read_source() -> str:
    """Lê o código-fonte do AgendaRoom.tsx como texto puro."""
    assert AGENDA_PATH.exists(), f"Source file not found: {AGENDA_PATH}"
    return AGENDA_PATH.read_text(encoding="utf-8")


def _find_block_by_id(source: str, element_id: str) -> str | None:
    """Extrai o bloco `<div ... id="<element_id>" ...>...</div>` do source.

    Faz o aninhamento por contagem de `<div ...>` vs `</div>` para tolerar
    divs aninhadas dentro do bloco. Trata corretamente tags self-closing
    (`<div ... />`) para não quebrar a contagem.
    """
    m = re.search(rf'<div[^>]*id\s*=\s*"{re.escape(element_id)}"[^>]*>', source)
    if not m:
        return None

    div_start = m.start()
    depth = 0
    i = div_start
    while i < len(source):
        if source[i:i + 4] == '<div' and not source[i:i + 5] == '</div':
            # Pula atributos até o fim da tag (>, />, ou <)
            j = i + 4
            while j < len(source) and source[j] not in ('>', '/'):
                j += 1
            if j < len(source) and source[j] == '>':
                # Verifica self-closing: char anterior é '/'
                if j > 0 and source[j - 1] == '/':
                    i = j + 1
                else:
                    depth += 1
                    i = j + 1
            elif j < len(source) and source[j] == '/':
                # Pula até o '>' que fecha a tag self-closing
                while j < len(source) and source[j] != '>':
                    j += 1
                i = j + 1
            else:
                i += 1
        elif source[i:i + 6] == '</div>':
            depth -= 1
            i += 6
            if depth == 0:
                return source[div_start:i]
        else:
            i += 1
    return None


# ── Tests ─────────────────────────────────────────────────────────────────


def test_b4_ac1_ev_row_tem_onclick_toggle() -> None:
    """AC#1 — Cada ev-row no tab "hoje" deve ter onClick de toggle.

    O bloco `id="ag-hoje"` deve conter, dentro do map de `todayEvents`, um
    elemento clicável (classe `ev-row` ou `dc-row`) com `onClick` que altera
    um state de expansão (ex: `toggleHojeDc(ev.id)`, `setHojeExpandedId(...)`,
    `toggleEvent(ev.id)`, etc.).
    """
    source = _read_source()
    hoje_block = _find_block_by_id(source, "ag-hoje")

    assert hoje_block is not None, (
        "RED — AC#1: Bloco do tab 'hoje' (id=ag-hoje) não encontrado em "
        "AgendaRoom.tsx.\n"
        "  Esperado: <div className=\"tc...\" id=\"ag-hoje\"> presente.\n"
        "  O tab 'hoje' deve ser preservado."
    )

    # Procura por uma linha de evento (ev-row ou dc-row) com onClick
    has_onclick_toggle = bool(re.search(
        r'<(?:ev-row|dc-row)[^>]*onClick\s*=',
        hoje_block,
    ))
    assert has_onclick_toggle, (
        "RED — AC#1: Nenhuma linha de evento (ev-row/dc-row) com onClick de "
        "toggle encontrada no tab 'hoje'.\n"
        "  Esperado: <div className=\"ev-row\" (ou dc-row) onClick={...toggle...}>\n"
        "  O Coder deve adicionar um onClick que alterne a expansão do "
        "evento, usando um state próprio (não `expandedId` dos approvals)."
    )


def test_b4_ac2_botao_confirmar_openchatwith() -> None:
    """AC#2 — Botão 'Confirmar' no evento expandido chama openChatWith.

    Dentro do bloco `id="ag-hoje"`, deve existir um botão com texto
    'Confirmar' (presença) que chama `openChatWith(...)` com contexto
    adequado (ex: 'Confirmar presença em ...').
    """
    source = _read_source()
    hoje_block = _find_block_by_id(source, "ag-hoje")

    assert hoje_block is not None, (
        "RED — AC#2: Bloco do tab 'hoje' (id=ag-hoje) não encontrado em "
        "AgendaRoom.tsx.\n"
        "  Esperado: <div className=\"tc...\" id=\"ag-hoje\"> presente."
    )

    # Procura um <button ...>Confirmar ...</button>
    btn_confirmar = re.search(
        r'<button[^>]*>\s*[^<]*Confirmar[^<]*</button>',
        hoje_block,
    )
    assert btn_confirmar is not None, (
        "RED — AC#2: Nenhum botão 'Confirmar' encontrado no tab 'hoje'.\n"
        "  Esperado: <button className=\"btn ...\" onClick={() => "
        "openChatWith('Confirmar presença em ...')}>Confirmar</button>\n"
        f"  Conteúdo atual do bloco:\n  {hoje_block[:500]}...\n"
        "  O Coder deve adicionar um botão 'Confirmar' (presença) dentro "
        "do bloco dc-expand do evento."
    )

    # Verifica que o MESMO <button> (ou o trecho próximo) tem openChatWith
    # O botão pode estar em múltiplas linhas — pega um trecho maior.
    button_start = hoje_block.rfind('<button', 0, btn_confirmar.start())
    if button_start >= 0:
        trecho = hoje_block[button_start:btn_confirmar.end()]
    else:
        trecho = btn_confirmar.group(0)

    has_openchat = bool(re.search(r'openChatWith\s*\(', trecho))
    assert has_openchat, (
        "RED — AC#2: Botão 'Confirmar' encontrado no tab 'hoje', mas SEM "
        "chamada a openChatWith.\n"
        f"  Trecho: {trecho[:240]}...\n"
        "  Esperado: onClick={() => openChatWith('...')} no botão.\n"
        "  O Coder deve conectar o onClick do botão 'Confirmar' ao "
        "openChatWith com contexto de presença/confirmar."
    )


def test_b4_ac3_botao_remarcar_openchatwith() -> None:
    """AC#3 — Botão 'Remarcar' no evento expandido chama openChatWith.

    Dentro do bloco `id="ag-hoje"`, deve existir um botão com texto
    'Remarcar' (ou 'Reagendar') que chama `openChatWith(...)` com contexto
    adequado (ex: 'Remarcar reunião ...').
    """
    source = _read_source()
    hoje_block = _find_block_by_id(source, "ag-hoje")

    assert hoje_block is not None, (
        "RED — AC#3: Bloco do tab 'hoje' (id=ag-hoje) não encontrado em "
        "AgendaRoom.tsx.\n"
        "  Esperado: <div className=\"tc...\" id=\"ag-hoje\"> presente."
    )

    # Procura um <button ...>Remarcar ...</button> (ou Reagendar)
    btn_remarcar = re.search(
        r'<button[^>]*>\s*[^<]*(?:Remarcar|Reagendar)[^<]*</button>',
        hoje_block,
    )
    assert btn_remarcar is not None, (
        "RED — AC#3: Nenhum botão 'Remarcar' (ou 'Reagendar') encontrado "
        "no tab 'hoje'.\n"
        "  Esperado: <button className=\"btn ...\" onClick={() => "
        "openChatWith('Remarcar reunião ...')}>Remarcar</button>\n"
        f"  Conteúdo atual do bloco:\n  {hoje_block[:500]}...\n"
        "  O Coder deve adicionar um botão 'Remarcar' (ou 'Reagendar') "
        "dentro do bloco dc-expand do evento."
    )

    # Verifica que o MESMO <button> (ou o trecho próximo) tem openChatWith
    button_start = hoje_block.rfind('<button', 0, btn_remarcar.start())
    if button_start >= 0:
        trecho = hoje_block[button_start:btn_remarcar.end()]
    else:
        trecho = btn_remarcar.group(0)

    has_openchat = bool(re.search(r'openChatWith\s*\(', trecho))
    assert has_openchat, (
        "RED — AC#3: Botão 'Remarcar' encontrado no tab 'hoje', mas SEM "
        "chamada a openChatWith.\n"
        f"  Trecho: {trecho[:240]}...\n"
        "  Esperado: onClick={() => openChatWith('...')} no botão.\n"
        "  O Coder deve conectar o onClick do botão 'Remarcar' ao "
        "openChatWith com contexto de remarcar/reagendar."
    )


def test_b4_ac4_contato_observacao_ao_expandir() -> None:
    """AC#4 — Ao expandir, mostrar `ev.contact` e `ev.observation`.

    Dentro do bloco `id="ag-hoje"`, o trecho de detalhes (geralmente dentro
    de um `dc-expand`) deve referenciar `ev.contact` e `ev.observation`
    para exibir os dados de contato/observação do evento quando expandido.
    """
    source = _read_source()
    hoje_block = _find_block_by_id(source, "ag-hoje")

    assert hoje_block is not None, (
        "RED — AC#4: Bloco do tab 'hoje' (id=ag-hoje) não encontrado em "
        "AgendaRoom.tsx.\n"
        "  Esperado: <div className=\"tc...\" id=\"ag-hoje\"> presente."
    )

    has_contact = bool(re.search(r'ev\.contact', hoje_block))
    has_observation = bool(re.search(r'ev\.observation', hoje_block))

    assert has_contact, (
        "RED — AC#4: Referência a 'ev.contact' não encontrada no tab 'hoje'.\n"
        "  Esperado: o bloco dc-expand (detalhes) do evento deve usar\n"
        "  {ev.contact} e/ou {ev.observation} para exibir dados de\n"
        "  contato/observação ao expandir.\n"
        f"  Conteúdo atual do bloco:\n  {hoje_block[:500]}...\n"
        "  O Coder deve adicionar a renderização de ev.contact no dc-expand."
    )

    assert has_observation, (
        "RED — AC#4: Referência a 'ev.observation' não encontrada no tab "
        "'hoje'.\n"
        "  Esperado: o bloco dc-expand (detalhes) do evento deve usar\n"
        "  {ev.observation} para exibir a observação ao expandir.\n"
        f"  Conteúdo atual do bloco:\n  {hoje_block[:500]}...\n"
        "  O Coder deve adicionar a renderização de ev.observation no "
        "dc-expand."
    )


def test_b4_ac5_expandedid_diferente_do_pendentes() -> None:
    """AC#5 — Estado de expansão do 'hoje' deve ser DIFERENTE do pendentes.

    A expansão dos eventos "hoje" NÃO pode reusar o `expandedId` (do
    `useAppStore`) nem o `toggleDc` (do `useAppStore`) — caso contrário,
    expandir um evento em "hoje" fecharia o approval expandido em
    "pendentes" e vice-versa.

    Espera-se um state próprio (ex: `hojeExpandedId`, `eventExpandedId`,
    `expandedEventId`, ...) e/ou um toggle próprio (ex: `toggleHojeDc`,
    `toggleEvent`, `setExpandedEventId`).
    """
    source = _read_source()

    hoje_block = _find_block_by_id(source, "ag-hoje")
    assert hoje_block is not None, (
        "RED — AC#5: Bloco do tab 'hoje' (id=ag-hoje) não encontrado em "
        "AgendaRoom.tsx.\n"
        "  Esperado: <div className=\"tc...\" id=\"ag-hoje\"> presente."
    )

    # Procura por um useState próprio para a expansão do "hoje".
    # Aceita nomes como: hojeExpandedId, expandedEventId, eventExpandedId,
    # expandedHojeId, hojeDc, etc.
    has_own_state = bool(re.search(
        r'useState[<(][^>]*?>\(\s*(?:null|"")\s*\)',
        source,
    )) and bool(re.search(
        r'(?:hoje|event|dc)[_-]?(?:ExpandedId|Dc)|(?:ExpandedId|Dc)[_-]?(?:Hoje|Event)',
        source,
        re.IGNORECASE,
    ))

    # Procura também por um setter chamado a partir do onClick na linha
    # do evento "hoje" (setHojeExpandedId, setExpandedEventId, etc.) ou
    # um toggle próprio (toggleHojeDc, toggleEvent).
    has_own_toggle = bool(re.search(
        r'(?:setHojeExpanded|setExpandedEvent|setEventExpanded|'
        r'setExpandedHoje|toggleHojeDc|toggleEvent|toggleEventDc)\s*\(',
        source,
    ))

    # Garante que o onClick no ag-hoje NÃO é toggleDc puro (do store)
    # (o toggleDc do store manipula expandedId e conflitaria com pendentes)
    onclick_toggleDc_hoje = bool(re.search(
        r'onClick\s*=\s*\{\s*\(\)\s*=>\s*toggleDc\s*\(',
        hoje_block,
    ))

    if onclick_toggleDc_hoje and not (has_own_state or has_own_toggle):
        pytest.fail(
            "RED — AC#5: O tab 'hoje' está reusando `toggleDc` do store "
            "para a expansão dos eventos.\n"
            "  ANTI-GOAL VIOLATED: isso CONFLITA com a expansão dos "
            "approvals na aba 'pendentes' (que usa o MESMO `expandedId`).\n"
            "  Esperado: criar um state próprio (ex: useState<string|null> "
            "para hojeExpandedId) e/ou um toggle próprio "
            "(ex: toggleHojeDc / toggleEvent).\n"
            "  O Coder deve isolar a expansão dos eventos 'hoje' em uma "
            "variável/função diferente de `expandedId`/`toggleDc`."
        )

    assert has_own_state or has_own_toggle, (
        "RED — AC#5: Nenhum state/toggle próprio para a expansão dos "
        "eventos 'hoje' foi encontrado.\n"
        "  Esperado: declarar useState próprio (ex: const [hojeExpandedId, "
        "setHojeExpandedId] = useState<string|null>(null))\n"
        "  e/ou um toggle próprio (ex: toggleHojeDc(ev.id)).\n"
        "  Anti-goal: reusar `expandedId` + `toggleDc` do store faz a "
        "expansão de 'hoje' conflitar com a de 'pendentes'.\n"
        "  O Coder deve criar estado isolado para a expansão dos eventos "
        "do tab 'hoje'."
    )


def test_b4_ac6_padrao_visual_dc_row() -> None:
    """AC#6 — Mesmo padrão visual `dc-row` usado nos approvals.

    Dentro do bloco `id="ag-hoje"`, o card do evento deve usar as classes
    `dc-row`, `dc-chev` e `dc-expand` (o mesmo padrão visual dos approvals
    da aba "pendentes").
    """
    source = _read_source()
    hoje_block = _find_block_by_id(source, "ag-hoje")

    assert hoje_block is not None, (
        "RED — AC#6: Bloco do tab 'hoje' (id=ag-hoje) não encontrado em "
        "AgendaRoom.tsx.\n"
        "  Esperado: <div className=\"tc...\" id=\"ag-hoje\"> presente."
    )

    has_dc_row = bool(re.search(r'className\s*=\s*"[^"]*\bdc-row\b', hoje_block))
    has_dc_chev = bool(re.search(r'className\s*=\s*"[^"]*\bdc-chev\b', hoje_block))
    has_dc_expand = bool(re.search(r'className\s*=\s*"[^"]*\bdc-expand\b', hoje_block))

    missing: list[str] = []
    if not has_dc_row:
        missing.append("dc-row")
    if not has_dc_chev:
        missing.append("dc-chev")
    if not has_dc_expand:
        missing.append("dc-expand")

    assert not missing, (
        f"RED — AC#6: Classes do padrão visual dc-row AUSENTES no tab "
        f"'hoje': {missing}.\n"
        "  Esperado: o card do evento deve usar as classes 'dc-row', "
        "'dc-chev' e 'dc-expand',\n"
        "  iguais às usadas na aba 'pendentes' (approvals), para manter o "
        "mesmo padrão visual.\n"
        f"  Conteúdo atual do bloco:\n  {hoje_block[:500]}...\n"
        "  O Coder deve aplicar as classes dc-row / dc-chev / dc-expand "
        "no card do evento 'hoje', replicando o padrão dos approvals."
    )
