"""RED test for B-5 (BATCH #208) — Design system auditado + modo grafo
na Biblioteca.

GOAL:
    Confirmar que a ``BibliotecaRoom.tsx`` ainda NÃO implementa o modo
    grafo — ou seja, o type ``ViewMode`` continua sendo ``'grid' | 'list'``
    (sem o literal ``'graph'``) e o toggle de visualização da toolbar
    continua com apenas dois botões (``grid`` + ``list``), sem o terceiro
    botão ``graph`` rotulado ``Grafo``. Este é um teste
    source-inspection TRUE RED — cada AC deve passar enquanto a feature
    não tiver sido entregue, sinalizando que o B-5 ainda não foi
    implementado.

BEHAVIOR:
    B-5 (Modo Grafo) — ``apps/blu_v3/src/pages/app/BibliotecaRoom.tsx``
    deve:

        1. Estender o type ``ViewMode`` para incluir o literal ``'graph'``
           (union atual ``'grid' | 'list'`` → ``'grid' | 'list' | 'graph'``).
        2. Adicionar um terceiro botão no toggle de visualização da
           toolbar do painel ``Documentos`` com ``title="Grafo"``
           (atualmente só existem os botões ``title="Grade"`` e
           ``title="Lista"``).

    Estado atual (BEFORE — confirmado por inspeção de
    ``apps/blu_v3/src/pages/app/BibliotecaRoom.tsx``):

        - Linha 9: ``type ViewMode = 'grid' | 'list'`` → NÃO inclui
          ``'graph'``.
        - Linhas 344-355: toggle da toolbar do painel ``Documentos``
          contém apenas dois ``<button>`` com ``title="Grade"`` e
          ``title="Lista"`` → NÃO há terceiro botão ``title="Grafo"``.

AC (Acceptance Criteria):
    AC#1 — O type ``ViewMode`` NÃO inclui o literal ``'graph'`` na
           union (o source ainda não referencia o modo grafo em lugar
           nenhum).
    AC#2 — O toggle de visualização da toolbar NÃO tem um terceiro
           botão com ``title="Grafo"``.

DECISION:
    Estratégia: editar
    ``apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`` in-place,
    estendendo o type ``ViewMode`` para incluir ``'graph'`` e
    adicionando o terceiro botão ao toggle de visualização. A
    renderização condicional do modo grafo em si (canvas, nós, arestas)
    pode ser entregue em um GREEN subsequente — o teste B-5 cobre
    apenas o gate mínimo: type extendido + botão presente.

Test strategy:
    Source-inspection (lê o ``.tsx`` como texto). O test runner não
    transpila nem executa TSX — apenas regex-match na string lida do
    disco. Cada AC é um método da classe ``TestB5ModoGrafoBiblioteca``:

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
       pelos 2 padrões textuais definidos nas ACs.
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

BIBLIOTECA_ROOM_TSX = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "BibliotecaRoom.tsx"
)


# ── Override root conftest cleanup (pure file-based test) ────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — este teste é puro file-inspection, sem DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────────


def read_source() -> str:
    """Lê o conteúdo de ``BibliotecaRoom.tsx`` como texto UTF-8.

    Garante que o arquivo existe antes de tentar ler. Usado por todos
    os métodos de teste da classe ``TestB5ModoGrafoBiblioteca``.
    """
    assert BIBLIOTECA_ROOM_TSX.exists(), (
        f"Arquivo de produção não encontrado em {BIBLIOTECA_ROOM_TSX}. "
        "O teste B-5 pressupõe que BibliotecaRoom.tsx existe em "
        "apps/blu_v3/src/pages/app/."
    )
    return BIBLIOTECA_ROOM_TSX.read_text(encoding="utf-8")


# ── Tests ────────────────────────────────────────────────────────────────────


class TestB5ModoGrafoBiblioteca:
    """RED tests para B-5 (BATCH #208) — Modo Grafo na Biblioteca.

    Cada ``test_acN_*`` valida uma AC e deve PASSAR (TRUE RED) enquanto
    a feature não tiver sido implementada. Após a entrega do GREEN, o
    padrão procurado pela regex será encontrado e o teste falhará com
    ``pytest.fail("FALSE RED — …")`` — sinalizando que o RED foi
    violado e o teste precisa ser atualizado/removido.
    """

    # ── AC#1 ────────────────────────────────────────────────────────────────

    def test_ac1_view_mode_nao_inclui_graph(self) -> None:
        """AC#1 — O type ``ViewMode`` NÃO inclui o literal ``'graph'``.

        GREEN esperado:
            ``type ViewMode = 'grid' | 'list' | 'graph'``
        (o literal ``'graph'`` deve aparecer em algum lugar do source,
        tipicamente dentro da union do type ``ViewMode`` na linha 9).

        Hoje (linha 9) o type é
        ``type ViewMode = 'grid' | 'list'`` — sem ``'graph'``. Não há
        nenhuma outra referência ao literal ``'graph'`` em
        ``BibliotecaRoom.tsx``.
        """
        source = read_source()
        match = re.search(r"""['"]graph['"]""", source)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#1 violada: o literal `'graph'` JÁ aparece "
                f"em BibliotecaRoom.tsx (match em offset {match.start()}). "
                "Esperava-se que o type `ViewMode` ainda NÃO incluísse "
                "`'graph'` na union para que este teste RED passasse. "
                "A feature B-5 já foi entregue e este teste precisa ser "
                "removido/atualizado para a nova realidade GREEN."
            )

    # ── AC#2 ────────────────────────────────────────────────────────────────

    def test_ac2_toggle_nao_tem_grafo(self) -> None:
        """AC#2 — O toggle de visualização NÃO tem botão ``title="Grafo"``.

        GREEN esperado: o toggle da toolbar do painel ``Documentos``
        (atualmente linhas 344-355) deve ganhar um terceiro
        ``<button title="Grafo" …>`` ao lado dos já existentes
        ``title="Grade"`` e ``title="Lista"``, para que o usuário
        possa alternar entre os três modos de visualização.

        Hoje só existem os botões com ``title="Grade"`` e
        ``title="Lista"``.
        """
        source = read_source()
        # Aceita aspas duplas ou simples no atributo title.
        match = re.search(
            r"""title\s*=\s*["']Grafo["']""",
            source,
        )
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#2 violada: o botão `title=\"Grafo\"` JÁ "
                f"existe no toggle de visualização de BibliotecaRoom.tsx "
                f"(match em offset {match.start()}). Esperava-se que o "
                "toggle ainda NÃO tivesse o terceiro botão 'Grafo' para "
                "que este teste RED passasse. A feature B-5 já foi "
                "entregue."
            )
