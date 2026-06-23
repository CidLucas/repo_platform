# tests/unit/test_shared_memory_export.py
"""Unit tests for shared_memory_export tool (T5.4).

Tests the _shared_memory_export_logic function with:
- Mocked Supabase client (avoids real database)
- Covers: success, empty results, filtered exports, invalid input

The function is loaded in isolation via exec() to avoid triggering the
full package dependency chain.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


# -- Stand-in ToolError --------------------------------------------

class ToolError(Exception):
    """Replacement for fastmcp.exceptions.ToolError in isolation."""
    pass


# -- Load the function in isolation --------------------------------

# Build a minimal namespace with all needed stubs
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
    """Extract _shared_memory_export_logic from memory_module.py source."""
    import pathlib
    mod_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "src" / "tool_pool_api" / "server" / "tool_modules"
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

    # Extract _shared_memory_export_logic
    marker = "async def _shared_memory_export_logic("
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
        if "async def _shared_memory_export_logic(" in line:
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
    return _NAMESPACE["_shared_memory_export_logic"]


_shared_memory_export_logic = _load_function()


# -- Helpers -------------------------------------------------------


def _make_result(rows):
    """Build a mock Supabase execute() result with .data."""
    mock_result = MagicMock()
    mock_result.data = rows
    return mock_result


def _setup_supabase_chain(mock_supabase, rows):
    """Set up the full Supabase query chain mock so
    db.schema().table().select().eq().order().execute() returns the rows."""
    result = _make_result(rows)

    # Build the chain bottom-up:
    # query.execute() -> result
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.execute = AsyncMock(return_value=result)

    # schema.table() -> query
    schema_mock = MagicMock()
    schema_mock.table.return_value = query

    # db.schema() -> schema_mock
    mock_supabase.schema.return_value = schema_mock


def _sample_rows(count=3):
    """Build sample row data for testing."""
    rows = []
    for i in range(1, count + 1):
        rows.append({
            "id": f"fact-{i:03d}",
            "entity_type": "client",
            "entity_name": f"cliente_{i}",
            "key": f"preferencia_{i}",
            "value": {"canal": "email", "prioridade": i},
            "metadata": {"agent_id": "agent-1"},
            "source": "manual",
            "confidence": 0.9,
            "version": 1,
            "created_at": "2026-06-19T10:00:00Z",
            "updated_at": "2026-06-19T10:00:00Z",
        })
    return rows


# -- Fixtures ------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_stubs():
    """Reset all stubs between tests."""
    _stub_get_supabase_client.reset_mock()
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
async def test_export_success(mock_supabase):
    """Should return all records for a client."""
    client_id = str(uuid.uuid4())
    sample = _sample_rows(count=3)

    _setup_supabase_chain(mock_supabase, sample)

    result = await _shared_memory_export_logic(client_id=client_id)

    assert result["client_id"] == client_id
    assert result["entity_type_filter"] is None
    assert result["entity_name_filter"] is None
    assert result["total_records"] == 3
    assert len(result["records"]) == 3
    assert result["records"][0]["id"] == "fact-001"
    assert result["records"][0]["entity_type"] == "client"
    assert result["records"][0]["key"] == "preferencia_1"
    assert result["records"][0]["value"] == {"canal": "email", "prioridade": 1}
    assert result["records"][0]["source"] == "manual"
    assert result["records"][0]["confidence"] == 0.9
    assert result["records"][0]["version"] == 1


@pytest.mark.asyncio
async def test_export_empty(mock_supabase):
    """Should return empty records array for client with no data."""
    client_id = str(uuid.uuid4())

    _setup_supabase_chain(mock_supabase, [])

    result = await _shared_memory_export_logic(client_id=client_id)

    assert result["client_id"] == client_id
    assert result["total_records"] == 0
    assert result["records"] == []


@pytest.mark.asyncio
async def test_export_none_data(mock_supabase):
    """Should handle None .data gracefully (returns empty)."""
    client_id = str(uuid.uuid4())

    _setup_supabase_chain(mock_supabase, None)

    result = await _shared_memory_export_logic(client_id=client_id)

    assert result["total_records"] == 0
    assert result["records"] == []


@pytest.mark.asyncio
async def test_export_filtered_by_entity_type(mock_supabase):
    """Should apply entity_type filter when provided."""
    client_id = str(uuid.uuid4())
    sample = _sample_rows(count=1)

    _setup_supabase_chain(mock_supabase, sample)

    result = await _shared_memory_export_logic(
        client_id=client_id,
        entity_type="client",
    )

    assert result["entity_type_filter"] == "client"
    assert result["total_records"] == 1


@pytest.mark.asyncio
async def test_export_filtered_by_entity_name(mock_supabase):
    """Should normalize and apply entity_name filter."""
    client_id = str(uuid.uuid4())
    sample = _sample_rows(count=1)

    _setup_supabase_chain(mock_supabase, sample)

    result = await _shared_memory_export_logic(
        client_id=client_id,
        entity_name="  Cliente_1  ",
    )

    assert result["entity_name_filter"] == "cliente_1"
    assert result["total_records"] == 1


@pytest.mark.asyncio
async def test_export_invalid_entity_type():
    """Should raise ValueError for invalid entity_type."""
    client_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="Invalid entity_type"):
        await _shared_memory_export_logic(
            client_id=client_id,
            entity_type="invalid_type",
        )


@pytest.mark.asyncio
async def test_export_logs_success(mock_supabase):
    """Should log entry and completion messages."""
    client_id = str(uuid.uuid4())

    _setup_supabase_chain(mock_supabase, [])

    await _shared_memory_export_logic(client_id=client_id)

    # Check that info logs were emitted
    info_calls = [
        c[0][0] for c in _stub_logger.info.call_args_list
        if isinstance(c[0], tuple) and len(c[0]) > 0
    ]
    assert any("shared_memory_export" in str(c) for c in info_calls)
    export_logs = [c for c in info_calls if "shared_memory_export" in str(c)]
    assert any("complete" in str(c) for c in export_logs)


@pytest.mark.asyncio
async def test_export_preserves_metadata(mock_supabase):
    """Should include metadata field in exported records."""
    client_id = str(uuid.uuid4())
    rows = [{
        "id": "fact-meta",
        "entity_type": "client",
        "entity_name": "cliente_meta",
        "key": "info",
        "value": {"dado": "valor"},
        "metadata": {"source_agent": "specialist-7", "priority": 5},
        "source": "specialist",
        "confidence": 0.99,
        "version": 2,
        "created_at": "2026-06-19T10:00:00Z",
        "updated_at": "2026-06-19T11:00:00Z",
    }]

    _setup_supabase_chain(mock_supabase, rows)

    result = await _shared_memory_export_logic(client_id=client_id)

    assert result["records"][0]["metadata"] == {
        "source_agent": "specialist-7",
        "priority": 5,
    }
    assert result["records"][0]["confidence"] == 0.99
    assert result["records"][0]["version"] == 2

# =====================================================================
# B5 — Export lifecycle fields (validates B3)
# Goal: Implementar exportação de memórias como JSON com lifecycle fields
# Behavior B5: Testes de unidade para export com lifecycle fields (valida B3)
# AC#1: Records exportados incluem ttl_tier, soft_delete_at, hard_delete_at, category
# AC#3: Export continua read-only — não filtra flushed entries
# Decision: fix_and_extend — adicionar testes de lifecycle ao test_shared_memory_export.py
# =====================================================================


def _sample_rows_with_lifecycle(count=3):
    """Build sample row data with lifecycle fields for B5 testing."""
    rows = []
    for i in range(1, count + 1):
        rows.append({
            # Existing fields (must remain in output)
            "id": f"fact-lifecycle-{i:03d}",
            "entity_type": "client",
            "entity_name": f"cliente_{i}",
            "key": f"preferencia_{i}",
            "value": {"canal": "email", "prioridade": i},
            "metadata": {"agent_id": "agent-1"},
            "source": "manual",
            "confidence": 0.9,
            "version": 1,
            "created_at": "2026-06-19T10:00:00Z",
            "updated_at": "2026-06-19T10:00:00Z",
            # NEW lifecycle fields (AC#1)
            "ttl_tier": "standard",
            "soft_delete_at": None,
            "hard_delete_at": "2027-06-19T10:00:00Z",
            "category": "business",
        })
    return rows


@pytest.mark.asyncio
async def test_b5_export_includes_lifecycle_fields(mock_supabase):
    """AC#1 — Records exportados devem incluir os 4 lifecycle fields.

    B5 valida B3: a funcao _shared_memory_export_logic deve propagar
    os campos de ciclo de vida (ttl_tier, soft_delete_at, hard_delete_at,
    category) para o dicionario de cada record exportado.

    RED: esta assertion falha porque a implementacao atual em main
    nao exporta os campos de lifecycle.
    """
    client_id = str(uuid.uuid4())
    sample = _sample_rows_with_lifecycle(count=1)

    _setup_supabase_chain(mock_supabase, sample)

    result = await _shared_memory_export_logic(client_id=client_id)

    assert result["total_records"] == 1
    record = result["records"][0]

    # AC#1 — Lifecycle fields must be present in exported record
    assert "ttl_tier" in record, (
        "B5/AC#1: 'ttl_tier' missing from exported record. "
        "Behavior B3 must add this lifecycle field to export output."
    )
    assert record["ttl_tier"] == "standard", (
        f"Expected ttl_tier='standard', got {record.get('ttl_tier')!r}"
    )

    assert "soft_delete_at" in record, (
        "B5/AC#1: 'soft_delete_at' missing from exported record."
    )
    assert record["soft_delete_at"] is None, (
        f"Expected soft_delete_at=None, got {record.get('soft_delete_at')!r}"
    )

    assert "hard_delete_at" in record, (
        "B5/AC#1: 'hard_delete_at' missing from exported record."
    )
    assert record["hard_delete_at"] == "2027-06-19T10:00:00Z", (
        f"Expected hard_delete_at='2027-06-19T10:00:00Z', "
        f"got {record.get('hard_delete_at')!r}"
    )

    assert "category" in record, (
        "B5/AC#1: 'category' missing from exported record."
    )
    assert record["category"] == "business", (
        f"Expected category='business', got {record.get('category')!r}"
    )
