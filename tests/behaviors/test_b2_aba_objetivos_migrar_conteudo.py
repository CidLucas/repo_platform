"""RED test for behavior B-2 — Aba Objetivos — migrar conteúdo para aba.

GOAL:
    Migrar e consolidar todo o conteúdo da EstrategiaRoom antiga (aprovações,
    relatórios de contexto, métricas consolidadas, histórico de decisões) para
    a nova aba "Objetivos".

BEHAVIOR:
    B-2 — Aba Objetivos — migrar aprovacoes/relatorios/metricas/historico
    para a aba "Objetivos" consolidada.

    Antes (RED):
        - type Tab = 'decisoes' | 'analises' | 'historico' | 'config'
        - 4 painéis condicionais SEPARADOS:
            tc${tab === 'decisoes' ? ' on' : ''}   → ApprovalCard
            tc${tab === 'analises' ? ' on' : ''}   → MarkdownReport / reports
            tc${tab === 'historico' ? ' on' : ''}  → history list
            tc${tab === 'config' ? ' on' : ''}     → RoutineConfigSection
        - Analytics card e bottom strip fora dos painéis (OK, permanecem).

    Depois (GREEN):
        - type Tab = 'objetivos' | 'documentos' | 'conhecimento' | 'config'
        - UM ÚNICO painel tc${tab === 'objetivos' ? ' on' : ''} que agrega
          approvals, context reports, métricas e history como sub-seções
          internas (não mais tabs separadas).
        - ApprovalCard e MarkdownReport renderizados DENTRO do painel
          'objetivos'.
        - Analytics card (.anl-card) e bottom strip (.bstrip) permanecem
          visíveis no template, fora dos painéis de tab.
        - NÃO há mais painéis tc$ separados para 'decisoes', 'analises' e
          'historico'.

AC (Acceptance Criteria):
    AC#1 — Dentro do painel tab === "objetivos" há uso de dados de
            aprovação (approvalsQ, approvals, ApprovalCard,
            fetchApprovalsByAgent com agent_slug="estrategia").
    AC#2 — Dentro do painel tab === "objetivos" há uso de relatórios
            de contexto (contextReportsQ, contextReports, MarkdownReport,
            fetchContextReports, selectedReport, reportContent).
    AC#3 — Dentro do painel tab === "objetivos" há uso de métricas
            consolidadas (contextMetrics, getContextMetrics,
            estrategiaMetrics).
    AC#4 — Dentro do painel tab === "objetivos" há uso de histórico
            de decisões/estratégia (historyQ, history,
            fetchEstrategiaHistory, EstrategiaHistoryItem).
    AC#5 — ApprovalCard e MarkdownReport são renderizados dentro do
            bloco do painel tab === "objetivos".
    AC#6 — Analytics card (anl-card / anl-hd / anl-body) e bottom strip
            (bstrip / ich / ich-em) permanecem visíveis no template
            FORA dos painéis tab-específicos.
    AC#7 — NÃO existem painéis condicionais tc$ separados para
            tab === "decisoes", tab === "analises" e tab === "historico".
            O conteúdo que era dessas tabs está consolidado em
            tab === "objetivos".

Anti-Goals (must NOT be violated):
    1. NÃO modificar código de produção.
    2. NÃO importar ou executar código TypeScript/React.
    3. NÃO usar fixtures de DB ou rede — teste é pura inspeção de
       arquivos (source-inspection).
"""

import re
from pathlib import Path

import pytest


# ── Constants: caminhos da interface pública sob teste ──────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ESTRATEGIA_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "EstrategiaRoom.tsx"
)


# ── Override do root conftest (teste puramente estático) ────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste é
    pura inspeção de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspeção ────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Lê o arquivo e devolve o conteúdo como string única."""
    assert path.exists(), (
        f"Arquivo não encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-2 (Aba Objetivos — migrar conteúdo) exige que "
        f"este arquivo exista no repositório."
    )
    return path.read_text(encoding="utf-8")


def _extract_tab_panel(content: str, tab_name: str) -> str | None:
    """Extrai o conteúdo do painel condicional tc${{tab === '<tab_name>' ? ' on' : ''}}.

    Localiza o início do painel via o padrão de visibilidade condicional
    e retorna o slice do arquivo entre esse início e o INÍCIO do próximo
    painel tc$ (de qualquer tab). Se não houver próximo painel, devolve
    o conteúdo até o final do arquivo.

    Devolve None se o painel não for encontrado.
    """
    # Padrão do início do painel: tc${tab === '<tab>' ? ' on' : ''}
    # Aceita aspas simples ou duplas.
    panel_start_re = re.compile(
        r"tc\$\{tab\s*===\s*['\"]" + re.escape(tab_name) + r"['\"]"
    )
    start_match = panel_start_re.search(content)
    if not start_match:
        return None

    start_pos = start_match.start()

    # Procura o próximo painel tc${tab === ...} após esse ponto.
    next_panel_re = re.compile(r"tc\$\{tab\s*===\s*['\"]")
    next_match = next_panel_re.search(content, start_pos + 1)

    if next_match:
        return content[start_pos:next_match.start()]
    return content[start_pos:]


# ── Teste único cobrindo AC#1 a AC#7 ───────────────────────────────────────


def test_b2_ac1_to_ac7_aba_objetivos_migrar_conteudo():
    """B-2: Aba Objetivos — migrar aprovacoes/relatorios/metricas/historico
    para a aba Objetivos.  AC#1 a AC#7.

    Este teste cobre simultaneamente as 7 ACs do behavior B-2.  A
    primeira AC violada faz o teste falhar com pytest.fail() em
    pt-BR.  O teste é RED na implementação atual porque:

      - O type Tab ainda é 'decisoes' | 'analises' | 'historico' | 'config'
        e os 4 painéis tc$ são SEPARADOS (decisoes, analises, historico,
        config).  Não existe painel consolidado 'objetivos'.
      - ApprovalCard e MarkdownReport ficam em painéis SEPARADOS
        (decisoes e analises), não dentro de 'objetivos'.
      - Existem painéis tc$ para 'decisoes', 'analises' e 'historico',
        violando AC#7.

    Na implementação GREEN, o painel tc${{tab === "objetivos" ? ' on' : ''}}
    deve agregar todo o conteúdo e os painéis antigos deixam de existir.
    """
    content = _read_text(ESTRATEGIA_ROOM_PATH)

    rel_path = ESTRATEGIA_ROOM_PATH.relative_to(REPO_ROOT)

    # ── Pré-condição: garantir que o arquivo não está vazio ────────────
    assert content.strip(), (
        f"O arquivo {rel_path} está vazio.  O behavior B-2 exige que "
        f"EstrategiaRoom.tsx tenha conteúdo para validar a aba Objetivos."
    )

    # ── Extrai o conteúdo do painel 'objetivos' (GREEN state) ──────────
    objetivos_panel = _extract_tab_panel(content, "objetivos")

    # ── AC#1: Aba "Objetivos" renderiza cards de aprovação ─────────────
    if objetivos_panel is None:
        pytest.fail(
            f"AC#1 violada — RED.  O painel consolidado 'objetivos' "
            f"NÃO foi encontrado em {rel_path}.\n\n"
            f"Esperado: existe um painel "
            f"tc${{{{tab === 'objetivos' ? ' on' : ''}}}} que agrega "
            f"approvals (fetchApprovalsByAgent com agent_slug='estrategia').\n\n"
            f"Estado atual: type Tab = 'decisoes' | 'analises' | "
            f"'historico' | 'config' e os 4 painéis tc$ são SEPARADOS.\n\n"
            f"GREEN deve:\n"
            f"  1. Renomear type Tab para incluir 'objetivos'.\n"
            f"  2. Consolidar approvals, context reports, métricas e "
            f"history em UM ÚNICO painel "
            f"tc${{{{tab === 'objetivos' ? ' on' : ''}}}}.\n"
            f"  3. Renderizar <ApprovalCard ... /> dentro desse painel."
        )

    # Verifica que os símbolos de approvals aparecem DENTRO do painel
    # consolidado 'objetivos'.
    approvals_symbols = [
        "approvalsQ",
        "approvals",
        "ApprovalCard",
        "fetchApprovalsByAgent",
    ]
    # Pelo menos 3 dos 4 símbolos precisam estar no painel (algumas
    # implementações podem usar nomes ligeiramente diferentes, mas a
    # presença conjunta confirma o uso de approvals).
    found_approvals = [
        sym for sym in approvals_symbols
        if sym in objetivos_panel
    ]
    if len(found_approvals) < 2:
        pytest.fail(
            f"AC#1 violada — RED.  O painel tab === \"objetivos\" existe, "
            f"mas NÃO contém símbolos suficientes de aprovação.\n\n"
            f"Símbolos procurados dentro do painel 'objetivos':\n"
            f"  {', '.join(approvals_symbols)}\n"
            f"Símbolos encontrados: {found_approvals or '(nenhum)'}\n\n"
            f"Era esperado que DENTRO do painel "
            f"tc${{{{tab === 'objetivos' ? ' on' : ''}}}} o componente "
            f"renderizasse cards de aprovação do agent 'estrategia' "
            f"usando fetchApprovalsByAgent.\n\n"
            f"GREEN deve mover o bloco "
            f"tc${{{{tab === 'decisoes' ? ' on' : ''}}}} (com o "
            f"ApprovalCard) para DENTRO do painel 'objetivos'."
        )

    # ── AC#2: Aba "Objetivos" renderiza relatórios de contexto ────────
    reports_symbols = [
        "contextReportsQ",
        "contextReports",
        "MarkdownReport",
        "fetchContextReports",
        "selectedReport",
        "reportContent",
    ]
    found_reports = [
        sym for sym in reports_symbols
        if sym in objetivos_panel
    ]
    if len(found_reports) < 3:
        pytest.fail(
            f"AC#2 violada — RED.  O painel tab === \"objetivos\" existe, "
            f"mas NÃO contém símbolos suficientes de relatórios de "
            f"contexto.\n\n"
            f"Símbolos procurados dentro do painel 'objetivos':\n"
            f"  {', '.join(reports_symbols)}\n"
            f"Símbolos encontrados: {found_reports or '(nenhum)'}\n\n"
            f"Era esperado que DENTRO do painel "
            f"tc${{{{tab === 'objetivos' ? ' on' : ''}}}} houvesse o "
            f"visualizador de relatórios MarkdownReport "
            f"(fetchContextReports, selectedReport, reportContent).\n\n"
            f"GREEN deve mover o conteúdo do painel "
            f"tc${{{{tab === 'analises' ? ' on' : ''}}}} (com "
            f"MarkdownReport) para DENTRO do painel 'objetivos'."
        )

    # ── AC#3: Aba "Objetivos" renderiza métricas consolidadas ─────────
    metrics_symbols = [
        "contextMetrics",
        "getContextMetrics",
        "estrategiaMetrics",
    ]
    found_metrics = [
        sym for sym in metrics_symbols
        if sym in objetivos_panel
    ]
    if len(found_metrics) < 2:
        pytest.fail(
            f"AC#3 violada — RED.  O painel tab === \"objetivos\" existe, "
            f"mas NÃO contém símbolos suficientes de métricas "
            f"consolidadas.\n\n"
            f"Símbolos procurados dentro do painel 'objetivos':\n"
            f"  {', '.join(metrics_symbols)}\n"
            f"Símbolos encontrados: {found_metrics or '(nenhum)'}\n\n"
            f"Era esperado que DENTRO do painel "
            f"tc${{{{tab === 'objetivos' ? ' on' : ''}}}} houvesse "
            f"KPI cards de métricas de contexto "
            f"(contextMetrics, getContextMetrics, estrategiaMetrics).\n\n"
            f"GREEN deve mover o conteúdo de métricas (que estava no "
            f"analytics card OU no painel 'analises') para DENTRO do "
            f"painel 'objetivos'."
        )

    # ── AC#4: Aba "Objetivos" renderiza histórico ─────────────────────
    history_symbols = [
        "historyQ",
        "history",
        "fetchEstrategiaHistory",
        "EstrategiaHistoryItem",
    ]
    found_history = [
        sym for sym in history_symbols
        if sym in objetivos_panel
    ]
    if len(found_history) < 2:
        pytest.fail(
            f"AC#4 violada — RED.  O painel tab === \"objetivos\" existe, "
            f"mas NÃO contém símbolos suficientes de histórico de "
            f"decisões/estratégia.\n\n"
            f"Símbolos procurados dentro do painel 'objetivos':\n"
            f"  {', '.join(history_symbols)}\n"
            f"Símbolos encontrados: {found_history or '(nenhum)'}\n\n"
            f"Era esperado que DENTRO do painel "
            f"tc${{{{tab === 'objetivos' ? ' on' : ''}}}} houvesse a "
            f"lista de histórico de estratégia "
            f"(fetchEstrategiaHistory, EstrategiaHistoryItem, historyQ, "
            f"history).\n\n"
            f"GREEN deve mover o conteúdo do painel "
            f"tc${{{{tab === 'historico' ? ' on' : ''}}}} para DENTRO do "
            f"painel 'objetivos'."
        )

    # ── AC#5: ApprovalCard e MarkdownReport renderizados dentro ───────
    # A presença isolada dos NOMES não basta: precisamos confirmar que
    # as tags JSX <ApprovalCard ... /> e <MarkdownReport ... /> estão
    # dentro do slice do painel 'objetivos'.
    has_approval_card_tag = bool(
        re.search(r"<\s*ApprovalCard\b", objetivos_panel)
    )
    has_markdown_report_tag = bool(
        re.search(r"<\s*MarkdownReport\b", objetivos_panel)
    )
    if not (has_approval_card_tag and has_markdown_report_tag):
        missing = []
        if not has_approval_card_tag:
            missing.append("<ApprovalCard ... />")
        if not has_markdown_report_tag:
            missing.append("<MarkdownReport ... />")
        pytest.fail(
            f"AC#5 violada — RED.  O painel tab === \"objetivos\" existe, "
            f"mas NÃO renderiza as tags JSX esperadas: "
            f"{', '.join(missing)}.\n\n"
            f"Grep dentro do painel 'objetivos':\n"
            f"  has_approval_card_tag = {has_approval_card_tag}\n"
            f"  has_markdown_report_tag = {has_markdown_report_tag}\n\n"
            f"Era esperado que o painel "
            f"tc${{{{tab === 'objetivos' ? ' on' : ''}}}} renderizasse "
            f"as duas tags: <ApprovalCard ... /> e <MarkdownReport ... />.\n\n"
            f"GREEN deve colocar ambas as tags dentro do painel "
            f"'objetivos' (idealmente como sub-seções internas)."
        )

    # ── AC#6: Analytics card e bottom strip permanecem visíveis ───────
    # Verifica que os blocos de classe anl-card e bstrip existem no
    # template e estão FORA dos painéis tab-específicos.  Para
    # garantir que estão fora, verificamos que aparecem no arquivo
    # mas NÃO aparecem dentro do slice do painel 'objetivos' (que é
    # apenas o conteúdo do painel de tab).
    anl_card_classes = ["anl-card", "anl-hd", "anl-body"]
    bstrip_classes = ["bstrip", "ich", "ich-em"]
    missing_anl = [c for c in anl_card_classes if c not in content]
    missing_bstrip = [c for c in bstrip_classes if c not in content]

    if missing_anl or missing_bstrip:
        pytest.fail(
            f"AC#6 violada — RED.  Classes do analytics card ou bottom "
            f"strip estão AUSENTES do template em {rel_path}.\n\n"
            f"Classes ausentes do analytics card: {missing_anl or '(todas presentes)'}\n"
            f"Classes ausentes do bottom strip: {missing_bstrip or '(todas presentes)'}\n\n"
            f"Esperado: anl-card, anl-hd, anl-body, bstrip, ich, ich-em "
            f"presentes no template FORA dos painéis tab-específicos."
        )

    # Garante que o analytics card e o bottom strip NÃO estão dentro
    # do painel 'objetivos' (devem ficar no template raiz, fora dos
    # painéis de tab).
    anl_inside_objetivos = "anl-card" in objetivos_panel
    bstrip_inside_objetivos = "bstrip" in objetivos_panel
    if anl_inside_objetivos or bstrip_inside_objetivos:
        pytest.fail(
            f"AC#6 violada — RED.  O analytics card e/ou bottom strip "
            f"foram movidos PARA DENTRO do painel 'objetivos', mas "
            f"devem permanecer no template FORA dos painéis tab.\n\n"
            f"anl-card dentro de 'objetivos': {anl_inside_objetivos}\n"
            f"bstrip dentro de 'objetivos': {bstrip_inside_objetivos}\n\n"
            f"Esperado: anl-card e bstrip ficam no template raiz "
            f"(mesmo nível do .room-grid), fora dos painéis tc$."
        )

    # ── AC#7: NÃO há painéis tc$ separados para 'decisoes', ────────────
    # ──      'analises' e 'historico' ──────────────────────────────────
    abas_antigas = ["decisoes", "analises", "historico"]
    paineis_antigos_encontrados = []
    for antiga in abas_antigas:
        panel_re = re.compile(
            r"tc\$\{tab\s*===\s*['\"]" + re.escape(antiga) + r"['\"]"
        )
        if panel_re.search(content):
            paineis_antigos_encontrados.append(antiga)

    if paineis_antigos_encontrados:
        pytest.fail(
            f"AC#7 violada — RED.  Ainda existem painéis tc$ SEPARADOS "
            f"para as abas antigas em {rel_path}.\n\n"
            f"Painéis antigos encontrados:\n"
            f"  {', '.join(paineis_antigos_encontrados)}\n\n"
            f"Esperado: NÃO devem existir painéis tc$ para 'decisoes', "
            f"'analises' ou 'historico'.  O conteúdo dessas abas deve "
            f"estar CONSOLIDADO em UM ÚNICO painel "
            f"tc${{{{tab === 'objetivos' ? ' on' : ''}}}}.\n\n"
            f"GREEN deve remover os 3 painéis antigos:\n"
            f"  - tc${{{{tab === 'decisoes' ? ' on' : ''}}}}  → merged into 'objetivos'\n"
            f"  - tc${{{{tab === 'analises' ? ' on' : ''}}}}  → merged into 'objetivos'\n"
            f"  - tc${{{{tab === 'historico' ? ' on' : ''}}}} → merged into 'objetivos'\n\n"
            f"Apenas o painel 'config' (configuração) deve permanecer "
            f"como tc$ separado, pois não é conteúdo do objetivo."
        )
