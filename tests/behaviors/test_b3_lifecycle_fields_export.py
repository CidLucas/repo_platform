"""RED test for behavior B3 — lifecycle fields in shared memory export.

GOAL:
    Implementar exportação de memórias como JSON com lifecycle fields
    (ttl_tier, soft_delete_at, hard_delete_at, category). O export deve
    propagar para o output final os campos de ciclo de vida registrados
    na tabela ``shared_business_memory`` para que o consumidor downstream
    possa tomar decisões de retenção sem precisar inspecionar o DB.

BEHAVIOR:
    B3 — Adicionar lifecycle fields ao export em ``_shared_memory_export_logic``.

AC (Acceptance Criteria):
    AC#1 — Records exportados incluem ``ttl_tier``, ``soft_delete_at``,
           ``hard_delete_at`` e ``category``.
    AC#2 — Export filtra por ``entity_type`` e/ou ``entity_name`` (já funciona,
           lifecycle fields adicionados ao mesmo output).

DECISION:
    Estratégia: extend
    Arquivo alvo: services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py
    Estender: corpo de ``_shared_memory_export_logic`` adicionando os 4
    campos de lifecycle ao dicionário de cada record exportado.

Anti-Goals (must NOT be violated):
    1. NÃO quebrar AC#2 — o filtro por entity_type / entity_name deve
       continuar funcionando exatamente como antes.
    2. NÃO remover nem renomear nenhum dos campos já exportados
       (id, entity_type, entity_name, key, value, metadata, source,
        confidence, version, created_at, updated_at).
    3. NÃO introduzir campos derivados de outras tabelas — apenas
       propagar colunas já presentes em shared_business_memory.

Padrão de teste:
    O comportamento é verificado carregando ``_shared_memory_export_logic``
    via ``exec()`` isolation (mesma técnica usada em
    ``services/tool_pool_api/tests/unit/test_shared_memory_export.py``)
    e o contrato é parseado a partir do source (estilo
    ``tests/behaviors/test_b3_auto_link_parameter.py``) para garantir
    que a assinatura da função permaneça compatível.

Estado atual: RED — a função ``_shared_memory_export_logic`` atual não
inclui os campos de lifecycle no dicionário exportado, então a asserção
de presença falha com KeyError / AssertionError até que a feature seja
implementada na fase GREEN.
"""

import re
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── Paths ────────────────────────────────────────────────────────────────

THIS_FILE = Path(__file__).resolve()
BEHAVIORS_DIR = THIS_FILE.parent
TESTS_DIR = BEHAVIORS_DIR.parent
REPO_ROOT = TESTS_DIR.parent

MEMORY_MODULE_PATH = (
    REPO_ROOT
    / "services"
    / "tool_pool_api"
    / "src"
    / "tool_pool_api"
    / "server"
    / "tool_modules"
    / "memory_module.py"
)


# ── Override root conftest cleanup (no real Supabase needed) ─────────────


@pytest.fixture(autouse=True)
def _cleanup_test_data():
    """Override root conftest — this test is pure unit, no DB teardown."""
    yield


# ── Stand-in ToolError (mirror of the unit test isolation pattern) ──────


class ToolError(Exception):
    """Replacement for fastmcp.exceptions.ToolError in isolation."""
    pass


# ── Source parsing helpers (mirror of test_b3_auto_link_parameter) ──────


def _extract_function_body(source: str, func_name: str) -> str:
    """Return the body text of the first ``(async) def <func_name>(...)``.

    The body is the text after the signature's terminating ':' up to the
    next top-level ``def`` / ``async def`` declaration.
    """
    pattern = rf"(?:async\s+)?def\s+{re.escape(func_name)}\s*\("
    match = re.search(pattern, source)
    if not match:
        return ""
    start = match.end()
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        char = source[i]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        i += 1
    j = i
    while j < len(source) and source[j] != ":":
        j += 1
    body_start = j + 1
    next_def = re.search(
        r"^[\s]{0,8}(?:async\s+)?def\s+",
        source[body_start:],
        re.MULTILINE,
    )
    if next_def:
        return source[body_start : body_start + next_def.start()]
    return source[body_start:]


# ── exec() isolation (copy of test_shared_memory_export loader) ──────────

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
    """Extract ``_shared_memory_export_logic`` from memory_module.py source.

    Mirrors the loader in
    ``services/tool_pool_api/tests/unit/test_shared_memory_export.py``:
    parses out the constants and helpers the function needs, then exec's
    only the function body in a controlled namespace.
    """
    assert MEMORY_MODULE_PATH.exists(), (
        f"Source file not found: {MEMORY_MODULE_PATH}"
    )
    source = MEMORY_MODULE_PATH.read_text()

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


# ── Supabase chain mock helpers ──────────────────────────────────────────


def _make_result(rows):
    """Build a mock Supabase execute() result with .data."""
    mock_result = MagicMock()
    mock_result.data = rows
    return mock_result


def _setup_supabase_chain(mock_supabase, rows):
    """Set up the full Supabase query chain mock so
    ``db.schema().table().select().eq().order().execute()`` returns rows."""
    result = _make_result(rows)

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.execute = AsyncMock(return_value=result)

    schema_mock = MagicMock()
    schema_mock.table.return_value = query

    mock_supabase.schema.return_value = schema_mock


def _sample_row_with_lifecycle():
    """A single row that includes ALL existing fields PLUS the four new
    lifecycle fields required by AC#1.
    """
    return {
        # ---- existing fields (must remain in output) ----
        "id": "fact-lifecycle-001",
        "entity_type": "client",
        "entity_name": "cliente_lifecycle",
        "key": "preferencias_lifecycle",
        "value": {"canal": "email", "prioridade": 1},
        "metadata": {"agent_id": "agent-1"},
        "source": "manual",
        "confidence": 0.9,
        "version": 1,
        "created_at": "2026-06-19T10:00:00Z",
        "updated_at": "2026-06-19T10:00:00Z",
        # ---- NEW lifecycle fields (AC#1) ----
        "ttl_tier": "standard",
        "soft_delete_at": None,
        "hard_delete_at": "2027-06-19T10:00:00Z",
        "category": "business",
    }


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_stubs():
    """Reset stubs between tests."""
    _stub_get_supabase_client.reset_mock()
    yield


@pytest.fixture
def mock_supabase():
    """Mock Supabase client returning a chainable query builder."""
    db = MagicMock()
    _stub_get_supabase_client.return_value = db
    yield db
    _stub_get_supabase_client.reset_mock()


# ── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_b3_export_includes_lifecycle_fields(mock_supabase):
    """AC#1 — Records exportados devem incluir os 4 lifecycle fields.

    Mockamos o Supabase com uma linha que já contém
    ``ttl_tier="standard"``, ``soft_delete_at=None``,
    ``hard_delete_at="2027-06-19T10:00:00Z"`` e ``category="business"``
    e verificamos que cada um deles aparece no record exportado.
    """
    client_id = str(uuid.uuid4())
    sample = [_sample_row_with_lifecycle()]

    _setup_supabase_chain(mock_supabase, sample)

    result = await _shared_memory_export_logic(client_id=client_id)

    assert result["client_id"] == client_id
    assert result["total_records"] == 1
    assert len(result["records"]) == 1

    record = result["records"][0]

    # AC#1 — os 4 lifecycle fields devem estar presentes.
    assert "ttl_tier" in record, (
        "Exported record is missing 'ttl_tier'. "
        "Behavior B3 / AC#1 requires the export to include the "
        "lifecycle field 'ttl_tier' from shared_business_memory."
    )
    assert record["ttl_tier"] == "standard", (
        f"Expected ttl_tier='standard', got {record.get('ttl_tier')!r}."
    )

    assert "soft_delete_at" in record, (
        "Exported record is missing 'soft_delete_at'. "
        "Behavior B3 / AC#1 requires the export to include "
        "'soft_delete_at' (may be None for active records)."
    )
    assert record["soft_delete_at"] is None, (
        f"Expected soft_delete_at=None, got {record.get('soft_delete_at')!r}."
    )

    assert "hard_delete_at" in record, (
        "Exported record is missing 'hard_delete_at'. "
        "Behavior B3 / AC#1 requires the export to include "
        "'hard_delete_at' from shared_business_memory."
    )
    assert record["hard_delete_at"] == "2027-06-19T10:00:00Z", (
        f"Expected hard_delete_at='2027-06-19T10:00:00Z', "
        f"got {record.get('hard_delete_at')!r}."
    )

    assert "category" in record, (
        "Exported record is missing 'category'. "
        "Behavior B3 / AC#1 requires the export to include the "
        "lifecycle field 'category' from shared_business_memory."
    )
    assert record["category"] == "business", (
        f"Expected category='business', got {record.get('category')!r}."
    )


@pytest.mark.asyncio
async def test_b3_export_preserves_existing_fields(mock_supabase):
    """Anti-Goal #2 — Nenhum campo pré-existente pode ser removido.

    Garante backward compat: a adição dos lifecycle fields não pode
    quebrar consumidores que dependem do shape atual do record.
    """
    client_id = str(uuid.uuid4())
    sample = [_sample_row_with_lifecycle()]

    _setup_supabase_chain(mock_supabase, sample)

    result = await _shared_memory_export_logic(client_id=client_id)
    record = result["records"][0]

    expected_existing_fields = {
        "id",
        "entity_type",
        "entity_name",
        "key",
        "value",
        "metadata",
        "source",
        "confidence",
        "version",
        "created_at",
        "updated_at",
    }
    missing = expected_existing_fields - set(record.keys())
    assert not missing, (
        f"Exported record is missing pre-existing fields: {sorted(missing)}. "
        f"Behavior B3 must not remove any field that was exported before "
        f"(Anti-Goal #2). Got keys: {sorted(record.keys())}"
    )

    # Spot-check a couple of values to ensure no silent corruption.
    assert record["id"] == "fact-lifecycle-001"
    assert record["entity_type"] == "client"
    assert record["entity_name"] == "cliente_lifecycle"
    assert record["key"] == "preferencias_lifecycle"
    assert record["value"] == {"canal": "email", "prioridade": 1}
    assert record["metadata"] == {"agent_id": "agent-1"}
    assert record["source"] == "manual"
    assert record["confidence"] == 0.9
    assert record["version"] == 1
    assert record["created_at"] == "2026-06-19T10:00:00Z"
    assert record["updated_at"] == "2026-06-19T10:00:00Z"


@pytest.mark.asyncio
async def test_b3_export_lifecycle_fields_under_entity_type_filter(mock_supabase):
    """AC#2 — O filtro por entity_type deve continuar funcionando e os
    lifecycle fields devem aparecer no mesmo output.
    """
    client_id = str(uuid.uuid4())
    sample = [_sample_row_with_lifecycle()]

    _setup_supabase_chain(mock_supabase, sample)

    result = await _shared_memory_export_logic(
        client_id=client_id,
        entity_type="client",
    )

    assert result["entity_type_filter"] == "client"
    assert result["total_records"] == 1

    record = result["records"][0]
    for field in ("ttl_tier", "soft_delete_at", "hard_delete_at", "category"):
        assert field in record, (
            f"AC#2: lifecycle field '{field}' missing from exported record "
            f"under entity_type filter. Got keys: {sorted(record.keys())}"
        )


@pytest.mark.asyncio
async def test_b3_export_lifecycle_fields_under_entity_name_filter(mock_supabase):
    """AC#2 — O filtro por entity_name (com normalização) deve continuar
    funcionando e os lifecycle fields devem aparecer no mesmo output.
    """
    client_id = str(uuid.uuid4())
    sample = [_sample_row_with_lifecycle()]

    _setup_supabase_chain(mock_supabase, sample)

    result = await _shared_memory_export_logic(
        client_id=client_id,
        entity_name="  Cliente_Lifecycle  ",
    )

    assert result["entity_name_filter"] == "cliente_lifecycle"
    assert result["total_records"] == 1

    record = result["records"][0]
    for field in ("ttl_tier", "soft_delete_at", "hard_delete_at", "category"):
        assert field in record, (
            f"AC#2: lifecycle field '{field}' missing from exported record "
            f"under entity_name filter. Got keys: {sorted(record.keys())}"
        )


def test_b3_source_function_body_reads_lifecycle_fields():
    """Source-level guard: ``_shared_memory_export_logic`` deve fazer
    referência aos 4 campos de lifecycle dentro do seu corpo. Este
    contrato protege contra regressões silenciosas no parsing do
    ``_load_function`` (ex.: alguém pode adicionar um campo só nos
    testes mas esquecer de propagar na função real).
    """
    assert MEMORY_MODULE_PATH.exists(), (
        f"Source file not found: {MEMORY_MODULE_PATH}"
    )
    source = MEMORY_MODULE_PATH.read_text()
    body = _extract_function_body(source, "_shared_memory_export_logic")
    assert body, "Could not extract body of _shared_memory_export_logic"

    for field in ("ttl_tier", "soft_delete_at", "hard_delete_at", "category"):
        assert field in body, (
            f"_shared_memory_export_logic body does not reference "
            f"'{field}'. Behavior B3 / AC#1 requires the function body "
            f"to read each lifecycle column from the row."
        )
