"""RED test for behavior B3.1 — _auto_create_links batch upsert in memory_module.py.

GOAL:
    Corrigir bottlenecks P0 N+1 no código de produção. Issue #121 — Performance.
    O `_auto_create_links` em memory_module.py atualmente faz um loop sobre
    `references` e chama `_shared_memory_link_logic()` para cada referência
    individualmente — cada chamada é um round-trip DB separado (N+1).

BEHAVIOR:
    B3.1 — `_auto_create_links` (linha ~1285 em memory_module.py) deve usar
    batch upsert para criar todos os links em 1 única chamada DB em vez de
    N chamadas no loop for ref in references.

    Hoje (RED) o código faz:
        for ref in references:
            await _shared_memory_link_logic(
                client_id=client_id,
                source_entity_type=entity_type,
                source_entity_name=entity_name,
                target_entity_type=ref["entity_type"],
                target_entity_name=ref["entity_name"],
                link_type="references",
                source="system",
                confidence=1.0,
            )

    O contrato GREEN esperado é:
        # Batch upsert all links in a single DB call
        payloads = [{...} for ref in references]
        await db.schema("public").table(_LINKS_TABLE).upsert(
            payloads, on_conflict="..."
        ).execute()

AC (Acceptance Criteria):
    AC#3 — `_auto_create_links` faz exatamente 1 chamada a .execute()
           no shared_memory_links quando há N referências (batch upsert)
    AC#4 — Duplicatas (uq_shared_memory_link) continuam sendo ignoradas
           via ON CONFLICT (já tratado pelo upsert)

DECISION:
    Estratégia: extend (refatorar _auto_create_links para batch upsert)
    Arquivo alvo: services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py
    Função alvo: _auto_create_links (linha ~1285)
    Substituir o for ref in references: ... por um batch upsert com lista
    de payloads diretamente na tabela _LINKS_TABLE.

Anti-Goals (must NOT be violated):
    1. NÃO alterar a assinatura de _auto_create_links
    2. NÃO alterar o contrato de retorno ({links_created, references_found})
    3. NÃO introduzir dependência externa nova
    4. NÃO alterar _shared_memory_link_logic ou outras funções não-alvo
    5. NÃO modificar _TABLE, _LINKS_TABLE ou constantes do módulo

Estado atual: RED — o loop per-row `for ref in references:` ainda está
presente no corpo da função. O teste source-level falha com AssertionError
ao verificar que não há `.upsert(` no nível do `_LINKS_TABLE` dentro do
corpo, ou que o loop for ainda existe. A GREEN vai consolidar tudo em um
único batch upsert.
"""

import re
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── Override root conftest cleanup (pure unit test, no DB teardown) ──────

@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test uses mocked Supabase only."""
    yield


# ── Paths ────────────────────────────────────────────────────────────────

MEMORY_MODULE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "services"
    / "tool_pool_api"
    / "src"
    / "tool_pool_api"
    / "server"
    / "tool_modules"
    / "memory_module.py"
)

_LINKS_TABLE = "shared_memory_links"


# ── exec() isolation namespace ────────────────────────────────────────────

_stub_logger = MagicMock()
_stub_get_supabase_client = AsyncMock()

_NAMESPACE: dict = {
    "__name__": "memory_module",
    "json": __import__("json"),
    "logging": __import__("logging"),
    "re": __import__("re"),
    "time": __import__("time"),
    "text": __import__("sqlalchemy").text,
    "Any": __import__("typing").Any,
    "Optional": __import__("typing").Optional,
    "logger": _stub_logger,
    "Context": MagicMock,
    "FastMCP": MagicMock,
    "ToolError": type("ToolError", (Exception,), {}),
    "mcp_inject_client_id": MagicMock(return_value=lambda fn: fn),
    "get_supabase_client": _stub_get_supabase_client,
    "get_direct_engine": AsyncMock(),
    "register_module": MagicMock(return_value=lambda fn: fn),
    "get_context_service": AsyncMock(),
    "_SNAPSHOT_DIMENSION_FIELDS": {},
}


def _load_auto_create_links() -> callable:
    """Extract ``_auto_create_links`` from memory_module.py source.

    Pulls in the minimum surface area the function needs:
        - _LINKS_TABLE, _TABLE constants
        - _VALID_ENTITY_TYPES
        - _extract_entity_references
        - _shared_memory_link_logic
    """
    assert MEMORY_MODULE_PATH.exists(), (
        f"Source file not found: {MEMORY_MODULE_PATH}"
    )
    source = MEMORY_MODULE_PATH.read_text(encoding="utf-8")

    # 1) Extract constants
    for const_name in ("_TABLE", "_LINKS_TABLE", "_VALID_ENTITY_TYPES"):
        cn_marker = f"{const_name}: "
        cn_idx = source.find(cn_marker)
        assert cn_idx != -1, f"Could not find {const_name}"
        # Grab until end of line
        cn_line_end = source.index("\n", cn_idx)
        cn_line = source[cn_idx:cn_line_end].rstrip()
        exec(cn_line, _NAMESPACE)

    # 2) Extract _extract_entity_references helper
    ref_marker = "def _extract_entity_references("
    ref_idx = source.find(ref_marker)
    assert ref_idx != -1, "Could not find _extract_entity_references"
    # Find the next top-level def or module comment boundary
    ref_body_end = _find_next_top_level_def(source, ref_idx + 1)
    exec(source[ref_idx:ref_body_end], _NAMESPACE)

    # 3) Extract _normalize_entity_name helper
    norm_marker = "def _normalize_entity_name("
    norm_idx = source.find(norm_marker)
    if norm_idx != -1:
        norm_end = _find_next_top_level_def(source, norm_idx + 1)
        exec(source[norm_idx:norm_end], _NAMESPACE)

    # 4) Stub _shared_memory_link_logic (we don't want it called in batch flow)
    async def _stub_link_logic(**kwargs):
        return {"id": str(uuid.uuid4()), "client_id": kwargs.get("client_id", "")}
    _NAMESPACE["_shared_memory_link_logic"] = _stub_link_logic

    # 5) Execute the target function
    func_marker = "async def _auto_create_links("
    func_idx = source.find(func_marker)
    assert func_idx != -1, "Could not find _auto_create_links"
    func_end = _find_next_top_level_def(source, func_idx + 1)
    exec(source[func_idx:func_end], _NAMESPACE)

    return _NAMESPACE["_auto_create_links"]


def _find_next_top_level_def(source: str, start: int) -> int:
    """Find the end of a function body by looking for the next top-level def
    or a line starting with '# ---' divider."""
    lines = source[start:].split("\n")
    depth = 0
    for i, line in enumerate(lines):
        stripped = line.rstrip()
        # Track brace/indent depth
        if depth > 0:
            if stripped.startswith("async def ") or stripped.startswith("def "):
                if depth <= 1:
                    return start + sum(len(l) + 1 for l in lines[:i])
            depth += stripped.count(":") if stripped and not stripped.startswith("#") else 0
            if depth < 0:
                depth = 0
        else:
            if stripped.startswith("async def ") or stripped.startswith("def "):
                if i > 1:  # skip the function itself
                    return start + sum(len(l) + 1 for l in lines[:i])
            if stripped.startswith("# ---"):
                return start + sum(len(l) + 1 for l in lines[:i])
    return start + len(source) - start


# ── Recorder ──────────────────────────────────────────────────────────────

class _BatchUpsertRecorder:
    """Records calls to the shared_memory_links upsert chain.

    Install via:
        table_mock.upsert = recorder.upsert
        recorder.upsert.return_value = recorder

    Then assert:
        recorder.upsert.call_count == 1
        len(recorder.last_payloads) == N
    """

    def __init__(self):
        self.upsert = MagicMock()
        self.upsert.return_value = self
        self.execute = AsyncMock()
        self.upsert.return_value.execute = self.execute
        self.last_payloads: list = []

    @property
    def call_count(self) -> int:
        return self.upsert.call_count

    @property
    def execute_call_count(self) -> int:
        return self.execute.call_count

    def get_last_payloads(self) -> list:
        """Return the payloads passed to the last upsert call."""
        if self.upsert.call_count == 0:
            return []
        call = self.upsert.call_args
        args = call[0] if call else []
        return args[0] if args else []


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_supabase():
    """Mock Supabase client returning a chainable query builder."""
    db = MagicMock()
    _stub_get_supabase_client.return_value = db
    yield db
    _stub_get_supabase_client.reset_mock()


@pytest.fixture
def upsert_recorder():
    """A fresh ``_BatchUpsertRecorder`` per test."""
    return _BatchUpsertRecorder()


# ── Source-level guard 1: must have .upsert( with list of payloads ───────

def test_b3_1_source_uses_batch_upsert():
    """Source-level guard: the body of ``_auto_create_links`` must use
    a batch ``.upsert([...], on_conflict=...)`` on ``_LINKS_TABLE``.

    The per-row ``for ref in references: await _shared_memory_link_logic(...)``
    must be replaced with a single batch upsert.
    """
    assert MEMORY_MODULE_PATH.exists()
    source = MEMORY_MODULE_PATH.read_text(encoding="utf-8")

    body_marker = "async def _auto_create_links("
    idx = source.find(body_marker)
    assert idx != -1, "Could not locate _auto_create_links"

    # Take a generous window: from the function header to the next
    # blank line followed by a top-level ``# ---`` or top-level def.
    window = source[idx : idx + 3000]

    assert f".table({_LINKS_TABLE!r})" in window or ".table(_LINKS_TABLE)" in window, (
        "Behavior B3.1 / AC#3 violated: _auto_create_links body must operate "
        "on the _LINKS_TABLE (shared_memory_links) directly instead of "
        "calling _shared_memory_link_logic per row."
    )

    assert ".upsert(" in window, (
        "Behavior B3.1 / AC#3 violated: _auto_create_links body must use "
        "a batch `.upsert(...)` call on the _LINKS_TABLE chain to upsert "
        "ALL links in a single DB call. Source does not contain `.upsert(` "
        "inside the function window."
    )

    # The upsert must be called with a list of payloads (not a single dict)
    # Look for .upsert([  (list starts after upsert call)
    upsert_idx = window.find(".upsert(")
    after_upsert = window[upsert_idx : upsert_idx + 20]
    assert "[" in after_upsert or "payloads" in window[:upsert_idx+200], (
        "Behavior B3.1 / AC#3 violated: .upsert() must be called with a "
        "list of payloads (e.g. `.upsert([{...}, {...}], ...)`) not a "
        "single dict. The batch must handle multiple references at once."
    )


# ── Source-level guard 2: per-row loop must be removed ───────────────────

def test_b3_1_source_no_per_row_loop():
    """Anti-goal enforcement: the ``for ref in references:`` loop that
    calls ``_shared_memory_link_logic`` must be REMOVED from the function body.
    """
    assert MEMORY_MODULE_PATH.exists()
    source = MEMORY_MODULE_PATH.read_text(encoding="utf-8")

    body_marker = "async def _auto_create_links("
    idx = source.find(body_marker)
    assert idx != -1

    window = source[idx : idx + 3000]

    assert not re.search(
        r"for\s+\w+\s+in\s+references\s*:",
        window,
    ), (
        "Behavior B3.1 / Anti-goal: _auto_create_links still contains "
        "a `for ... in references:` loop. The batch implementation must "
        "upsert ALL links in a single Supabase call, removing the per-row loop."
    )


# ── Runtime behavior test ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_b3_1_auto_create_links_uses_batch_upsert(
    mock_supabase, upsert_recorder
):
    """AC#3 — _auto_create_links must use a batch .upsert() call.

    Setup: value containing 3 references [label1](type:a),
    [label2](type:b), [label3](type:c). The batch implementation invokes
    .upsert() once with a list of 3 payloads, then .execute() once.

    The buggy per-row implementation invokes _shared_memory_link_logic
    3 times (N+1).
    """
    db = mock_supabase

    # Arrange: wire the _LINKS_TABLE upsert chain to the recorder
    # db.schema("public").table("shared_memory_links").upsert(...).execute()
    schema_mock = MagicMock()
    table_mock = MagicMock()
    table_mock.upsert = upsert_recorder.upsert
    schema_mock.table.return_value = table_mock
    db.schema.return_value = schema_mock

    # Arrange: also mock _TABLE upsert chain (for the last_auto_link_at update)
    _stub_table_mock = MagicMock()
    _stub_execute = AsyncMock()
    _stub_table_mock.update = MagicMock(return_value=_stub_table_mock)
    _stub_table_mock.eq = MagicMock(return_value=_stub_table_mock)
    _stub_table_mock.execute = _stub_execute
    schema_mock2 = MagicMock()
    schema_mock2.table.return_value = _stub_table_mock
    # Wire both schemas: first call returns the links one, second call returns _TABLE
    db.schema.side_effect = [schema_mock, schema_mock2]

    # Load the function
    func = _load_auto_create_links()
    client_id = str(uuid.uuid4())

    # Act: call _auto_create_links with 3 references
    # The value "[Client A](client:acme) and [Vendor X](supplier:vendor-x)"
    # and [Product Z](product:z) should produce 3 references.
    result = await func(
        client_id=client_id,
        entity_type="skill",
        entity_name="test-skill",
        value="[Client A](client:acme) and [Vendor X](supplier:vendor-x) and [Product Z](product:z)",
    )

    # Assert: upsert was called exactly ONCE with a list payload
    assert upsert_recorder.call_count == 1, (
        f"Expected 1 batch upsert call, got {upsert_recorder.call_count}. "
        "The per-row loop calls _shared_memory_link_logic N times; "
        "batch must call .upsert() exactly once."
    )

    # Assert: execute was called exactly ONCE on the upsert chain
    assert upsert_recorder.execute_call_count == 1, (
        f"Expected 1 .execute() call on the upsert chain, got {upsert_recorder.execute_call_count}. "
    )

    # Assert: the payload is a list containing the expected link entries
    payloads = upsert_recorder.get_last_payloads()
    assert isinstance(payloads, list), (
        "The batch upsert payload must be a list of dicts."
    )
    assert len(payloads) >= 2, (
        f"Expected at least 2 link payloads (for 2+ references), got {len(payloads)}. "
        "The value '[Client A](client:acme) and [Vendor X](supplier:vendor-x) and [Product Z](product:z)' "
        "should produce at least 2 reference objects."
    )

    # Assert: each payload has the required keys
    for p in payloads:
        assert "client_id" in p, f"Missing client_id in payload: {p}"
        assert "source_entity_type" in p, f"Missing source_entity_type in payload: {p}"
        assert "source_entity_name" in p, f"Missing source_entity_name in payload: {p}"
        assert "target_entity_type" in p, f"Missing target_entity_type in payload: {p}"
        assert "target_entity_name" in p, f"Missing target_entity_name in payload: {p}"
        assert "link_type" in p, f"Missing link_type in payload: {p}"
        assert "source" in p, f"Missing source in payload: {p}"
        assert p["source"] == "system", f"Expected source=system, got {p['source']}"
        assert p["link_type"] == "references", f"Expected link_type=references, got {p['link_type']}"

    # Assert: return dict has the expected shape
    assert isinstance(result, dict), "Return value must be a dict"
    assert "links_created" in result, "Return dict must have links_created"
    assert result["links_created"] >= 2, (
        f"Expected links_created >= 2, got {result['links_created']}"
    )


@pytest.mark.asyncio
async def test_b3_1_auto_create_links_empty_references(
    mock_supabase, upsert_recorder
):
    """Edge case: value with no references should not call upsert at all."""
    db = mock_supabase

    schema_mock = MagicMock()
    table_mock = MagicMock()
    table_mock.upsert = upsert_recorder.upsert
    schema_mock.table.return_value = table_mock
    db.schema.return_value = schema_mock

    _stub_table_mock = MagicMock()
    _stub_execute = AsyncMock()
    _stub_table_mock.update = MagicMock(return_value=_stub_table_mock)
    _stub_table_mock.eq = MagicMock(return_value=_stub_table_mock)
    _stub_table_mock.execute = _stub_execute
    schema_mock2 = MagicMock()
    schema_mock2.table.return_value = _stub_table_mock
    db.schema.side_effect = [schema_mock, schema_mock2]

    func = _load_auto_create_links()
    client_id = str(uuid.uuid4())

    result = await func(
        client_id=client_id,
        entity_type="skill",
        entity_name="test-skill",
        value="No references here at all.",
    )

    # No links upsert called for empty references
    # (the batch path won't call upsert if references is empty)
    if upsert_recorder.call_count > 0:
        payloads = upsert_recorder.get_last_payloads()
        assert len(payloads) == 0, (
            f"Expected empty payloads for no references, got {len(payloads)}"
        )

    assert result["links_created"] == 0, (
        f"Expected 0 links_created, got {result['links_created']}"
    )
