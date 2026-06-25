"""RED test for behavior B-2 — Strips de analytics na aba correta (NAO implementado).

GOAL:
    Garantir que o behavior de posicionar KpiMetricsPanel (e demais strips de
    analytics) **dentro de uma aba "analises"** das salas FinanceiroRoom,
    ComprasRoom e ClientesRoom esteja implementado de forma consistente,
    incluindo um chip de bottom strip que navega para a aba "analises".

BEHAVIOR:
    B-2 — Strips de analytics na aba correta:
    Cada uma das tres salas (FinanceiroRoom, ComprasRoom, ClientesRoom) DEVE:
      1) Ter o type `Tab` incluindo o valor literal 'analises'.
      2) Renderizar <KpiMetricsPanel> (ou outro analytics) DENTRO de um bloco
         condicional `tab === 'analises'`.
      3) Ter pelo menos um bottom strip (`.nums-chip`) com
         `onClick={() => setTab('analises')}` para que o usuario possa
         navegar para a aba de analytics a partir do strip inferior.

AC (Acceptance Criteria):
    AC#1 — FinanceiroRoom.tsx: type Tab inclui 'analises'; <KpiMetricsPanel>
            renderizado dentro de tab === 'analises'; bottom strip com
            setTab('analises') presente.
    AC#2 — ComprasRoom.tsx: type Tab inclui 'analises'; <KpiMetricsPanel>
            renderizado dentro de tab === 'analises'; bottom strip com
            setTab('analises') presente.
    AC#3 — ClientesRoom.tsx: type Tab inclui 'analises'; <KpiMetricsPanel>
            renderizado dentro de tab === 'analises'; bottom strip com
            setTab('analises') presente.

ESTADO ATUAL (RED):
    - FinanceiroRoom.tsx: type Tab = 'decisoes' | 'compromissos' | 'tarefas' |
      'historico' | 'config' (sem 'analises'); nenhum <KpiMetricsPanel>;
      bottom strip chama setTab('tarefas') e setTab('historico').
    - ComprasRoom.tsx: type Tab = 'decisoes' | 'tarefas' | 'historico' |
      'config' (sem 'analises'); nenhum <KpiMetricsPanel>; bottom strip
      chama setTab('tarefas').
    - ClientesRoom.tsx: type Tab = 'followup' | 'ativos' | 'historico' |
      'config' (sem 'analises'); nenhum <KpiMetricsPanel>; bottom strip
      chama setTab('config').

ESTADO ALVO (GREEN):
    - Em cada sala, type Tab deve incluir 'analises' (ex.: 'decisoes' |
      'analises' | 'historico' | 'config' ou variacoes com 5 valores).
    - Cada sala deve ter um bloco {tab === 'analises' && (... analytics ...)}
      que renderiza <KpiMetricsPanel metrics={...} />.
    - Cada sala deve ter pelo menos um bottom strip `.nums-chip` com
      onClick={() => setTab('analises')}.

Anti-Goals:
    1. NAO remover abas existentes (decisoes, historico, config, etc.).
    2. NAO quebrar filtros/logica de cada sala.
    3. NAO introduzir mocks ou dependencias de DB — apenas inspecao textual
       com regex sobre o codigo-fonte.
    4. NAO modificar codigo de producao — este teste deve ser TRUE RED.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

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


# ── Override do root conftest (teste puramente estatico) ────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste eh
    pura inspecao de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Source-level helpers ───────────────────────────────────────────────────


def _read_source(path: Path) -> str:
    """Le o codigo-fonte TSX como texto puro."""
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _extract_type_tab(source: str) -> str | None:
    """Retorna a declaracao completa do type Tab, ou None se nao existir.

    Aceita quebras de linha no meio do union type (ex.: um valor por linha).
    """
    match = re.search(r"type\s+Tab\s*=", source)
    if not match:
        return None
    start = match.start()
    # O type pode estar em uma unica linha ou em multiplas linhas ate o ';'
    # ou ate a proxima declaracao.  Varre ate o primeiro ';' que esteja
    # fora de strings (heuristica simples: para no primeiro ';' apos o '=').
    eq_idx = source.find("=", start)
    if eq_idx == -1:
        return None
    end = source.find(";", eq_idx)
    if end == -1:
        end = start + 400
    return source[start:end].strip()


def _tab_type_includes_analises(source: str) -> tuple[bool, str | None]:
    """Retorna (True, decl) se o type Tab inclui 'analises'."""
    decl = _extract_type_tab(source)
    if decl is None:
        return False, None
    return "'analises'" in decl, decl


def _has_kpi_panel_in_analises_tab(source: str) -> bool:
    """Retorna True se ha <KpiMetricsPanel> dentro de um bloco
    `tab === 'analises'`.
    """
    return bool(
        re.search(
            r"tab\s*===\s*['\"]analises['\"].*?<KpiMetricsPanel\s",
            source,
            re.DOTALL,
        )
    )


def _has_kpi_panel_anywhere(source: str) -> bool:
    """Retorna True se o arquivo contem <KpiMetricsPanel ...> em qualquer
    lugar (util para detectar renderizacao na aba errada).
    """
    return bool(re.search(r"<KpiMetricsPanel\s", source))


def _has_bottom_strip_analises(source: str) -> bool:
    """Retorna True se ha pelo menos um bottom strip `.nums-chip` com
    onClick que chama setTab('analises').
    """
    # Procura .nums-chip com onClick que contenha setTab('analises') no
    # mesmo bloco.  Padrao flexivel: tolera whitespace e atributos
    # adicionais entre .nums-chip e o onClick.
    pattern = (
        r'className\s*=\s*["\']nums-chip["\'][^>]*?'
        r'onClick\s*=\s*\{\s*\(\s*\)\s*=>\s*setTab\s*\(\s*[\'"]analises[\'"]\s*\)\s*\}'
    )
    return bool(re.search(pattern, source, re.DOTALL))


# ── AC#1 — FinanceiroRoom.tsx ──────────────────────────────────────────────


def test_b2_ac1_financeiro_aba_analises_com_strip() -> None:
    """AC#1: FinanceiroRoom.tsx DEVE ter type Tab incluindo 'analises',
    renderizar <KpiMetricsPanel> dentro do bloco `tab === 'analises'`, e
    ter um bottom strip `.nums-chip` com `setTab('analises')`.

    Falha (RED) enquanto qualquer uma destas condicoes nao for satisfeita.
    """
    source = _read_source(FINANCEIRO_ROOM_PATH)

    has_analises_in_tab, tab_decl = _tab_type_includes_analises(source)
    has_analises_panel = _has_kpi_panel_in_analises_tab(source)
    has_strip = _has_bottom_strip_analises(source)

    if has_analises_in_tab and has_analises_panel and has_strip:
        return  # GREEN — implementado

    errors: list[str] = []

    if tab_decl is None:
        errors.append(
            "FinanceiroRoom.tsx NAO possui a declaracao 'type Tab = ...'.  "
            "Esperado: type Tab = 'decisoes' | 'analises' | 'historico' | 'config' "
            "(ou variacao com 'analises' incluido)."
        )
    elif not has_analises_in_tab:
        errors.append(
            f"FinanceiroRoom.tsx: type Tab NAO inclui 'analises'.  "
            f"Atual: {tab_decl}\n"
            f"  Esperado: incluir 'analises' no union type, ex.:\n"
            f"    type Tab = 'decisoes' | 'analises' | 'historico' | 'config'\n"
            f"  O Coder deve adicionar ' | \"analises\"' ao type Tab."
        )

    if not _has_kpi_panel_anywhere(source):
        errors.append(
            "FinanceiroRoom.tsx NAO renderiza <KpiMetricsPanel> em lugar nenhum.  "
            "Esperado: <KpiMetricsPanel metrics={financeiroContextMetrics} /> "
            "dentro de um bloco condicional {tab === 'analises' && (...)}."
        )
    elif not has_analises_panel:
        errors.append(
            "FinanceiroRoom.tsx renderiza <KpiMetricsPanel> mas NAO dentro de "
            "um bloco `tab === 'analises'`.  "
            "Esperado: o <KpiMetricsPanel> deve aparecer SOMENTE na aba analises, "
            "em um padrao similar a:\n"
            "  {tab === 'analises' && (\n"
            "    <KpiMetricsPanel metrics={financeiroContextMetrics} />\n"
            "  )}"
        )

    if not has_strip:
        errors.append(
            "FinanceiroRoom.tsx NAO possui um bottom strip `.nums-chip` com "
            "`onClick={() => setTab('analises')}`.  "
            "Esperado: pelo menos um elemento com className='nums-chip' e "
            "onClick que chame setTab('analises'), ex.:\n"
            "  <div className='nums-chip' onClick={() => setTab('analises')} "
            "style={{ cursor: 'pointer' }}>\n"
            "    <div className='nums-head'>📊 Análises</div>\n"
            "    <div style={{ fontSize: 11, color: 'var(--mu)' }}>Ver aba Análises →</div>\n"
            "  </div>"
        )

    pytest.fail(
        "RED — AC#1 (FinanceiroRoom): uma ou mais condicoes nao foram "
        "satisfeitas.\n" + "\n".join(errors)
    )


# ── AC#2 — ComprasRoom.tsx ─────────────────────────────────────────────────


def test_b2_ac2_compras_aba_analises_com_strip() -> None:
    """AC#2: ComprasRoom.tsx DEVE ter type Tab incluindo 'analises',
    renderizar <KpiMetricsPanel> dentro do bloco `tab === 'analises'`, e
    ter um bottom strip `.nums-chip` com `setTab('analises')`.

    Falha (RED) enquanto qualquer uma destas condicoes nao for satisfeita.
    """
    source = _read_source(COMPRAS_ROOM_PATH)

    has_analises_in_tab, tab_decl = _tab_type_includes_analises(source)
    has_analises_panel = _has_kpi_panel_in_analises_tab(source)
    has_strip = _has_bottom_strip_analises(source)

    if has_analises_in_tab and has_analises_panel and has_strip:
        return  # GREEN — implementado

    errors: list[str] = []

    if tab_decl is None:
        errors.append(
            "ComprasRoom.tsx NAO possui a declaracao 'type Tab = ...'.  "
            "Esperado: type Tab = 'decisoes' | 'analises' | 'historico' | 'config' "
            "(ou variacao com 'analises' incluido)."
        )
    elif not has_analises_in_tab:
        errors.append(
            f"ComprasRoom.tsx: type Tab NAO inclui 'analises'.  "
            f"Atual: {tab_decl}\n"
            f"  Esperado: incluir 'analises' no union type, ex.:\n"
            f"    type Tab = 'decisoes' | 'analises' | 'historico' | 'config'\n"
            f"  O Coder deve adicionar ' | \"analises\"' ao type Tab."
        )

    if not _has_kpi_panel_anywhere(source):
        errors.append(
            "ComprasRoom.tsx NAO renderiza <KpiMetricsPanel> em lugar nenhum.  "
            "Esperado: <KpiMetricsPanel metrics={comprasContextMetrics} /> "
            "dentro de um bloco condicional {tab === 'analises' && (...)}."
        )
    elif not has_analises_panel:
        errors.append(
            "ComprasRoom.tsx renderiza <KpiMetricsPanel> mas NAO dentro de "
            "um bloco `tab === 'analises'`.  "
            "Esperado: o <KpiMetricsPanel> deve aparecer SOMENTE na aba analises, "
            "em um padrao similar a:\n"
            "  {tab === 'analises' && (\n"
            "    <KpiMetricsPanel metrics={comprasContextMetrics} />\n"
            "  )}"
        )

    if not has_strip:
        errors.append(
            "ComprasRoom.tsx NAO possui um bottom strip `.nums-chip` com "
            "`onClick={() => setTab('analises')}`.  "
            "Esperado: pelo menos um elemento com className='nums-chip' e "
            "onClick que chame setTab('analises'), ex.:\n"
            "  <div className='nums-chip' onClick={() => setTab('analises')} "
            "style={{ cursor: 'pointer' }}>\n"
            "    <div className='nums-head'>📊 Análises</div>\n"
            "    <div style={{ fontSize: 11, color: 'var(--mu)' }}>Ver aba Análises →</div>\n"
            "  </div>"
        )

    pytest.fail(
        "RED — AC#2 (ComprasRoom): uma ou mais condicoes nao foram "
        "satisfeitas.\n" + "\n".join(errors)
    )


# ── AC#3 — ClientesRoom.tsx ────────────────────────────────────────────────


def test_b2_ac3_clientes_aba_analises_com_strip() -> None:
    """AC#3: ClientesRoom.tsx DEVE ter type Tab incluindo 'analises',
    renderizar <KpiMetricsPanel> dentro do bloco `tab === 'analises'`, e
    ter um bottom strip `.nums-chip` com `setTab('analises')`.

    Falha (RED) enquanto qualquer uma destas condicoes nao for satisfeita.
    """
    source = _read_source(CLIENTES_ROOM_PATH)

    has_analises_in_tab, tab_decl = _tab_type_includes_analises(source)
    has_analises_panel = _has_kpi_panel_in_analises_tab(source)
    has_strip = _has_bottom_strip_analises(source)

    if has_analises_in_tab and has_analises_panel and has_strip:
        return  # GREEN — implementado

    errors: list[str] = []

    if tab_decl is None:
        errors.append(
            "ClientesRoom.tsx NAO possui a declaracao 'type Tab = ...'.  "
            "Esperado: type Tab = 'followup' | 'analises' | 'historico' | 'config' "
            "(ou variacao com 'analises' incluido)."
        )
    elif not has_analises_in_tab:
        errors.append(
            f"ClientesRoom.tsx: type Tab NAO inclui 'analises'.  "
            f"Atual: {tab_decl}\n"
            f"  Esperado: incluir 'analises' no union type, ex.:\n"
            f"    type Tab = 'followup' | 'analises' | 'historico' | 'config'\n"
            f"  O Coder deve adicionar ' | \"analises\"' ao type Tab."
        )

    if not _has_kpi_panel_anywhere(source):
        errors.append(
            "ClientesRoom.tsx NAO renderiza <KpiMetricsPanel> em lugar nenhum.  "
            "Esperado: <KpiMetricsPanel metrics={clientesContextMetrics} /> "
            "dentro de um bloco condicional {tab === 'analises' && (...)}."
        )
    elif not has_analises_panel:
        errors.append(
            "ClientesRoom.tsx renderiza <KpiMetricsPanel> mas NAO dentro de "
            "um bloco `tab === 'analises'`.  "
            "Esperado: o <KpiMetricsPanel> deve aparecer SOMENTE na aba analises, "
            "em um padrao similar a:\n"
            "  {tab === 'analises' && (\n"
            "    <KpiMetricsPanel metrics={clientesContextMetrics} />\n"
            "  )}"
        )

    if not has_strip:
        errors.append(
            "ClientesRoom.tsx NAO possui um bottom strip `.nums-chip` com "
            "`onClick={() => setTab('analises')}`.  "
            "Esperado: pelo menos um elemento com className='nums-chip' e "
            "onClick que chame setTab('analises'), ex.:\n"
            "  <div className='nums-chip' onClick={() => setTab('analises')} "
            "style={{ cursor: 'pointer' }}>\n"
            "    <div className='nums-head'>📊 Análises</div>\n"
            "    <div style={{ fontSize: 11, color: 'var(--mu)' }}>Ver aba Análises →</div>\n"
            "  </div>"
        )

    pytest.fail(
        "RED — AC#3 (ClientesRoom): uma ou mais condicoes nao foram "
        "satisfeitas.\n" + "\n".join(errors)
    )
