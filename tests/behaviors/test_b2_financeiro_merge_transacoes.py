"""RED test for B-2 (BATCH #205) — Merge "Compromissos"+"Histórico" → "Transações".

GOAL:
    Confirmar que a ``FinanceiroRoom.tsx`` ainda NÃO foi atualizada para
    unificar as abas ``compromissos`` + ``historico`` em uma única aba
    ``transacoes``. Este é um teste source-inspection TRUE RED — cada AC
    deve passar enquanto o código de produção estiver em seu estado
    anterior (5 tabs separadas), sinalizando que a feature ainda não foi
    entregue.

BEHAVIOR:
    B-2 — ``apps/blu_v3/src/pages/app/FinanceiroRoom.tsx`` deve:
        1. Substituir ``'compromissos' | 'historico'`` no type Tab por
           ``'transacoes'``,
           resultando em ``type Tab = 'decisoes' | 'transacoes' | 'tarefas' | 'config'``
           (4 tabs, em vez de 5).
        2. Renomear a label da nova aba unificada para ``Transações``.
        3. Criar um novo bloco ``tc`` para ``transacoes`` que combina
           bills (antigo ``f-compromissos``) + transações bancárias
           (antigo ``f-historico``) no mesmo scroll, ordenados por data.
        4. Adicionar filtro de período via pills (hoje, 7d, 30d, tudo).

    Estado atual (BEFORE — confirmado por inspeção de
    ``apps/blu_v3/src/pages/app/FinanceiroRoom.tsx``):

        - Linha 24: ``type Tab = 'decisoes' | 'compromissos' | 'tarefas' | 'historico' | 'config'``
          → 5 tabs, com ``'compromissos'`` e ``'historico'`` separados.
        - Linha 263: array ``['decisoes', 'compromissos', 'tarefas', 'historico', 'config']``.
        - Linhas 265-268: ternário de labels com ``'Compromissos'`` e ``'Histórico'``.
        - Linha 313: ``<div className={\`tc\${tab === 'compromissos' ? ' on' : ''}\`} id="f-compromissos">``.
        - Linha 464: ``<div className={\`tc\${tab === 'historico' ? ' on' : ''}\`} id="f-historico">``.

AC (Acceptance Criteria):
    AC#1 — O type ``Tab`` inclui o literal ``'compromissos'`` (TRUE RED).
    AC#2 — O type ``Tab`` inclui o literal ``'historico'`` (TRUE RED).
    AC#3 — O type ``Tab`` NÃO inclui o literal ``'transacoes'`` (TRUE RED).
    AC#4 — A label ``Compromissos`` existe no ternário de labels das tabs.
    AC#5 — A label ``Histórico`` existe no ternário de labels das tabs.
    AC#6 — O painel ``#f-compromissos`` (id="f-compromissos") existe.
    AC#7 — O painel ``#f-historico`` (id="f-historico") existe.

DECISION:
    Estratégia: source-inspection (lê o ``.tsx`` como texto). O test runner
    não transpila nem executa TSX — apenas regex-match na string lida do
    disco. Cada AC é um método da classe ``TestB2FinanceiroMerge``:

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
    4. NÃO testar a implementação interna dos componentes das tabs
       (já existem e têm seu próprio coverage).
    5. NÃO falhar o teste por causa de imports ou whitespace — apenas
       pelos 7 padrões textuais definidos nas ACs.
    6. NÃO inverter a polaridade do teste: o teste deve passar AGORA
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

FINANCEIRO_ROOM_TSX = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "FinanceiroRoom.tsx"
)


# ── Override root conftest cleanup (pure file-based test) ────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — este teste é puro file-inspection, sem DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────────


def read_source() -> str:
    """Lê o conteúdo de ``FinanceiroRoom.tsx`` como texto UTF-8.

    Garante que o arquivo existe antes de tentar ler. Usado por todos
    os métodos de teste da classe ``TestB2FinanceiroMerge``.
    """
    assert FINANCEIRO_ROOM_TSX.exists(), (
        f"Arquivo de produção não encontrado em {FINANCEIRO_ROOM_TSX}. "
        "O teste B-2 pressupõe que FinanceiroRoom.tsx existe em "
        "apps/blu_v3/src/pages/app/."
    )
    return FINANCEIRO_ROOM_TSX.read_text(encoding="utf-8")


# ── Tests ────────────────────────────────────────────────────────────────────


class TestB2FinanceiroMerge:
    """RED tests para B-2 (BATCH #205) — Merge Compromissos+Histórico → Transações.

    Cada ``test_acN_*`` valida uma AC e deve PASSAR (TRUE RED) enquanto
    a feature não tiver sido implementada. Após a entrega do GREEN, o
    padrão procurado pela regex será encontrado e o teste falhará com
    ``pytest.fail("FALSE RED — …")`` — sinalizando que o RED foi
    violado e o teste precisa ser atualizado/removido.
    """

    # ── AC#1 ────────────────────────────────────────────────────────────────

    def test_ac1_type_tab_inclui_compromissos(self) -> None:
        """AC#1 — O type ``Tab`` inclui o literal ``'compromissos'``.

        GREEN esperado:
            O literal ``'compromissos'`` foi removido do type Tab
            (agora é ``'decisoes' | 'transacoes' | 'tarefas' | 'config'``).
            Portanto, se ``'compromissos'`` ainda estiver presente no
            source, o teste RED ainda é válido.

        Hoje (linha 24) o type é
        ``type Tab = 'decisoes' | 'compromissos' | 'tarefas' | 'historico' | 'config'``
        — ``'compromissos'`` está presente.
        """
        source = read_source()
        match = re.search(r"""['"]compromissos['"]""", source)
        if match is None:
            pytest.fail(
                "FALSE RED — AC#1 violada: o literal `'compromissos'` NÃO "
                f"está mais presente em FinanceiroRoom.tsx. "
                "Esperava-se que o type `Tab` ainda tivesse `'compromissos'` "
                "para que este teste RED passasse. A feature B-2 já foi "
                "entregue e este teste precisa ser revisado."
            )

    # ── AC#2 ────────────────────────────────────────────────────────────────

    def test_ac2_type_tab_inclui_historico(self) -> None:
        """AC#2 — O type ``Tab`` inclui o literal ``'historico'``.

        GREEN esperado:
            O literal ``'historico'`` foi removido do type Tab.
            Hoje (linha 24) o type é
            ``type Tab = 'decisoes' | 'compromissos' | 'tarefas' | 'historico' | 'config'``
            — ``'historico'`` está presente.
        """
        source = read_source()
        match = re.search(r"""['"]historico['"]""", source)
        if match is None:
            pytest.fail(
                "FALSE RED — AC#2 violada: o literal `'historico'` NÃO "
                f"está mais presente em FinanceiroRoom.tsx. "
                "Esperava-se que o type `Tab` ainda tivesse `'historico'` "
                "para que este teste RED passasse. A feature B-2 já foi "
                "entregue e este teste precisa ser revisado."
            )

    # ── AC#3 ────────────────────────────────────────────────────────────────

    def test_ac3_type_tab_nao_inclui_transacoes(self) -> None:
        """AC#3 — O type ``Tab`` NÃO inclui o literal ``'transacoes'``.

        GREEN esperado:
            O literal ``'transacoes'`` substitui ``'compromissos' | 'historico'``
            no type Tab (agora ``'decisoes' | 'transacoes' | 'tarefas' | 'config'``).

        Hoje (linha 24) não há ``'transacoes'`` no type Tab. Se
        ``'transacoes'`` for encontrado, significa que o GREEN já foi
        implementado.
        """
        source = read_source()
        match = re.search(r"""['"]transacoes['"]""", source)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#3 violada: o literal `'transacoes'` JÁ "
                f"aparece em FinanceiroRoom.tsx (match em offset {match.start()}). "
                "Esperava-se que a tab unificada ainda NÃO existisse para "
                "que este teste RED passasse. A feature B-2 já foi entregue "
                "e este teste precisa ser revisado."
            )

    # ── AC#4 ────────────────────────────────────────────────────────────────

    def test_ac4_label_compromissos_existe(self) -> None:
        """AC#4 — A label ``Compromissos`` existe no ternário de labels.

        GREEN esperado:
            A label ``Compromissos`` é substituída por ``Transações`` no
            ternário de labels das tabs (linhas 265-268). Hoje (linha 266)
            existe o branch ``'compromissos' ? <>Compromissos …</>``.
        """
        source = read_source()
        match = re.search(r"""Compromissos""", source)
        if match is None:
            pytest.fail(
                "FALSE RED — AC#4 violada: a label `Compromissos` NÃO "
                f"está mais presente em FinanceiroRoom.tsx. "
                "Esperava-se que o ternário de labels das tabs ainda "
                "tivesse a opção 'Compromissos' para que este teste RED "
                "passasse. A feature B-2 já foi entregue."
            )

    # ── AC#5 ────────────────────────────────────────────────────────────────

    def test_ac5_label_historico_existe(self) -> None:
        """AC#5 — A label ``Histórico`` existe no ternário de labels.

        GREEN esperado:
            A label ``Histórico`` é substituída por ``Transações`` no
            ternário de labels das tabs (linhas 265-268). Hoje (linha 267)
            existe o branch ``'historico' ? 'Histórico'``.
        """
        source = read_source()
        match = re.search(r"""Histórico""", source)
        if match is None:
            pytest.fail(
                "FALSE RED — AC#5 violada: a label `Histórico` NÃO "
                f"está mais presente em FinanceiroRoom.tsx. "
                "Esperava-se que o ternário de labels das tabs ainda "
                "tivesse a opção 'Histórico' para que este teste RED "
                "passasse. A feature B-2 já foi entregue."
            )

    # ── AC#6 ────────────────────────────────────────────────────────────────

    def test_ac6_painel_f_compromissos_existe(self) -> None:
        """AC#6 — O painel ``#f-compromissos`` existe.

        GREEN esperado:
            O bloco ``<div className={\`tc\${tab === 'compromissos' ? ' on' : ''}\`} id="f-compromissos">``
            (linha 313) é removido, substituído pelo novo bloco
            ``transacoes`` que unifica bills + transações.

        Hoje (linha 313) o painel ``#f-compromissos`` existe com a lógica
        de exibição de faturas de cartão (polpBills).
        """
        source = read_source()
        match = re.search(r'id="f-compromissos"', source)
        if match is None:
            pytest.fail(
                "FALSE RED — AC#6 violada: o painel `#f-compromissos` "
                f"NÃO está mais presente em FinanceiroRoom.tsx. "
                "Esperava-se que o painel de compromissos ainda existisse "
                "separadamente para que este teste RED passasse. "
                "A feature B-2 já foi entregue."
            )

    # ── AC#7 ────────────────────────────────────────────────────────────────

    def test_ac7_painel_f_historico_existe(self) -> None:
        """AC#7 — O painel ``#f-historico`` existe.

        GREEN esperado:
            O bloco ``<div className={\`tc\${tab === 'historico' ? ' on' : ''}\`} id="f-historico">``
            (linha 464) é removido, substituído pelo novo bloco
            ``transacoes`` que unifica bills + transações.

        Hoje (linha 464) o painel ``#f-historico`` existe com a lista
        de transações bancárias (polpTransactions).
        """
        source = read_source()
        match = re.search(r'id="f-historico"', source)
        if match is None:
            pytest.fail(
                "FALSE RED — AC#7 violada: o painel `#f-historico` "
                f"NÃO está mais presente em FinanceiroRoom.tsx. "
                "Esperava-se que o painel de histórico ainda existisse "
                "separadamente para que este teste RED passasse. "
                "A feature B-2 já foi entregue."
            )
