"""RED test for behavior — Unified Tab Navigation Schema between rooms.

GOAL:
    Padronizar o esquema de abas (tabs) entre todas as salas, eliminando
    nomes divergentes e criando um schema consistente via constante
    compartilhada.

BEHAVIOR:
    Um schema de tabs padrao (decisoes, tarefas, historico, config) deve
    ser definido em uma constante/config compartilhada. Cada sala pode
    adicionar tabs extras especificas, mas os nomes comuns devem ser
    consistentes entre todas as salas.

    Inconsistencias atuais:
        - ComprasRoom:   decisoes | tarefas | historico | config         ✓
        - FinanceiroRoom: decisoes | compromissos | tarefas | historico   ✓
                         | config
        - AgendaRoom:    gantt | hoje | pendentes | config               ✗ (falta decisoes, historico)
        - EstrategiaRoom: decisoes | analises | historico | config       ✗ ('analises' nao eh tab padrao)
        - ClientesRoom:  followup | ativos | historico | config          ✗ ('followup' deveria ser 'decisoes')

    Schema-alvo:
        - Decisoes   (presente em todas as salas com approvals)
        - Tarefas    (onde houver execucao de rotinas)
        - Historico  (presente em todas as salas)
        - Conteudo-especifico (ex: Compromissos no financeiro)
        - Config     (presente em todas as salas)

AC (Acceptance Criteria):
    AC#1 — Shared constant/config file exists at
           apps/blu_v3/src/utils/tabSchema.ts exporting STANDARD_TABS
           with 'decisoes', 'tarefas', 'historico', 'config'
    AC#2 — All rooms use consistent common tab names; no room uses
           'followup', 'analises', 'gantt', 'hoje', or 'pendentes' in
           place of standard tab names
    AC#3 — FinanceiroRoom has both 'tarefas' AND 'compromissos' as
           separate entries in its Tab type (compromissos is extra, not
           replacement)
    AC#4 — AgendaRoom Tab type includes 'decisoes' and 'historico' in
           addition to its room-specific extras (gantt, hoje, pendentes)
    AC#5 — All 5 rooms (Compras, Financeiro, Agenda, Estrategia,
           Clientes) have at least 'decisoes', 'historico', 'config' in
           their Tab type

Estado atual: RED — shared tab config nao existe e as salas tem nomes
divergentes.

Anti-Goals (must NOT be violated):
    1. Nao remover tabs especificas existentes nas salas
    2. Nao alterar a estrutura de renderizacao das salas (rtabs divs)
    3. Nao quebrar a navegacao entre salas (go(), goWithTab())
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Paths ─────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

TAB_CONFIG_PATH = REPO_ROOT / "apps" / "blu_v3" / "src" / "utils" / "tabSchema.ts"

ROOM_PAGES_DIR = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app"

EXPECTED_ROOMS = [
    "ComprasRoom.tsx",
    "FinanceiroRoom.tsx",
    "AgendaRoom.tsx",
    "EstrategiaRoom.tsx",
    "ClientesRoom.tsx",
]

STANDARD_TABS = ["decisoes", "tarefas", "historico", "config"]


# ── Source-level helpers ───────────────────────────────────────────────────


def _read_source(path: Path) -> str:
    assert path.exists(), f"Source file not found: {path}"
    return path.read_text(encoding="utf-8")


def _extract_tab_union(source: str) -> list[str]:
    """Extract tab names from a `type Tab = 'a' | 'b' | 'c'` declaration."""
    m = re.search(
        r"type\s+Tab\s*=\s*((?:'\w+'\s*\|\s*)*'\w+')",
        source,
    )
    if not m:
        return []
    # Extract all single-quoted words
    return re.findall(r"'(\w+)'", m.group(1))


def _file_has_import_from(source: str, names: list[str], module_hint: str) -> dict[str, bool]:
    """Check if source imports specific named exports from a module path containing module_hint."""
    import_block = re.search(
        rf"import\s*{{([^}}]+)}}\s*from\s*['\"][^'\"]*{re.escape(module_hint)}[^'\"]*['\"]",
        source,
        re.DOTALL,
    )
    if not import_block:
        return {n: False for n in names}
    block = import_block.group(1)
    return {n: re.search(rf"\b{re.escape(n)}\b", block) is not None for n in names}


# ── Tests ─────────────────────────────────────────────────────────────────


def test_ac1_shared_tab_config_exists():
    """AC#1 — Shared constant file must exist with STANDARD_TABS.

    Um arquivo apps/blu_v3/src/utils/tabSchema.ts deve existir e exportar
    uma constante STANDARD_TABS contendo os tabs padrao: decisoes, tarefas,
    historico, config.
    """
    assert TAB_CONFIG_PATH.exists(), (
        "RED — AC#1: Arquivo compartilhado de config de tabs nao encontrado.\n"
        f"  Esperado: {TAB_CONFIG_PATH}\n"
        "  O Coder deve criar apps/blu_v3/src/utils/tabSchema.ts\n"
        "  exportando `STANDARD_TABS = ['decisoes', 'tarefas', 'historico', 'config'] as const`"
    )

    source = TAB_CONFIG_PATH.read_text(encoding="utf-8")

    # Check that STANDARD_TABS is exported
    assert re.search(r"export\s+(const|let|var)\s+STANDARD_TABS\b", source), (
        "RED — AC#1: STANDARD_TABS nao foi exportada do arquivo de config.\n"
        f"  Esperado: export const STANDARD_TABS = [...] as const"
    )

    # Check that it contains all 4 standard tabs
    for tab in STANDARD_TABS:
        assert re.search(rf"['\"]{tab}['\"]", source), (
            f"RED — AC#1: Tab padrao '{tab}' nao encontrado em STANDARD_TABS.\n"
            f"  Esperado: STANDARD_TABS contenha '{tab}'"
        )


def test_ac2_consistent_common_tab_names():
    """AC#2 — All rooms use consistent common tab names.

    Nenhuma sala deve usar nomes divergentes para os tabs padrao:
    - 'followup' (ClientesRoom) deve ser substituido por 'decisoes'
    - 'analises' (EstrategiaRoom) deve ser padronizado ou virar tab extra
    - 'gantt'/'hoje'/'pendentes' (AgendaRoom) devem ser extras,
      nao substituir decisoes/historico
    """
    findings: list[str] = []

    for room_file in EXPECTED_ROOMS:
        path = ROOM_PAGES_DIR / room_file
        source = _read_source(path)
        tabs = _extract_tab_union(source)

        # Check for non-standard tab names that occupy standard slots
        non_standard_in_standard_slot = {
            "followup": "decisoes",
            "analises": None,  # Could be extra or need renaming
        }

        for bad_name, expected in non_standard_in_standard_slot.items():
            if bad_name in tabs:
                if expected:
                    findings.append(
                        f"  {room_file}: usa '{bad_name}' no lugar de '{expected}'"
                    )
                else:
                    findings.append(
                        f"  {room_file}: usa '{bad_name}' como tab padrao"
                    )

        # AgendaRoom specific: check that gantt/hoje/pendentes are extra
        if room_file == "AgendaRoom.tsx":
            if "gantt" in tabs or "hoje" in tabs or "pendentes" in tabs:
                # These are only problems if the room is MISSING standard tabs
                # (handled by AC5) — for AC2 we just check consistency
                pass

    assert not findings, (
        "RED — AC#2: Nomes de tabs inconsistentes encontrados:\n"
        + "\n".join(findings) + "\n\n"
        "O Coder deve padronizar os nomes dos tabs comuns:\n"
        "  - ClientesRoom: substituir 'followup' por 'decisoes'\n"
        "  - EstrategiaRoom: decisoes deve ser tab padrao, analises extra\n"
        "  - AgendaRoom: decisoes e historico devem ser tabs padrao"
    )


def test_ac3_financeiro_has_tarefas_and_compromissos():
    """AC#3 — FinanceiroRoom has both 'tarefas' AND 'compromissos'.

    'Compromissos' deve ser um tab extra no Financeiro, nao substituir
    'Tarefas'. Ambos devem existir como entradas separadas no tipo Tab.
    """
    path = ROOM_PAGES_DIR / "FinanceiroRoom.tsx"
    source = _read_source(path)
    tabs = _extract_tab_union(source)

    assert "tarefas" in tabs, (
        "RED — AC#3: FinanceiroRoom nao tem 'tarefas' no tipo Tab.\n"
        "'Compromissos' substituiu 'Tarefas' — ambos devem coexistir."
    )

    assert "compromissos" in tabs, (
        "RED — AC#3: FinanceiroRoom nao tem 'compromissos' no tipo Tab.\n"
        "Compromissos deve ser um tab extra no Financeiro."
    )


def test_ac4_agenda_has_standard_tabs_plus_extras():
    """AC#4 — AgendaRoom has 'decisoes' and 'historico' (standard) plus extras.

    A AgendaRoom deve incluir os tabs padrao 'decisoes' e 'historico'
    alem dos seus extras especificos (gantt, hoje, pendentes).
    """
    path = ROOM_PAGES_DIR / "AgendaRoom.tsx"
    source = _read_source(path)
    tabs = _extract_tab_union(source)

    assert "decisoes" in tabs, (
        "RED — AC#4: AgendaRoom nao tem 'decisoes' no tipo Tab.\n"
        "A Agenda precisa de 'decisoes' como tab padrao (tem approvals)."
    )

    assert "historico" in tabs, (
        "RED — AC#4: AgendaRoom nao tem 'historico' no tipo Tab.\n"
        "Toda sala precisa de 'historico'."
    )

    # 'config' is already present — verify it
    assert "config" in tabs, (
        "RED — AC#4: AgendaRoom nao tem 'config' no tipo Tab.\n"
        "Toda sala precisa de 'config'."
    )


def test_ac5_all_rooms_have_decisoes_historico_config():
    """AC#5 — All 5 rooms have at least decisoes/historico/config.

    Toda sala (Compras, Financeiro, Agenda, Estrategia, Clientes) deve
    ter pelo menos 'decisoes', 'historico' e 'config' no tipo Tab.
    """
    missing: list[str] = []

    for room_file in EXPECTED_ROOMS:
        path = ROOM_PAGES_DIR / room_file
        source = _read_source(path)
        tabs = _extract_tab_union(source)

        room_missing = []
        for required in ["decisoes", "historico", "config"]:
            if required not in tabs:
                room_missing.append(required)

        if room_missing:
            missing.append(f"  {room_file}: faltando {room_missing}")

    assert not missing, (
        "RED — AC#5: Salas com tabs padrao faltando:\n"
        + "\n".join(missing) + "\n\n"
        "Todas as 5 salas devem ter pelo menos decisoes, historico e config.\n"
        "Corrigir:\n"
        "  - AgendaRoom: adicionar 'decisoes' e 'historico'\n"
        "  - ClientesRoom: adicionar 'decisoes' (ou renomear 'followup')\n"
        "  - Demais salas: OK"
    )
