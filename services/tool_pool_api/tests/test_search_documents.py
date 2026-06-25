"""Unit tests for services/tool_pool_api/src/tool_pool_api/services/search_documents/.

Pure-CPU + mocked tests. Cohere and Supabase RPC are mocked; the tests
verify the search_documents function calls the right RPC with the right
shape and parses the response correctly.

These tests are the regression coverage that replaces the old Deno EF.

Run with: pytest services/tool_pool_api/tests/test_search_documents.py
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from tool_pool_api.services.search_documents import (
    EMBEDDING_DIMENSIONS,
    _build_doc_ids_param,
    _build_text_array_param,
    _format_embedding,
    _validate_inputs,
    generate_embedding,
    search_documents,
)


# ── Fake blu_llm_service injection ────────────────────────────────────
#
# ``generate_embedding`` does ``from blu_llm_service import
# get_cohere_embedding_model``. We install a fake module in sys.modules
# so the import works even when blu_llm_service isn't pip-installed in
# the test venv (it lives in libs/ as an editable workspace member).


@pytest.fixture
def fake_blu_llm_service():
    """Inject a fake blu_llm_service module so generate_embedding imports."""
    mod = types.ModuleType("blu_llm_service")
    mod.get_cohere_embedding_model = MagicMock()
    sys.modules["blu_llm_service"] = mod
    yield mod
    sys.modules.pop("blu_llm_service", None)


# ── Constants ──────────────────────────────────────────────────────────


class TestConstants:
    def test_embedding_dimensions_matches_process_document(self):
        """The 384-dim model must match what process-document stores."""
        assert EMBEDDING_DIMENSIONS == 384


# ── _format_embedding ──────────────────────────────────────────────────


class TestFormatEmbedding:
    def test_formats_as_postgres_array_literal(self):
        embedding = [0.1, -0.2, 0.3]
        result = _format_embedding(embedding)
        assert result == "[0.1,-0.2,0.3]"

    def test_empty_list(self):
        assert _format_embedding([]) == "[]"

    def test_large_list(self):
        embedding = [0.001] * 384
        result = _format_embedding(embedding)
        assert result == f"[{','.join('0.001' for _ in range(384))}]"


# ── _build_doc_ids_param ──────────────────────────────────────────────


class TestBuildDocIdsParam:
    def test_none_returns_none(self):
        assert _build_doc_ids_param(None) is None

    def test_empty_list_returns_none(self):
        assert _build_doc_ids_param([]) is None

    def test_single_uuid(self):
        result = _build_doc_ids_param(["abc-123"])
        assert result == "{abc-123}"

    def test_multiple_uuids(self):
        result = _build_doc_ids_param(["uuid-1", "uuid-2", "uuid-3"])
        assert result == "{uuid-1,uuid-2,uuid-3}"


# ── _build_text_array_param ───────────────────────────────────────────


class TestBuildTextArrayParam:
    def test_none_no_default_returns_none(self):
        assert _build_text_array_param(None) is None

    def test_none_with_default(self):
        result = _build_text_array_param(None, default=["platform", "client"])
        assert result == "{platform,client}"

    def test_empty_list_no_default(self):
        assert _build_text_array_param([]) is None

    def test_values_provided(self):
        result = _build_text_array_param(["tax_knowledge", "dados_negocio"])
        assert result == "{tax_knowledge,dados_negocio}"


# ── _validate_inputs ──────────────────────────────────────────────────


class TestValidateInputs:
    def test_missing_query_raises(self):
        with pytest.raises(ValueError, match="Missing required fields"):
            _validate_inputs(None, "client-uuid", "hybrid", "rrf")

    def test_missing_client_id_raises(self):
        with pytest.raises(ValueError, match="Missing required fields"):
            _validate_inputs("query", None, "hybrid", "rrf")

    def test_invalid_search_mode_raises(self):
        with pytest.raises(ValueError, match="Invalid search_mode"):
            _validate_inputs("q", "c", "keyword", "rrf")

    def test_invalid_fusion_strategy_raises(self):
        with pytest.raises(ValueError, match="Invalid fusion_strategy"):
            _validate_inputs("q", "c", "hybrid", "bad")

    def test_valid_inputs_pass(self):
        _validate_inputs("query", "client-uuid", "hybrid", "rrf")
        _validate_inputs("query", "client-uuid", "semantic", "weighted")


# ── generate_embedding ────────────────────────────────────────────────


class TestGenerateEmbedding:
    def test_returns_384_dim_vector(self, fake_blu_llm_service):
        fake_blu_llm_service.get_cohere_embedding_model.return_value = MagicMock(
            embed_query=MagicMock(return_value=[0.1] * 384)
        )
        embedding = generate_embedding("hello world")
        assert len(embedding) == 384

    def test_calls_embed_query_with_stripped_text(self, fake_blu_llm_service):
        mock_embedder = MagicMock(embed_query=MagicMock(return_value=[0.1] * 384))
        fake_blu_llm_service.get_cohere_embedding_model.return_value = mock_embedder
        generate_embedding("  hello  ")
        mock_embedder.embed_query.assert_called_once_with("hello")

    def test_wrong_dimensions_raises_runtime_error(self, fake_blu_llm_service):
        fake_blu_llm_service.get_cohere_embedding_model.return_value = MagicMock(
            embed_query=MagicMock(return_value=[0.1] * 512)
        )
        with pytest.raises(RuntimeError, match="dimensões"):
            generate_embedding("hello")


# ── search_documents ───────────────────────────────────────────────────


def _make_mock_db(rpc_response_data: list[dict] | None = None, raise_error: Exception | None = None) -> MagicMock:
    """Build a mock supabase client whose .rpc(...).execute() returns the given data."""
    db = MagicMock()
    rpc = MagicMock()
    if raise_error:
        rpc.execute.side_effect = raise_error
    else:
        exec_result = MagicMock()
        exec_result.data = rpc_response_data or []
        rpc.execute.return_value = exec_result
    db.rpc.return_value = rpc
    return db


def _patch_cohere(embedding: list[float] | None = None):
    """Patch the search_documents.generate_embedding function directly.

    Bypasses the blu_llm_service import (which is not installed in the
    test venv) and lets us control the embedding vector returned.
    """
    if embedding is None:
        embedding = [0.1] * 384
    return patch(
        "tool_pool_api.services.search_documents.generate_embedding",
        return_value=embedding,
    )


class TestSearchDocuments:
    CLIENT_ID = "11111111-2222-3333-4444-555555555555"

    def test_hybrid_mode_calls_hybrid_match_documents(self):
        db = _make_mock_db([{"id": 1, "content": "x", "similarity": 0.9}])
        with _patch_cohere():
            data = search_documents(
                db,
                query="what is X?",
                client_id=self.CLIENT_ID,
                search_mode="hybrid",
                fusion_strategy="rrf",
                keyword_weight=0.3,
                vector_weight=0.7,
            )
        db.rpc.assert_called_once()
        call_args = db.rpc.call_args
        assert call_args[0][0] == "hybrid_match_documents"
        params = call_args[0][1]
        assert params["p_client_id"] == self.CLIENT_ID
        assert params["p_query_text"] == "what is X?"
        assert params["p_fusion_strategy"] == "rrf"
        assert params["p_keyword_weight"] == 0.3
        assert params["p_vector_weight"] == 0.7
        assert data["results"][0]["similarity"] == 0.9

    def test_semantic_mode_calls_match_documents(self):
        db = _make_mock_db([{"id": 1, "content": "x", "similarity": 0.8}])
        with _patch_cohere():
            data = search_documents(
                db,
                query="q",
                client_id=self.CLIENT_ID,
                search_mode="semantic",
            )
        call_args = db.rpc.call_args
        assert call_args[0][0] == "match_documents"
        assert "p_query_text" not in call_args[0][1]
        assert data["results"][0]["similarity"] == 0.8

    def test_embedding_formatted_as_halfvec_array(self):
        db = _make_mock_db([])
        with _patch_cohere(embedding=[0.1, 0.2, 0.3] + [0.0] * 381):
            search_documents(
                db, query="q", client_id=self.CLIENT_ID, search_mode="semantic"
            )
        params = db.rpc.call_args[0][1]
        assert params["p_query_embed"].startswith("[0.1,0.2,0.3,")
        assert params["p_query_embed"].endswith("]")

    def test_document_ids_passed_as_postgres_array(self):
        db = _make_mock_db([])
        with _patch_cohere():
            search_documents(
                db,
                query="q",
                client_id=self.CLIENT_ID,
                document_ids=["doc-1", "doc-2"],
                search_mode="semantic",
            )
        params = db.rpc.call_args[0][1]
        assert params["p_document_ids"] == "{doc-1,doc-2}"

    def test_document_ids_none_becomes_null_param(self):
        db = _make_mock_db([])
        with _patch_cohere():
            search_documents(
                db,
                query="q",
                client_id=self.CLIENT_ID,
                document_ids=None,
                search_mode="semantic",
            )
        params = db.rpc.call_args[0][1]
        assert params["p_document_ids"] is None

    def test_hybrid_default_scope_is_platform_and_client(self):
        db = _make_mock_db([])
        with _patch_cohere():
            search_documents(
                db,
                query="q",
                client_id=self.CLIENT_ID,
                search_mode="hybrid",
                scope=None,
            )
        params = db.rpc.call_args[0][1]
        assert params["p_scope"] == "{platform,client}"

    def test_themes_passed_through(self):
        db = _make_mock_db([])
        with _patch_cohere():
            search_documents(
                db,
                query="q",
                client_id=self.CLIENT_ID,
                search_mode="hybrid",
                themes=["financial_reporting"],
            )
        params = db.rpc.call_args[0][1]
        assert params["p_themes"] == "{financial_reporting}"

    def test_returns_results_dict_shape(self):
        db = _make_mock_db([{"id": 1, "content": "c", "similarity": 0.5}])
        with _patch_cohere():
            data = search_documents(
                db, query="q", client_id=self.CLIENT_ID, search_mode="semantic"
            )
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_empty_results(self):
        db = _make_mock_db([])
        with _patch_cohere():
            data = search_documents(
                db, query="q", client_id=self.CLIENT_ID, search_mode="hybrid"
            )
        assert data == {"results": []}

    def test_missing_query_raises_value_error(self):
        db = _make_mock_db([])
        with _patch_cohere():
            with pytest.raises(ValueError, match="Missing required fields"):
                search_documents(db, query=None, client_id=self.CLIENT_ID)

    def test_invalid_search_mode_raises_value_error(self):
        db = _make_mock_db([])
        with _patch_cohere():
            with pytest.raises(ValueError, match="Invalid search_mode"):
                search_documents(
                    db, query="q", client_id=self.CLIENT_ID, search_mode="keyword"
                )

    def test_rpc_failure_raises_runtime_error(self):
        db = _make_mock_db(raise_error=Exception("DB connection lost"))
        with _patch_cohere():
            with pytest.raises(RuntimeError, match="Vector RPC failed"):
                search_documents(
                    db, query="q", client_id=self.CLIENT_ID, search_mode="semantic"
                )

    def test_match_count_and_threshold_passed(self):
        db = _make_mock_db([])
        with _patch_cohere():
            search_documents(
                db,
                query="q",
                client_id=self.CLIENT_ID,
                match_count=15,
                match_threshold=0.75,
                search_mode="semantic",
            )
        params = db.rpc.call_args[0][1]
        assert params["p_match_count"] == 15
        assert params["p_match_threshold"] == 0.75
