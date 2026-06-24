"""RED behavior test for Post-boarding — Connections Management API.

GOAL:
    The post-boarding home page displays a Connections section
    (``ConnectionsSection``) that lists uploaded files and allows users to
    add new connections via ``ConnectionsModal``.  However, today there is
    **no** backend REST API that the post-boarding home (or any other
    caller) can use to programmatically list, create, or remove connections
    (external-service credentials) for a client.

    The tool_pool_api already exposes an ``/integrations`` router for OAuth
    integrations (Google Calendar, etc.).  This test asserts that a
    *connections management* sub-API at ``/integrations/connections`` is
    exposed by the same router, providing three endpoints that mirror the
    CRUD contract the frontend currently invokes directly through Supabase:

      * ``GET    /integrations/connections``   — list all credentials
      * ``POST   /integrations/connections``   — create a new credential
      * ``DELETE /integrations/connections/{credential_id}`` — remove

    Until these routes are added to ``integrations_router.py`` the test
    remains RED.

BEHAVIOR:
    Once implemented (GREEN phase), the ``integrations_router.py`` must:

      * Define a ``GET /integrations/connections`` endpoint (or
        ``/integrations/connections/list``) that accepts a ``client_id``
        query parameter and returns a list of ``credencial_servico_externo``
        rows for that client, mapped to a ConnectionResponse schema.
      * Define a ``POST /integrations/connections`` endpoint (or
        ``/integrations/connections/create``) that accepts a
        ``CreateConnectionRequest`` body (``platform``, ``nome_servico``,
        ``credentials``) and ``client_id``, inserts into
        ``credencial_servico_externo``, and returns the created row.
      * Define a ``DELETE /integrations/connections/{credential_id}``
        endpoint (or ``/integrations/connections/{id}``) that accepts a
        path parameter ``credential_id`` and a ``client_id`` query,
        deletes the matching row (after verifying ownership), and returns
        204 No Content.

AC (Acceptance Criteria):
    AC#1 — ``integrations_router.py`` contains a ``@router.get`` decorator
           whose route path matches ``/connections`` or ``/connections/list``
           or ``/connections/`` — i.e. it exposes a GET route under
           ``/integrations`` that can list connections.
    AC#2 — ``integrations_router.py`` contains a ``@router.delete`` decorator
           whose route path matches ``/connections/{param}`` or
           ``/connections/{param}/`` — i.e. it exposes a DELETE route under
           ``/integrations`` that can remove a credential by its id.
    AC#3 — ``integrations_router.py`` contains a ``@router.post`` decorator
           whose route path matches ``/connections`` or ``/connections/create``
           or ``/connections/`` — i.e. it exposes a POST route under
           ``/integrations`` that can create a new credential.

Anti-Goals (must NOT be violated):
    1. NÃO duplicar lógica de conexão no frontend — o CRUD deve ser
       centralizado no backend (tool_pool_api).
    2. NÃO expor o schema do Supabase diretamente — o endpoint deve
       retornar um Pydantic ``ConnectionResponse``, não uma linha bruta
       da tabela.
    3. NÃO acoplar o teste a um banco real — é um teste de inspeção de
       fonte puro (mesmo padrão de ``test_post_boarding_connections.py``).

Estado atual (RED):
    * ``integrations_router.py`` contém zero decorators que incluem a
      substring ``/connection`` na rota.
    * As operações de listar, criar e remover conexões são feitas
      exclusivamente pelo frontend via ``supabase`` client-side.

    Todas as três verificações abaixo falham hoje.  Quando o GREEN for
    implementado (adicionar os três endpoints ao router), as três passam.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ── Path resolution (root of repo) ────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

INTEGRATIONS_ROUTER_PY = (
    REPO_ROOT
    / "services"
    / "tool_pool_api"
    / "src"
    / "tool_pool_api"
    / "api"
    / "integrations_router.py"
)


# ── Override root conftest cleanup (pure file-based test) ────────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure file inspection, no DB."""
    yield


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_integrations_router() -> str:
    """Read the integrations_router source file."""
    assert INTEGRATIONS_ROUTER_PY.exists(), (
        f"File not found: {INTEGRATIONS_ROUTER_PY}"
    )
    return INTEGRATIONS_ROUTER_PY.read_text(encoding="utf-8")


def _has_get_connections_route(text: str) -> bool:
    """AC#1: @router.get decorator with route containing ``connection``.

    Accepts any of:
      * @router.get("/connections")
      * @router.get("/connections/list")
      * @router.get("/connections/")
      * @router.get("/connections/{...}")
      * @router.get("/connections/list/")
    """
    # Match ``@router.get(`` followed by a string containing ``connection``
    # anywhere inside the route path, on the same logical line.
    pattern = re.compile(
        r"@router\.get\s*\(\s*[\"'][^\"']*connection[^\"']*[\"']",
        re.IGNORECASE,
    )
    return bool(pattern.search(text))


def _has_delete_connections_route(text: str) -> bool:
    """AC#2: @router.delete decorator with route containing ``connection``.

    Accepts any of:
      * @router.delete("/connections/{credential_id}")
      * @router.delete("/connections/{id}")
      * @router.delete("/connections/{conn_id}")
    """
    pattern = re.compile(
        r"@router\.delete\s*\(\s*[\"'][^\"']*connection[^\"']*[\"']",
        re.IGNORECASE,
    )
    return bool(pattern.search(text))


def _has_post_connections_route(text: str) -> bool:
    """AC#3: @router.post decorator with route containing ``connection``.

    Accepts any of:
      * @router.post("/connections")
      * @router.post("/connections/create")
      * @router.post("/connections/")
    """
    pattern = re.compile(
        r"@router\.post\s*\(\s*[\"'][^\"']*connection[^\"']*[\"']",
        re.IGNORECASE,
    )
    return bool(pattern.search(text))


# ── The single behavior under test ──────────────────────────────────────


def test_post_boarding_connections_mgmt_red():
    """Post-boarding Connections Management API must exist on tool_pool_api.

    The test inspects the ``integrations_router.py`` source for FastAPI
    route decorators that expose connections CRUD endpoints under the
    ``/integrations`` prefix.

    All three checks fail in the current state (RED) because:
      * ``integrations_router.py`` has zero route decorators whose
        path includes the substring ``connection``.
      * All connection operations (list, create, delete) are performed
        client-side via ``supabase``.
    """
    failures: list[str] = []

    # Read the source of truth
    router_text = _read_integrations_router()

    # ── AC#1 — GET route for listing connections ───────────────────
    if not _has_get_connections_route(router_text):
        failures.append(
            "AC#1 violated: integrations_router.py does NOT define a "
            "@router.get(...) route whose path contains 'connection'.  "
            "The post-boarding home needs a backend endpoint to list "
            "connections/credentials for a client.  Expected: "
            "@router.get('/connections') or similar under the "
            "'/integrations' prefix.  "
            f"File: {INTEGRATIONS_ROUTER_PY}"
        )

    # ── AC#2 — DELETE route for removing a connection ──────────────
    if not _has_delete_connections_route(router_text):
        failures.append(
            "AC#2 violated: integrations_router.py does NOT define a "
            "@router.delete(...) route whose path contains 'connection'.  "
            "The post-boarding home needs a backend endpoint to remove "
            "a credential.  Expected: "
            "@router.delete('/connections/{credential_id}') or similar.  "
            f"File: {INTEGRATIONS_ROUTER_PY}"
        )

    # ── AC#3 — POST route for creating a connection ────────────────
    if not _has_post_connections_route(router_text):
        failures.append(
            "AC#3 violated: integrations_router.py does NOT define a "
            "@router.post(...) route whose path contains 'connection'.  "
            "The post-boarding home needs a backend endpoint to create "
            "a new credential.  Expected: "
            "@router.post('/connections') or similar.  "
            f"File: {INTEGRATIONS_ROUTER_PY}"
        )

    # ── Aggregate all failures ─────────────────────────────────────
    assert not failures, (
        "Post-boarding — Connections Management API is NOT yet "
        "implemented on the tool_pool_api.  The following acceptance "
        "criteria are violated:\n\n  - "
        + "\n  - ".join(failures)
    )
