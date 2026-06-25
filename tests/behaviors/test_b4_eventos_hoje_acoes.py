"""RED test for B-4 (BATCH #205) — Eventos da aba ``Hoje`` com ações + integração fixa.

GOAL:
    Confirmar que a ``AgendaRoom.tsx`` ainda NÃO foi atualizada para tornar
    os eventos da aba ``Hoje`` interativos (com ``expandedEventId``,
    ``onClick`` para expandir/colapsar e botões de ação ``Confirmar`` /
    ``Remarcar``) e nem para tornar o botão ``Adicionar Integração``
    sticky/fixed. Este é um teste source-inspection TRUE RED — cada AC
    deve passar enquanto o código de produção estiver em seu estado
    anterior, sinalizando que a feature ainda não foi entregue.

BEHAVIOR:
    B-4 — ``apps/blu_v3/src/pages/app/AgendaRoom.tsx`` deve:

        1. Adicionar state React ``expandedEventId`` (string | null) ao
           ``AgendaRoom`` para controlar qual evento da aba ``Hoje`` está
           expandido.
        2. Adicionar handler ``onClick`` em cada ``.ev-row`` da aba
           ``Hoje`` para toggle do estado expandido.
        3. Quando expandido, mostrar detalhes + botão de ação
           ``Confirmar`` para o evento.
        4. Quando expandido, mostrar detalhes + botão de ação
           ``Remarcar`` para o evento.
        5. Tornar o botão ``Adicionar Integração`` (no painel principal)
           sticky/fixed para que continue acessível sem scroll.

    Estado atual (BEFORE — confirmado por inspeção de
    ``apps/blu_v3/src/pages/app/AgendaRoom.tsx``):

        - Linha 50: ``const [tab, setTab] = useState<Tab>('gantt')``
          → NÃO há state ``expandedEventId``.
        - Linhas 179-191: eventos renderizados como ``<div … className="ev-row">``
          simples, SEM ``onClick`` e SEM botões de ação.
        - Linhas 349-360: botão ``＋ Adicionar integração`` dentro de
          ``<CollapsiblePanel id="agenda-calendarios" …>`` → seção
          ``Gestão de Projetos`` → SEM posicionamento sticky/fixed
          (``style={{ fontSize: 10 }}`` apenas).

AC (Acceptance Criteria):
    AC#1 — ``AgendaRoom.tsx`` NÃO possui state React ``expandedEventId``.
    AC#2 — As linhas de evento (``.ev-row``) na aba ``Hoje`` NÃO possuem
           handler ``onClick`` para toggle de expansão.
    AC#3 — NÃO há botão de ação ``Confirmar`` associado a eventos na aba
           ``Hoje``.
    AC#4 — NÃO há botão de ação ``Remarcar`` associado a eventos na aba
           ``Hoje``.
    AC#5 — O botão ``Adicionar Integração`` NÃO está posicionado como
           sticky/fixed (sem ``position: 'sticky'`` / ``position: 'fixed'``
           próximo ao texto ``Adicionar integração``).

DECISION:
    Estratégia: extend — editar
    ``apps/blu_v3/src/pages/app/AgendaRoom.tsx`` in-place.
    Nenhum arquivo novo deve ser criado. As alterações ficam
    contidas na ``AgendaRoom`` (state, handlers, JSX do painel principal
    e estilo sticky do botão de integração).

Test strategy:
    Source-inspection (lê o ``.tsx`` como texto). O test runner não
    transpila nem executa TSX — apenas regex-match na string lida do
    disco. Cada AC é um método da classe ``TestB4EventosHoje``:

        - Lê o source uma vez por teste (helper ``read_source``).
        - Aplica uma regex específica da AC.
        - Se a regex ENCONTRAR o padrão esperado no estado GREEN,
          dispara ``pytest.fail("FALSE RED — …")`` com mensagem em
          pt-BR explicando por que o teste está FAILING (a feature já
          foi implementada, então o RED é inválido).
        - Se a regex NÃO ENCONTRAR o padrão, o teste passa em silêncio
          (TRUE RED — a feature ainda não foi entregue).

Anti-Goals (must NOT be violated):
    1. NÃO modificar o código de produção — apenas escrever o teste.
    2. NÃO transpilar nem executar TSX — source-inspection puro.
    3. NÃO usar mocks, Supabase, banco de dados ou rede.
    4. NÃO falhar o teste por causa de imports ou whitespace — apenas
       pelos 5 padrões textuais definidos nas ACs.
    5. NÃO inverter a polaridade do teste: o test deve passar AGORA
       (RED = feature ausente) e falhar depois que a feature for
       entregue (GREEN). A inversão de polaridade é uma armadilha
       clássica em testes de source-inspection.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Path resolution (repo root) ──────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

AGENDA_ROOM_TSX = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "AgendaRoom.tsx"
)


# ── Override root conftest cleanup (pure file-based test) ────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — este teste é puro file-inspection, sem DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────────


def read_source() -> str:
    """Lê o conteúdo de ``AgendaRoom.tsx`` como texto UTF-8.

    Garante que o arquivo existe antes de tentar ler. Usado por todos
    os métodos de teste da classe ``TestB4EventosHoje``.
    """
    assert AGENDA_ROOM_TSX.exists(), (
        f"Arquivo de produção não encontrado em {AGENDA_ROOM_TSX}. "
        "O teste B-4 pressupõe que AgendaRoom.tsx existe em "
        "apps/blu_v3/src/pages/app/."
    )
    return AGENDA_ROOM_TSX.read_text(encoding="utf-8")


# ── Tests ────────────────────────────────────────────────────────────────────


class TestB4EventosHoje:
    """RED tests para B-4 (BATCH #205) — Eventos da aba ``Hoje`` com ações.

    Cada ``test_acN_*`` valida uma AC e deve PASSAR (TRUE RED) enquanto
    a feature não tiver sido implementada. Após a entrega do GREEN, o
    padrão procurado pela regex será encontrado e o teste falhará com
    ``pytest.fail("FALSE RED — …")`` — sinalizando que o RED foi
    violado e o teste precisa ser atualizado/removido.
    """

    # ── AC#1 ────────────────────────────────────────────────────────────────

    def test_ac1_no_expanded_event_id_state(self) -> None:
        """AC#1 — ``AgendaRoom.tsx`` NÃO possui state ``expandedEventId``.

        GREEN esperado:
            ``const [expandedEventId, setExpandedEventId] = useState<string | null>(null)``
        (ou similar, em qualquer posição do bloco de states do componente,
        junto aos demais ``useState`` do arquivo — atualmente linha 50).

        Hoje (linha 50) o único ``useState`` é
        ``const [tab, setTab] = useState<Tab>('gantt')`` — sem
        ``expandedEventId``.
        """
        source = read_source()
        match = re.search(r"expandedEventId", source)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#1 violada: o identificador `expandedEventId` "
                f"JÁ aparece em AgendaRoom.tsx (match em offset {match.start()}). "
                "Esperava-se que o state `expandedEventId` ainda NÃO tivesse "
                "sido adicionado para que este teste RED passasse. A feature "
                "B-4 já foi entregue e este teste precisa ser revisado."
            )

    # ── AC#2 ────────────────────────────────────────────────────────────────

    def test_ac2_ev_row_no_onclick(self) -> None:
        """AC#2 — As linhas de evento (``.ev-row``) na aba ``Hoje`` NÃO
        possuem handler ``onClick``.

        GREEN esperado: o ``<div … className="ev-row">`` (atualmente linha
        180) precisa ganhar um ``onClick={() => toggleExpand(ev.id)}``
        (ou similar) para permitir expandir/colapsar o evento. O regex
        abaixo captura o padrão ``className="ev-row"`` seguido de
        ``onClick=`` dentro de 300 chars (cobre o atributo ``key``
        existente + o novo ``onClick``).

        Hoje o ``.ev-row`` (linha 180) é apenas
        ``<div key={ev.id} className="ev-row">`` — sem ``onClick``.
        """
        source = read_source()
        match = re.search(
            r"""className\s*=\s*["']ev-row["'][\s\S]{0,300}?onClick\s*=""",
            source,
        )
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#2 violada: o handler `onClick=` JÁ está "
                "presente na `.ev-row` da aba Hoje "
                f"(match em offset {match.start()}). "
                "Esperava-se que a linha de evento ainda não tivesse "
                "onClick para que este teste RED passasse. A feature "
                "B-4 já foi entregue."
            )

    # ── AC#3 ────────────────────────────────────────────────────────────────

    def test_ac3_no_confirmar_action_button(self) -> None:
        """AC#3 — NÃO há botão de ação ``Confirmar`` na aba ``Hoje``.

        GREEN esperado: dentro do bloco expandido do ``.ev-row`` (após o
        toggle implementado pela AC#2) deve aparecer um
        ``<button>Confirmar</button>`` (ou ``<button …>Confirmar</button>``
        com classe/ícones adicionais). O regex abaixo procura a string
        literal ``Confirmar`` em qualquer ponto do source.

        Hoje não há nenhuma ocorrência de ``Confirmar`` no arquivo
        (o único approve button existente, na aba ``Pendentes`` linha
        217, diz ``👍 Aprovar`` — não ``Confirmar``).
        """
        source = read_source()
        match = re.search(r"Confirmar", source, flags=re.IGNORECASE)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#3 violada: o texto `Confirmar` JÁ aparece "
                f"em AgendaRoom.tsx (match em offset {match.start()}). "
                "Esperava-se que a action button `Confirmar` ainda NÃO "
                "tivesse sido adicionada à aba Hoje para que este teste "
                "RED passasse. A feature B-4 já foi entregue."
            )

    # ── AC#4 ────────────────────────────────────────────────────────────────

    def test_ac4_no_remarcar_action_button(self) -> None:
        """AC#4 — NÃO há botão de ação ``Remarcar`` na aba ``Hoje``.

        GREEN esperado: dentro do bloco expandido do ``.ev-row`` (após o
        toggle implementado pela AC#2) deve aparecer um
        ``<button>Remarcar</button>`` (ou ``<button …>Remarcar</button>``
        com classe/ícones adicionais). O regex abaixo procura a string
        literal ``Remarcar`` em qualquer ponto do source.

        Hoje não há nenhuma ocorrência de ``Remarcar`` no arquivo
        (o único snooze button existente, na aba ``Pendentes`` linha
        218, diz ``⏰ Depois`` — não ``Remarcar``).
        """
        source = read_source()
        match = re.search(r"Remarcar", source, flags=re.IGNORECASE)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#4 violada: o texto `Remarcar` JÁ aparece "
                f"em AgendaRoom.tsx (match em offset {match.start()}). "
                "Esperava-se que a action button `Remarcar` ainda NÃO "
                "tivesse sido adicionada à aba Hoje para que este teste "
                "RED passasse. A feature B-4 já foi entregue."
            )

    # ── AC#5 ────────────────────────────────────────────────────────────────

    def test_ac5_adicionar_integracao_not_sticky(self) -> None:
        """AC#5 — O botão ``Adicionar Integração`` NÃO está sticky/fixed.

        GREEN esperado: o botão ``＋ Adicionar integração`` (atualmente
        linhas 352-358) deve ganhar posicionamento sticky ou fixed —
        tipicamente via ``style={{ position: 'sticky', bottom: 0, … }}``
        ou ``style={{ position: 'fixed', … }}``. O regex abaixo localiza
        o texto ``Adicionar integração`` e procura por
        ``position: 'sticky'`` ou ``position: 'fixed'`` em uma janela
        de 600 chars antes/depois (cobre a ``<div className="dr-sec">``
        envolvente e o ``<button …>`` interno).

        Hoje (linha 354) o botão tem apenas
        ``style={{ fontSize: 10 }}`` — sem ``position: sticky/fixed``.
        """
        source = read_source()
        # 1) Localizar a âncora: o texto do botão "Adicionar integração".
        anchor = re.search(r"Adicionar\s+integra[çc][ãa]o", source)
        if anchor is None:
            pytest.fail(
                "FALSE RED — AC#5 violada de forma inesperada: nem o "
                "próprio texto `Adicionar integração` foi encontrado em "
                "AgendaRoom.tsx. O teste pressupõe que o botão existe "
                "(linhas 352-358 do estado atual); se ele foi removido, "
                "esta AC precisa ser reescrita para o novo estado."
            )
            return
        # 2) Janela de 600 chars em torno da âncora (cobre a div + button).
        window_start = max(0, anchor.start() - 600)
        window_end = min(len(source), anchor.end() + 600)
        surrounding = source[window_start:window_end]
        sticky_or_fixed = re.search(
            r"position\s*:\s*['\"]?\s*(?:sticky|fixed)\s*['\"]?",
            surrounding,
        )
        if sticky_or_fixed is not None:
            pytest.fail(
                "FALSE RED — AC#5 violada: foi encontrado "
                f"`position: {'sticky' if 'sticky' in sticky_or_fixed.group(0) else 'fixed'}` "
                "próximo ao botão `Adicionar integração` "
                f"(match em offset {window_start + sticky_or_fixed.start()}). "
                "Esperava-se que o botão ainda NÃO tivesse posicionamento "
                "sticky/fixed para que este teste RED passasse. A feature "
                "B-4 já foi entregue."
            )
