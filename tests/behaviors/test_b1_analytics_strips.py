"""RED test for behavior B-1 — Strips de analytics posicionadas corretamente (BKL-018 + BKL-030) (NAO implementado).

GOAL:
    Validar que a feature de posicionar KpiMetricsPanel dentro de uma aba
    "Análises" de cada sala (FinanceiroRoom, ComprasRoom, ClientesRoom)
    **NAO esta implementada** no estado atual do repositorio.

    O behavior B-1 (a ser entregue em fase GREEN) deve:
      1) Importar KpiMetricsPanel em cada sala
      2) Adicionar uma aba "Análises" ao array de tabs
      3) Renderizar <KpiMetricsPanel metrics={contextMetrics} /> condicionalmente
         dentro dessa aba
      4) Passar os context metrics corretos (financeiroContextMetrics,
         comprasContextMetrics, clientesContextMetrics) como prop
      5) Nao renderizar KpiMetricsPanel em outras abas

BEHAVIOR:
    B-1 — Strips de analytics posicionadas corretamente (BKL-018 + BKL-030):
    KpiMetricsPanel aparece SOMENTE na aba "Análises" (ou equivalente) de cada
    sala. Quando clicado, carrega os context metrics corretos. Nao aparece em
    outras abas.

    **Estado atual (RED):** nenhum desses pontos esta implementado.
    Nenhuma sala importa KpiMetricsPanel, nenhuma tem uma aba "analises",
    e o contexto metrics eh renderizado inline (nao via KpiMetricsPanel).

AC (Acceptance Criteria):
    AC#1 — FinanceiroRoom.tsx importa KpiMetricsPanel de
            '../../components/shared/KpiMetricsPanel' e define uma aba "analises"
            nas tabs que renderiza <KpiMetricsPanel> condicionalmente.
    AC#2 — ComprasRoom.tsx importa KpiMetricsPanel de
            '../../components/shared/KpiMetricsPanel' e define uma aba "analises"
            nas tabs que renderiza <KpiMetricsPanel> condicionalmente.
    AC#3 — ClientesRoom.tsx importa KpiMetricsPanel de
            '../../components/shared/KpiMetricsPanel' e define uma aba "analises"
            nas tabs que renderiza <KpiMetricsPanel> condicionalmente.
    AC#4 — Cada sala passa o array de context metrics correto
            (financeiroContextMetrics / comprasContextMetrics /
            clientesContextMetrics) como prop metrics=<name> no
            <KpiMetricsPanel>.
    AC#5 — KpiMetricsPanel nao eh renderizado em nenhuma aba que NAO seja
            "analises" (as demais abas nao contem <KpiMetricsPanel>).

Estado atual: RED — todas as ACs violadas. Nenhuma das tres salas importa
KpiMetricsPanel nem tem uma aba "analises". Cada teste falha com
pytest.fail() e mensagem detalhada em pt-BR.

Anti-Goals:
    1. NAO modificar codigo de producao (sao apenas testes estaticos).
    2. NAO executar / parsear TypeScript — so inspecao textual com regex.
    3. NAO usar mocks, Supabase, browser testing, jsdom.
    4. NAO quebrar funcionalidade existente (decisoes, compromissos, etc.).
    5. NAO relaxar o teste para que ele passe no estado atual — ele
       precisa ser TRUE RED agora.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent.parent

FINANCEIRO_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "FinanceiroRoom.tsx"
)

COMPRAS_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "ComprasRoom.tsx"
)

CLIENTES_ROOM_PATH = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "ClientesRoom.tsx"
)


# ── Override do root conftest (teste puramente estatico) ─────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste eh
    pura inspecao de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspecao do TypeScript ────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Le o arquivo e devolve o conteudo como string unica."""
    assert path.exists(), (
        f"Arquivo nao encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-1 (strips de analytics) exige que este "
        f"arquivo exista no repositorio."
    )
    return path.read_text(encoding="utf-8")


def _has_kpi_import(source: str) -> bool:
    """Retorna True se o arquivo importa KpiMetricsPanel do caminho esperado."""
    return bool(
        re.search(
            r"from\s+['\"]\.\./\.\./components/shared/KpiMetricsPanel['\"]\s+import\s+KpiMetricsPanel",
            source,
        )
    )


def _has_analises_tab(source: str) -> bool:
    """Retorna True se o arquivo declara uma tab chamada 'analises'."""
    return bool(re.search(r"['\"]analises['\"]", source))


def _has_kpi_metrics_panel_jsx(source: str) -> bool:
    """Retorna True se o arquivo contem <KpiMetricsPanel ...> JSX."""
    return bool(re.search(r"<KpiMetricsPanel\s", source))


def _has_kpi_metrics_panel_in_analyses_tab(source: str) -> bool:
    """Retorna True se ha <KpiMetricsPanel> dentro de um bloco com
    tab === 'analises'.
    """
    return bool(
        re.search(
            r"tab\s*===\s*['\"]analises['\"].*?<KpiMetricsPanel\s",
            source,
            re.DOTALL,
        )
    )


def _context_metrics_passed_to_kpi(source: str, var_name: str) -> bool:
    """Retorna True se <KpiMetricsPanel metrics={var_name}> aparece."""
    return bool(
        re.search(
            rf"<KpiMetricsPanel\s[^>]*metrics=\{{{re.escape(var_name)}\}}",
            source,
        )
    )


# ── AC#1 — FinanceiroRoom.tsx ────────────────────────────────────────────────


def test_b1_ac1_financeiro_import_e_tab_analises_ausente():
    """AC#1: FinanceiroRoom.tsx DEVE importar KpiMetricsPanel e ter uma
    aba 'analises' que renderiza <KpiMetricsPanel> condicionalmente.

    Falha (RED) enquanto o import e a tab nao existirem.
    """
    source = _read_text(FINANCEIRO_ROOM_PATH)

    if _has_kpi_import(source) and _has_analises_tab(source) and _has_kpi_metrics_panel_in_analyses_tab(source):
        return  # GREEN — implementado

    erros: list[str] = []
    if not _has_kpi_import(source):
        erros.append(
            "FinanceiroRoom.tsx NAO importa KpiMetricsPanel de "
            "'../../components/shared/KpiMetricsPanel'.  "
            "Esperado: from '../../components/shared/KpiMetricsPanel' import KpiMetricsPanel"
        )
    if not _has_analises_tab(source):
        erros.append(
            "FinanceiroRoom.tsx NAO tem uma tab 'analises' definida no array de tabs.  "
            "Esperado: 'analises' no type Tab e no map das tabs"
        )
    if not _has_kpi_metrics_panel_jsx(source):
        erros.append(
            "FinanceiroRoom.tsx NAO renderiza <KpiMetricsPanel> em lugar nenhum.  "
            "Esperado: <KpiMetricsPanel metrics={financeiroContextMetrics} /> dentro da aba analises"
        )
    elif not _has_kpi_metrics_panel_in_analyses_tab(source):
        erros.append(
            "FinanceiroRoom.tsx renderiza <KpiMetricsPanel> mas NAO dentro de um bloco "
            "condicional tab === 'analises'.  "
            "Esperado: o <KpiMetricsPanel> deve aparecer SOMENTE na aba analises"
        )

    pytest.fail("\n".join(erros))


# ── AC#2 — ComprasRoom.tsx ───────────────────────────────────────────────────


def test_b1_ac2_compras_import_e_tab_analises_ausente():
    """AC#2: ComprasRoom.tsx DEVE importar KpiMetricsPanel e ter uma
    aba 'analises' que renderiza <KpiMetricsPanel> condicionalmente.

    Falha (RED) enquanto o import e a tab nao existirem.
    """
    source = _read_text(COMPRAS_ROOM_PATH)

    if _has_kpi_import(source) and _has_analises_tab(source) and _has_kpi_metrics_panel_in_analyses_tab(source):
        return  # GREEN — implementado

    erros: list[str] = []
    if not _has_kpi_import(source):
        erros.append(
            "ComprasRoom.tsx NAO importa KpiMetricsPanel de "
            "'../../components/shared/KpiMetricsPanel'.  "
            "Esperado: import KpiMetricsPanel from '../../components/shared/KpiMetricsPanel'"
        )
    if not _has_analises_tab(source):
        erros.append(
            "ComprasRoom.tsx NAO tem uma tab 'analises' definida no array de tabs.  "
            "Esperado: 'analises' no type Tab e no map das tabs"
        )
    if not _has_kpi_metrics_panel_jsx(source):
        erros.append(
            "ComprasRoom.tsx NAO renderiza <KpiMetricsPanel> em lugar nenhum.  "
            "Esperado: <KpiMetricsPanel metrics={comprasContextMetrics} /> dentro da aba analises"
        )
    elif not _has_kpi_metrics_panel_in_analyses_tab(source):
        erros.append(
            "ComprasRoom.tsx renderiza <KpiMetricsPanel> mas NAO dentro de um bloco "
            "condicional tab === 'analises'.  "
            "Esperado: o <KpiMetricsPanel> deve aparecer SOMENTE na aba analises"
        )

    pytest.fail("\n".join(erros))


# ── AC#3 — ClientesRoom.tsx ──────────────────────────────────────────────────


def test_b1_ac3_clientes_import_e_tab_analises_ausente():
    """AC#3: ClientesRoom.tsx DEVE importar KpiMetricsPanel e ter uma
    aba 'analises' que renderiza <KpiMetricsPanel> condicionalmente.

    Falha (RED) enquanto o import e a tab nao existirem.
    """
    source = _read_text(CLIENTES_ROOM_PATH)

    if _has_kpi_import(source) and _has_analises_tab(source) and _has_kpi_metrics_panel_in_analyses_tab(source):
        return  # GREEN — implementado

    erros: list[str] = []
    if not _has_kpi_import(source):
        erros.append(
            "ClientesRoom.tsx NAO importa KpiMetricsPanel de "
            "'../../components/shared/KpiMetricsPanel'.  "
            "Esperado: import KpiMetricsPanel from '../../components/shared/KpiMetricsPanel'"
        )
    if not _has_analises_tab(source):
        erros.append(
            "ClientesRoom.tsx NAO tem uma tab 'analises' definida no array de tabs.  "
            "Esperado: 'analises' no type Tab e no map das tabs"
        )
    if not _has_kpi_metrics_panel_jsx(source):
        erros.append(
            "ClientesRoom.tsx NAO renderiza <KpiMetricsPanel> em lugar nenhum.  "
            "Esperado: <KpiMetricsPanel metrics={clientesContextMetrics} /> dentro da aba analises"
        )
    elif not _has_kpi_metrics_panel_in_analyses_tab(source):
        erros.append(
            "ClientesRoom.tsx renderiza <KpiMetricsPanel> mas NAO dentro de um bloco "
            "condicional tab === 'analises'.  "
            "Esperado: o <KpiMetricsPanel> deve aparecer SOMENTE na aba analises"
        )

    pytest.fail("\n".join(erros))


# ── AC#4 — Context metrics corretos para cada sala ──────────────────────────


def test_b1_ac4_context_metrics_corretos_por_sala():
    """AC#4: Cada sala DEVE passar o array de context metrics correto
    como prop metrics=<varName> no <KpiMetricsPanel>.

    - FinanceiroRoom: metrics={financeiroContextMetrics}
    - ComprasRoom:    metrics={comprasContextMetrics}
    - ClientesRoom:   metrics={clientesContextMetrics}

    Falha (RED) enquanto os metrics corretos nao forem passados.
    """
    erros: list[str] = []

    fin_src = _read_text(FINANCEIRO_ROOM_PATH)
    if _has_kpi_metrics_panel_jsx(fin_src) and not _context_metrics_passed_to_kpi(fin_src, "financeiroContextMetrics"):
        erros.append(
            "FinanceiroRoom.tsx renderiza <KpiMetricsPanel> mas NAO passa "
            "metrics={financeiroContextMetrics}.  "
            "Esperado: <KpiMetricsPanel metrics={financeiroContextMetrics} ... />"
        )

    comp_src = _read_text(COMPRAS_ROOM_PATH)
    if _has_kpi_metrics_panel_jsx(comp_src) and not _context_metrics_passed_to_kpi(comp_src, "comprasContextMetrics"):
        erros.append(
            "ComprasRoom.tsx renderiza <KpiMetricsPanel> mas NAO passa "
            "metrics={comprasContextMetrics}.  "
            "Esperado: <KpiMetricsPanel metrics={comprasContextMetrics} ... />"
        )

    cli_src = _read_text(CLIENTES_ROOM_PATH)
    if _has_kpi_metrics_panel_jsx(cli_src) and not _context_metrics_passed_to_kpi(cli_src, "clientesContextMetrics"):
        erros.append(
            "ClientesRoom.tsx renderiza <KpiMetricsPanel> mas NAO passa "
            "metrics={clientesContextMetrics}.  "
            "Esperado: <KpiMetricsPanel metrics={clientesContextMetrics} ... />"
        )

    if erros:
        pytest.fail("\n".join(erros))


# ── AC#5 — KpiMetricsPanel NAO aparece em outras abas ───────────────────────


def test_b1_ac5_kpi_metrics_panel_fora_da_aba_analises():
    """AC#5: <KpiMetricsPanel> NAO deve ser renderizado em nenhuma aba
    que NAO seja 'analises'.

    Isto eh, se o arquivo tem <KpiMetricsPanel> dentro de um bloco
    tab === X para X != 'analises', o teste falha.

    A unica renderizacao condicional de <KpiMetricsPanel> permitida
    eh dentro de tab === 'analises'.
    """
    erros: list[str] = []

    for label, path in [
        ("FinanceiroRoom", FINANCEIRO_ROOM_PATH),
        ("ComprasRoom", COMPRAS_ROOM_PATH),
        ("ClientesRoom", CLIENTES_ROOM_PATH),
    ]:
        source = _read_text(path)
        matches = re.findall(
            r"tab\s*===\s*['\"]([^'\"]+)['\"].*?<KpiMetricsPanel\s",
            source,
            re.DOTALL,
        )
        for tab_name in matches:
            if tab_name != "analises":
                erros.append(
                    f"{label}.tsx renderiza <KpiMetricsPanel> dentro da tab "
                    f"'{tab_name}', mas so deveria renderizar na tab 'analises'."
                )

    if erros:
        pytest.fail("\n".join(erros))
