# tests/unit/test_version_module.py
"""Unit tests for version_module (version storage and retrieval).

Tests the business-logic functions with mocked Supabase client.
Covers: archive, list, get, prune, error handling, memory limits.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── Stand-in ToolError ────────────────────────────────────────────

class ToolError(Exception):
    """Replacement for fastmcp.exceptions.ToolError in isolation."""
    pass


# ── Load functions in isolation ───────────────────────────────────

_stub_logger = MagicMock()
_stub_get_supabase_client = AsyncMock()

_NAMESPACE = {
    "__name__": "version_module",
    "logging": __import__("logging"),
    "logger": _stub_logger,
    "Context": MagicMock,
    "FastMCP": MagicMock,
    "ToolError": ToolError,
    "mcp_inject_client_id": MagicMock(return_value=lambda fn: fn),
    "get_supabase_client": _stub_get_supabase_client,
    "register_module": MagicMock(return_value=lambda fn: fn),
    # Module-level constants needed by the functions
    "_VERSION_TABLE": "shared_business_memory_versions",
    "_MAX_VERSIONS_PER_KEY": 50,
    "_VALID_SOURCES": frozenset(
        {"manual", "memory_agent", "specialist", "migration", "system"}
    ),
    "_VALID_ENTITY_TYPES": frozenset(
        {"skill", "client", "contact", "supplier", "user",
         "snapshot", "routine", "agent_result", "agent_metadata"}
    ),
}


def _load_module_functions():
    """Extract key functions from version_module.py source."""
    import pathlib
    mod_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "src" / "tool_pool_api" / "server" / "tool_modules"
        / "version_module.py"
    )
    source = mod_path.read_text()

    funcs_to_load = [
        "_validate_entity_type",
        "_normalize_entity_name",
        "_format_version_row",
        "_archive_memory_version",
        "_get_memory_versions",
        "_get_memory_version",
        "_prune_old_versions",
    ]

    for func_name in funcs_to_load:
        marker = f"async def {func_name}(" if "await" in source else f"def {func_name}("
        # Try async first
        marker_async = f"async def {func_name}("
        marker_sync = f"def {func_name}("
        idx_async = source.find(marker_async)
        idx_sync = source.find(marker_sync)
        if idx_async != -1:
            idx = idx_async
        elif idx_sync != -1:
            idx = idx_sync
        else:
            raise AssertionError(f"Could not find '{func_name}'")

        lines = source[idx:].split("\n")
        fn_lines = []
        in_fn = False
        for line in lines:
            stripped = line.rstrip()
            if not stripped and not in_fn:
                continue
            if f"def {func_name}(" in line:
                in_fn = True
                fn_lines.append(stripped)
                continue
            if in_fn:
                if stripped == "":
                    fn_lines.append("")
                    continue
                indent = len(line) - len(line.lstrip())
                if indent == 0 and (
                    stripped.startswith("async def ")
                    or stripped.startswith("def ")
                    or stripped.startswith("@")
                    or stripped.startswith("# ---")
                ):
                    break
                fn_lines.append(stripped)

        fn_source = "\n".join(fn_lines)
        exec(fn_source, _NAMESPACE)

    return {f: _NAMESPACE[f] for f in funcs_to_load}


_funcs = _load_module_functions()
_validate_entity_type = _funcs["_validate_entity_type"]
_normalize_entity_name = _funcs["_normalize_entity_name"]
_format_version_row = _funcs["_format_version_row"]
_archive_memory_version = _funcs["_archive_memory_version"]
_get_memory_versions = _funcs["_get_memory_versions"]
_get_memory_version = _funcs["_get_memory_version"]
_prune_old_versions = _funcs["_prune_old_versions"]


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_stubs():
    """Reset all stubs between tests."""
    _stub_get_supabase_client.reset_mock()
    _stub_logger.reset_mock()
    yield


@pytest.fixture
def mock_db():
    """Mock Supabase client with chainable methods."""
    db = MagicMock()
    _stub_get_supabase_client.return_value = db
    yield db
    _stub_get_supabase_client.reset_mock()


CLIENT_ID = "00000000-0000-0000-0000-000000000001"


# ── _validate_entity_type ─────────────────────────────────────────

def test_validate_entity_type_valid():
    """Should not raise for valid types."""
    for et in ("skill", "client", "contact", "supplier", "user",
               "snapshot", "routine", "agent_result", "agent_metadata"):
        _validate_entity_type(et)  # should not raise


def test_validate_entity_type_invalid():
    """Should raise ValueError for invalid types."""
    with pytest.raises(ValueError, match="Invalid entity_type"):
        _validate_entity_type("invalid_type")


# ── _normalize_entity_name ────────────────────────────────────────

def test_normalize_entity_name():
    """Should lowercase and trim."""
    assert _normalize_entity_name("  Cliente Alpha  ") == "cliente alpha"
    assert _normalize_entity_name("FINANCEIRO:SEMANAL") == "financeiro:semanal"


# ── _format_version_row ───────────────────────────────────────────

def test_format_version_row():
    """Should format a DB row into the API shape."""
    row = {
        "id": "ver-001",
        "memory_id": "mem-001",
        "client_id": CLIENT_ID,
        "entity_type": "snapshot",
        "entity_name": "financeiro:semanal",
        "key": "2025-06-19t10:00:00z",
        "value": {"saldo": 1000},
        "metadata": {"tipo": "snapshot"},
        "source": "specialist",
        "confidence": 0.95,
        "version": 3,
        "archived_at": "2025-06-19T12:00:00Z",
        "original_created_at": "2025-06-18T10:00:00Z",
        "original_updated_at": "2025-06-19T11:00:00Z",
    }
    result = _format_version_row(row)
    assert result["id"] == "ver-001"
    assert result["memory_id"] == "mem-001"
    assert result["value"] == {"saldo": 1000}
    assert result["confidence"] == 0.95
    assert result["version"] == 3


def test_format_version_row_defaults():
    """Should handle missing optional fields."""
    row = {
        "id": "ver-002",
        "client_id": CLIENT_ID,
        "entity_type": "skill",
        "entity_name": "negociacao",
        "key": "tom",
        "value": {},
        "metadata": {},
        "source": "manual",
        "confidence": 1.0,
        "version": 1,
        "archived_at": "2025-06-19T12:00:00Z",
    }
    result = _format_version_row(row)
    assert result["memory_id"] is None
    assert result["original_created_at"] is None
    assert result["metadata"] == {}


# ── _archive_memory_version ───────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_no_existing_row(mock_db):
    """Should return None when there is no existing row (first write)."""
    # Simulate: maybe_single() returns no data
    mock_execute = AsyncMock(return_value=MagicMock(data=None))
    mock_select_chain = MagicMock()
    mock_select_chain.maybe_single = MagicMock(return_value=MagicMock())
    mock_select_chain.maybe_single.return_value.execute = mock_execute

    # Build the chain: db.schema().table().select().eq().eq().eq().eq().maybe_single()
    mock_filter = MagicMock()
    mock_filter.eq.return_value = mock_filter
    mock_filter.maybe_single = MagicMock(return_value=mock_filter)
    mock_filter.execute = mock_execute

    mock_select = MagicMock()
    mock_select.eq.return_value = mock_filter

    mock_table = MagicMock()
    mock_table.select.return_value = mock_select

    mock_schema = MagicMock()
    mock_schema.table.return_value = mock_table

    mock_db.schema.return_value = mock_schema

    result = await _archive_memory_version(
        CLIENT_ID, "snapshot", "financeiro:semanal", "2025-06-19t10:00:00z"
    )
    assert result is None


@pytest.mark.asyncio
async def test_archive_success(mock_db):
    """Should archive the current row and return version count."""
    existing_row = {
        "id": "mem-001",
        "value": {"saldo": 1000},
        "metadata": {"tipo": "snapshot"},
        "source": "specialist",
        "confidence": 0.95,
        "version": 2,
        "created_at": "2025-06-18T10:00:00Z",
        "updated_at": "2025-06-19T11:00:00Z",
    }

    # Build chain: schema.table().select(...).eq().eq().eq().eq().maybe_single().execute()
    read_exec = AsyncMock(return_value=MagicMock(data=existing_row))
    read_maybe_single = MagicMock()
    read_maybe_single.execute = read_exec

    def _build_read_chain(data=None):
        """Build a chain where every .eq() returns a chain ending in .execute()."""
        chain = MagicMock()
        chain.eq.return_value = chain
        if data is not None:
            chain.maybe_single = MagicMock(return_value=chain)
            chain.execute = AsyncMock(return_value=MagicMock(data=data))
        else:
            chain.execute = AsyncMock(return_value=MagicMock(data=[]))
        return chain

    # For the select(*) call on shared_business_memory
    read_chain = _build_read_chain(data=existing_row)
    read_chain.maybe_single = MagicMock(return_value=read_chain)

    # For the insert call on shared_business_memory_versions
    insert_chain = MagicMock()
    insert_chain.execute = AsyncMock(return_value=MagicMock(data=[{"id": "ver-new"}]))

    # For the count query on shared_business_memory_versions
    count_chain = _build_read_chain(data=[{} for _ in range(5)])
    count_chain.execute = AsyncMock(return_value=MagicMock(data=[{} for _ in range(5)]))

    call_count = [0]

    def table_side_effect(name):
        t = MagicMock()
        if name == "shared_business_memory":
            t.select.return_value = read_chain
            return t
        elif name == "shared_business_memory_versions":
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: insert
                t.insert.return_value = insert_chain
                t.select.return_value = count_chain
            else:
                # Subsequent calls: select
                t.select.return_value = count_chain
            return t
        return t

    mock_schema = MagicMock()
    mock_schema.table.side_effect = table_side_effect
    mock_db.schema.return_value = mock_schema

    result = await _archive_memory_version(
        CLIENT_ID, "snapshot", "financeiro:semanal", "2025-06-19t10:00:00z"
    )
    assert result == 5  # 5 versions total (4 + 1 new)


@pytest.mark.asyncio
async def test_archive_invalid_entity_type(mock_db):
    """Should raise ValueError for invalid entity_type."""
    with pytest.raises(ValueError, match="Invalid entity_type"):
        await _archive_memory_version(
            CLIENT_ID, "invalid", "financeiro:semanal", "key"
        )


@pytest.mark.asyncio
async def test_archive_empty_name(mock_db):
    """Should raise ValueError for empty entity_name."""
    with pytest.raises(ValueError, match="entity_name and key are required"):
        await _archive_memory_version(CLIENT_ID, "snapshot", "   ", "key")


# ── _get_memory_versions ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_versions_success(mock_db):
    """Should return a list of formatted versions."""
    rows = [
        {
            "id": "ver-003", "memory_id": "mem-001",
            "client_id": CLIENT_ID, "entity_type": "snapshot",
            "entity_name": "financeiro:semanal", "key": "2025-06-19t10:00:00z",
            "value": {"saldo": 1500}, "metadata": {}, "source": "specialist",
            "confidence": 0.95, "version": 3,
            "archived_at": "2025-06-19T15:00:00Z",
            "original_created_at": None, "original_updated_at": None,
        },
        {
            "id": "ver-002", "memory_id": "mem-001",
            "client_id": CLIENT_ID, "entity_type": "snapshot",
            "entity_name": "financeiro:semanal", "key": "2025-06-19t10:00:00z",
            "value": {"saldo": 1200}, "metadata": {}, "source": "specialist",
            "confidence": 0.90, "version": 2,
            "archived_at": "2025-06-19T12:00:00Z",
            "original_created_at": None, "original_updated_at": None,
        },
    ]

    # Build chain
    mock_exec = AsyncMock(return_value=MagicMock(data=rows))
    mock_order_chain = MagicMock()
    mock_order_chain.execute = mock_exec
    mock_order_chain.limit.return_value = mock_order_chain

    mock_filter = MagicMock()
    mock_filter.eq.return_value = mock_filter
    mock_filter.order.return_value = mock_order_chain

    mock_select = MagicMock()
    mock_select.eq.return_value = mock_filter

    mock_table = MagicMock()
    mock_table.select.return_value = mock_select

    mock_schema = MagicMock()
    mock_schema.table.return_value = mock_table
    mock_db.schema.return_value = mock_schema

    result = await _get_memory_versions(
        CLIENT_ID, "snapshot", "financeiro:semanal", "2025-06-19t10:00:00z"
    )

    assert len(result) == 2
    assert result[0]["version"] == 3
    assert result[1]["version"] == 2
    assert result[0]["value"] == {"saldo": 1500}


@pytest.mark.asyncio
async def test_get_versions_empty(mock_db):
    """Should return empty list when no versions exist."""
    mock_exec = AsyncMock(return_value=MagicMock(data=[]))
    mock_order_chain = MagicMock()
    mock_order_chain.execute = mock_exec
    mock_order_chain.limit.return_value = mock_order_chain

    mock_filter = MagicMock()
    mock_filter.eq.return_value = mock_filter
    mock_filter.order.return_value = mock_order_chain

    mock_select = MagicMock()
    mock_select.eq.return_value = mock_filter

    mock_table = MagicMock()
    mock_table.select.return_value = mock_select

    mock_schema = MagicMock()
    mock_schema.table.return_value = mock_table
    mock_db.schema.return_value = mock_schema

    result = await _get_memory_versions(
        CLIENT_ID, "snapshot", "financeiro:semanal", "nonexistent"
    )
    assert result == []


@pytest.mark.asyncio
async def test_get_versions_invalid_limit(mock_db):
    """Should raise ValueError for invalid limit."""
    with pytest.raises(ValueError, match="limit must be between"):
        await _get_memory_versions(
            CLIENT_ID, "snapshot", "financeiro:semanal", "key", limit=0
        )
    with pytest.raises(ValueError, match="limit must be between"):
        await _get_memory_versions(
            CLIENT_ID, "snapshot", "financeiro:semanal", "key", limit=101
        )


# ── _get_memory_version ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_version_success(mock_db):
    """Should return a specific version."""
    row = {
        "id": "ver-005", "memory_id": "mem-002",
        "client_id": CLIENT_ID, "entity_type": "skill",
        "entity_name": "negociacao", "key": "tom",
        "value": {"tom": "assertivo"}, "metadata": {}, "source": "manual",
        "confidence": 1.0, "version": 5,
        "archived_at": "2025-06-19T16:00:00Z",
        "original_created_at": None, "original_updated_at": None,
    }

    mock_exec = AsyncMock(return_value=MagicMock(data=row))
    mock_filter = MagicMock()
    mock_filter.eq.return_value = mock_filter
    mock_filter.maybe_single = MagicMock(return_value=mock_filter)
    mock_filter.execute = mock_exec

    mock_select = MagicMock()
    mock_select.eq.return_value = mock_filter

    mock_table = MagicMock()
    mock_table.select.return_value = mock_select

    mock_schema = MagicMock()
    mock_schema.table.return_value = mock_table
    mock_db.schema.return_value = mock_schema

    result = await _get_memory_version(
        CLIENT_ID, "skill", "negociacao", "tom", 5
    )
    assert result["version"] == 5
    assert result["value"] == {"tom": "assertivo"}


@pytest.mark.asyncio
async def test_get_version_not_found(mock_db):
    """Should raise ValueError when version doesn't exist."""
    mock_exec = AsyncMock(return_value=MagicMock(data=None))
    mock_filter = MagicMock()
    mock_filter.eq.return_value = mock_filter
    mock_filter.maybe_single = MagicMock(return_value=mock_filter)
    mock_filter.execute = mock_exec

    mock_select = MagicMock()
    mock_select.eq.return_value = mock_filter

    mock_table = MagicMock()
    mock_table.select.return_value = mock_select

    mock_schema = MagicMock()
    mock_schema.table.return_value = mock_table
    mock_db.schema.return_value = mock_schema

    with pytest.raises(ValueError, match="Version 99 not found"):
        await _get_memory_version(
            CLIENT_ID, "skill", "negociacao", "tom", 99
        )


@pytest.mark.asyncio
async def test_get_version_invalid_version_number(mock_db):
    """Should raise ValueError for version < 1."""
    with pytest.raises(ValueError, match="version must be >= 1"):
        await _get_memory_version(CLIENT_ID, "skill", "neg", "key", 0)
    with pytest.raises(ValueError, match="version must be >= 1"):
        await _get_memory_version(CLIENT_ID, "skill", "neg", "key", -1)


# ── _prune_old_versions ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_prune_no_op(mock_db):
    """Should return 0 when within limit."""
    rows = [{"id": f"v-{i}"} for i in range(5)]  # 5 versions, limit 50

    mock_exec = AsyncMock(return_value=MagicMock(data=rows))
    mock_order_chain = MagicMock()
    mock_order_chain.execute = mock_exec

    mock_filter = MagicMock()
    mock_filter.eq.return_value = mock_filter
    mock_filter.order.return_value = mock_order_chain

    mock_select = MagicMock()
    mock_select.eq.return_value = mock_filter

    mock_table = MagicMock()
    mock_table.select.return_value = mock_select

    mock_schema = MagicMock()
    mock_schema.table.return_value = mock_table
    mock_db.schema.return_value = mock_schema

    result = await _prune_old_versions(
        CLIENT_ID, "snapshot", "financeiro:semanal", "key", max_versions=50
    )
    assert result == 0


@pytest.mark.asyncio
async def test_prune_exceeds_limit(mock_db):
    """Should delete oldest versions when over limit."""
    rows = [{"id": f"v-{i}"} for i in range(10)]  # 10 versions, limit 5

    mock_exec = AsyncMock(return_value=MagicMock(data=rows))
    mock_order_chain = MagicMock()
    mock_order_chain.execute = mock_exec

    mock_filter = MagicMock()
    mock_filter.eq.return_value = mock_filter
    mock_filter.order.return_value = mock_order_chain

    mock_select = MagicMock()
    mock_select.eq.return_value = mock_filter

    # Mock delete chain
    mock_delete_exec = AsyncMock()
    mock_delete_filter = MagicMock()
    mock_delete_filter.eq.return_value = mock_delete_filter
    mock_delete_filter.execute = mock_delete_exec

    mock_delete = MagicMock()
    mock_delete.eq.return_value = mock_delete_filter

    # Need a separate mock for the delete table call
    def table_side_effect(name):
        if name == "shared_business_memory_versions":
            # For select calls
            t = MagicMock()
            t.select.return_value = mock_select
            t.delete.return_value = mock_delete
            return t
        return MagicMock()

    mock_schema = MagicMock()
    mock_schema.table.side_effect = table_side_effect
    mock_db.schema.return_value = mock_schema

    result = await _prune_old_versions(
        CLIENT_ID, "snapshot", "financeiro:semanal", "key", max_versions=5
    )
    assert result == 5  # 10 - 5 = 5 deleted


@pytest.mark.asyncio
async def test_prune_invalid_max(mock_db):
    """Should raise ValueError for max_versions < 1."""
    with pytest.raises(ValueError, match="max_versions must be >= 1"):
        await _prune_old_versions(
            CLIENT_ID, "snapshot", "f:s", "k", max_versions=0
        )
