"""RED test for B-5 (BATCH #209) — Design System auditado.

GOAL:
    Confirmar que as salas ``FinanceiroRoom``, ``ComprasRoom``,
    ``ClientesRoom`` e ``AgendaRoom`` ainda NÃO estão padronizadas com
    os tokens CSS do design system (``var(--r)``, ``var(--gb)``, etc.)
    usados como referência em ``BusinessMemoryPage.tsx``. Este é um
    teste source-inspection TRUE RED — cada AC deve passar enquanto o
    código de produção estiver em seu estado anterior, sinalizando
    que a feature ainda não foi entregue.

BEHAVIOR:
    B-5 — as quatro salas de produto devem consumir os tokens CSS do
    design system (``var(--r)``, ``var(--gb)``, ``var(--glass)`` etc.)
    que já são usados em ``BusinessMemoryPage.tsx`` e em outros
    componentes (e.g. ``BibliotecaRoom.tsx``, ``AdminScreen.tsx``,
    ``AgentesScreen.tsx``). O critério mínimo para considerar a sala
    "tokenizada" é o uso consistente de ``var(--r)`` em **pelo menos
    3 lugares** do arquivo.

    Estado atual (BEFORE — confirmado por inspeção de source):

        - ``apps/blu_v3/src/pages/app/FinanceiroRoom.tsx`` → 0 matches de
          ``var(--r)``.
        - ``apps/blu_v3/src/pages/app/ComprasRoom.tsx`` → 0 matches de
          ``var(--r)``.
        - ``apps/blu_v3/src/pages/app/ClientesRoom.tsx`` → 0 matches de
          ``var(--r)``.
        - ``apps/blu_v3/src/pages/app/AgendaRoom.tsx`` → 0 matches de
          ``var(--r)``.

    Referência GREEN (já entregue em outros componentes):

        - ``apps/blu_v3/src/pages/app/BibliotecaRoom.tsx`` → 4 matches
          de ``var(--r)`` (linhas 84, 203, 410, 431).
        - ``apps/blu_v3/src/pages/app/AgentesScreen.tsx`` → 4 matches
          de ``var(--r)`` (linhas 142, 156, 168, 332).
        - ``apps/blu_v3/src/pages/app/AdminScreen.tsx`` → 2 matches de
          ``var(--r)`` (linhas 734, 981).

AC (Acceptance Criteria):
    AC#1 — ``FinanceiroRoom.tsx`` usa ``var(--r)`` em pelo menos 3
           lugares.
    AC#2 — ``ComprasRoom.tsx`` usa ``var(--r)`` em pelo menos 3
           lugares.
    AC#3 — ``ClientesRoom.tsx`` usa ``var(--r)`` em pelo menos 3
           lugares.
    AC#4 — ``AgendaRoom.tsx`` usa ``var(--r)`` em pelo menos 3
           lugares.

DECISION:
    Estratégia: source-inspection (lê o ``.tsx`` como texto). O test
    runner não transpila nem executa TSX — apenas conta matches de
    ``var(--r)`` no source lido do disco. Cada AC é um método da
    classe ``TestB5DesignSystemTokens``:

        - Lê o source uma vez por teste (helper ``read_source_xxx``
          específico para cada sala).
        - Conta quantas vezes o literal ``var(--r)`` aparece no source.
        - Se a contagem for ``>= 3``, dispara
          ``pytest.fail("FALSE RED — …")`` com mensagem em pt-BR
          explicando que o teste está FAILING porque a feature já foi
          implementada e o RED é inválido.
        - Se a contagem for ``< 3``, o teste passa em silêncio (TRUE
          RED — a feature ainda não foi entregue).

    Nenhum arquivo de produção deve ser modificado — apenas escrever
    o teste.

Test strategy:
    Source-inspection puro. Para cada sala, o método de teste:

        1. Lê o arquivo ``.tsx`` como string UTF-8.
        2. Conta matches de ``var(--r)`` via ``re.findall``.
        3. Compara o contador com o limiar ``MIN_VAR_R = 3``.
        4. Reporta PASS (TRUE RED) ou FAIL (FALSE RED) via
           ``pytest.fail``.

Anti-Goals (must NOT be violated):
    1. NÃO modificar o código de produção — apenas escrever o teste.
    2. NÃO transpilar nem executar TSX — source-inspection puro.
    3. NÃO usar mocks, Supabase, banco de dados ou rede.
    4. NÃO testar a implementação interna do design system — apenas
       a presença textual de ``var(--r)`` no source.
    5. NÃO falhar o teste por causa de imports ou whitespace — apenas
       pela contagem de matches de ``var(--r)``.
    6. NÃO inverter a polaridade do teste: o test deve passar AGORA
       (RED = feature ausente, 0 matches) e falhar depois que a
       feature for entregue (GREEN = 3+ matches). A inversão de
       polaridade é uma armadilha clássica em testes de
       source-inspection.
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

COMPRAS_ROOM_TSX = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "ComprasRoom.tsx"
)

CLIENTES_ROOM_TSX = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "ClientesRoom.tsx"
)

AGENDA_ROOM_TSX = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "AgendaRoom.tsx"
)


# ── Limiares ─────────────────────────────────────────────────────────────────

# Cada sala deve consumir ``var(--r)`` em pelo menos 3 lugares
# (mesmo critério usado em ``BibliotecaRoom.tsx``: 4 matches,
# ``AgentesScreen.tsx``: 4 matches). Este é o mínimo para garantir
# consistência visual com a referência ``BusinessMemoryPage.tsx``.
MIN_VAR_R = 3


# ── Override root conftest cleanup (pure file-based test) ────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — este teste é puro file-inspection, sem DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────────


def _read_source(path: Path) -> str:
    """Lê o conteúdo de um ``.tsx`` como texto UTF-8.

    Garante que o arquivo existe antes de tentar ler. Usado por todos
    os métodos de teste da classe ``TestB5DesignSystemTokens`` —
    cada um aponta para um arquivo diferente.
    """
    assert path.exists(), (
        f"Arquivo de produção não encontrado em {path}. "
        "O teste B-5 pressupõe que as salas "
        "FinanceiroRoom/ComprasRoom/ClientesRoom/AgendaRoom existem "
        "em apps/blu_v3/src/pages/app/."
    )
    return path.read_text(encoding="utf-8")


def _count_var_r(source: str) -> int:
    """Conta quantas vezes o literal ``var(--r)`` aparece no source.

    Considera tanto a forma ``'var(--r)'`` (string em JSX inline) quanto
    ``var(--r)`` em qualquer outro contexto textual. A regex é case-
    sensitive e tolerante a whitespace ao redor.
    """
    return len(re.findall(r"var\(--r\)", source))


# ── Tests ────────────────────────────────────────────────────────────────────


class TestB5DesignSystemTokens:
    """RED tests para B-5 (BATCH #209) — Design System auditado.

    Cada ``test_acN_*`` valida uma AC e deve PASSAR (TRUE RED) enquanto
    a sala correspondente ainda não tiver sido tokenizada com
    ``var(--r)`` em pelo menos ``MIN_VAR_R = 3`` lugares. Após a
    entrega do GREEN, o contador atingirá o limiar e o teste falhará
    com ``pytest.fail("FALSE RED — …")`` — sinalizando que o RED foi
    violado e o teste precisa ser atualizado/removido.
    """

    # ── AC#1 ────────────────────────────────────────────────────────────────

    def test_ac1_financeiro_room_var_r(self) -> None:
        """AC#1 — ``FinanceiroRoom.tsx`` usa ``var(--r)`` em >= 3 lugares.

        GREEN esperado: a sala ``FinanceiroRoom`` precisa consumir o
        token ``var(--r)`` em pelo menos 3 lugares do source (cards,
        listas, headers etc.), seguindo o padrão de
        ``BibliotecaRoom.tsx`` (4 matches) e ``AgentesScreen.tsx``
        (4 matches).

        Hoje a sala tem 0 matches de ``var(--r)`` — bordas e
        ``borderRadius`` provavelmente estão hard-coded em pixels ou
        usam outros tokens ad-hoc.
        """
        source = _read_source(FINANCEIRO_ROOM_TSX)
        count = _count_var_r(source)
        if count >= MIN_VAR_R:
            pytest.fail(
                f"FALSE RED — AC#1 violada: `var(--r)` JÁ aparece "
                f"{count} vezes em FinanceiroRoom.tsx (>= {MIN_VAR_R}). "
                "A sala FinanceiroRoom já foi tokenizada com o design "
                "system e este teste RED precisa ser removido/atualizado "
                "para a nova realidade GREEN."
            )

    # ── AC#2 ────────────────────────────────────────────────────────────────

    def test_ac2_compras_room_var_r(self) -> None:
        """AC#2 — ``ComprasRoom.tsx`` usa ``var(--r)`` em >= 3 lugares.

        GREEN esperado: a sala ``ComprasRoom`` precisa consumir o
        token ``var(--r)`` em pelo menos 3 lugares do source (cards
        de pedido, badges de fornecedor, painel de cotação etc.),
        seguindo o padrão de ``BibliotecaRoom.tsx`` (4 matches) e
        ``AgentesScreen.tsx`` (4 matches).

        Hoje a sala tem 0 matches de ``var(--r)``.
        """
        source = _read_source(COMPRAS_ROOM_TSX)
        count = _count_var_r(source)
        if count >= MIN_VAR_R:
            pytest.fail(
                f"FALSE RED — AC#2 violada: `var(--r)` JÁ aparece "
                f"{count} vezes em ComprasRoom.tsx (>= {MIN_VAR_R}). "
                "A sala ComprasRoom já foi tokenizada com o design "
                "system e este teste RED precisa ser removido/atualizado "
                "para a nova realidade GREEN."
            )

    # ── AC#3 ────────────────────────────────────────────────────────────────

    def test_ac3_clientes_room_var_r(self) -> None:
        """AC#3 — ``ClientesRoom.tsx`` usa ``var(--r)`` em >= 3 lugares.

        GREEN esperado: a sala ``ClientesRoom`` precisa consumir o
        token ``var(--r)`` em pelo menos 3 lugares do source (cards
        de cliente, chips de tag, painel de histórico etc.),
        seguindo o padrão de ``BibliotecaRoom.tsx`` (4 matches) e
        ``AgentesScreen.tsx`` (4 matches).

        Hoje a sala tem 0 matches de ``var(--r)``.
        """
        source = _read_source(CLIENTES_ROOM_TSX)
        count = _count_var_r(source)
        if count >= MIN_VAR_R:
            pytest.fail(
                f"FALSE RED — AC#3 violada: `var(--r)` JÁ aparece "
                f"{count} vezes em ClientesRoom.tsx (>= {MIN_VAR_R}). "
                "A sala ClientesRoom já foi tokenizada com o design "
                "system e este teste RED precisa ser removido/atualizado "
                "para a nova realidade GREEN."
            )

    # ── AC#4 ────────────────────────────────────────────────────────────────

    def test_ac4_agenda_room_var_r(self) -> None:
        """AC#4 — ``AgendaRoom.tsx`` usa ``var(--r)`` em >= 3 lugares.

        GREEN esperado: a sala ``AgendaRoom`` precisa consumir o
        token ``var(--r)`` em pelo menos 3 lugares do source (cards
        de compromisso, badges de status, painel de dia/semana
        etc.), seguindo o padrão de ``BibliotecaRoom.tsx``
        (4 matches) e ``AgentesScreen.tsx`` (4 matches).

        Hoje a sala tem 0 matches de ``var(--r)``.
        """
        source = _read_source(AGENDA_ROOM_TSX)
        count = _count_var_r(source)
        if count >= MIN_VAR_R:
            pytest.fail(
                f"FALSE RED — AC#4 violada: `var(--r)` JÁ aparece "
                f"{count} vezes em AgendaRoom.tsx (>= {MIN_VAR_R}). "
                "A sala AgendaRoom já foi tokenizada com o design "
                "system e este teste RED precisa ser removido/atualizado "
                "para a nova realidade GREEN."
            )
