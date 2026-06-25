"""RED test for B-4 (BATCH #208) — Aba Conhecimento + Config consolidado.

GOAL:
    Confirmar que a ``EstrategiaRoom.tsx`` ainda NÃO foi atualizada para
    integrar a antiga ``BibliotecaRoom`` como aba ``Conhecimento`` e nem
    para consolidar o bloco de Config com as rotinas de documentos
    (``domain="documentos"``). Este é um teste source-inspection TRUE RED
    — cada AC deve passar enquanto o código de produção estiver em seu
    estado anterior, sinalizando que a feature ainda não foi entregue.

BEHAVIOR:
    B-4 — ``apps/blu_v3/src/pages/app/EstrategiaRoom.tsx`` deve:

        1. Importar o componente ``BibliotecaRoom`` do mesmo diretório
           (``import BibliotecaRoom from './BibliotecaRoom'``).
        2. Estender o type ``Tab`` para incluir o literal
           ``'conhecimento'``.
        3. Renderizar uma nova aba rotulada ``Conhecimento`` na lista de
           tabs do componente (alinhada com ``decisoes``, ``analises``,
           ``historico``, ``config``).
        4. Renderizar ``<BibliotecaRoom />`` dentro do painel da aba
           ``Conhecimento``.
        5. Consolidar o bloco ``Config`` adicionando um
           ``<RoutineConfigSection domain="documentos" />`` ao lado do já
           existente ``<RoutineConfigSection domain="estrategia" />``.

    Estado atual (BEFORE — confirmado por inspeção de
    ``apps/blu_v3/src/pages/app/EstrategiaRoom.tsx``):

        - Linha 21: ``import RoutineConfigSection from '../../components/shared/RoutineConfigSection'``
          → NÃO há ``import BibliotecaRoom``.
        - Linha 27: ``type Tab = 'decisoes' | 'analises' | 'historico' | 'config'``
          → NÃO inclui ``'conhecimento'``.
        - Linha 242: array de tabs = ``['decisoes', 'analises', 'historico', 'config']``
          → NÃO há label ``Conhecimento`` no ternário que rotula as tabs.
        - Linhas 248-261: ternário que mapeia cada tab para o seu label
          (Decisões, Análises, Histórico, Config) → NÃO há
          ``<BibliotecaRoom />`` em nenhum branch.
        - Linha 340: ``<RoutineConfigSection domain="estrategia" />``
          → NÃO há ``<RoutineConfigSection domain="documentos" />``.

AC (Acceptance Criteria):
    AC#1 — EstrategiaRoom.tsx importa ``BibliotecaRoom``.
    AC#2 — O type ``Tab`` inclui o literal ``'conhecimento'``.
    AC#3 — A lista de tabs renderizadas inclui o label ``Conhecimento``.
    AC#4 — O painel da aba conhecimento renderiza ``<BibliotecaRoom />``.
    AC#5 — A aba Config inclui ``<RoutineConfigSection domain="documentos" />``.

DECISION:
    Estratégia: extend — editar
    ``apps/blu_v3/src/pages/app/EstrategiaRoom.tsx`` in-place.
    Nenhum arquivo novo deve ser criado (o ``BibliotecaRoom.tsx`` já
    existe e é re-aproveitado). A consolidação do Config preserva o
    bloco existente ``domain="estrategia"`` e adiciona um segundo
    ``RoutineConfigSection`` com ``domain="documentos"``.

Test strategy:
    Source-inspection (lê o ``.tsx`` como texto). O test runner não
    transpila nem executa TSX — apenas regex-match na string lida do
    disco. Cada AC é um método da classe ``TestB4ConhecimentoConfig``:

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
    4. NÃO testar a implementação interna de ``BibliotecaRoom`` (já
       existe e tem seu próprio coverage).
    5. NÃO falhar o teste por causa de imports ou whitespace — apenas
       pelos 5 padrões textuais definidos nas ACs.
    6. NÃO inverter a polaridade do teste: o test deve passar AGORA
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

ESTRATEGIA_ROOM_TSX = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "EstrategiaRoom.tsx"
)


# ── Override root conftest cleanup (pure file-based test) ────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — este teste é puro file-inspection, sem DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────────


def read_source() -> str:
    """Lê o conteúdo de ``EstrategiaRoom.tsx`` como texto UTF-8.

    Garante que o arquivo existe antes de tentar ler. Usado por todos
    os métodos de teste da classe ``TestB4ConhecimentoConfig``.
    """
    assert ESTRATEGIA_ROOM_TSX.exists(), (
        f"Arquivo de produção não encontrado em {ESTRATEGIA_ROOM_TSX}. "
        "O teste B-4 pressupõe que EstrategiaRoom.tsx existe em "
        "apps/blu_v3/src/pages/app/."
    )
    return ESTRATEGIA_ROOM_TSX.read_text(encoding="utf-8")


# ── Tests ────────────────────────────────────────────────────────────────────


class TestB4ConhecimentoConfig:
    """RED tests para B-4 (BATCH #208) — Aba Conhecimento + Config consolidado.

    Cada ``test_acN_*`` valida uma AC e deve PASSAR (TRUE RED) enquanto
    a feature não tiver sido implementada. Após a entrega do GREEN, o
    padrão procurado pela regex será encontrado e o teste falhará com
    ``pytest.fail("FALSE RED — …")`` — sinalizando que o RED foi
    violado e o teste precisa ser atualizado/removido.
    """

    # ── AC#1 ────────────────────────────────────────────────────────────────

    def test_ac1_import_biblioteca_room(self) -> None:
        """AC#1 — ``EstrategiaRoom.tsx`` importa ``BibliotecaRoom``.

        GREEN esperado:
            ``import BibliotecaRoom from './BibliotecaRoom'``
        (declarado em qualquer posição do bloco de imports no topo do
        arquivo). Hoje a AC#1 está RED porque o único import de
        ``BibliotecaRoom`` está em ``DocumentosRoom.tsx`` (linha 25), não
        em ``EstrategiaRoom.tsx``.
        """
        source = read_source()
        match = re.search(
            r"""import\s+BibliotecaRoom\s+from\s+['"]\./BibliotecaRoom['"]""",
            source,
        )
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#1 violada: o import "
                "`import BibliotecaRoom from './BibliotecaRoom'` JÁ existe "
                f"em EstrategiaRoom.tsx (match em offset {match.start()}). "
                "A feature B-4 já foi entregue e este teste RED precisa ser "
                "removido/atualizado para a nova realidade GREEN."
            )

    # ── AC#2 ────────────────────────────────────────────────────────────────

    def test_ac2_type_tab_conhecimento(self) -> None:
        """AC#2 — O type ``Tab`` inclui o literal ``'conhecimento'``.

        GREEN esperado:
            ``type Tab = 'decisoes' | 'analises' | 'historico' | 'conhecimento' | 'config'``
        (em qualquer ordem dos membros da union, desde que
        ``'conhecimento'`` esteja presente).

        Hoje (linha 27) o type é
        ``type Tab = 'decisoes' | 'analises' | 'historico' | 'config'`` —
        sem ``'conhecimento'``.
        """
        source = read_source()
        match = re.search(r"""['"]conhecimento['"]""", source)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#2 violada: o literal `'conhecimento'` JÁ "
                f"aparece em EstrategiaRoom.tsx (match em offset {match.start()}). "
                "Esperava-se que o type `Tab` ainda NÃO o tivesse para que "
                "este teste RED passasse. A feature B-4 já foi entregue e "
                "este teste precisa ser revisado."
            )

    # ── AC#3 ────────────────────────────────────────────────────────────────

    def test_ac3_tab_label_conhecimento(self) -> None:
        """AC#3 — A lista de tabs renderizadas inclui o label ``Conhecimento``.

        GREEN esperado: o ternário/labels das tabs (atualmente linhas
        248-261) precisa ter um branch que renderize a string literal
        ``'Conhecimento'`` para a nova tab. Pode ser via ternário
        ``t === 'conhecimento' ? 'Conhecimento' : …`` ou via map de
        labels — desde que a string apareça no source.

        Hoje o ternário só tem branches para ``decisoes``,
        ``analises``, ``historico`` e o ``else`` (``Config``).
        """
        source = read_source()
        match = re.search(r"""['"]Conhecimento['"]""", source)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#3 violada: o label `'Conhecimento'` JÁ "
                f"aparece em EstrategiaRoom.tsx (match em offset {match.start()}). "
                "Esperava-se que o ternário de labels das tabs ainda não "
                "tivesse a opção 'Conhecimento' para que este teste RED "
                "passasse. A feature B-4 já foi entregue."
            )

    # ── AC#4 ────────────────────────────────────────────────────────────────

    def test_ac4_render_biblioteca_room(self) -> None:
        """AC#4 — O painel da aba conhecimento renderiza ``<BibliotecaRoom />``.

        GREEN esperado: o componente ``<BibliotecaRoom />`` (ou
        ``<BibliotecaRoom>`` com filhos) deve aparecer em algum lugar do
        JSX de ``EstrategiaRoom`` — tipicamente dentro de um
        ``<div className={`tc${tab === 'conhecimento' ? ' on' : ''}`}>``
        (mesmo padrão das outras tabs).

        Hoje não há nenhuma referência a ``<BibliotecaRoom`` no source.
        """
        source = read_source()
        match = re.search(r"""<BibliotecaRoom\b""", source)
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#4 violada: o JSX `<BibliotecaRoom` JÁ é "
                f"renderizado em EstrategiaRoom.tsx (match em offset {match.start()}). "
                "Esperava-se que a aba Conhecimento ainda não tivesse sido "
                "implementada para que este teste RED passasse. A feature "
                "B-4 já foi entregue."
            )

    # ── AC#5 ────────────────────────────────────────────────────────────────

    def test_ac5_config_tab_domain_documentos(self) -> None:
        """AC#5 — A aba Config inclui ``<RoutineConfigSection domain="documentos" />``.

        GREEN esperado: além do já existente
        ``<RoutineConfigSection domain="estrategia" />`` (linha 340),
        o componente deve renderizar um segundo ``RoutineConfigSection``
        com ``domain="documentos"`` (ou ``domain='documentos'``) para
        consolidar as rotinas de documentos na Config da EstrategiaRoom.

        Hoje só existe ``<RoutineConfigSection domain="estrategia" />``.
        """
        source = read_source()
        # Aceita aspas duplas ou simples no atributo domain.
        match = re.search(
            r"""RoutineConfigSection\s+domain\s*=\s*["']documentos["']""",
            source,
        )
        if match is not None:
            pytest.fail(
                "FALSE RED — AC#5 violada: o JSX "
                "`<RoutineConfigSection domain=\"documentos\" />` JÁ é "
                f"renderizado em EstrategiaRoom.tsx (match em offset {match.start()}). "
                "Esperava-se que a Config ainda NÃO estivesse consolidada "
                "com as rotinas de documentos para que este teste RED "
                "passasse. A feature B-4 já foi entregue."
            )
