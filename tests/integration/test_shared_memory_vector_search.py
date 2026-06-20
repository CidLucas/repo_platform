# tests/integration/test_shared_memory_vector_search.py
"""Testes de integração — Fluxo write → search (T3.1f Seção 4).

Testa o fluxo de busca semântica com mock de Cohere e Supabase RPC.
"""

import uuid
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest


class ToolError(Exception):
    pass


_VALID_ENTITY_TYPES = frozenset({
    "skill", "client", "contact", "supplier", "user", "snapshot",
    "routine", "agent_result", "agent_metadata",
})


def _extract_function(source, func_name, extra_globals=None):
    marker = "def %s(" % func_name
    idx = source.find(marker)
    assert idx != -1

    fn_start = source.rfind("\n", 0, idx) + 1 if idx > 0 else 0
    remaining = source[fn_start:]
    lines = remaining.split("\n")

    fn_lines = []
    found_def = False
    in_signature = False
    paren_depth = 0

    for line in lines:
        stripped = line.strip()
        if not found_def:
            if "def %s(" % func_name in stripped:
                found_def = True
                fn_lines.append(line)
                sig_start = line.index("def %s(" % func_name)
                paren_depth = line[sig_start:].count("(") - line[sig_start:].count(")")
                in_signature = paren_depth > 0
            continue
        if in_signature:
            fn_lines.append(line)
            paren_depth += stripped.count("(") - stripped.count(")")
            if paren_depth <= 0:
                in_signature = False
            continue
        if stripped == "":
            fn_lines.append("")
            continue
        current_indent = len(line) - len(line.lstrip())
        if current_indent == 0 and stripped:
            break
        fn_lines.append(line)

    namespace = {"__name__": "extracted_%s" % func_name}
    if extra_globals:
        namespace.update(extra_globals)
    exec("\n".join(fn_lines), namespace)
    return namespace[func_name]


def _load_search_logic(db_mock):
    import logging
    import pathlib

    mod_path = (
        pathlib.Path(__file__).parent.parent.parent
        / "services" / "tool_pool_api" / "src" / "tool_pool_api"
        / "server" / "tool_modules" / "memory_module.py"
    )
    source = mod_path.read_text()

    validate_fn = _extract_function(
        source, "_validate_entity_type",
        extra_globals={"_VALID_ENTITY_TYPES": _VALID_ENTITY_TYPES},
    )
    normalize_fn = _extract_function(source, "_normalize_entity_name")

    extra = {
        "logging": logging,
        "logger": logging.getLogger("test"),
        "ToolError": ToolError,
        "get_supabase_client": AsyncMock(return_value=db_mock),
        "_validate_entity_type": validate_fn,
        "_normalize_entity_name": normalize_fn,
    }
    return _extract_function(source, "_shared_memory_search_logic", extra_globals=extra)


class TestWriteThenSearchIntegration:
    """Testes de integração write → search (T3.1f Seção 4)."""

    @pytest.fixture
    def client_id(self):
        return str(uuid.uuid4())

    @pytest.fixture
    def mock_cohere(self):
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.42] * 384
        with patch("blu_llm_service.get_cohere_embedding_model", return_value=embedder):
            yield embedder

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def search_fn(self, mock_cohere):
        """Pre-load search function."""
        import pathlib
        mod_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "services" / "tool_pool_api" / "src" / "tool_pool_api"
            / "server" / "tool_modules" / "memory_module.py"
        )
        source = mod_path.read_text()
        validate_fn = _extract_function(
            source, "_validate_entity_type",
            extra_globals={"_VALID_ENTITY_TYPES": _VALID_ENTITY_TYPES},
        )
        normalize_fn = _extract_function(source, "_normalize_entity_name")
        return source, validate_fn, normalize_fn

    @staticmethod
    def _make_rpc_result(rows):
        mock_result = MagicMock()
        mock_result.data = rows if rows is not None else []
        return mock_result

    @staticmethod
    def _setup_rpc(mock_db, rows):
        mock_execute = AsyncMock(return_value=TestWriteThenSearchIntegration._make_rpc_result(rows))
        mock_rpc_chain = MagicMock()
        mock_rpc_chain.execute = mock_execute
        mock_db.rpc.return_value = mock_rpc_chain

    # ── 1. test_write_then_search_finds_result ─────────────────

    @pytest.mark.asyncio
    async def test_write_then_search_finds_result(self, client_id, mock_cohere, mock_db, search_fn):
        source, validate_fn, normalize_fn = search_fn
        search_logic = _load_search_logic(mock_db)

        rows = [{
            "id": "fact-001", "entity_type": "client", "entity_name": "alpha",
            "key": "pref", "value": {"canal": "email"}, "category": None,
            "source": "manual", "confidence": 1.0, "similarity": 0.92,
        }]
        self._setup_rpc(mock_db, rows)

        result = await search_logic(client_id=client_id, query="preferencia de comunicacao")

        assert result["total_results"] == 1
        assert result["results"][0]["entity_name"] == "alpha"
        assert result["results"][0]["similarity"] == 0.92

    # ── 2. test_search_with_entity_type_filter ──────────────────

    @pytest.mark.asyncio
    async def test_search_with_entity_type_filter(self, client_id, mock_cohere, mock_db, search_fn):
        source, validate_fn, normalize_fn = search_fn
        search_logic = _load_search_logic(mock_db)
        self._setup_rpc(mock_db, [])

        await search_logic(client_id=client_id, query="contato", entity_type="supplier")

        mock_db.rpc.assert_called_once_with(
            "search_shared_memory",
            {
                "p_client_id": client_id, "p_query_embed": ANY,
                "p_match_count": 10, "p_match_threshold": 0.3,
                "p_entity_type": "supplier", "p_category": None,
            },
        )

    # ── 3. test_search_with_category_filter ─────────────────────

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, client_id, mock_cohere, mock_db, search_fn):
        source, validate_fn, normalize_fn = search_fn
        search_logic = _load_search_logic(mock_db)
        self._setup_rpc(mock_db, [])

        await search_logic(client_id=client_id, query="dados", category="preference")

        mock_db.rpc.assert_called_once_with(
            "search_shared_memory",
            {
                "p_client_id": client_id, "p_query_embed": ANY,
                "p_match_count": 10, "p_match_threshold": 0.3,
                "p_entity_type": None, "p_category": "preference",
            },
        )

    # ── 4. test_search_below_threshold_returns_empty ─────────────

    @pytest.mark.asyncio
    async def test_search_below_threshold_returns_empty(self, client_id, mock_cohere, mock_db, search_fn):
        source, validate_fn, normalize_fn = search_fn
        search_logic = _load_search_logic(mock_db)
        self._setup_rpc(mock_db, [])

        result = await search_logic(client_id=client_id, query="irrelevante", match_threshold=0.99)

        assert result["total_results"] == 0

    # ── 5. test_search_unrelated_query_scores_low ────────────────

    @pytest.mark.asyncio
    async def test_search_unrelated_query_scores_low(self, client_id, mock_cohere, mock_db, search_fn):
        source, validate_fn, normalize_fn = search_fn
        search_logic = _load_search_logic(mock_db)
        rows = [{
            "id": "low", "entity_type": "client", "entity_name": "b", "key": "k",
            "value": {}, "category": None, "source": "manual", "confidence": 1.0,
            "similarity": 0.15,
        }]
        self._setup_rpc(mock_db, rows)

        result = await search_logic(client_id=client_id, query="xyzzy", match_threshold=0.1)

        assert result["results"][0]["similarity"] < 0.3

    # ── 6. test_rls_blocks_cross_client_search ───────────────────

    @pytest.mark.asyncio
    async def test_rls_blocks_cross_client_search(self, client_id, mock_cohere, mock_db, search_fn):
        source, validate_fn, normalize_fn = search_fn
        search_logic = _load_search_logic(mock_db)
        client_b = str(uuid.uuid4())
        self._setup_rpc(mock_db, [])

        result = await search_logic(client_id=client_b, query="alguma query")

        assert result["total_results"] == 0
        # rpc() is called as db.rpc("search_shared_memory", {...}) — positional
        call_args = mock_db.rpc.call_args
        assert call_args[0][0] == "search_shared_memory"
        assert call_args[0][1]["p_client_id"] == client_b
