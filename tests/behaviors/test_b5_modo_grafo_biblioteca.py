"""GREEN test for B-5 (BATCH #208) — Design system auditado + modo grafo
na Biblioteca.

GOAL:
    Validar que a ``BibliotecaRoom.tsx`` EXPÕE o modo grafo — ou seja, o
    type ``ViewMode`` agora é ``'grid' | 'list' | 'graph'`` (inclui o
    literal ``'graph'``) e o toggle de visualização da toolbar tem os
    três botões (``grid`` + ``list`` + ``graph``), com o terceiro
    botão ``graph`` rotulado ``Grafo``. Este é um teste
    source-inspection GREEN — cada AC deve passar enquanto a feature
    estiver implementada e falhar (REGRESSED) se a feature for removida.

BEHAVIOR:
    B-5 (Modo Grafo) — ``apps/blu_v3/src/pages/app/BibliotecaRoom.tsx``
    deve:

        1. Estender o type ``ViewMode`` para incluir o literal ``'graph'``
           (union atual ``'grid' | 'list'`` → ``'grid' | 'list' | 'graph'``).
        2. Adicionar um terceiro botão no toggle de visualização da
           toolbar do painel ``Documentos`` com ``title="Grafo"``
           (ao lado dos já existentes ``title="Grade"`` e
           ``title="Lista"``).

    Estado atual (GREEN — confirmado por inspeção de
    ``apps/blu_v3/src/pages/app/BibliotecaRoom.tsx``):

        - Linha 13: ``type ViewMode = 'grid' | 'list' | 'graph'`` → inclui
          ``'graph'``.
        - Linhas ~559-564: toggle da toolbar do painel ``Documentos``
          contém três ``<button>`` com ``title="Grade"``, ``title="Lista"``
          e ``title="Grafo"``.

AC (Acceptance Criteria):
    AC#1 — O type ``ViewMode`` INCLUI o literal ``'graph'`` na union.
    AC#2 — O toggle de visualização da toolbar TEM um terceiro botão
           com ``title="Grafo"``.

DECISION:
    A GREEN anterior (commit f9b32fa4) entregou: ``type ViewMode`` com
    ``'graph'``, botão ``title="Grafo"`` no toggle, e o componente
    ``DocGraph`` (e ``GraphView``) renderizado condicionalmente quando
    ``viewMode === 'graph'``. Este teste foi escrito como FALSE RED
    tripwire e foi FLIPADO para GREEN neste commit, seguindo o mesmo
    pattern do c1fbd182 (post-merge cleanup de FALSE RED tests).

Test strategy:
    Source-inspection (lê o ``.tsx`` como texto). O test runner não
    transpila nem executa TSX — apenas regex-match na string lida do
    disco. Cada AC é um método da classe ``TestB5ModoGrafoBiblioteca``:

        - Lê o source uma vez por teste (helper ``read_source``).
        - Aplica uma regex específica da AC.
        - Se a regex NÃO ENCONTRAR o padrão esperado (estado GREEN
          regrediu), dispara ``pytest.fail("AC#N REGRESSED — …")`` com
          mensagem em pt-BR explicando por que o teste está FAILING.
        - Se a regex ENCONTRAR o padrão, o teste passa em silêncio
          (GREEN — a feature está em vigor).

Anti-Goals (must NOT be violated):
    1. NÃO exigir alterações no código de produção — o código JÁ
       implementa o modo grafo.
    2. NÃO transpilar nem executar TSX — source-inspection puro.
    3. NÃO usar mocks, Supabase, banco de dados ou rede.
    4. NÃO falhar o teste por causa de imports ou whitespace — apenas
       pelos 2 padrões textuais definidos nas ACs.
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
    """GREEN tests para B-5 (BATCH #208) — Modo Grafo na Biblioteca.

    Cada ``test_acN_*`` valida uma AC e deve PASSAR (GREEN) enquanto a
    feature estiver implementada. Se a feature for removida (regressed),
    o teste falhará com ``pytest.fail("AC#N REGRESSED — …")`` —
    sinalizando que alguém removeu parte do B-5 e o teste precisa ser
    revisado.

    Este arquivo foi FLIPADO de FALSE RED para GREEN seguindo o mesmo
    pattern do commit c1fbd182 (post-merge cleanup de inverted RED
    tests). A GREEN original está no commit f9b32fa4.
    """

    # ── AC#1 ────────────────────────────────────────────────────────────────

    def test_ac1_view_mode_inclui_graph(self) -> None:
        """AC#1 — O type ``ViewMode`` INCLUI o literal ``'graph'`` na union.

        GREEN esperado:
            ``type ViewMode = 'grid' | 'list' | 'graph'``
        (o literal ``'graph'`` deve aparecer em algum lugar do source,
        dentro da union do type ``ViewMode`` na linha 13).
        """
        source = read_source()
        match = re.search(r"""['"]graph['"]""", source)
        assert match is not None, (
            "AC#1 REGRESSED: o literal `'graph'` NÃO aparece em "
            "BibliotecaRoom.tsx. "
            "Esperado: `type ViewMode = 'grid' | 'list' | 'graph'` "
            "na linha 13 (com o literal `'graph'` na union). "
            "O Coder removeu o modo grafo da union do type ViewMode — "
            "REVERTER imediatamente."
        )

    # ── AC#2 ────────────────────────────────────────────────────────────────

    def test_ac2_toggle_tem_grafo(self) -> None:
        """AC#2 — O toggle de visualização TEM botão ``title="Grafo"``.

        GREEN esperado: o toggle da toolbar do painel ``Documentos``
        tem um terceiro ``<button title="Grafo" …>`` ao lado dos já
        existentes ``title="Grade"`` e ``title="Lista"``, para que o
        usuário possa alternar entre os três modos de visualização.
        """
        source = read_source()
        # Aceita aspas duplas ou simples no atributo title.
        match = re.search(
            r"""title\s*=\s*["']Grafo["']""",
            source,
        )
        assert match is not None, (
            "AC#2 REGRESSED: o toggle de visualização NÃO tem botão "
            "`title=\"Grafo\"` em BibliotecaRoom.tsx. "
            "Esperado: `<button title=\"Grafo\" ... "
            "onClick={() => setViewMode('graph')}>...</button>` "
            "ao lado dos já existentes `title=\"Grade\"` e "
            "`title=\"Lista\"` no painel Documentos. "
            "O Coder removeu o terceiro botão (modo grafo) — REVERTER "
            "imediatamente."
        )
