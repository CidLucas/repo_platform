"""RED test for behavior B1 — fix _shared_memory_flush_logic (remove dead code, implement batch flush).

GOAL:
    flush must mark metadata.flushed_at on matching entries.

BEHAVIOR:
    B1 — fix _shared_memory_flush_logic (remove dead code, implement batch flush).

    The function ``_shared_memory_flush_logic`` in
    ``services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py``
    (line 2351) currently has a **premature return** of listing data
    (``{"total_entities": N, "client_id": ..., "by_type": ..., "entities": [...]}``)
    that prevents the actual flush from executing.  The real flush logic lives
    below the premature return (lines ~2435+) and is therefore **dead code**.

    After the fix, the function must actually mark ``metadata.flushed_at`` on
    every matching entry (soft-delete) and return a dict whose contract is
    ``{"flushed_count": N, "total_scanned": N, "skipped_already_flushed": N}``.

AC (Acceptance Criteria):
    AC#4 — flush marks metadata.flushed_at on matching entries.

DECISION:
    fix_and_extend
    Arquivo alvo: services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py

Anti-Goals (must NOT be violated):
    1. NÃO remover o helper ``_shared_memory_meta_list_logic`` (B2 pode
       reusá-lo, mas este behavior não toca nele).
    2. NÃO alterar ``_shared_memory_export_logic``.
    3. NÃO introduzir dependência real do Supabase — o teste usa exec().

Estado atual: RED — ``_shared_memory_flush_logic`` retorna prematuramente
com ``{"total_entities": N, ...}`` em vez de executar o flush propriamente
dito.  O teste falha com AssertionError até que o dead code seja removido
e o flush em batch seja implementado (fase GREEN).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


# -- Stand-in ToolError --------------------------------------------


class ToolError(Exception):
    """Replacement for fastmcp.exceptions.ToolError in isolation."""
    pass


# -- Load the function in isolation --------------------------------

# Build a minimal namespace with all needed stubs.
_stub_logger = MagicMock()
_stub_get_supabase_client = AsyncMock()

_NAMESPACE = {
    "__name__": "memory_module",
    "json": __import__("json"),
    "logging": __import__("logging"),
    "logger": _stub_logger,
    "Context": MagicMock,
    "FastMCP": MagicMock,
    "ToolError": ToolError,
    "mcp_inject_client_id": MagicMock(return_value=lambda fn: fn),
    "get_supabase_client": _stub_get_supabase_client,
    "get_context_service": MagicMock(),
    "register_module": MagicMock(return_value=lambda fn: fn),
}


def _load_function() -> callable:
    """Extract ``_shared_memory_flush_logic`` from memory_module.py source.

    Mirrors the exec() pattern used by
    ``services/tool_pool_api/tests/unit/test_shared_memory_export.py``.
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
        / "memory_module.py"
    )
    source = mod_path.read_text()

    # Extract _VALID_ENTITY_TYPES constant
    vt_marker = "_VALID_ENTITY_TYPES: frozenset[str] = frozenset("
    vt_idx = source.find(vt_marker)
    assert vt_idx != -1, "Could not find _VALID_ENTITY_TYPES"
    vlines = source[vt_idx:].split("\n")
    vt_source_lines = []
    for vline in vlines:
        vt_source_lines.append(vline.rstrip())
        if ")" in vline and not vline.strip().startswith("#"):
            break
    exec("\n".join(vt_source_lines), _NAMESPACE)

    # Extract helpers: _validate_entity_type, _normalize_entity_name
    for helper_name in ("_validate_entity_type", "_normalize_entity_name"):
        helper_marker = f"def {helper_name}("
        hidx = source.find(helper_marker)
        if hidx != -1:
            hlines = source[hidx:].split("\n")
            h_fn_lines = []
            h_in_fn = False
            for hline in hlines:
                hs = hline.rstrip()
                if f"def {helper_name}(" in hs:
                    h_in_fn = True
                    h_fn_lines.append(hs)
                    continue
                if h_in_fn:
                    if hs == "":
                        h_fn_lines.append("")
                        continue
                    hindent = len(hline) - len(hline.lstrip())
                    if hindent == 0 and hs and not hs.strip().startswith("#"):
                        break
                    h_fn_lines.append(hs)
            exec("\n".join(h_fn_lines), _NAMESPACE)

    # Extract _TABLE constant
    table_marker = '_TABLE = "shared_business_memory"'
    tidx = source.find(table_marker)
    assert tidx != -1, "Could not find _TABLE"
    exec(source[tidx : tidx + len(table_marker) + 1], _NAMESPACE)

    # Extract _shared_memory_flush_logic
    marker = "async def _shared_memory_flush_logic("
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
        if "async def _shared_memory_flush_logic(" in line:
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
    return _NAMESPACE["_shared_memory_flush_logic"]


_shared_memory_flush_logic = _load_function()


# -- Helpers -------------------------------------------------------


def _make_list_result(rows):
    """Build a mock Supabase execute() result with a LIST in .data."""
    mock_result = MagicMock()
    mock_result.data = rows
    return mock_result


def _make_single_result(row_dict):
    """Build a mock Supabase single() result with a DICT in .data."""
    mock_result = MagicMock()
    mock_result.data = row_dict
    return mock_result


def _setup_supabase_chain(mock_supabase, rows):
    """Set up a chainable Supabase mock that supports both the buggy
    early-return path and the correct full-flush path.

    The early-return path does:
        db.schema().table().select().eq().group_by().execute()

    The correct flush path does:
        db.schema().table().select().eq().execute()         # scan rows
        db.schema().table().select().eq().single().execute()  # read metadata
        db.schema().table().update().eq().eq().execute()       # write metadata
    """
    schema_mock = MagicMock()
    mock_supabase.schema.return_value = schema_mock

    table_mock = MagicMock()
    schema_mock.table.return_value = table_mock

    # All chaining methods return the same table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.group_by.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.in_.return_value = table_mock

    # single() returns its own mock whose execute() returns a single dict
    single_mock = MagicMock()
    single_mock.execute = AsyncMock(
        return_value=_make_single_result({"metadata": {"agent_id": "agent-1"}})
    )
    table_mock.single.return_value = single_mock

    # table_mock.execute() returns the list of rows
    table_mock.execute = AsyncMock(return_value=_make_list_result(rows))


def _sample_rows(count=3):
    """Build sample row data WITHOUT ``flushed_at`` in metadata."""
    rows = []
    for i in range(1, count + 1):
        rows.append({
            "id": f"fact-{i:03d}",
            "entity_type": "client",
            "entity_name": f"cliente_{i}",
            "key": f"preferencia_{i}",
            "value": {"canal": "email", "prioridade": i},
            "metadata": {"agent_id": "agent-1"},  # NOTE: no "flushed_at"
            "source": "manual",
            "confidence": 0.9,
            "version": 1,
            "client_id": "client-id",
            "created_at": "2026-06-19T10:00:00Z",
            "updated_at": "2026-06-19T10:00:00Z",
        })
    return rows


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
async def test_flush_returns_flushed_count_not_total_entities(mock_supabase):
    """AC#4: flush must mark metadata.flushed_at on matching entries.

    Contract:
        - The result must have a ``flushed_count`` key (number of entries
          that had ``metadata.flushed_at`` written in this call).
        - The result must NOT carry the buggy ``total_entities`` key (that
          is the listing-data key returned by the premature return).

    Currently fails because the function returns early with
    ``{"total_entities": N, "by_type": {...}, "entities": [...]}`` before
    the actual flush code runs.
    """
    client_id = str(uuid.uuid4())
    sample = _sample_rows(count=3)

    _setup_supabase_chain(mock_supabase, sample)

    result = await _shared_memory_flush_logic(client_id=client_id)

    # AC#4 contract: result reports how many rows were flushed.
    assert "flushed_count" in result, (
        "AC#4 violated: result must contain 'flushed_count' (the number of "
        "entries that had metadata.flushed_at written). Got keys: "
        f"{sorted(result.keys())}. "
        "The function is taking the buggy early-return path and returning "
        "listing data ('total_entities', 'by_type', 'entities') instead of "
        "executing the actual flush."
    )

    # The buggy premature-return key must NOT be present in a correct result.
    assert "total_entities" not in result, (
        "AC#4 violated: result must NOT contain 'total_entities' — that key "
        "is leaked from the buggy premature return of listing data. "
        f"Got keys: {sorted(result.keys())}."
    )

    # Sanity: flushed_count is a non-negative int (matches AC#4 contract).
    assert isinstance(result["flushed_count"], int)
    assert result["flushed_count"] >= 0


@pytest.mark.asyncio
async def test_flush_skips_already_flushed_entries(mock_supabase):
    """AC#4: entries with ``metadata.flushed_at`` already set must be skipped
    (idempotency) and reported via ``skipped_already_flushed``.

    Currently fails because the function never reaches the flush path that
    computes this counter.
    """
    client_id = str(uuid.uuid4())
    # 2 of 3 rows are already flushed → only 1 should be flushed in this call.
    rows = [
        {
            "id": "fact-001",
            "entity_type": "client",
            "entity_name": "cliente_1",
            "key": "preferencia_1",
            "metadata": {"agent_id": "agent-1", "flushed_at": "2026-06-20T00:00:00Z"},
            "client_id": client_id,
        },
        {
            "id": "fact-002",
            "entity_type": "client",
            "entity_name": "cliente_2",
            "key": "preferencia_2",
            "metadata": {"agent_id": "agent-1"},
            "client_id": client_id,
        },
        {
            "id": "fact-003",
            "entity_type": "client",
            "entity_name": "cliente_3",
            "key": "preferencia_3",
            "metadata": {"agent_id": "agent-1", "flushed_at": "2026-06-21T00:00:00Z"},
            "client_id": client_id,
        },
    ]

    _setup_supabase_chain(mock_supabase, rows)

    result = await _shared_memory_flush_logic(client_id=client_id)

    assert "flushed_count" in result, (
        "AC#4 violated: result must contain 'flushed_count'. "
        f"Got keys: {sorted(result.keys())}."
    )
    assert "skipped_already_flushed" in result, (
        "AC#4 violated: result must contain 'skipped_already_flushed' to "
        "report idempotent skips. "
        f"Got keys: {sorted(result.keys())}."
    )
    assert "total_entities" not in result
