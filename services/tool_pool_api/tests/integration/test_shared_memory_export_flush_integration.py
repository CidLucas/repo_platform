# tests/integration/test_shared_memory_export_flush_integration.py
"""Integration RED test for B4 — shared_memory_flush (AC#4).

Validates AC#4: flush must mark metadata.flushed_at in matching entries,
**merging** with existing metadata fields (B1 fix + B2 extension).

Current code at memory_module.py:2447 calls:
    .update({"metadata": {"flushed_at": now_iso}})
which REPLACES the entire metadata JSONB, destroying any pre-existing
fields.  This RED test exercises that bug by pre-populating an entry
with non-trivial metadata and asserting the merged payload preserves
the original keys while adding ``flushed_at``.

Uses exec()-based isolation (same pattern as the unit tests) to avoid
the full FastMCP / Supabase dependency chain.
"""

import re
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


# -- Stand-in ToolError --------------------------------------------

class ToolError(Exception):
    """Replacement for fastmcp.exceptions.ToolError in isolation."""
    pass


# -- Constants -----------------------------------------------------

_REPO_ROOT = "/home/ec2-user/repo_platform"
_MODULE_PATH = (
    f"{_REPO_ROOT}/services/tool_pool_api/src/tool_pool_api/server/"
    "tool_modules/memory_module.py"
)


# -- Load _shared_memory_flush_logic in isolation ------------------

_stub_logger = MagicMock()
_stub_get_supabase_client = AsyncMock()

_NAMESPACE: dict = {
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


def _load_flush_logic() -> callable:
    """Extract _shared_memory_flush_logic from memory_module.py source."""
    import pathlib
    source = pathlib.Path(_MODULE_PATH).read_text()

    # 1. _VALID_ENTITY_TYPES constant
    vt_marker = "_VALID_ENTITY_TYPES: frozenset[str] = frozenset("
    vt_idx = source.find(vt_marker)
    assert vt_idx != -1, "Could not find _VALID_ENTITY_TYPES"
    vt_lines = []
    for vline in source[vt_idx:].split("\n"):
        vt_lines.append(vline.rstrip())
        if ")" in vline and not vline.strip().startswith("#"):
            break
    exec("\n".join(vt_lines), _NAMESPACE)

    # 2. Helpers
    for helper_name in ("_validate_entity_type", "_normalize_entity_name",
                         "_is_flushed", "_check_not_flushed"):
        marker = f"def {helper_name}("
        idx = source.find(marker)
        if idx == -1:
            continue
        in_fn = False
        fn_lines: list[str] = []
        for line in source[idx:].split("\n"):
            stripped = line.rstrip()
            if f"def {helper_name}(" in stripped:
                in_fn = True
                fn_lines.append(stripped)
                continue
            if in_fn:
                if stripped == "":
                    fn_lines.append("")
                    continue
                indent = len(line) - len(line.lstrip())
                if indent == 0 and stripped and not stripped.strip().startswith("#"):
                    break
                fn_lines.append(stripped)
        exec("\n".join(fn_lines), _NAMESPACE)

    # 3. _TABLE constant
    table_marker = '_TABLE = "shared_business_memory"'
    tidx = source.find(table_marker)
    assert tidx != -1, "Could not find _TABLE"
    exec(source[tidx : tidx + len(table_marker) + 1], _NAMESPACE)

    # 4. _shared_memory_flush_logic
    flush_marker = "async def _shared_memory_flush_logic("
    fidx = source.find(flush_marker)
    assert fidx != -1, f"Could not find '{flush_marker}'"

    section_start = source.rfind("#", 0, fidx)
    assert section_start != -1

    in_fn = False
    fn_lines: list[str] = []
    for line in source[section_start:].split("\n"):
        s = line.rstrip()
        if not s and not in_fn:
            continue
        if "async def _shared_memory_flush_logic(" in s:
            in_fn = True
            fn_lines.append(s)
            continue
        if in_fn:
            if s == "":
                fn_lines.append("")
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0 and s.startswith("# -------"):
                break
            if indent == 0 and (
                s.startswith("async def ") or s.startswith("@") or s.startswith("def ")
            ):
                break
            fn_lines.append(s)

    exec("\n".join(fn_lines), _NAMESPACE)
    return _NAMESPACE["_shared_memory_flush_logic"]


_flush_logic = _load_flush_logic()
_TABLE = _NAMESPACE.get("_TABLE", "shared_business_memory")


# -- Helpers -------------------------------------------------------

def _make_result(data):
    """Build a mock Supabase execute() result with .data."""
    mock_result = MagicMock()
    mock_result.data = data
    return mock_result


# -- Fixtures ------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_stubs():
    _stub_get_supabase_client.reset_mock()
    _stub_logger.reset_mock()
    yield
    _stub_get_supabase_client.reset_mock()
    _stub_logger.reset_mock()


@pytest.fixture
def db():
    db_mock = MagicMock()
    _stub_get_supabase_client.return_value = db_mock
    yield db_mock
    _stub_get_supabase_client.reset_mock()


# =====================================================================
# B4 — AC#4: flush marks metadata.flushed_at in entries
# =====================================================================


class TestFlushMarksFlushedAt:
    """AC#4 — flush must mark ``metadata.flushed_at`` on matching entries,
    while **preserving** any pre-existing metadata fields (B1 fix + B2
    extension)."""

    @pytest.mark.asyncio
    async def test_flush_marks_flushed_at_preserving_existing_metadata(self, db):
        """Calling _shared_memory_flush_logic on an entry with rich
        pre-existing metadata must produce an update payload that
        BOTH contains ``flushed_at`` AND retains the original keys.

        The current implementation calls
            .update({"metadata": {"flushed_at": now_iso}})
        which REPLACES the entire metadata, dropping every other key.
        This test asserts the post-fix behaviour: the metadata passed
        to .update() must be a merge of the existing dict and
        ``{"flushed_at": <iso-timestamp>}``.
        """
        client_id = str(uuid.uuid4())

        # Existing metadata that must survive the flush (B1 fix).
        existing_meta = {
            "key1": "value1",
            "key2": "value2",
            "created_by": "user_x",
            "source": "manual",
        }

        row = {
            "id": "row-1",
            "client_id": client_id,
            "entity_type": "client",
            "entity_name": "cliente_teste",
            "key": "preferencia_1",
            "value": {"canal": "email"},
            "metadata": existing_meta,
            "source": "manual",
            "confidence": 0.9,
            "version": 1,
            "created_at": "2026-06-19T10:00:00Z",
            "updated_at": "2026-06-19T10:00:00Z",
        }

        # ---- Build the mocked Supabase chain ------------------------
        # The flush function performs exactly one query that returns
        # matching rows (select id, metadata) and one update that writes
        # the new metadata back.
        main_result = _make_result([row])

        main_query = MagicMock()
        main_query.select.return_value = main_query
        main_query.eq.return_value = main_query
        main_query.execute = AsyncMock(return_value=main_result)

        # Capture the payload handed to .update().
        captured: dict = {}
        update_result = _make_result(None)

        update_query = MagicMock()
        update_query.in_.return_value = update_query
        update_query.eq.return_value = update_query
        update_query.execute = AsyncMock(return_value=update_result)

        def _capture(payload):
            # Deep-copy so later mutations to the dict don't affect us.
            import copy
            captured["payload"] = copy.deepcopy(payload)
            return update_query

        update_query.update = MagicMock(side_effect=_capture)

        schema_mock = MagicMock()
        call_count = [0]

        def _table(name):
            call_count[0] += 1
            return main_query if call_count[0] == 1 else update_query

        schema_mock.table = MagicMock(side_effect=_table)
        db.schema.return_value = schema_mock

        # ---- Execute -------------------------------------------------
        result = await _flush_logic(client_id=client_id)

        # ---- AC#4: result reports a successful flush -----------------
        assert result["flushed_count"] == 1, (
            f"expected flushed_count=1, got {result['flushed_count']!r}"
        )
        assert result["total_scanned"] == 1
        assert result["skipped_already_flushed"] == 0
        assert "flushed_at" in result, "result must include the flush timestamp"

        # ---- AC#4: the update call was issued with metadata ---------
        assert captured.get("payload"), (
            "update() was never called — flush must write the new metadata"
        )
        assert "metadata" in captured["payload"], (
            f"update() payload must contain 'metadata', got: {captured['payload']!r}"
        )
        new_meta = captured["payload"]["metadata"]

        # ---- AC#4: flushed_at is present -----------------------------
        assert "flushed_at" in new_meta, (
            f"flushed_at must be added to metadata, got: {new_meta!r}"
        )
        # The timestamp must look like an ISO 8601 string.
        assert isinstance(new_meta["flushed_at"], str), (
            f"flushed_at must be a string, got {type(new_meta['flushed_at']).__name__}"
        )
        assert re.match(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
            new_meta["flushed_at"],
        ), f"flushed_at must be ISO 8601, got: {new_meta['flushed_at']!r}"

        # ---- B1 fix: existing metadata fields are preserved ---------
        for key, value in existing_meta.items():
            assert key in new_meta, (
                f"existing metadata key {key!r} must survive the flush; "
                f"new metadata was {new_meta!r}"
            )
            assert new_meta[key] == value, (
                f"existing metadata value for {key!r} must be preserved; "
                f"expected {value!r}, got {new_meta[key]!r}"
            )
