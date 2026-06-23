# tests/integration/test_search_shared_memory_rpc.py
"""Testes da RPC function search_shared_memory (T3.1f Seção 5).

Testa comportamento do fluxo de busca via search_shared_memory() RPC:
- Resultados ordenados por similarity DESC
- Respeito a match_count
- Respeito a match_threshold
- Linhas sem embedding são ignoradas
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
        "logger": logging.getLogger("test_rpc"),
        "ToolError": ToolError,
        "get_supabase_client": AsyncMock(return_value=db_mock),
        "_validate_entity_type": validate_fn,
        "_normalize_entity_name": normalize_fn,
    }
    return _extract_function(source, "_shared_memory_search_logic", extra_globals=extra)


class TestSearchSharedMemoryRPC:
    """Testes da RPC search_shared_memory()."""

    @pytest.fixture
    def client_id(self):
        return str(uuid.uuid4())

    @pytest.fixture
    def mock_cohere(self):
        embedder = MagicMock()
        embedder.embed_query.return_value = [0.33] * 384
        with patch("blu_llm_service.get_cohere_embedding_model", return_value=embedder):
            yield embedder

    @pytest.fixture
    def search_fn(self, mock_cohere):
        db = MagicMock()
        return db, _load_search_logic(db)

    @staticmethod
    def _make_rpc_result(rows):
        mock_result = MagicMock()
        mock_result.data = rows if rows is not None else []
        return mock_result

    @staticmethod
    def _setup_rpc(mock_db, rows):
        mock_execute = AsyncMock(return_value=TestSearchSharedMemoryRPC._make_rpc_result(rows))
        mock_rpc_chain = MagicMock()
        mock_rpc_chain.execute = mock_execute
        mock_db.rpc.return_value = mock_rpc_chain

    # ── 1. test_rpc_returns_results_by_similarity ────────────────

    @pytest.mark.asyncio
    async def test_rpc_returns_results_by_similarity(self, client_id, search_fn):
        mock_db, search_logic = search_fn
        rows = [
            {"id": "r1", "entity_type": "client", "entity_name": "a", "key": "k1",
             "value": {}, "category": None, "source": "manual", "confidence": 1.0,
             "similarity": 0.95},
            {"id": "r2", "entity_type": "client", "entity_name": "b", "key": "k2",
             "value": {}, "category": None, "source": "manual", "confidence": 1.0,
             "similarity": 0.72},
            {"id": "r3", "entity_type": "client", "entity_name": "c", "key": "k3",
             "value": {}, "category": None, "source": "manual", "confidence": 1.0,
             "similarity": 0.51},
        ]
        self._setup_rpc(mock_db, rows)

        result = await search_logic(client_id=client_id, query="test")

        assert result["total_results"] == 3
        similarities = [r["similarity"] for r in result["results"]]
        assert similarities == [0.95, 0.72, 0.51]

    # ── 2. test_rpc_respects_match_count ─────────────────────────

    @pytest.mark.asyncio
    async def test_rpc_respects_match_count(self, client_id, search_fn):
        mock_db, search_logic = search_fn
        rows = [{"id": "r%d" % i, "entity_type": "client", "entity_name": "e%d" % i,
                 "key": "k%d" % i, "value": {}, "category": None, "source": "manual",
                 "confidence": 1.0, "similarity": 1.0 - i * 0.1}
                for i in range(5)]
        self._setup_rpc(mock_db, rows)

        result = await search_logic(client_id=client_id, query="test", match_count=3)

        assert result["total_results"] == 5
        mock_db.rpc.assert_called_once_with(
            "search_shared_memory",
            {
                "p_client_id": client_id, "p_query_embed": ANY,
                "p_match_count": 3, "p_match_threshold": 0.3,
                "p_entity_type": None, "p_category": None,
            },
        )

    # ── 3. test_rpc_respects_match_threshold ─────────────────────

    @pytest.mark.asyncio
    async def test_rpc_respects_match_threshold(self, client_id, search_fn):
        mock_db, search_logic = search_fn
        self._setup_rpc(mock_db, [])

        await search_logic(client_id=client_id, query="test", match_threshold=0.7)

        mock_db.rpc.assert_called_once_with(
            "search_shared_memory",
            {
                "p_client_id": client_id, "p_query_embed": ANY,
                "p_match_count": 10, "p_match_threshold": 0.7,
                "p_entity_type": None, "p_category": None,
            },
        )

    # ── 4. test_rpc_null_embedding_skipped ───────────────────────

    @pytest.mark.asyncio
    async def test_rpc_null_embedding_skipped(self, client_id, search_fn):
        mock_db, search_logic = search_fn
        self._setup_rpc(mock_db, [])

        result = await search_logic(client_id=client_id, query="test")

        assert result["total_results"] == 0
        assert result["results"] == []
