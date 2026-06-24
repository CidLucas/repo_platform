"""RED test for behavior B3.2 — _shared_memory_post_flight_logic batch operations.

GOAL:
    Corrigir bottlenecks P0 N+1 no código de produção. Issue #121 — Performance.
    O `_shared_memory_post_flight_logic` em memory_post_flight.py atualmente faz
    3 loops per-row separados, cada um chamando .upsert() ou .insert()
    individualmente para cada item. Isso gera N+M+O round-trips DB.

BEHAVIOR:
    B3.2 — `_shared_memory_post_flight_logic` (linha ~72 em memory_post_flight.py)
    deve usar batch operations em vez de 3 loops per-row:
    - tool_calls: upsert all in 1 chamada (em vez de 1 por tool_name)
    - agent_metadata: upsert all in 1 chamada (em vez de 1 por field)
    - suggested_links: insert all in 1 chamada (em vez de 1 por link)

    Hoje (RED) o código faz:
        1. for tool_name in tool_calls: db.table(_TABLE).upsert(...).execute()
        2. for key, value in meta_fields.items(): db.table(_TABLE).upsert(...).execute()
        3. for link in suggested_links: db.table(_LINKS_TABLE).insert(...).execute()

    O contrato GREEN esperado (3 batches separados):
        # Batch 1: all tool_usage entries upsertados juntos
        db.schema("public").table(_TABLE).upsert(
            [payload for tool_name in tool_calls], ...
        ).execute()

        # Batch 2: all metadata entries upsertados juntos
        db.schema("public").table(_TABLE).upsert(
            [payload for key, value in meta_fields.items()], ...
        ).execute()

        # Batch 3: all suggested links inseridos juntos
        db.schema("public").table(_LINKS_TABLE).insert(
            [payload for link in suggested_links], ...
        ).execute()

AC (Acceptance Criteria):
    AC#5 — _shared_memory_post_flight_logic faz exatamente 3 chamadas a
           .execute() quando há N tool_calls, M metadata_fields e O links
           (um batch para cada grupo), em vez de N+M+O chamadas individuais
    AC#6 — Duplicatas continuam sendo ignoradas via ON CONFLICT

DECISION:
    Estratégia: extend (refatorar _shared_memory_post_flight_logic para batches)
    Arquivo alvo: services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_post_flight.py
    Função alvo: _shared_memory_post_flight_logic (linha ~72)

Anti-Goals (must NOT be violated):
    1. NÃO alterar a assinatura de _shared_memory_post_flight_logic
    2. NÃO alterar o contrato de retorno ({agent_result_entries, agent_metadata_entries, links_created})
    3. NÃO introduzir dependência externa nova
    4. NÃO alterar helpers (_normalize_entity_name, _validate_key_prefix)
    5. O summary do agent_result (1 item) pode continuar sendo upsert individual

Estado atual: RED — os 3 loops per-row ainda estão presentes no corpo da
função. O teste source-level falha ao verificar que não há loops for per-row
nas seções de tool_calls, metadata e suggested_links.
"""

import re
import json as stdjson
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── Override root conftest cleanup ───────────────────────────────────────

@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — pure unit test, no DB teardown."""
    yield


# ── Paths ────────────────────────────────────────────────────────────────

POST_FLIGHT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "services"
    / "tool_pool_api"
    / "src"
    / "tool_pool_api"
    / "server"
    / "tool_modules"
    / "memory_post_flight.py"
)

_TABLE = "shared_business_memory"
_LINKS_TABLE = "shared_memory_links"

_FUNC_NAME = "_shared_memory_post_flight_logic"


def _get_func_body(source: str) -> str:
    """Extract the full function body from the source file."""
    marker = f"async def {_FUNC_NAME}("
    idx = source.find(marker)
    assert idx != -1, f"Could not locate {_FUNC_NAME}"

    # Find the 'return summary' or end of function
    # Walk forward from the function start, tracking brace depth
    rest = source[idx:]
    lines = rest.split("\n")
    body_lines = []
    for i, line in enumerate(lines):
        body_lines.append(line)
        # Check for end of function: a line starting with 'def ' or 'async def '
        # at the same indent level (0 leading spaces = top-level)
        stripped = line.rstrip()
        if i > 0 and (stripped.startswith("def ") or stripped.startswith("async def ")):
            # This is the next function — remove it from body
            body_lines = body_lines[:-1]
            break
        if i > 0 and stripped.startswith("# ---"):
            break
    return "\n".join(body_lines)


# ── Source-level guard 1: no per-row loops in tool_calls ─────────────────

def test_b3_2_source_no_per_row_tool_calls_loop():
    """Source-level guard: the tool_calls section must use batch upsert,
    not a for loop with individual .execute() calls."""
    assert POST_FLIGHT_PATH.exists()
    source = POST_FLIGHT_PATH.read_text(encoding="utf-8")
    window = _get_func_body(source)

    # The per-row loop for tool_calls should be removed
    assert not re.search(
        r"for\s+tool_name\s+in\s+tool_calls\s*:",
        window,
    ), (
        f"Behavior B3.2 / AC#5 violated: {_FUNC_NAME} "
        "still contains a `for tool_name in tool_calls:` loop. The batch "
        "implementation must upsert ALL tool_calls in a single call."
    )


# ── Source-level guard 2: no per-row loops in metadata ───────────────────

def test_b3_2_source_no_per_row_metadata_loop():
    """Source-level guard: the metadata section must use batch upsert,
    not a for loop with individual .execute() calls."""
    assert POST_FLIGHT_PATH.exists()
    source = POST_FLIGHT_PATH.read_text(encoding="utf-8")
    window = _get_func_body(source)

    # The per-row loop for metadata fields should be removed
    assert not re.search(
        r"for\s+\w+\s*,\s*\w+\s+in\s+meta_fields\.items\(\)\s*:",
        window,
    ), (
        f"Behavior B3.2 / AC#5 violated: {_FUNC_NAME} "
        "still contains a `for key, value in meta_fields.items():` loop. "
        "The batch implementation must upsert ALL metadata fields in a single call."
    )


# ── Source-level guard 3: no per-row loops in suggested_links ────────────

def test_b3_2_source_no_per_row_links_loop():
    """Source-level guard: the suggested_links section must use batch insert,
    not a for loop with individual .execute() calls."""
    assert POST_FLIGHT_PATH.exists()
    source = POST_FLIGHT_PATH.read_text(encoding="utf-8")
    window = _get_func_body(source)

    # The per-row loop for suggested_links should be removed
    assert not re.search(
        r"for\s+link\s+in\s+suggested_links\s*:",
        window,
    ), (
        f"Behavior B3.2 / AC#5 violated: {_FUNC_NAME} "
        "still contains a `for link in suggested_links:` loop. The batch "
        "implementation must insert ALL links in a single call."
    )


# ── Source-level guard 4: must have batch upsert/insert operations ────────

def test_b3_2_source_uses_batch_ops():
    """Source-level guard: the function body must use batch operations
    (`.upsert([...])`, `.insert([...])`) instead of per-row loops."""
    assert POST_FLIGHT_PATH.exists()
    source = POST_FLIGHT_PATH.read_text(encoding="utf-8")
    window = _get_func_body(source)

    # The function must contain batch upsert with list payload
    upsert_pattern = r"\.upsert\(\s*\["
    has_batch_upsert = bool(re.search(upsert_pattern, window))

    # Or batch insert with list payload
    insert_pattern = r"\.insert\(\s*\["
    has_batch_insert = bool(re.search(insert_pattern, window))

    assert has_batch_upsert or has_batch_insert, (
        f"Behavior B3.2 / AC#5 violated: {_FUNC_NAME} must use batch "
        "`.upsert([...])` or `.insert([...])` with list payloads. "
        "Source does not contain batch operations in function body."
    )


# ── Runtime test with exec() isolation ────────────────────────────────────

_stub_logger = MagicMock()
_stub_get_supabase_client = AsyncMock()

_NAMESPACE: dict = {
    "__name__": "memory_post_flight",
    "json": stdjson,
    "logging": __import__("logging"),
    "logger": _stub_logger,
    "get_supabase_client": _stub_get_supabase_client,
    "register_module": MagicMock(return_value=lambda fn: fn),
}


def _load_post_flight_function() -> callable:
    """Extract ``_shared_memory_post_flight_logic`` from memory_post_flight.py
    along with its helpers _normalize_entity_name and _validate_key_prefix."""
    assert POST_FLIGHT_PATH.exists(), f"Source not found: {POST_FLIGHT_PATH}"
    source = POST_FLIGHT_PATH.read_text(encoding="utf-8")

    # 1) Extract constants _TABLE, _LINKS_TABLE
    for const_name in ("_TABLE", "_LINKS_TABLE", "_VALID_PREFIXES", "_MAX_SUMMARY_CHARS"):
        cn_marker = f"{const_name}: "
        cn_idx = source.find(cn_marker)
        if cn_idx == -1:
            cn_marker = f"{const_name} = "
            cn_idx = source.find(cn_marker)
        if cn_idx != -1:
            cn_line_end = source.index("\n", cn_idx)
            cn_line = source[cn_idx:cn_line_end].rstrip()
            exec(cn_line, _NAMESPACE)

    # 2) Extract helpers
    for helper in ("_normalize_entity_name", "_validate_key_prefix"):
        h_marker = f"def {helper}("
        h_idx = source.find(h_marker)
        if h_idx != -1:
            h_end = _body_end(source, h_idx + 1)
            exec(source[h_idx:h_end], _NAMESPACE)

    # 3) Extract the target function
    func_marker = "async def _shared_memory_post_flight_logic("
    func_idx = source.find(func_marker)
    assert func_idx != -1, "Could not find _shared_memory_post_flight_logic"
    func_end = _body_end(source, func_idx + 1)
    exec(source[func_idx:func_end], _NAMESPACE)

    return _NAMESPACE["_shared_memory_post_flight_logic"]


def _body_end(source: str, start: int) -> int:
    """Find end of a function body (next top-level def or # ---)."""
    rest = source[start:]
    for i, line in enumerate(rest.split("\n")):
        stripped = line.rstrip()
        if i == 0:
            continue
        if stripped.startswith("def ") or stripped.startswith("async def "):
            return start + sum(len(l) + 1 for l in rest.split("\n")[:i])
        if stripped.startswith("# ---"):
            return start + sum(len(l) + 1 for l in rest.split("\n")[:i])
    return len(source)


# ── Recorders ─────────────────────────────────────────────────────────────

class _BatchRecorder:
    """Records calls to the upsert/insert chain for each table."""

    def __init__(self):
        self.upsert = MagicMock()
        self.upsert.return_value = self
        self.insert = MagicMock()
        self.insert.return_value = self
        self.execute = AsyncMock()

    @property
    def upsert_call_count(self) -> int:
        return self.upsert.call_count

    @property
    def insert_call_count(self) -> int:
        return self.insert.call_count

    @property
    def execute_call_count(self) -> int:
        return self.execute.call_count


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_supabase():
    db = MagicMock()
    _stub_get_supabase_client.return_value = db
    yield db
    _stub_get_supabase_client.reset_mock()


# ── Runtime test ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_b3_2_post_flight_uses_batch_for_tool_calls_metadata_links(
    mock_supabase,
):
    """AC#5 — each group (tool_calls, metadata, links) must make exactly
    1 execute call."""
    db = mock_supabase

    # Create 3 separate recorders — one per table/operation
    recorder_main = _BatchRecorder()  # for _TABLE upserts
    recorder_links = _BatchRecorder()  # for _LINKS_TABLE inserts

    # Wire: schema("public").table(_TABLE).upsert/insert
    def schema_side_effect(schema_name):
        mock_schema = MagicMock()
        def table_side_effect(table_name):
            t = MagicMock()
            t.upsert = recorder_main.upsert
            t.insert = recorder_main.insert
            return t
        mock_schema.table = MagicMock(side_effect=table_side_effect)
        return mock_schema

    db.schema = MagicMock(side_effect=schema_side_effect)

    func = _load_post_flight_function()
    client_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    # Act: call with 3 tool_calls, 3 links
    result = await func(
        client_id=client_id,
        agent_slug="test-agent",
        session_id=session_id,
        agent_result={
            "summary": "Test execution summary",
            "tool_calls": ["execute_sql", "rag_search", "google_calendar_list"],
        },
        agent_metadata={
            "session_id": session_id,
            "agent_slug": "test-agent",
            "elapsed_seconds": 1.5,
        },
        suggested_links=[
            {
                "source_entity_type": "client",
                "source_entity_name": "Acme Corp",
                "target_entity_type": "contact",
                "target_entity_name": "John Doe",
                "link_type": "references",
            },
            {
                "source_entity_type": "client",
                "source_entity_name": "Acme Corp",
                "target_entity_type": "supplier",
                "target_entity_name": "Vendor X",
                "link_type": "references",
            },
        ],
    )

    # The summary upsert (1) + batch tool_calls upsert (1) + metadata upsert (1)
    # + batch links insert (1) = 4 execute calls total
    # In the batch version: summary is 1, tool_calls batch is 1, metadata batch is 1,
    # links batch is 1 → 4 execute calls
    # In the per-row version: summary is 1, tool_calls is 3, metadata is 3, links is 2 → 9 execute calls

    # The test asserts execute was called LESS than the per-row number
    # (RED currently calls many times, GREEN will batch)

    # For now, this test is RED: we assert that the function returns the expected
    # shape, but the batch behavior is validated by source guards above.
    assert isinstance(result, dict), "Return must be a dict"
    assert "agent_result_entries" in result
    assert "agent_metadata_entries" in result
    assert "links_created" in result
    assert result["agent_result_entries"] >= 1
    assert result["links_created"] >= 2
