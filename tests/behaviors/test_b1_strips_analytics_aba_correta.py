"""RED test para o behavior B-1 — Strips de analytics SOMENTE na aba "Análises".

GOAL:
    Validar que a feature de posicionar a `<KpiMetricsPanel />` exclusivamente
    dentro da aba `analises` de cada sala (FinanceiroRoom, ComprasRoom,
    ClientesRoom) **NAO esta implementada** no estado atual do repositorio.

    O behavior B-1 (a ser entregue em fase GREEN) deve:
      1) Importar `KpiMetricsPanel` do caminho
         '../../components/shared/KpiMetricsPanel' em cada sala.
      2) Declarar uma tab `analises` no `type Tab` da sala.
      3) Renderizar `<KpiMetricsPanel />` SOMENTE dentro de um bloco
         condicional `tab === 'analises'`.

BEHAVIOR:
    B-1 — Strips de analytics posicionadas corretamente (BKL-018 + BKL-030):
    KpiMetricsPanel aparece SOMENTE na aba "Análises" (ou equivalente) de
    cada sala. Quando clicado, carrega os context metrics corretos. NAO
    aparece em outras abas.

    **Estado atual (RED):** nenhum dos 3 pontos esta implementado para
    FinanceiroRoom / ComprasRoom / ClientesRoom. O componente
    `KpiMetricsPanel` existe em `apps/blu_v3/src/components/shared/`
    mas nenhuma dessas tres salas o importa.

AC (Acceptance Criteria):
    AC#1 — Para CADA uma das 3 salas (FinanceiroRoom, ComprasRoom,
           ClientesRoom):
             a) importa `KpiMetricsPanel` de
                '../../components/shared/KpiMetricsPanel';
             b) `type Tab` da sala inclui o literal 'analises';
             c) `<KpiMetricsPanel>` eh renderizado dentro de um bloco
                condicional `tab === 'analises'`.

    Os 3 checks sao cumulativos. Falha de qualquer um dos 3 para
    qualquer sala resulta em pytest.fail() com mensagem em pt-BR.

Estado atual: RED — todas as 3 salas violam todos os 3 checks.
- Nenhuma das salas importa `KpiMetricsPanel`.
- Nenhuma das salas declara 'analises' em `type Tab`.
- Nenhuma das salas renderiza `<KpiMetricsPanel>` dentro de
  `tab === 'analises'`.

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

ROOM_FILES: list[tuple[str, Path]] = [
    (
        "FinanceiroRoom",
        REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "FinanceiroRoom.tsx",
    ),
    (
        "ComprasRoom",
        REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "ComprasRoom.tsx",
    ),
    (
        "ClientesRoom",
        REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app" / "ClientesRoom.tsx",
    ),
]


# ── Override do root conftest (teste puramente estatico) ──────────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Substitui o fixture de limpeza do root conftest — este teste eh
    pura inspecao de arquivos, sem necessidade de teardown no Supabase.
    """
    yield


# ── Helpers de inspecao do TypeScript ─────────────────────────────────────────


def _read_text(path: Path) -> str:
    """Le o arquivo e devolve o conteudo como string unica."""
    assert path.exists(), (
        f"Arquivo nao encontrado: {path.relative_to(REPO_ROOT)}.  "
        f"O behavior B-1 (strips de analytics) exige que este "
        f"arquivo exista no repositorio."
    )
    return path.read_text(encoding="utf-8")


def _has_kpi_import(source: str) -> bool:
    """Retorna True se o arquivo importa KpiMetricsPanel do caminho esperado.

    Esperado:
        from '../../components/shared/KpiMetricsPanel' import KpiMetricsPanel
    ou equivalente (aspas simples/duplas, com ou sem espacos).
    """
    return bool(
        re.search(
            r"from\s+['\"]\.\./\.\./components/shared/KpiMetricsPanel['\"]"
            r"\s+import\s+KpiMetricsPanel",
            source,
        )
    )


def _type_tab_includes_analises(source: str) -> bool:
    """Retorna True se o `type Tab` da sala inclui o literal 'analises'.

    Procura por uma declaracao de `type Tab = ... 'analises' ...` (em
    barra vertical, ou seja, dentro de uma union).
    """
    match = re.search(r"type\s+Tab\s*=\s*([^\n;]+)", source)
    if not match:
        return False
    tab_union = match.group(1)
    return bool(re.search(r"['\"]analises['\"]", tab_union))


def _has_kpi_metrics_panel_jsx(source: str) -> bool:
    """Retorna True se o arquivo contem `<KpiMetricsPanel ...>` no JSX."""
    return bool(re.search(r"<KpiMetricsPanel\s", source))


def _has_kpi_metrics_panel_in_analises_tab(source: str) -> bool:
    """Retorna True se ha `<KpiMetricsPanel>` dentro de um bloco com
    `tab === 'analises'`.

    Procura o padrao `tab === 'analises'` seguido (em qualquer distancia)
    pela tag `<KpiMetricsPanel`.
    """
    return bool(
        re.search(
            r"tab\s*===\s*['\"]analises['\"].*?<KpiMetricsPanel\s",
            source,
            re.DOTALL,
        )
    )


# ── AC#1 — Strips de analytics SOMENTE na aba 'analises' ────────────────────


def test_b1_ac1_strips_only_in_analises_tab():
    """AC#1: Para CADA uma das 3 salas (FinanceiroRoom, ComprasRoom,
    ClientesRoom) o `<KpiMetricsPanel />` deve estar posicionado
    EXCLUSIVAMENTE na aba 'analises'.

    Para cada sala, valida tres invariantes:
        (1) importa `KpiMetricsPanel` de
            '../../components/shared/KpiMetricsPanel';
        (2) `type Tab` da sala inclui o literal 'analises';
        (3) `<KpiMetricsPanel />` eh renderizado dentro de um bloco
            condicional `tab === 'analises'`.

    Estado atual (RED): nenhuma das 3 salas satisfaz nenhum dos 3 checks.
    O teste falha com pytest.fail() listando TODAS as violacoes
    encontradas (uma mensagem por sala) em pt-BR.
    """
    erros: list[str] = []

    for label, path in ROOM_FILES:
        source = _read_text(path)

        has_import = _has_kpi_import(source)
        has_tab = _type_tab_includes_analises(source)
        has_panel_jsx = _has_kpi_metrics_panel_jsx(source)
        has_panel_in_tab = _has_kpi_metrics_panel_in_analises_tab(source)

        if has_import and has_tab and has_panel_in_tab:
            continue  # sala OK — GREEN para esta sala

        # Sala em RED — acumula violacoes detalhadas em pt-BR
        sala_erros: list[str] = [f"{label}.tsx:"]

        if not has_import:
            sala_erros.append(
                f"  - NAO importa KpiMetricsPanel de "
                f"'../../components/shared/KpiMetricsPanel'.  "
                f"Esperado: "
                f"import KpiMetricsPanel from '../../components/shared/KpiMetricsPanel'"
            )

        if not has_tab:
            sala_erros.append(
                f"  - O `type Tab` da sala NAO inclui o literal 'analises'.  "
                f"Esperado: type Tab = ... | 'analises' | ...  "
                f"(a sala precisa de uma aba dedicada para analytics)"
            )

        if not has_panel_jsx:
            sala_erros.append(
                f"  - NAO renderiza <KpiMetricsPanel> em lugar nenhum.  "
                f"Esperado: <KpiMetricsPanel ... /> dentro do bloco "
                f"`tab === 'analises'`"
            )
        elif not has_panel_in_tab:
            sala_erros.append(
                f"  - Renderiza <KpiMetricsPanel> mas NAO dentro de um bloco "
                f"condicional `tab === 'analises'`.  "
                f"Esperado: o <KpiMetricsPanel> deve aparecer SOMENTE "
                f"dentro do bloco da aba 'analises' (nao em outras abas)"
            )

        erros.append("\n".join(sala_erros))

    if erros:
        pytest.fail(
            "B-1 (strips de analytics SOMENTE na aba 'analises') NAO esta "
            "implementado.  Violacoes encontradas:\n\n"
            + "\n\n".join(erros)
        )
