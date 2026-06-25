"""RED test — B-3: Aba Objetivos — Migrar decisões, análises, histórico, métricas.

GOAL:
    Migrar o conteúdo da antiga EstrategiaRoom (decisões, análises, histórico,
    relatórios de contexto, métricas) para a aba Objetivos da nova estrutura.

BEHAVIOR:
    "B-3: Aba Objetivos — Migrar decisões, análises, histórico, métricas
     da antiga EstrategiaRoom."

    A nova EstrategiaRoom (em apps/blu_v3/src/pages/app/EstrategiaRoom.tsx)
    ainda usa 4 tabs no topo (decisoes, analises, historico, config) em vez
    de ter uma aba "Objetivos" com sub-seções internas para cada categoria.

    Estado atual (BEFORE):
        - type Tab = 'decisoes' | 'analises' | 'historico' | 'config'
        - tabs renderizadas via {(["decisoes", "analises", "historico", "config"] as Tab[]).map(...)}
        - const [tab, setTab] = useState<Tab>('decisoes')
        - Cada tab renderiza conteúdo diretamente no painel principal
        - Analytics card separado no final do painel

    Estado esperado (AFTER — GREEN):
        - A aba "Objetivos" existe com sub-seções internas
        - Sub-seção "Decisões" com approvals do agent 'estrategia'
        - Sub-seção "Análises" com context reports + MarkdownReport
        - Sub-seção "Histórico" com estratégia aprovadas/rejeitadas
        - Sub-seção "Métricas" com contextMetrics em KPI cards
        - Navegação interna entre sub-seções
        - Remover tabs 'decisoes', 'analises', 'historico' antigas

AC (Acceptance Criteria):
    AC#1 — Aba Objetivos exibe decisões pendentes (approvals do agent 'estrategia')
    AC#2 — Análises (context reports com visualizador markdown)
    AC#3 — Histórico de estratégia (aprovadas/rejeitadas)
    AC#4 — Métricas de contexto no analytics card
    AC#5 — Navegação entre seções (decisões, análises, histórico, métricas) dentro da aba

Estado atual: RED — todas as ACs violadas porque o código atual usa tabs
decisoes/analises/historico/config em vez de uma aba Objetivos unificada com
sub-seções internas. Cada teste falha com AssertionError detalhado em pt-BR.

Anti-Goals:
    1. NÃO usar mocks, Supabase, browser testing — só source-inspection.
    2. NÃO modificar produção — só escrever testes que comprovam o gap.
    3. NÃO remover funcionalidade existente ao migrar (approvals, reports, etc.).
    4. NÃO introduzir dependências externas de UI (bibliotecas de tabs).
"""

import re
from pathlib import Path

import pytest

# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

ESTRATEGIA_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "EstrategiaRoom.tsx"
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _read_source() -> str:
    """Read the current EstrategiaRoom.tsx as plain text."""
    if not ESTRATEGIA_ROOM_PATH.is_file():
        pytest.fail(
            f"Arquivo não encontrado: {ESTRATEGIA_ROOM_PATH}\n"
            "O teste espera que EstrategiaRoom.tsx exista."
        )
    return ESTRATEGIA_ROOM_PATH.read_text(encoding="utf-8")


# ── Tests ─────────────────────────────────────────────────────────────────


def test_ac1_objetivos_exibe_decisoes():
    """AC#1 — Aba Objetivos exibe decisões pendentes (approvals do agent 'estrategia').

    RED: O código atual usa tabs 'decisoes/analises/historico/config' em vez
    de ter uma aba 'Objetivos' com sub-seção 'Decisões'. Este teste falha
    porque não encontra um bloco <div> com texto contendo 'Decisões' dentro
    de uma seção Objetivos.
    """
    source = _read_source()

    # O código atual declara as tabs no topo: "decisoes", "analises", "historico", "config"
    # Em vez disso, deveria ter "Objetivos" como tab principal e sub-seções internas.
    # Procuramos evidências de que uma seção "Objetivos" existe.
    tem_objetivos_tab = bool(re.search(
        r"['\"']Objetivos['\"']",
        source,
    ))

    tem_objetivos_section = "Objetivos" in source and any(
        keyword in source
        for keyword in ["sub-seção", "subSecao", "sub-section", "objetivosSecao"]
    )

    if not (tem_objetivos_tab or tem_objetivos_section):
        pytest.fail(
            "AC#1 não atendida — Aba 'Objetivos' não encontrada.\n\n"
            "O código atual usa tabs no topo:\n"
            "  ['decisoes', 'analises', 'historico', 'config']\n\n"
            "O esperado é que exista uma aba 'Objetivos' (ou 'objetivos') que\n"
            "agrupe as sub-seções de Decisões, Análises, Histórico e Métricas.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )

    # Procurar por referências a approvals dentro de contexto Objetivos
    tem_decisoes_dentro_objetivos = bool(
        re.search(
            r"(?i)objetivos.*decis[ãó]es|decis[ãó]es.*objetivos",
            source,
        )
    )

    if (tem_objetivos_tab or tem_objetivos_section) and not tem_decisoes_dentro_objetivos:
        pytest.fail(
            "AC#1 parcial — Aba 'Objetivos' encontrada mas sem sub-seção "
            "'Decisões'.\n\n"
            "A aba Objetivos deve conter uma sub-seção que exiba approvals\n"
            "pendentes do agent 'estrategia' (fetchApprovalsByAgent)."
        )

    # Se chegou aqui, o teste passaria — mas é RED porque nada existe
    # (garantia dupla: se a implementação futura incluir Objetivos, falhar
    #  porque ainda não há conteúdo de decisões dentro dela)
    if not tem_decisoes_dentro_objetivos:
        pytest.fail(
            "AC#1 não atendida — Nenhuma sub-seção 'Decisões' dentro de 'Objetivos'.\n\n"
            "A aba Objetivos deve exibir approvals pendentes do agent 'estrategia'\n"
            "com botões Aprovar/Depois/Ignorar, similar ao que existe na tab 'decisoes'.\n\n"
            "Comportamento esperado:\n"
            "  1. fetchApprovalsByAgent('estrategia', clientId)\n"
            "  2. Renderizar ApprovalCard com onApprove/onReject/onSnooze\n"
            "  3. Badge com contagem de approvals pendentes"
        )


def test_ac2_objetivos_exibe_analises():
    """AC#2 — Análises (context reports com visualizador markdown).

    RED: O código atual renderiza análises na tab 'analises'. O esperado é
    que exista uma sub-seção 'Análises' dentro da aba Objetivos com o mesmo
    MarkdownReport viewer.
    """
    source = _read_source()

    # Verificar se existe seção "Análises" dentro da aba Objetivos
    tem_analises_em_objetivos = bool(
        re.search(
            r"(?i)objetivos.*an[aá]lises|an[aá]lises.*objetivos",
            source,
        )
    )

    # Verificar se MarkdownReport é usado dentro de contexto Objetivos
    tem_markdown_em_objetivos = bool(
        re.search(
            r"(?i)objetivos.*MarkdownReport|MarkdownReport.*objetivos",
            source,
        )
    )

    if not tem_analises_em_objetivos and not tem_markdown_em_objetivos:
        pytest.fail(
            "AC#2 não atendida — Sub-seção 'Análises' não encontrada dentro da "
            "aba Objetivos.\n\n"
            "O código atual renderiza análises na tab 'analises' com:\n"
            "  - ContextReport list na coluna direita\n"
            "  - MarkdownReport viewer no painel principal\n\n"
            "O esperado é que a aba Objetivos contenha uma sub-seção 'Análises'\n"
            "com o mesmo visualizador Markdown e lista de relatórios.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )


def test_ac3_objetivos_exibe_historico():
    """AC#3 — Histórico de estratégia (aprovadas/rejeitadas).

    RED: O código atual renderiza histórico na tab 'historico'. O esperado é
    que exista uma sub-seção 'Histórico' dentro da aba Objetivos.
    """
    source = _read_source()

    # Verificar se existe seção "Histórico" dentro da aba Objetivos
    tem_historico_em_objetivos = bool(
        re.search(
            r"(?i)objetivos.*hist[óo]rico|hist[óo]rico.*objetivos",
            source,
        )
    )

    if not tem_historico_em_objetivos:
        pytest.fail(
            "AC#3 não atendida — Sub-seção 'Histórico' não encontrada dentro da "
            "aba Objetivos.\n\n"
            "O código atual renderiza histórico na tab 'historico' com:\n"
            "  - fetchEstrategiaHistory(clientId)\n"
            "  - Lista de itens com title, relativeTime, action (approved/rejected)\n"
            "  - Cores: verde para aprovada, vermelho para rejeitada\n\n"
            "O esperado é que a aba Objetivos contenha uma sub-seção 'Histórico'\n"
            "com a mesma lista de análises aprovadas/rejeitadas.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )


def test_ac4_objetivos_exibe_metricas():
    """AC#4 — Métricas de contexto no analytics card.

    RED: O código atual renderiza métricas num analytics card separado no
    final do painel principal. O esperado é que exista uma sub-seção
    'Métricas' dentro da aba Objetivos com os mesmos KPI cards.
    """
    source = _read_source()

    # Verificar se existe seção "Métricas" dentro da aba Objetivos
    tem_metricas_em_objetivos = bool(
        re.search(
            r"(?i)objetivos.*m[eé]tricas|m[eé]tricas.*objetivos",
            source,
        )
    )

    if not tem_metricas_em_objetivos:
        pytest.fail(
            "AC#4 não atendida — Sub-seção 'Métricas' não encontrada dentro da "
            "aba Objetivos.\n\n"
            "O código atual renderiza métricas em analytics card separado:\n"
            "  - estrategiaMetrics filtrados de contextMetrics\n"
            "  - Grid de KPI cards com label, value, MoM % change\n"
            "  - Formatação: R$ para monetário, % para percentuais\n\n"
            "O esperado é que a aba Objetivos contenha uma sub-seção 'Métricas'\n"
            "com os mesmos KPI cards de contexto.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )


def test_ac5_objetivos_navegacao_entre_secoes():
    """AC#5 — Navegação entre seções dentro da aba Objetivos.

    RED: O código atual usa tabs no topo para navegar entre decisoes/analises/
    historico/config. O esperado é que exista navegação secundária (sub-tabs
    ou botões) dentro da aba Objetivos para alternar entre Decisões, Análises,
    Histórico e Métricas.
    """
    source = _read_source()

    # Procurar por sub-navegação dentro da aba Objetivos
    tem_subnav_dentro_objetivos = bool(
        re.search(
            r"(?i)(objetivos.*(decis|an.lise|hist.rico|m.trica)"
            r"|(decis|an.lise|hist.rico|m.trica).*objetivos)",
            source,
        )
    )

    # Verificar se ainda existe a estrutura antiga de tabs
    tem_tabs_antigas = bool(
        re.search(
            r"""['"](decisoes|analises|historico|config)['"]""",
            source,
        )
    )

    if not tem_subnav_dentro_objetivos:
        if tem_tabs_antigas:
            pytest.fail(
                "AC#5 não atendida — Navegação entre seções não encontrada dentro "
                "da aba Objetivos.\n\n"
                "O código atual usa tabs no topo:\n"
                "  {(['decisoes', 'analises', 'historico', 'config'] as Tab[]).map(...)}\n\n"
                "O esperado é que a aba Objetivos contenha sub-navegação interna\n"
                "para alternar entre:\n"
                "  - Decisões (approvals pendentes)\n"
                "  - Análises (context reports)\n"
                "  - Histórico (aprovadas/rejeitadas)\n"
                "  - Métricas (KPI cards)\n\n"
                "Pode ser implementado como sub-tabs, botões de seção ou\n"
                "accordion, desde que permita navegação entre as 4 categorias.\n\n"
                f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
            )

        pytest.fail(
            "AC#5 não atendida — Navegação entre seções não encontrada "
            "na aba Objetivos.\n\n"
            "A aba Objetivos deve ter navegação secundária para alternar entre\n"
            "Decisões, Análises, Histórico e Métricas.\n\n"
            f"Arquivo: {ESTRATEGIA_ROOM_PATH}"
        )
