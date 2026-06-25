"""RED test para B-3 (BATCH #205) — Botão Open Finance no quadro Contas.

GOAL:
    Confirmar que a ``FinanceiroRoom.tsx`` ainda NÃO foi atualizada para
    substituir o botão de ação do CollapsiblePanel "Contas" por um modal
    de integração bancária. Este é um teste source-inspection TRUE RED —
    cada AC deve passar enquanto o código de produção estiver em seu
    estado anterior (botão abre chat via ``openChatWith``), sinalizando
    que a feature ainda não foi entregue.

BEHAVIOR:
    B-3 — ``apps/blu_v3/src/pages/app/FinanceiroRoom.tsx`` deve:
        1. Substituir ``onClick={() => openChatWith('...')}`` no botão
           do CollapsiblePanel "Contas" por ``onClick={() => setShowConnectModal(true)}``.
        2. Adicionar estado ``const [showConnectModal, setShowConnectModal] = useState(false)``.
        3. Importar e renderizar ``IntegrationModal`` com opções de
           integração bancária (Open Finance via Polp, conexão manual).
        4. Garantir que o botão "Adicionar Conta" / "Conectar Banco"
           esteja visível SEMPRE no header do quadro Contas.

    Estado atual (BEFORE — confirmado por inspeção de
    ``apps/blu_v3/src/pages/app/FinanceiroRoom.tsx``):

        - Linha 126: ``const { go, toggleDc, expandedId, addToast, openChatWith } = useAppStore()``
        - Linha 708: Botão ``<button className="ph-add" onClick={() => openChatWith('Quero adicionar uma nova conta bancária')}>＋</button>``
          dentro do ``<CollapsiblePanel id="fin-contas" icon="🏦" title="Contas">``.
        - NÃO há referência a ``showConnectModal``, ``setShowConnectModal``
          ou ``IntegrationModal`` em lugar nenhum do arquivo.

AC (Acceptance Criteria):
    AC#1 — O onClick do Contas chama ``openChatWith`` (TRUE RED).
    AC#2 — ``showConnectModal`` / ``setShowConnectModal`` NÃO estão declarados (TRUE RED).
    AC#3 — ``IntegrationModal`` NÃO está importado (TRUE RED).
    AC#4 — ``<IntegrationModal>`` NÃO está renderizado (TRUE RED).
    AC#5 — O CollapsiblePanel ``id="fin-contas"`` existe (TRUE RED).

DECISION:
    Estratégia: source-inspection (lê o ``.tsx`` como texto). O test runner
    não transpila nem executa TSX — apenas regex-match na string lida do
    disco. Cada AC é um método da classe ``TestB3BotaoOpenFinance``:

        - Lê o source uma vez por teste (helper ``read_source``).
        - Aplica uma regex específica da AC.
        - Se a regex ENCONTRAR o padrão esperado no estado RED,
          o teste passa em silêncio (TRUE RED — a feature ainda não
          foi entregue).
        - Se o padrão NÃO for encontrado (ou for encontrado quando
          não deveria), dispara ``pytest.fail("FALSE RED — …")`` com
          mensagem em pt-BR explicando por que o teste está FAILING.
        - A polaridade de cada AC está documentada na docstring do método.

Anti-Goals (must NOT be violated):
    1. NÃO modificar o código de produção — apenas escrever o teste.
    2. NÃO transpilar nem executar TSX — source-inspection puro.
    3. NÃO usar mocks, Supabase, banco de dados ou rede.
    4. NÃO testar a implementação interna dos componentes do sidebar
       (já existem e têm seu próprio coverage).
    5. NÃO falhar o teste por causa de imports ou whitespace — apenas
       pelos 5 padrões textuais definidos nas ACs.
    6. NÃO inverter a polaridade do teste: o teste deve passar AGORA
       (RED = feature ausente) e falhar depois que a feature for
       entregue (GREEN). A inversão de polaridade é uma armadilha
       clássica em testes de source-inspection.
"""

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
    os métodos de teste da classe ``TestB3BotaoOpenFinance``.
    """
    assert FINANCEIRO_ROOM_TSX.exists(), (
        f"Arquivo de produção não encontrado em {FINANCEIRO_ROOM_TSX}. "
        "O teste B-3 pressupõe que FinanceiroRoom.tsx existe em "
        "apps/blu_v3/src/pages/app/."
    )
    return FINANCEIRO_ROOM_TSX.read_text(encoding="utf-8")


# ── Tests ────────────────────────────────────────────────────────────────────


class TestB3BotaoOpenFinance:
    """RED tests para B-3 (BATCH #205) — Botão Open Finance no quadro Contas.

    Cada ``test_acN_*`` valida uma AC e deve PASSAR (TRUE RED) enquanto
    a feature não tiver sido implementada. Após a entrega do GREEN, o
    padrão procurado pela regex será encontrado (ou não, conforme a
    polaridade da AC) e o teste falhará com
    ``pytest.fail("FALSE RED — …")`` — sinalizando que o RED foi
    violado e o teste precisa ser atualizado/removido.
    """

    # ── AC#1 ────────────────────────────────────────────────────────────────

    def test_ac1_botao_contas_chama_open_chat_with(self) -> None:
        """AC#1 — O onClick do Contas chama ``openChatWith``.

        Polaridade:
            PROCVURA por ``openChatWith`` no contexto do CollapsiblePanel
            "Contas". Se NÃO encontrar, o GREEN já foi implementado
            (a feature substituiu o onClick por ``setShowConnectModal``).

        GREEN esperado:
            O onClick do botão no painel Contas foi alterado de
            ``openChatWith('...')`` para ``setShowConnectModal(true)``.
            Portanto, ``openChatWith`` não aparecerá mais no escopo
            do CollapsiblePanel Contas.

        Hoje (linha 708) o onClick é
        ``openChatWith('Quero adicionar uma nova conta bancária')``
        — ``openChatWith`` está presente.
        """
        source = read_source()
        match = source.find("openChatWith")
        if match == -1:
            pytest.fail(
                "FALSE RED — AC#1 violada: o termo `openChatWith` NÃO "
                f"está mais presente em FinanceiroRoom.tsx. "
                "Esperava-se que o botão do CollapsiblePanel Contas ainda "
                "chamasse `openChatWith` para que este teste RED passasse. "
                "A feature B-3 já foi entregue e este teste precisa ser revisado."
            )

    # ── AC#2 ────────────────────────────────────────────────────────────────

    def test_ac2_show_connect_modal_nao_declarado(self) -> None:
        """AC#2 — ``showConnectModal`` / ``setShowConnectModal`` NÃO estão declarados.

        Polaridade:
            PROCVURA por ``showConnectModal`` ou ``setShowConnectModal``
            em todo o arquivo. Se ENCONTRAR, o GREEN já foi implementado
            (a feature adicionou o estado de controle do modal).

        GREEN esperado:
            ``const [showConnectModal, setShowConnectModal] = useState(false)``
            é adicionado ao componente. Hoje (linha 129+) não há qualquer
            menção a ``showConnectModal`` na source.
        """
        source = read_source()
        match = source.find("showConnectModal")
        if match != -1:
            pytest.fail(
                "FALSE RED — AC#2 violada: `showConnectModal` JÁ aparece "
                f"em FinanceiroRoom.tsx (offset {match}). "
                "Esperava-se que o estado do modal ainda NÃO existisse para "
                "que este teste RED passasse. A feature B-3 já foi entregue "
                "e este teste precisa ser revisado."
            )

    # ── AC#3 ────────────────────────────────────────────────────────────────

    def test_ac3_integration_modal_nao_importado(self) -> None:
        """AC#3 — ``IntegrationModal`` NÃO está importado.

        Polaridade:
            PROCVURA por import do ``IntegrationModal``. Se ENCONTRAR,
            o GREEN já foi implementado (a feature adicionou o import).

        GREEN esperado:
            ``import IntegrationModal from '../../components/shared/IntegrationModal'``
            é adicionado aos imports do arquivo. Hoje (linhas 1-22) não há
            import de ``IntegrationModal``.
        """
        source = read_source()
        match = source.find("IntegrationModal")
        if match != -1:
            pytest.fail(
                "FALSE RED — AC#3 violada: `IntegrationModal` JÁ aparece "
                f"em FinanceiroRoom.tsx (offset {match}). "
                "Esperava-se que o import do IntegrationModal ainda NÃO "
                "existisse para que este teste RED passasse. "
                "A feature B-3 já foi entregue e este teste precisa ser revisado."
            )

    # ── AC#4 ────────────────────────────────────────────────────────────────

    def test_ac4_integration_modal_nao_renderizado(self) -> None:
        """AC#4 — ``<IntegrationModal>`` NÃO está renderizado.

        Polaridade:
            PROCVURA pela tag JSX ``<IntegrationModal``. Se ENCONTRAR,
            o GREEN já foi implementado (a feature renderiza o modal).

        GREEN esperado:
            ``<IntegrationModal ... />`` é adicionado ao JSX retornado
            pela função FinanceiroRoom. Hoje não há ``<IntegrationModal``
            no source.
        """
        source = read_source()
        match = source.find("<IntegrationModal")
        if match != -1:
            pytest.fail(
                "FALSE RED — AC#4 violada: a tag `<IntegrationModal` JÁ "
                f"aparece em FinanceiroRoom.tsx (offset {match}). "
                "Esperava-se que o IntegrationModal ainda NÃO estivesse "
                "sendo renderizado para que este teste RED passasse. "
                "A feature B-3 já foi entregue e este teste precisa ser revisado."
            )

    # ── AC#5 ────────────────────────────────────────────────────────────────

    def test_ac5_painel_fin_contas_existe(self) -> None:
        """AC#5 — O CollapsiblePanel ``id="fin-contas"`` existe.

        Polaridade:
            PROCVURA por ``id="fin-contas"`` ou ``id='fin-contas'``.
            Se NÃO encontrar, o painel foi removido ou renomeado
            (sinal de que algo mudou estruturalmente).

        GREEN esperado:
            O CollapsiblePanel id="fin-contas" permanece (apenas o
            onClick do botão é alterado). Se não for encontrado,
            significa que a estrutura do sidebar mudou significativamente.
        """
        source = read_source()
        match = source.find('id="fin-contas"')
        if match == -1:
            match = source.find("id='fin-contas'")
        if match == -1:
            pytest.fail(
                "FALSE RED — AC#5 violada: o CollapsiblePanel Contas "
                "(id='fin-contas') NÃO está mais presente em "
                "FinanceiroRoom.tsx. Esperava-se que o painel ainda existisse "
                "para que este teste RED passasse. "
                "A estrutura do sidebar pode ter sido alterada."
            )
