"""RED test para behavior B-1 — Analytics strip FORA de qualquer tab (BKL-018, BKL-030).

GOAL:
    Verificar que o bloco de analytics inline (anl-hd + period pills + anl-body)
    no FinanceiroRoom.tsx esta atualmente FORA de qualquer bloco condicional
    `tab === 'X'`, ou seja, aparece em TODAS as abas — violando o requisito
    BKL-018/BKL-030 de que os analytics devem estar SOMENTE na aba "Análises".

BEHAVIOR:
    B-1 — Analytics strip nas abas "Análises" (BKL-018, BKL-030):
    O KpiMetricsPanel (ou bloco analytics inline) aparece SOMENTE dentro da aba
    "Análises". NAO aparece em outras abas. NAO fica solto no .pb.

AC (Acceptance Criteria):
    AC#1 — FinanceiroRoom.tsx: type Tab NAO inclui 'analises'.
            O bloco anl-hd/anl-body esta solto no .pb, fora de qualquer tab.
            Period pills (30d/90d/1y) estao fora de qualquer tab.
    AC#2 — ComprasRoom.tsx: type Tab NAO inclui 'analises'.
    AC#3 — ClientesRoom.tsx: type Tab NAO inclui 'analises'.

Estado atual (RED):
    - FinanceiroRoom.tsx type Tab = 'decisoes' | 'compromissos' | ... (sem 'analises')
    - Linhas 576-613 (anl-hd + period pills) e linhas 614-700 (anl-body) estao
      diretamente no escopo do .pb, DEPOIS do fechamento da tab config (linha 575)
      e ANTES do fechamento do .pb (linha 701).
    - Nao estao encapsulados em nenhum bloco condicional `tab ===`.
    - ComprasRoom.tsx type Tab = 'decisoes' | 'tarefas' | 'historico' | 'config'
    - ClientesRoom.tsx type Tab = 'followup' | 'ativos' | 'historico' | 'config'

Anti-Goals:
    1. NAO modificar codigo de producao (teste estatico apenas).
    2. NAO executar/parsear TypeScript — so inspecao textual com regex.
    3. NAO usar mocks, DB, browser testing, jsdom.
    4. NAO quebrar funcionalidade existente.
"""

import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

FINANCEIRO_ROOM = REPO_ROOT / "apps/blu_v3/src/pages/app/FinanceiroRoom.tsx"
COMPRAS_ROOM = REPO_ROOT / "apps/blu_v3/src/pages/app/ComprasRoom.tsx"
CLIENTES_ROOM = REPO_ROOT / "apps/blu_v3/src/pages/app/ClientesRoom.tsx"


def _read_text(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _has_analises_in_tab_type(source: str) -> bool:
    """Verifica se o type Tab contém 'analises'."""
    # Procura: type Tab = ... 'analises' | ...
    m = re.search(
        r"type\s+Tab\s*=\s*([^;]+)",
        source,
    )
    if not m:
        return False
    tab_def = m.group(1)
    return "'analises'" in tab_def or '"analises"' in tab_def


def _has_analises_tab_mapping(source: str) -> bool:
    """Verifica se o array de tabs no map contém 'analises'."""
    # Procura algo como: (['decisoes', 'analises', ...] as Tab[]).map(...)
    m = re.search(
        r"\(\s*\[([^\]]+)\]\s*as\s+Tab\[\]\s*\)\s*\.\s*map\s*\(",
        source,
        re.DOTALL,
    )
    if not m:
        return False
    tab_array = m.group(1)
    return "'analises'" in tab_array or '"analises"' in tab_array


def _has_anl_hd_inside_tab_conditional(source: str) -> bool:
    """Verifica se anl-hd esta dentro de um bloco tab === 'X'.

    Retorna True se encontrar `tab === 'algo'` antes de anl-hd sem fechar
    escopo. Usamos heuristica: verificar se ha um padrao
    `tab === '...' && (... anl-hd ...)` ou `{tab === '...' && (...)}`
    que contem a string anl-hd.
    """
    # Procura: `tab === 'ALGO'` seguido por `anl-hd` sem `</div>` no meio
    # que feche o escopo do condicional
    pattern = re.compile(
        r'tab\s*===\s*[\'"]([^\'"]+)[\'"]\s*&&[\s\S]{0,500}?anl-hd',
        re.DOTALL,
    )
    m = pattern.search(source)
    return m is not None


def _has_period_pills_inside_tab_conditional(source: str) -> bool:
    """Verifica se os period pills (30d/90d/1y) estao dentro de tab conditional."""
    pattern = re.compile(
        r'tab\s*===\s*[\'"]([^\'"]+)[\'"]\s*&&[\s\S]{0,500}?30d[\s\S]{0,200}?90d[\s\S]{0,200}?1y',
        re.DOTALL,
    )
    m = pattern.search(source)
    return m is not None


def _has_anl_body_inside_tab_conditional(source: str) -> bool:
    """Verifica se anl-body esta dentro de tab conditional."""
    pattern = re.compile(
        r'tab\s*===\s*[\'"]([^\'"]+)[\'"]\s*&&[\s\S]{0,500}?anl-body',
        re.DOTALL,
    )
    m = pattern.search(source)
    return m is not None


# ═══════════════════════════════════════════════════════════════════════════════
# AC#1 — FinanceiroRoom
# ═══════════════════════════════════════════════════════════════════════════════


def test_b1_ac1_financeiro_analytics_fora_de_tab():
    """AC#1: FinanceiroRoom — Tab type NAO tem 'analises'; anl-hd/anl-body
    aparecem fora de qualquer bloco condicional (TRUE RED).

    Estado atual: type Tab = 'decisoes' | 'compromissos' | 'tarefas' |
    'historico' | 'config' (sem 'analises'). Bloco analytics (anl-hd + pills +
    anl-body) aparece solto no .pb, fora de qualquer tab.
    """
    source = _read_text(FINANCEIRO_ROOM)
    erros: list[str] = []

    # 1. Tab type NAO tem 'analises' (RED = bom, eh o estado atual)
    if _has_analises_in_tab_type(source):
        erros.append(
            "FinanceiroRoom.tsx: type Tab JA inclui 'analises'. "
            "Estado atual (RED) deveria NAO ter a tab 'analises'."
        )

    # 2. Tab mapping NAO tem 'analises'
    if _has_analises_tab_mapping(source):
        erros.append(
            "FinanceiroRoom.tsx: o array de tabs no .map() JA inclui 'analises'. "
            "Estado atual (RED) deveria NAO ter a tab no mapping."
        )

    # 3. anl-hd NAO esta dentro de bloco tab conditional (deve estar solto)
    if _has_anl_hd_inside_tab_conditional(source):
        erros.append(
            "FinanceiroRoom.tsx: anl-hd esta DENTRO de um bloco condicional "
            "`tab === 'X'`. Estado atual (RED) deveria estar FORA (solto no .pb)."
        )

    # 4. Period pills NAO estao dentro de bloco tab conditional
    if _has_period_pills_inside_tab_conditional(source):
        erros.append(
            "FinanceiroRoom.tsx: period pills (30d/90d/1y) estao DENTRO de um "
            "bloco condicional. Estado atual (RED) deveria estar FORA."
        )

    # 5. anl-body NAO esta dentro de bloco tab conditional
    if _has_anl_body_inside_tab_conditional(source):
        erros.append(
            "FinanceiroRoom.tsx: anl-body esta DENTRO de um bloco condicional. "
            "Estado atual (RED) deveria estar FORA."
        )

    if erros:
        pytest.fail("\n".join(erros))
    else:
        pytest.fail(
            "FinanceiroRoom.tsx: ESTADO ATUAL (RED) — type Tab NAO tem 'analises' "
            "e o bloco analytics (anl-hd + pills + anl-body) esta FORA de qualquer "
            "bloco condicional `tab === 'X'`, ou seja, aparece em TODAS as abas. "
            "GREEN esperado: type Tab incluir 'analises' e o bloco analytics estar "
            "DENTRO de `tab === 'analises'`."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AC#2 — ComprasRoom
# ═══════════════════════════════════════════════════════════════════════════════


def test_b1_ac2_compras_analytics_fora_de_tab():
    """AC#2: ComprasRoom — type Tab NAO tem 'analises' (TRUE RED).

    Estado atual: type Tab = 'decisoes' | 'tarefas' | 'historico' | 'config'
    (sem 'analises').
    """
    source = _read_text(COMPRAS_ROOM)
    erros: list[str] = []

    if _has_analises_in_tab_type(source):
        erros.append(
            "ComprasRoom.tsx: type Tab JA inclui 'analises'. "
            "Estado atual (RED) deveria NAO ter 'analises'."
        )

    if _has_analises_tab_mapping(source):
        erros.append(
            "ComprasRoom.tsx: array de tabs JA inclui 'analises'. "
            "Estado atual (RED) deveria NAO ter a tab."
        )

    if erros:
        pytest.fail("\n".join(erros))
    else:
        pytest.fail(
            "ComprasRoom.tsx: ESTADO ATUAL (RED) — type Tab = 'decisoes' | "
            "'tarefas' | 'historico' | 'config' (sem 'analises'). "
            "GREEN esperado: type Tab incluir 'analises'."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AC#3 — ClientesRoom
# ═══════════════════════════════════════════════════════════════════════════════


def test_b1_ac3_clientes_analytics_fora_de_tab():
    """AC#3: ClientesRoom — type Tab NAO tem 'analises' (TRUE RED).

    Estado atual: type Tab = 'followup' | 'ativos' | 'historico' | 'config'
    (sem 'analises').
    """
    source = _read_text(CLIENTES_ROOM)
    erros: list[str] = []

    if _has_analises_in_tab_type(source):
        erros.append(
            "ClientesRoom.tsx: type Tab JA inclui 'analises'. "
            "Estado atual (RED) deveria NAO ter 'analises'."
        )

    if _has_analises_tab_mapping(source):
        erros.append(
            "ClientesRoom.tsx: array de tabs JA inclui 'analises'. "
            "Estado atual (RED) deveria NAO ter a tab."
        )

    if erros:
        pytest.fail("\n".join(erros))
    else:
        pytest.fail(
            "ClientesRoom.tsx: ESTADO ATUAL (RED) — type Tab = 'followup' | "
            "'ativos' | 'historico' | 'config' (sem 'analises'). "
            "GREEN esperado: type Tab incluir 'analises'."
        )
