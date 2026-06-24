"""RED test for #post-boarding-home — Connections section on HomePage.

GOAL:
    The post-boarding Home (``apps/blu_v3/src/pages/app/HomePage.tsx``) is
    the main dashboard a user lands on right after the FirstRunOverlay
    onboarding completes. Today the home page shows a *Decidir Agora* /
    *Plano de Hoje* / *Visão da Semana* / *Rotinas* strip, but it does
    **not** expose a *Connections* section — there is no way for the user
    to see which external data sources (Bling, Omie, Google Drive, CSV,
    BigQuery) are connected to their workspace, and no in-place affordance
    to add a new one. Connections are only ever managed through
    ``ConnectionsModal`` during the FirstRunOverlay.

    This test pins the GREEN contract: after the feature lands, the
    post-boarding home MUST surface a Connections section that:
      * lists the services the user has already connected, OR
      * shows an empty-state placeholder + an action to add a new one.

BEHAVIOR:
    Once implemented (GREEN phase), the post-boarding home must:

      * Import and render a connections-related component
        (e.g. ``ConnectionsSection``, ``ConnectionsCard``) or render the
        connections section directly in ``HomePage.tsx``.
      * Pull the list of already-connected services from the
        ``connectors`` API (e.g. via ``getUploadedFiles`` for CSV/planilhas,
        or any future ``fetchConnections`` / ``listCredentials`` helper
        added to ``apps/blu_v3/src/api/connectors.ts``).
      * When the user has **no** connections, show a friendly empty-state
        message (e.g. ``"Nenhuma conexão"``, ``"No connections yet"``,
        ``"Conectar dados"``) so the home is not blank.
      * When the user has **at least one** connection, show a list/grid
        of the connected services.
      * Provide an affordance (button, link, or handler) to add a new
        connection — typically by re-opening ``ConnectionsModal`` from
        ``apps/blu_v3/src/components/onboarding/ConnectionsModal.tsx``.

AC (Acceptance Criteria):
    AC#1 — ``HomePage.tsx`` imports a connections-related component OR
           imports from ``../../api/connectors`` so the data layer is
           reachable from the post-boarding home.
    AC#2 — The home (or its connections component) shows a clear
           empty-state message in Portuguese OR English when no
           connections exist.
    AC#3 — The home (or its connections component) renders a list/grid
           of connected services when at least one connection exists
           (i.e. some ``.map(...)`` over a connection-shaped collection,
           or a ``connections-grid``/``connections-list`` CSS class).
    AC#4 — An action to add/connect a new connection is available on
           the home — either via the existing ``ConnectionsModal``
           being opened from the home, or via a button/link that
           mentions ``Conectar`` / ``Adicionar`` / ``+ Conexão``.

DECISION:
    Estratégia: extend — adicionar uma seção "Conexões" ao HomePage
                pós-boarding reutilizando a ``ConnectionsModal`` já
                existente. NÃO duplicar o modal de conexões; a fonte
                de verdade da UI de escolha de provedor é
                ``components/onboarding/ConnectionsModal.tsx``.

    Arquivo alvo: ``apps/blu_v3/src/pages/app/HomePage.tsx``
    Componente auxiliar esperado:
        ``apps/blu_v3/src/components/home/ConnectionsSection.tsx``
        (ou ``apps/blu_v3/src/components/shared/ConnectionsSection.tsx``)
    API alvo:    ``apps/blu_v3/src/api/connectors.ts``
                 (já expõe ``getUploadedFiles``; pode ganhar um
                 ``fetchConnections``/``listCredentials`` no GREEN).

Anti-Goals (must NOT be violated):
    1. NÃO duplicar ``ConnectionsModal`` — a versão em
       ``components/onboarding/`` é a fonte da verdade; o home deve
       reabri-la, não criar um novo modal.
    2. NÃO acoplar o home a um cliente Supabase novo — o consumo de
       conexões deve passar pela API em ``apps/blu_v3/src/api/connectors.ts``.
    3. NÃO introduzir dependência externa neste teste — é um teste de
       unidade puro baseado em inspeção de arquivos fonte (mesmo
       padrão de ``test_platform_filter_routines.py``).
    4. NÃO renderizar a lista de conexões *inline* no HomePage sem um
       componente próprio — a renderização deve morar em
       ``ConnectionsSection`` (ou equivalente) para manter o
       HomePage enxuto.

Estado atual (RED):
    * ``HomePage.tsx`` NÃO importa ``ConnectionsSection``,
      ``ConnectionsCard``, ``ConnectionsList`` nem de
      ``'../../api/connectors'``.
    * ``HomePage.tsx`` NÃO contém nenhuma string de empty-state
      relacionada a conexões (``"Nenhuma conexão"``,
      ``"No connections yet"``, ``"Conectar dados"``, etc.).
    * ``HomePage.tsx`` NÃO contém nenhum ``.map(...)`` sobre uma
      coleção de conexões nem classes CSS
      ``connections-grid``/``connections-list``.
    * ``HomePage.tsx`` NÃO importa ``ConnectionsModal`` nem tem
      handler que abra o modal a partir do home.
    * Não existe ``apps/blu_v3/src/components/home/`` (diretório
      ausente) nem ``apps/blu_v3/src/components/shared/ConnectionsSection.tsx``.

    Todas as quatro verificações abaixo falham hoje. Quando o GREEN
    for implementado (criar ``ConnectionsSection`` que consome
    ``getUploadedFiles``/``fetchConnections``, importá-lo no
    ``HomePage.tsx``, mostrar empty-state + botão "Adicionar conexão"
    que reabre a ``ConnectionsModal``), as quatro passam.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Path resolution (root of repo) ────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

HOME_PAGE_TSX = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "pages"
    / "app"
    / "HomePage.tsx"
)
CONNECTORS_API_TS = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "api"
    / "connectors.ts"
)

# Possible locations for a new ``ConnectionsSection`` component. The
# GREEN phase is free to pick either; the test is permissive and accepts
# both, so the developer isn't forced into a specific path.
CONNECTIONS_SECTION_HOME = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "home"
    / "ConnectionsSection.tsx"
)
CONNECTIONS_SECTION_SHARED = (
    REPO_ROOT
    / "apps"
    / "blu_v3"
    / "src"
    / "components"
    / "shared"
    / "ConnectionsSection.tsx"
)


# ── Override root conftest cleanup (pure file-based test) ────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file inspection, no DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_text(path: Path) -> str:
    assert path.exists(), f"File not found: {path}"
    return path.read_text(encoding="utf-8")


def _optional_read_text(path: Path) -> str:
    """Return file contents if the file exists, else empty string."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _candidate_texts() -> dict[str, str]:
    """Collect the source files that may host the Connections section.

    Returns a dict ``{label: text}``. Missing files are represented by an
    empty string so callers can use ``any(... in text ...)`` without
    having to special-case absent files.
    """
    return {
        "HomePage.tsx": _optional_read_text(HOME_PAGE_TSX),
        "components/home/ConnectionsSection.tsx": _optional_read_text(CONNECTIONS_SECTION_HOME),
        "components/shared/ConnectionsSection.tsx": _optional_read_text(CONNECTIONS_SECTION_SHARED),
    }


def _homepage_imports_connections(homepage_text: str) -> bool:
    """AC#1: HomePage must import a connections component or the API.

    Accepts any of:
      * ``import ... from '../../api/connectors'`` (single OR double
        quotes) — pulls in the data layer.
      * ``import ... ConnectionsSection`` — pulls in the UI section.
      * ``import ... ConnectionsCard`` / ``ConnectionsList`` — any
        reasonable naming for the section.
    """
    if not homepage_text:
        return False
    needles = [
        "from '../../api/connectors'",
        'from "../../api/connectors"',
        "ConnectionsSection",
        "ConnectionsCard",
        "ConnectionsList",
        "ConnectionsPanel",
    ]
    return any(n in homepage_text for n in needles)


def _has_empty_state_message(texts: dict[str, str]) -> bool:
    """AC#2: empty-state placeholder when no connections exist.

    Accepts any Portuguese or English empty-state string that a user
    would understand as "you have no connections yet" inside ANY of the
    candidate files (HomePage or a ConnectionsSection component).
    """
    needles = [
        "Nenhuma conexão",
        "Nenhuma conex",
        "nenhuma conexão",
        "nenhuma conex",
        "No connections yet",
        "no connections yet",
        "Conecte uma fonte",
        "Conectar dados",
        "Conecte seus dados",
        "Nenhuma fonte conectada",
    ]
    return any(
        any(n in text for n in needles)
        for text in texts.values()
        if text
    )


def _has_connections_list(texts: dict[str, str]) -> bool:
    """AC#3: list/grid of connected services when at least one exists.

    Accepts EITHER:
      * A ``.map(...)`` over a connection-shaped variable
        (``connections.map(...)``, ``connectionsQ.data?.map(...)``,
        ``connections?.map(...)``, or a single-letter ``c`` / ``conn``
        inside a ``.map`` near connection identifiers), OR
      * A CSS class that names a connections grid/list
        (``connections-grid``, ``connections-list``, ``conn-grid``,
        ``conn-list``, ``conn-card``).
    """
    map_patterns = [
        r"\.map\(",
        r"\.map\s*\(",
    ]
    connection_identifiers = re.compile(
        r"\b(connections?|connectionsQ|connectionList|connList)\b",
        re.IGNORECASE,
    )
    css_classes = [
        "connections-grid",
        "connections-list",
        "connections-row",
        "connections-section",
        "conn-grid",
        "conn-list",
        "conn-card",
        "conn-tile",
    ]
    single_letter_map = re.compile(
        r"\.map\(\s*(c|conn|connection)\b",
        re.IGNORECASE,
    )

    for text in texts.values():
        if not text:
            continue
        for pat in map_patterns:
            if re.search(pat, text) and connection_identifiers.search(text):
                return True
        if single_letter_map.search(text):
            return True
        if any(css in text for css in css_classes):
            return True
    return False


def _has_add_connection_action(texts: dict[str, str]) -> bool:
    """AC#4: action to add/connect a new connection is reachable from home.

    Accepts EITHER:
      * A reference to the existing ``ConnectionsModal`` (e.g. an
        ``import ConnectionsModal`` or ``<ConnectionsModal ... />``
        in the candidate files), OR
      * A button/link text that says "add/connect a connection" in
        Portuguese or English, OR
      * A handler/state machine tied to opening the modal
        (e.g. ``setShowConnectionsModal``, ``onOpenConnections``,
        ``openConnectionsModal``).

    Notes on disambiguation:
      * "Conectar Google Calendar" is an existing single-integration
        button on the home; we deliberately do NOT match bare
        ``"Conectar"`` to avoid false positives from that button.
    """
    modal_needles = [
        "ConnectionsModal",
    ]
    text_needles = [
        "Adicionar conexão",
        "Adicionar conex",
        "adicionar conexão",
        "adicionar conex",
        "Nova conexão",
        "Nova conex",
        "Add connection",
        "+ Conexão",
        "Conectar nova fonte",
        "Conectar uma fonte",
    ]
    handler_needles = [
        "setShowConnectionsModal",
        "openConnectionsModal",
        "onOpenConnections",
        "showConnectionsModal",
        "setShowAddConnection",
    ]

    for text in texts.values():
        if not text:
            continue
        if any(n in text for n in modal_needles):
            return True
        if any(n in text for n in text_needles):
            return True
        if any(n in text for n in handler_needles):
            return True
    return False


# ── The single behavior under test ──────────────────────────────────────


def test_post_boarding_connections_red():
    """Post-boarding HomePage must surface a Connections section.

    The test inspects the repository's source-of-truth files (no mocks,
    no DB) and asserts:

      AC#1) ``HomePage.tsx`` imports a connections component (e.g.
             ``ConnectionsSection``) OR imports from
             ``../../api/connectors`` so the data layer is reachable
             from the post-boarding home.
      AC#2) HomePage (or its connections component) shows an empty-state
             message when no connections exist — e.g. ``"Nenhuma
             conexão"``, ``"No connections yet"``, ``"Conectar dados"``.
      AC#3) HomePage (or its connections component) renders a list/grid
             of connected services when at least one connection exists
             — a ``.map(...)`` over a connection-shaped collection OR a
             ``connections-grid``/``connections-list`` CSS class.
      AC#4) An action to add/connect a new connection is available
             from the home — either by re-opening the existing
             ``ConnectionsModal`` or via a button/link whose text
             explicitly invites the user to add a connection.

    All four checks fail in the current state (RED) because:

      * ``HomePage.tsx`` has zero references to
        ``ConnectionsSection`` / ``ConnectionsCard`` / ``ConnectionsList``
        and does not import from ``../../api/connectors``.
      * ``HomePage.tsx`` contains no empty-state string related to
        connections (the only ``Conectar`` literal is the
        Google Calendar button, not a generic add-connection action).
      * There is no ``.map(...)`` over a connection-shaped variable in
        ``HomePage.tsx`` and no ``connections-grid`` /
        ``connections-list`` class.
      * ``HomePage.tsx`` does not import ``ConnectionsModal`` nor has
        any handler that opens it from the home.
    """
    failures: list[str] = []

    # Read the source of truth (HomePage is mandatory; the connections
    # section file is optional — when missing, AC#1 still requires the
    # HomePage to at least import the connectors API).
    homepage_text = _read_text(HOME_PAGE_TSX)
    candidates = _candidate_texts()

    # ── AC#1 — HomePage imports a connections component or API ───
    if not _homepage_imports_connections(homepage_text):
        failures.append(
            "AC#1 violated: HomePage.tsx does NOT import a connections "
            "component nor the connectors API. The post-boarding home "
            "must surface a Connections section, which requires "
            "importing either a `ConnectionsSection` (or "
            "`ConnectionsCard`/`ConnectionsList`) component from "
            "`apps/blu_v3/src/components/home/` (or `shared/`) OR "
            "importing the data layer from "
            "`apps/blu_v3/src/api/connectors`. Today HomePage.tsx has "
            "neither — it does not even know the connectors module "
            "exists. "
            f"File: {HOME_PAGE_TSX}"
        )

    # ── AC#2 — Empty-state message when no connections exist ──────
    if not _has_empty_state_message(candidates):
        failures.append(
            "AC#2 violated: no empty-state message for connections on "
            "the post-boarding home. When the user has no connections, "
            "the Connections section must display a friendly "
            "placeholder (e.g. 'Nenhuma conexão', 'No connections "
            "yet', 'Conectar dados') in HomePage.tsx or in a "
            "`ConnectionsSection` component. Today neither file "
            "contains any of these strings. "
            f"Files inspected: HomePage.tsx ({HOME_PAGE_TSX}), "
            f"components/home/ConnectionsSection.tsx "
            f"({CONNECTIONS_SECTION_HOME}), "
            f"components/shared/ConnectionsSection.tsx "
            f"({CONNECTIONS_SECTION_SHARED})."
        )

    # ── AC#3 — List/grid of connected services ───────────────────
    if not _has_connections_list(candidates):
        failures.append(
            "AC#3 violated: the post-boarding home does NOT render a "
            "list/grid of connected services. When the user has at "
            "least one connection, HomePage (or its "
            "`ConnectionsSection`) must render a `.map(...)` over a "
            "connection-shaped collection (e.g. `connections.map(...)` "
            "or `connectionsQ.data?.map(...)`) OR a CSS class naming "
            "the list (e.g. `connections-grid`, `connections-list`, "
            "`conn-card`). Today HomePage.tsx has no such pattern. "
            f"Files inspected: HomePage.tsx ({HOME_PAGE_TSX}), "
            f"components/home/ConnectionsSection.tsx "
            f"({CONNECTIONS_SECTION_HOME}), "
            f"components/shared/ConnectionsSection.tsx "
            f"({CONNECTIONS_SECTION_SHARED})."
        )

    # ── AC#4 — Action to add a new connection ─────────────────────
    if not _has_add_connection_action(candidates):
        failures.append(
            "AC#4 violated: the post-boarding home does NOT provide an "
            "affordance to add/connect a new connection. The user "
            "must be able to open the connections flow from the home "
            "— either by reusing the existing `ConnectionsModal` "
            "(`apps/blu_v3/src/components/onboarding/ConnectionsModal.tsx`) "
            "or by a button/link with text such as 'Adicionar "
            "conexão', '+ Conexão', 'Add connection' or 'Conectar "
            "nova fonte'. Today HomePage.tsx does not import "
            "ConnectionsModal and has no such button/handler. "
            f"Files inspected: HomePage.tsx ({HOME_PAGE_TSX}), "
            f"components/home/ConnectionsSection.tsx "
            f"({CONNECTIONS_SECTION_HOME}), "
            f"components/shared/ConnectionsSection.tsx "
            f"({CONNECTIONS_SECTION_SHARED})."
        )

    # ── Aggregate all failures ───────────────────────────────────
    assert not failures, (
        "Post-boarding home — Connections section is NOT yet "
        "implemented. The following acceptance criteria are violated:\n\n  - "
        + "\n  - ".join(failures)
    )
