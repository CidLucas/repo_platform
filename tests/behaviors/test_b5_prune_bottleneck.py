"""RED test for behavior B5 — fix N+1 bottleneck in _prune_old_versions.

GOAL:
    Issue #121 — Performance. Fix P2 bottleneck: _prune_old_versions in
    version_module.py deletes old versions ONE BY ONE in a for-loop (N+1 DB
    problem). The fix must batch-delete using ``.in_()``.

BEHAVIOR:
    B5 — fix N+1 bottleneck in _prune_old_versions (batch delete).

    The function ``_prune_old_versions`` in
    ``services/tool_pool_api/src/tool_pool_api/server/tool_modules/version_module.py``
    deletes old versions in a for-loop calling ``.eq("id", vid)`` for each
    version individually.  This is an N+1 database problem — one SELECT followed
    by N individual DELETE queries.

    After the fix, the function must batch-delete using ``.in_()`` with a
    single DELETE query.

AC (Acceptance Criteria):
    AC#1 — _prune_old_versions uses ``.in_()`` for batch DELETE instead of
    individual ``.eq("id", ...)`` calls.

DECISION:
    fix_bottleneck
    Arquivo alvo: services/tool_pool_api/src/tool_pool_api/server/tool_modules/version_module.py

Anti-Goals (must NOT be violated):
    1. NÃO alterar o comportamento de retorno (deleted_count still accurate).
    2. NÃO alterar a lógica de seleção dos IDs a deletar.
    3. NÃO introduzir dependência real do Supabase — o teste usa exec().

Estado atual: RED — ``_prune_old_versions`` usa um loop for com
``.eq("id", vid)`` para cada deleção individual.  O teste falha com
AssertionError até que a deleção em batch via ``.in_()`` seja implementada
(fase GREEN).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


# -- Stand-in ToolError --------------------------------------------


class ToolError(Exception):
    """Replacement for fastmcp.exceptions.ToolError in isolation."""
    pass


# -- Stubs ---------------------------------------------------------

_stub_logger = MagicMock()
_stub_get_supabase_client = AsyncMock()

_NAMESPACE = {
    "__name__": "version_module",
    "json": __import__("json"),
    "hashlib": __import__("hashlib"),
    "difflib": __import__("difflib"),
    "logging": __import__("logging"),
    "Any": __import__("typing").Any,
    "logger": _stub_logger,
    "Context": MagicMock,
    "FastMCP": MagicMock,
    "ToolError": ToolError,
    "mcp_inject_client_id": MagicMock(return_value=lambda fn: fn),
    "get_supabase_client": _stub_get_supabase_client,
    "register_module": MagicMock(return_value=lambda fn: fn),
}


def _load_function() -> callable:
    """Extract ``_prune_old_versions`` from version_module.py source.

    Mirrors the exec() pattern from
    tests/behaviors/test_b1_flush_logic.py.
    """
    import pathlib
    mod_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent
        / "services"
        / "tool_pool_api"
        / "src"
        / "tool_pool_api"
        / "server"
        / "tool_modules"
        / "version_module.py"
    )
    source = mod_path.read_text()

    # --- 1. Extract constants ---

    # _VERSION_TABLE
    vt_marker = '_VERSION_TABLE = "shared_business_memory_versions"'
    vt_idx = source.find(vt_marker)
    assert vt_idx != -1, "Could not find _VERSION_TABLE"
    exec(source[vt_idx: vt_idx + len(vt_marker) + 1], _NAMESPACE)

    # _MAX_VERSIONS_PER_KEY
    maxv_marker = "_MAX_VERSIONS_PER_KEY = 50"
    maxv_idx = source.find(maxv_marker)
    assert maxv_idx != -1, "Could not find _MAX_VERSIONS_PER_KEY"
    exec(source[maxv_idx: maxv_idx + len(maxv_marker) + 1], _NAMESPACE)

    # _VALID_SOURCES (multi-line frozenset)
    vs_marker = "_VALID_SOURCES: frozenset[str] = frozenset("
    vs_idx = source.find(vs_marker)
    assert vs_idx != -1, "Could not find _VALID_SOURCES"
    vs_lines = source[vs_idx:].split("\n")
    vs_source_lines = []
    for vs_line in vs_lines:
        vs_source_lines.append(vs_line.rstrip())
        if ")" in vs_line and not vs_line.strip().startswith("#"):
            break
    exec("\n".join(vs_source_lines), _NAMESPACE)

    # _VALID_ENTITY_TYPES (multi-line frozenset)
    vet_marker = "_VALID_ENTITY_TYPES: frozenset[str] = frozenset("
    vet_idx = source.find(vet_marker)
    assert vet_idx != -1, "Could not find _VALID_ENTITY_TYPES"
    vet_lines = source[vet_idx:].split("\n")
    vet_source_lines = []
    for vet_line in vet_lines:
        vet_source_lines.append(vet_line.rstrip())
        if ")" in vet_line and not vet_line.strip().startswith("#"):
            break
    exec("\n".join(vet_source_lines), _NAMESPACE)

    # --- 2. Extract helper functions ---

    def _extract_function(func_name: str) -> None:
        """Find ``def func_name(`` in source and exec the function body."""
        marker = f"def {func_name}("
        idx = source.find(marker)
        if idx == -1:
            raise AssertionError(f"Could not find '{marker}'")
        lines = source[idx:].split("\n")
        fn_lines = []
        in_fn = False
        for line in lines:
            stripped = line.rstrip()
            if marker in line:
                in_fn = True
                fn_lines.append(stripped)
                continue
            if in_fn:
                if stripped == "":
                    fn_lines.append("")
                    continue
                indent = len(line) - len(line.lstrip())
                if indent == 0 and stripped and not stripped.startswith("#"):
                    break
                fn_lines.append(stripped)
        exec("\n".join(fn_lines), _NAMESPACE)

    for helper in (
        "compute_content_hash",
        "_text_diff",
        "_validate_entity_type",
        "_normalize_entity_name",
    ):
        _extract_function(helper)

    # --- 3. Extract _prune_old_versions ---

    marker = "async def _prune_old_versions("
    idx = source.find(marker)
    assert idx != -1, f"Could not find '{marker}'"

    # Walk backward to find section comment
    fn_start = source.rfind("#", 0, idx)
    assert fn_start != -1, "Could not find section start"

    lines = source[fn_start:].split("\n")
    fn_lines = []
    in_fn = False
    for line in lines:
        stripped = line.rstrip()
        if not stripped and not in_fn:
            continue
        if "async def _prune_old_versions(" in line:
            in_fn = True
            fn_lines.append(stripped)
            continue
        if in_fn:
            if stripped == "":
                fn_lines.append("")
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0 and stripped.startswith("# -------"):
                break
            if indent == 0 and (
                stripped.startswith("async def ")
                or stripped.startswith("@")
                or stripped.startswith("def ")
            ):
                break
            fn_lines.append(stripped)

    fn_source = "\n".join(fn_lines)
    exec(fn_source, _NAMESPACE)
    return _NAMESPACE["_prune_old_versions"]


_prune_old_versions = _load_function()


# -- Helpers -------------------------------------------------------


def _sample_version_rows(count: int = 15) -> list[dict]:
    """Build sample version rows for the same (client_id, entity_type, entity_name, key).

    Versions are ordered oldest-first (version 1 = oldest).
    """
    rows = []
    for i in range(1, count + 1):
        rows.append({
            "id": f"ver-{i:03d}",
            "client_id": "client-abc",
            "entity_type": "skill",
            "entity_name": "my_skill",
            "key": "config",
            "version": i,
            "value": {"setting": f"value_{i}"},
            "content_hash": f"hash{i:03d}",
            "created_at": f"2026-06-{19 + i:02d}T10:00:00Z",
        })
    return rows


def _setup_supabase_chain(mock_supabase, rows):
    """Set up a chainable Supabase mock for _prune_old_versions.

    Query flow in CURRENT code (N+1):
      1. db.schema().table().select("id").eq(...).eq(...).eq(...)
           .eq(...).order("version", desc=False).execute()
         → list of version rows (oldest first, all 15 rows)
      2. For each of the first 10 version ids (in a for-loop):
           db.schema().table().delete().eq("id", <vid>)
               .eq("client_id", <cid>).execute()

    After the fix (batch):
      1. Same SELECT.
      2. Single DELETE with .in_("id", [id1, id2, ...]):
           db.schema().table().delete().in_("id", [ids...])
               .eq("client_id", <cid>).execute()
    """
    schema_mock = MagicMock()
    mock_supabase.schema.return_value = schema_mock

    table_mock = MagicMock()
    schema_mock.table.return_value = table_mock

    # SELECT chain — all methods return table_mock itself
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock

    # SELECT execute returns the version rows
    table_mock.execute = AsyncMock(return_value=MagicMock(data=rows))

    # DELETE chain — returns a separate mock so we can track .in_() calls
    delete_mock = MagicMock(name="delete_chain")
    delete_mock.eq.return_value = delete_mock
    delete_mock.in_.return_value = delete_mock
    delete_mock.execute = AsyncMock(return_value=MagicMock(data=[]))
    table_mock.delete.return_value = delete_mock

    return delete_mock


# -- Fixtures ------------------------------------------------------


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test uses mocked Supabase, no DB teardown."""
    yield


@pytest.fixture
def mock_supabase():
    """Mock Supabase client returning a chainable query builder."""
    db = MagicMock()
    _stub_get_supabase_client.return_value = db
    yield db
    _stub_get_supabase_client.reset_mock()


# -- Tests ---------------------------------------------------------


@pytest.mark.asyncio
async def test_prune_batch_delete_uses_in_not_individual_eq(mock_supabase):
    """AC#1: _prune_old_versions must use ``.in_()`` for batch DELETE.

    Given 15 version rows for the same (client_id, entity_type, entity_name, key)
    and max_versions=5, the function must:
      - Delete the 10 oldest versions.
      - Use a SINGLE batch DELETE via ``.in_()`` instead of 10 individual
        ``.eq("id", ...)`` calls.

    Currently fails (RED) because the code uses a for-loop with individual
    ``.eq("id", <vid>)`` calls — an N+1 database problem.
    """
    client_id = "client-abc"
    entity_type = "skill"
    entity_name = "my_skill"
    key = "config"

    rows = _sample_version_rows(count=15)
    delete_mock = _setup_supabase_chain(mock_supabase, rows)

    # Call the function under test
    deleted_count = await _prune_old_versions(
        client_id=client_id,
        entity_type=entity_type,
        entity_name=entity_name,
        key=key,
        max_versions=5,
    )

    # --- Assertions that should PASS (business logic is correct) ---
    assert deleted_count == 10, (
        f"Expected 10 versions deleted (15 total - 5 kept), got {deleted_count}"
    )

    # --- RED assertion: .in_() must be used for batch DELETE ---
    # The current code uses .eq("id", vid) in a for-loop.
    # After the fix, it must use .in_() — this assertion fails NOW (RED).
    delete_mock.in_.assert_called_once_with(
        "id", [f"ver-{i:03d}" for i in range(1, 11)]
    )

    # Also verify that .eq("id", ...) was NOT called on the delete chain
    # (individual deletes should be gone after the fix).
    # For each call to delete_mock.eq, check the first arg isn't "id".
    for call_args in delete_mock.eq.call_args_list:
        args, _ = call_args
        assert args[0] != "id", (
            f"AC#1 violated: delete chain used .eq(\"id\", ...) instead of .in_(). "
            f"Call was: .eq({args[0]!r}, {args[1]!r}). "
            f"The fix must replace individual .eq(\"id\", ...) deletes with a "
            f"single .in_(\"id\", [...]) batch delete."
        )
