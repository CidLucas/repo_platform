# tests/unit/test_memory_confirm_item.py
"""Unit tests for confirm_memory_item tool (B6 / Issue #19).

Tests the _shared_memory_confirm_memory_item_logic function with:
- Mocked Supabase client (avoids real database)
- Validation that memory_id belongs to the client_id
- Rejection of already-curated entries
- Correct UPDATE of curated=true, expires_at=NULL
- Parameter validation (memory_id <= 0, empty client_id)

According to B6 spec, confirm_memory_item should:
  "Marcar entrada da shared memory como curated=true, impedindo expiração futura.
   Valida que memory_id pertence ao client_id.
   Se já curated=true, retorna erro.
   Faz UPDATE shared_business_memory SET curated=true, expires_at=NULL."

GOAL: Hook de handoff entre agentes na shared memory
BEHAVIOR: B6 — Adicionar tool confirm_memory_item em memory_module.py (auxiliar)
AC: AC1 — Agente A escreve learning notes na shared memory durante handoff
DECISÃO DO PLANNER: create_new — novo pacote handoff/ com extensão de AgentState
"""

# ruff: noqa: F841 (unused variables are intentional for isolation)

from __future__ import annotations

import uuid
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest


# ── Stand-in ToolError ────────────────────────────────────────────

class ToolError(Exception):
    """Replacement for fastmcp.exceptions.ToolError in isolation."""
    pass


# ── Shared mocks ─────────────────────────────────────────────────

_stub_logger = MagicMock()
_stub_get_supabase_client = AsyncMock()


def _make_row(
    *,
    memory_id: str | None = None,
    client_id: str | None = None,
    curated: bool = False,
    expires_at: str | None = None,
    entity_type: str = "skill",
    entity_name: str = "tom_amigavel",
    key: str = "preferencia_horario",
    value: dict | None = None,
    source: str = "specialist",
    confidence: float = 0.8,
    version: int = 1,
    metadata: dict | None = None,
    ttl_tier: str | None = "memory_agent_lo",
    soft_delete_at: str | None = None,
    hard_delete_at: str | None = None,
    archived: bool = False,
) -> dict:
    """Helper to build a mock DB row with curated/expires_at columns."""
    uid = memory_id or str(uuid.uuid4())
    return {
        "id": uid,
        "client_id": client_id or "00000000-0000-0000-0000-000000000001",
        "entity_type": entity_type,
        "entity_name": entity_name,
        "key": key,
        "value": value or {"horario": "09:00"},
        "source": source,
        "confidence": confidence,
        "version": version,
        "metadata": metadata or {},
        "curated": curated,
        "expires_at": expires_at,
        "ttl_tier": ttl_tier,
        "soft_delete_at": soft_delete_at,
        "hard_delete_at": hard_delete_at,
        "archived": archived,
        "created_at": "2025-06-19T10:00:00Z",
        "updated_at": "2025-06-19T10:00:00Z",
    }


# ── Module source path ───────────────────────────────────────────

_MODULE_PATH = (
    __import__("pathlib").Path(__file__).parent.parent.parent
    / "src" / "tool_pool_api" / "server" / "tool_modules"
    / "memory_module.py"
)


# ── Extract a single function from source by name ────────────────

def _extract_func(source: str, func_name: str, source_name: str = "memory_module.py") -> str:
    """Extract a function definition from source by its name.

    Works for `def func_name(` and `async def func_name(`.
    Returns the complete function source including its signature.
    """
    for prefix in ("async def ", "def "):
        marker = f"{prefix}{func_name}("
        idx = source.find(marker)
        if idx != -1:
            break
    else:
        raise AssertionError(f"Could not find function '{func_name}' in {source_name}")

    lines = source[idx:].split("\n")
    fn_lines: list[str] = []
    brace_depth = 0
    started = False

    for line in lines:
        stripped = line.rstrip()
        if not started:
            if f"def {func_name}(" in stripped:
                started = True
                fn_lines.append(stripped)
            continue

        # Track brace depth (for dicts/lists/parens within the function)
        brace_depth += stripped.count("{") - stripped.count("}")
        brace_depth += stripped.count("[") - stripped.count("]")
        brace_depth += stripped.count("(") - stripped.count(")")

        # Stop when we hit a new function definition at column 0
        # and we're not inside nested braces
        indent = len(line) - len(line.lstrip())
        if indent == 0 and brace_depth <= 0:
            if stripped.startswith(("async def ", "def ", "@", "# ---", "logger.")):
                break

        fn_lines.append(stripped)

    result = "\n".join(fn_lines)
    # Validate it compiles
    compile(result, f"<{func_name}>", "exec")
    return result


# ── Inline definitions (constants that we replicate, not extract) ─

_INLINE_SOURCE = r'''
from __future__ import annotations

_TABLE = "shared_business_memory"
'''


# ── Namespace builder ────────────────────────────────────────────

def _build_namespace():
    """Build the namespace with all constants and helpers needed by confirm logic."""
    ns: dict = {
        "__name__": "memory_module",
        "__builtins__": __builtins__,
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
        "blu_context_service": MagicMock(),
        "blu_supabase_client": MagicMock(),
    }
    ns["blu_auth"] = MagicMock()
    ns["blu_auth"].mcp = MagicMock()
    ns["blu_auth"].mcp.auth_middleware = MagicMock()
    ns["blu_auth"].mcp.auth_middleware.mcp_inject_client_id = MagicMock(return_value=lambda fn: fn)

    source = _MODULE_PATH.read_text()

    # 1. Execute inline constants
    exec(_INLINE_SOURCE, ns)

    # 2. Extract helper functions needed by confirm logic
    for helper_name in [
        "_normalize_entity_name",
    ]:
        try:
            fn_source = _extract_func(source, helper_name)
            exec(fn_source, ns)
        except (AssertionError, SyntaxError) as e:
            raise RuntimeError(f"Failed to extract helper {helper_name}: {e}")

    # 3. The main target function — will raise AssertionError since it
    #    doesn't exist yet (RED phase). That's expected.
    func_source = _extract_func(source, "_shared_memory_confirm_memory_item_logic")
    exec(func_source, ns)
    return ns


@pytest.fixture(scope="module")
def ns():
    return _build_namespace()


@pytest.fixture(scope="module")
def logic(ns):
    return ns["_shared_memory_confirm_memory_item_logic"]


@pytest.fixture(autouse=True)
def _reset_mocks():
    """Reset all shared mocks before each test."""
    _stub_get_supabase_client.reset_mock()
    _stub_get_supabase_client.return_value = _mock_db()


def _mock_db():
    """Build a mock Supabase client chain (plain MagicMock, not async)."""
    db = MagicMock()
    db.schema.return_value = db
    db.table.return_value = db
    db.select.return_value = db
    db.eq.return_value = db
    db.single.return_value = db
    db.execute.return_value = MagicMock(data=[])
    db.update.return_value = db
    return db


# ====================================================================
# B6 — confirm_memory_item parameter validation
# ====================================================================


class TestConfirmParameterValidation:
    """Parameter-level validation in _shared_memory_confirm_memory_item_logic."""

    @pytest.mark.parametrize(
        "bad_memory_id", [
            0,
            -1,
            -999,
        ]
    )
    @pytest.mark.asyncio
    async def test_rejects_non_positive_memory_id(self, logic, bad_memory_id):
        """Non-positive memory_id should raise ValueError."""
        with pytest.raises(ValueError, match="memory_id must be a positive integer"):
            await logic(
                memory_id=bad_memory_id,
                client_id=str(uuid.uuid4()),
            )

    @pytest.mark.parametrize(
        "bad_client_id", [
            "",
            "   ",
        ]
    )
    @pytest.mark.asyncio
    async def test_rejects_empty_client_id(self, logic, bad_client_id):
        """Empty client_id should raise ValueError."""
        with pytest.raises(ValueError, match="client_id is required"):
            await logic(
                memory_id=1,
                client_id=bad_client_id,
            )


# ====================================================================
# B6 — confirm_memory_item success path
# ====================================================================


class TestConfirmItemSuccess:
    """Happy-path: confirming an existing, non-curated memory item."""

    @pytest.mark.asyncio
    async def test_confirms_existing_memory(self, logic):
        """Confirm a valid memory entry that belongs to the client."""
        client_id = str(uuid.uuid4())
        memory_id = str(uuid.uuid4())
        row = _make_row(memory_id=memory_id, client_id=client_id, curated=False)

        db = _mock_db()
        _stub_get_supabase_client.return_value = db

        # First call returns the existing row (fetch before update)
        db.execute.return_value = MagicMock(data=[row])

        result = await logic(
            memory_id=memory_id,
            client_id=client_id,
        )

        # Verify the update was called
        db.update.assert_called_once()
        # Verify eq filters: memory_id and client_id
        eq_calls = db.eq.call_args_list
        assert len(eq_calls) >= 2, "Expected at least 2 eq() calls (memory_id + client_id)"

        # Verify result structure
        assert isinstance(result, dict)
        assert result.get("id") == memory_id

    @pytest.mark.asyncio
    async def test_update_sets_curated_true_and_expires_at_null(self, logic):
        """Verify that UPDATE sets curated=true and expires_at=NULL."""
        client_id = str(uuid.uuid4())
        memory_id = str(uuid.uuid4())
        original_expires_at = "2025-07-19T10:00:00Z"
        row = _make_row(
            memory_id=memory_id,
            client_id=client_id,
            curated=False,
            expires_at=original_expires_at,
        )

        db = _mock_db()
        _stub_get_supabase_client.return_value = db

        # First query returns existing row
        db.execute.return_value = MagicMock(data=[row])
        # Update returns the updated row
        updated_row = dict(row, curated=True, expires_at=None)
        db.execute.side_effect = [
            MagicMock(data=[row]),        # first: fetch existing
            MagicMock(data=[updated_row]), # second: return updated
        ]

        result = await logic(
            memory_id=memory_id,
            client_id=client_id,
        )

        # Verify the update payload
        update_call_args = db.update.call_args[0][0]
        assert update_call_args.get("curated") is True, \
            "Expected curated=true in UPDATE payload"
        assert update_call_args.get("expires_at") is None, \
            "Expected expires_at=NULL in UPDATE payload"


# ====================================================================
# B6 — confirm_memory_item error paths
# ====================================================================


class TestConfirmItemErrors:
    """Error-path: edge cases that should raise ToolError."""

    @pytest.mark.asyncio
    async def test_rejects_memory_id_from_other_client(self, logic):
        """Reject if memory_id does not belong to the client_id."""
        client_id = str(uuid.uuid4())
        other_client = str(uuid.uuid4())
        memory_id = str(uuid.uuid4())
        row = _make_row(memory_id=memory_id, client_id=other_client, curated=False)

        db = _mock_db()
        _stub_get_supabase_client.return_value = db
        db.execute.return_value = MagicMock(data=[row])

        with pytest.raises(ToolError, match="not found|not belong|not owned"):
            await logic(
                memory_id=memory_id,
                client_id=client_id,
            )

    @pytest.mark.asyncio
    async def test_rejects_memory_not_found(self, logic):
        """Reject if memory_id does not exist in the database."""
        client_id = str(uuid.uuid4())
        memory_id = str(uuid.uuid4())

        db = _mock_db()
        _stub_get_supabase_client.return_value = db
        db.execute.return_value = MagicMock(data=[])  # no rows returned

        with pytest.raises(ToolError, match="not found"):
            await logic(
                memory_id=memory_id,
                client_id=client_id,
            )

    @pytest.mark.asyncio
    async def test_rejects_already_curated_memory(self, logic):
        """Reject if the memory entry is already curated."""
        client_id = str(uuid.uuid4())
        memory_id = str(uuid.uuid4())
        row = _make_row(memory_id=memory_id, client_id=client_id, curated=True)

        db = _mock_db()
        _stub_get_supabase_client.return_value = db
        db.execute.return_value = MagicMock(data=[row])

        with pytest.raises(ToolError, match="already curated|already confirmed"):
            await logic(
                memory_id=memory_id,
                client_id=client_id,
            )
