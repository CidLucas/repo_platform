# tests/unit/test_shared_memory_search.py
"""Unit tests for shared_memory_search tool (T3.1c).

Tests the _shared_memory_search_logic function with:
- Mocked Cohere embedding (avoids real API calls)
- Mocked Supabase RPC (avoids real database)

The function is loaded in isolation via exec() to avoid triggering the
full package dependency chain, but the Cohere import inside the function
uses real Python import machinery (mockable via patch).
"""

import uuid
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest


# ── Stand-in ToolError ────────────────────────────────────────────

class ToolError(Exception):
    """Replacement for fastmcp.exceptions.ToolError in isolation."""
    pass


# ── Load the function in isolation ────────────────────────────────

# Build a minimal namespace with all needed stubs
_stub_logger = MagicMock()
_stub_get_supabase_client = AsyncMock()
_stub_validate_entity_type = MagicMock()

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
    """Extract _shared_memory_search_logic from memory_module.py source."""
    import pathlib
    mod_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "src" / "tool_pool_api" / "server" / "tool_modules"
        / "memory_module.py"
    )
    source = mod_path.read_text()

    # Extract _VALID_ENTITY_TYPES
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

    # Extract _validate_entity_type helper
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

    # Extract _shared_memory_search_logic
    marker = "async def _shared_memory_search_logic("
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
        if "async def _shared_memory_search_logic(" in line:
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
    return _NAMESPACE["_shared_memory_search_logic"]


_shared_memory_search_logic = _load_function()


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_stubs():
    """Reset all stubs between tests."""
    _stub_get_supabase_client.reset_mock()
    _stub_validate_entity_type.reset_mock()
    yield


@pytest.fixture
def mock_cohere():
    """Mock Cohere embedding that returns a fixed 384-dim vector."""
    embedder = MagicMock()
    embedder.embed_query.return_value = [0.1] * 384
    with patch(
        "blu_llm_service.get_cohere_embedding_model",
        return_value=embedder,
    ):
        yield embedder


@pytest.fixture
def mock_supabase():
    """Mock Supabase client and RPC call.

    The real get_supabase_client() returns a sync client.
    db.rpc() returns a chain object whose .execute() is awaitable.
    """
    db = MagicMock()
    _stub_get_supabase_client.return_value = db
    yield db
    _stub_get_supabase_client.reset_mock()


def _make_rpc_result(rows):
    """Helper to build a mock RPC execute() result."""
    mock_result = MagicMock()
    mock_result.data = rows if rows is not None else []
    return mock_result


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_success(mock_cohere, mock_supabase):
    """Should return formatted results when RPC returns data."""
    client_id = str(uuid.uuid4())

    stub_rows = [
        {
            "id": "fact-001",
            "entity_type": "client",
            "entity_name": "Cliente Alpha",
            "key": "preferencia_comunicacao",
            "value": {"canal": "WhatsApp", "tom": "amigavel"},
            "category": "preference",
            "source": "manual",
            "confidence": 0.95,
            "similarity": 0.8512,
        },
        {
            "id": "fact-002",
            "entity_type": "client",
            "entity_name": "Cliente Alpha",
            "key": "nome_responsavel",
            "value": {"nome": "João Silva"},
            "category": "knowledge",
            "source": "memory_agent",
            "confidence": 0.80,
            "similarity": 0.7231,
        },
    ]

    # Build the rpc chain: db.rpc().execute() where execute is awaitable
    mock_execute = AsyncMock(return_value=_make_rpc_result(stub_rows))
    mock_rpc_chain = MagicMock()
    mock_rpc_chain.execute = mock_execute
    mock_supabase.rpc.return_value = mock_rpc_chain

    result = await _shared_memory_search_logic(
        client_id=client_id,
        query="preferências de comunicação",
    )

    assert result["query"] == "preferências de comunicação"
    assert result["total_results"] == 2
    assert len(result["results"]) == 2

    r0 = result["results"][0]
    assert r0["id"] == "fact-001"
    assert r0["entity_type"] == "client"
    assert r0["entity_name"] == "Cliente Alpha"
    assert r0["similarity"] == 0.8512

    embedding_str = f"[{','.join('0.1' for _ in range(384))}]"
    mock_supabase.rpc.assert_called_once_with(
        "search_shared_memory",
        {
            "p_client_id": client_id,
            "p_query_embed": embedding_str,
            "p_match_count": 10,
            "p_match_threshold": 0.3,
            "p_entity_type": None,
            "p_category": None,
        },
    )


@pytest.mark.asyncio
async def test_empty_results(mock_cohere, mock_supabase):
    """Should return empty results when RPC returns no data."""
    client_id = str(uuid.uuid4())

    mock_execute = AsyncMock(return_value=_make_rpc_result([]))
    mock_rpc_chain = MagicMock()
    mock_rpc_chain.execute = mock_execute
    mock_supabase.rpc.return_value = mock_rpc_chain

    result = await _shared_memory_search_logic(
        client_id=client_id,
        query="xyzzy_nonexistent_term",
    )

    assert result["total_results"] == 0
    assert result["results"] == []


@pytest.mark.asyncio
async def test_with_filters(mock_cohere, mock_supabase):
    """Should pass entity_type and category filters to RPC."""
    client_id = str(uuid.uuid4())

    mock_execute = AsyncMock(return_value=_make_rpc_result([]))
    mock_rpc_chain = MagicMock()
    mock_rpc_chain.execute = mock_execute
    mock_supabase.rpc.return_value = mock_rpc_chain

    await _shared_memory_search_logic(
        client_id=client_id,
        query="dados financeiros",
        entity_type="supplier",
        category="finance",
        match_count=5,
        match_threshold=0.5,
    )

    mock_supabase.rpc.assert_called_once_with(
        "search_shared_memory",
        {
            "p_client_id": client_id,
            "p_query_embed": ANY,
            "p_match_count": 5,
            "p_match_threshold": 0.5,
            "p_entity_type": "supplier",
            "p_category": "finance",
        },
    )


@pytest.mark.asyncio
async def test_invalid_query(mock_cohere, mock_supabase):
    """Should raise ValueError for empty/blank query."""
    client_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="query is required"):
        await _shared_memory_search_logic(client_id=client_id, query="")

    with pytest.raises(ValueError, match="query is required"):
        await _shared_memory_search_logic(client_id=client_id, query="   ")


@pytest.mark.asyncio
async def test_invalid_entity_type(mock_cohere, mock_supabase):
    """Should raise ValueError for invalid entity_type."""
    client_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="Invalid entity_type"):
        await _shared_memory_search_logic(
            client_id=client_id,
            query="test",
            entity_type="invalid_type",
        )


@pytest.mark.asyncio
async def test_cohere_import_error(mock_supabase):
    """Should raise ToolError when blu_llm_service is not importable."""
    client_id = str(uuid.uuid4())

    with patch(
        "blu_llm_service.get_cohere_embedding_model",
        side_effect=ImportError("No module named 'blu_llm_service'"),
    ):
        with pytest.raises(ToolError, match="blu_llm_service não disponível"):
            await _shared_memory_search_logic(
                client_id=client_id,
                query="test",
            )


@pytest.mark.asyncio
async def test_cohere_missing_key(mock_supabase):
    """Should raise ToolError when CO_API_KEY is missing."""
    client_id = str(uuid.uuid4())

    with patch(
        "blu_llm_service.get_cohere_embedding_model",
        side_effect=ValueError("CO_API_KEY nao configurada"),
    ):
        with pytest.raises(ToolError, match="Configuração do Cohere ausente"):
            await _shared_memory_search_logic(
                client_id=client_id,
                query="test",
            )


@pytest.mark.asyncio
async def test_embedding_api_failure(mock_supabase):
    """Should raise ToolError when Cohere API call fails."""
    client_id = str(uuid.uuid4())

    embedder = MagicMock()
    embedder.embed_query.side_effect = RuntimeError("API timeout")

    with patch(
        "blu_llm_service.get_cohere_embedding_model",
        return_value=embedder,
    ):
        with pytest.raises(ToolError, match="Falha ao gerar embedding"):
            await _shared_memory_search_logic(
                client_id=client_id,
                query="test",
            )


@pytest.mark.asyncio
async def test_rpc_failure(mock_cohere, mock_supabase):
    """Should raise ToolError when RPC call fails."""
    client_id = str(uuid.uuid4())

    mock_execute = AsyncMock(side_effect=Exception("Database connection lost"))
    mock_rpc_chain = MagicMock()
    mock_rpc_chain.execute = mock_execute
    mock_supabase.rpc.return_value = mock_rpc_chain

    with pytest.raises(ToolError, match="Falha ao buscar na memória compartilhada"):
        await _shared_memory_search_logic(
            client_id=client_id,
            query="test",
        )


@pytest.mark.asyncio
async def test_rpc_returns_none_data(mock_cohere, mock_supabase):
    """Should handle None data from RPC gracefully (empty results)."""
    client_id = str(uuid.uuid4())

    mock_execute = AsyncMock(return_value=_make_rpc_result(None))
    mock_rpc_chain = MagicMock()
    mock_rpc_chain.execute = mock_execute
    mock_supabase.rpc.return_value = mock_rpc_chain

    result = await _shared_memory_search_logic(
        client_id=client_id,
        query="test",
    )

    assert result["total_results"] == 0
    assert result["results"] == []
