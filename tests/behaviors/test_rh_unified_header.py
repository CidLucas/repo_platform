"""RED test for behavior RH — Unified Room Header (rh) pattern across all rooms.

GOAL:
    AC#1 — Every room renders ``<div className="rh">`` with the unified
    header sub-classes: ``rav`` (avatar), ``rn`` (room name),
    ``rd`` (room description) and ``ra`` (room actions — including the
    ``← Início`` back button and a primary ``+`` action button).

BEHAVIOR:
    RH — Unified Room Header (rh) pattern across all rooms.

    The pattern has already been adopted by 7 of 8 room pages in
    ``apps/blu_v3/src/pages/app/``:

        * ComprasRoom, FinanceiroRoom, AgendaRoom, EstrategiaRoom,
          ClientesRoom, DocumentosRoom, BibliotecaRoom.

    ``HomePage`` does NOT use the pattern (it still uses
    ``<div className="home-grid">``), so this test is currently RED.

AC (Acceptance Criteria):
    AC#1 — Every room — including HomePage — must render
           ``<div className="rh">`` with the four child classes
           (``rav + rn + rd + ra``), the ``← Início`` back button, and
           a primary action button that starts with ``+``.

Anti-Goals (must NOT be violated):
    1. NÃO remover a navegação ``← Início`` que volta para ``home``.
    2. NÃO duplicar a estrutura — apenas UM ``<div className="rh">`` por sala.
    3. NÃO alterar o conteúdo semântico (rav emoji, rn título, rd descrição).

Estado atual: RED — ``HomePage.tsx`` não tem ``<div className="rh">``.
Este teste parseia o source TypeScript como texto (source-inspection
puro) e valida as 7 asserções de AC#1 em cada uma das 8 salas, falhando
com AssertionError até que a feature seja implementada na fase GREEN.
"""

import re
from pathlib import Path

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

ROOMS_DIR = REPO_ROOT / "apps" / "blu_v3" / "src" / "pages" / "app"

ROOMS = [
    "ComprasRoom.tsx",
    "FinanceiroRoom.tsx",
    "AgendaRoom.tsx",
    "EstrategiaRoom.tsx",
    "ClientesRoom.tsx",
    "DocumentosRoom.tsx",
    "BibliotecaRoom.tsx",
    "HomePage.tsx",
]


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure source inspection, no DB teardown."""
    yield


# ── Helpers: extract the <div className="rh">...</div> block ────────────


def _extract_rh_block(source: str) -> str:
    """Return the substring from the first ``<div className="rh">`` up to
    the matching closing ``</div>``.

    The walker counts ``<div ...>`` and ``</div>`` tags to handle the
    nested wrappers inside the rh block (e.g. the unnamed ``<div>``
    that groups ``rn``/``rd``, and the ``<div className="ra">`` that
    wraps the action buttons).

    Returns an empty string when the pattern is not present in the
    source (e.g. HomePage, which still uses ``home-grid``).
    """
    match = re.search(r'<div\s+className="rh">', source)
    if not match:
        return ""
    start = match.start()
    i = match.end()
    depth = 1
    while i < len(source) and depth > 0:
        open_m = re.search(r"<div\b[^>]*>", source[i:])
        close_m = re.search(r"</div>", source[i:])
        if not close_m:
            return ""
        if open_m and open_m.start() < close_m.start():
            depth += 1
            i += open_m.end()
        else:
            depth -= 1
            i += close_m.end()
    if depth != 0:
        return ""
    return source[start:i]


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "room_file",
    ROOMS,
    ids=[r.replace(".tsx", "") for r in ROOMS],
)
def test_rh_unified_header(room_file):
    """AC#1 — ``<room_file>`` deve renderizar o padrão unificado de header
    de sala ``<div className="rh">`` contendo:

        * ``className="rav"`` — avatar / ícone da sala
        * ``className="rn"``  — nome / título da sala
        * ``className="rd"``  — descrição curta da sala
        * ``className="ra"``  — container de ações

    E dentro de ``ra``:
        * botão ``← Início`` (volta para a Home);
        * botão de ação primária começando com ``+``
          (ex.: ``+ Nova Missão``, ``+ Novo evento``,
          ``+ Nova Análise``, ``+ Novo contato``,
          ``+ Novo documento``, ``+ Adicionar arquivo``).

    O padrão já foi adotado em 7 das 8 salas.  ``HomePage`` ainda usa
    ``<div className="home-grid">`` — este teste está RED até que ela
    seja migrada para o padrão ``rh``.
    """
    path = ROOMS_DIR / room_file
    assert path.exists(), (
        f"AC#1 violado em {room_file}: arquivo da sala não encontrado em "
        f"{path}. Behavior RH — Unified Room Header — exige que as 8 salas "
        f"existam em apps/blu_v3/src/pages/app/."
    )
    source = path.read_text()
    block = _extract_rh_block(source)

    assert block, (
        f"AC#1 violado em {room_file}: a sala NÃO contém "
        f"``<div className=\"rh\">``. Behavior RH — Unified Room Header "
        f"— exige que toda sala renderize o cabeçalho unificado "
        f"(rav + rn + rd + ra). HomePage em particular ainda usa o layout "
        f"``<div className=\"home-grid\">`` e precisa ser migrada para o "
        f"padrão ``rh``."
    )

    assert 'className="rav"' in block, (
        f"AC#1 violado em {room_file}: o bloco ``rh`` não contém "
        f"``<div className=\"rav\">`` (avatar/ícone da sala). Behavior RH "
        f"exige a hierarquia completa rav → rn → rd → ra dentro do "
        f"cabeçalho unificado."
    )

    assert 'className="rn"' in block, (
        f"AC#1 violado em {room_file}: o bloco ``rh`` não contém "
        f"``<div className=\"rn\">`` (nome/título da sala). Behavior RH "
        f"exige a hierarquia completa rav → rn → rd → ra."
    )

    assert 'className="rd"' in block, (
        f"AC#1 violado em {room_file}: o bloco ``rh`` não contém "
        f"``<div className=\"rd\">`` (descrição curta da sala). Behavior "
        f"RH exige a hierarquia completa rav → rn → rd → ra."
    )

    assert 'className="ra"' in block, (
        f"AC#1 violado em {room_file}: o bloco ``rh`` não contém "
        f"``<div className=\"ra\">`` (container de ações da sala). "
        f"Behavior RH exige a hierarquia completa rav → rn → rd → ra."
    )

    assert "← Início" in block, (
        f"AC#1 violado em {room_file}: o bloco ``rh`` não contém o botão "
        f"``← Início`` que volta para a Home. Behavior RH exige que toda "
        f"sala ofereça navegação de retorno à Home dentro do header "
        f"unificado."
    )

    assert re.search(r"\+\s+\w", block), (
        f"AC#1 violado em {room_file}: o bloco ``rh`` não contém um botão "
        f"de ação primária que comece com ``+`` (exemplos esperados: "
        f"``+ Nova Missão``, ``+ Novo evento``, ``+ Nova Análise``, "
        f"``+ Novo contato``, ``+ Novo documento``, ``+ Adicionar "
        f"arquivo``). Behavior RH exige que toda sala exponha sua CTA "
        f"primária dentro do header unificado."
    )
