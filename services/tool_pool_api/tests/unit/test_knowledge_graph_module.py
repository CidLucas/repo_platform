# tests/unit/test_knowledge_graph_module.py
"""Unit tests for consultar_grafo_conhecimento (T4.3 — leitura do LightRAG).

Inclui um teste de compatibilidade de assinatura contra o lightrag-hku REAL
(instalado como dependência) — garante que o contrato usado pelo synthesis
(`ainsert_custom_kg(custom_kg_dict)`) e pelo client (`workspace=`,
`embedding_func=`, `llm_model_func=`) existe de verdade na lib.
"""

import inspect
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.exceptions import ToolError
from tool_pool_api.server.tool_modules.knowledge_graph_module import (
    _consultar_grafo_conhecimento_logic,
)
from tool_pool_api.server.utils.lightrag_client import RAGClientError

TEST_CLIENT_ID = str(uuid.uuid4())

_MOD = "tool_pool_api.server.tool_modules.knowledge_graph_module"


def _patches(rag=None, blu_context=..., rag_error=None):
    """Common patch set: context service + get_client_rag."""
    ctx_service = MagicMock()
    ctx_service.get_client_context_by_id = AsyncMock(
        return_value=MagicMock(id=TEST_CLIENT_ID, tier="SME")
        if blu_context is ...
        else blu_context
    )
    if rag_error is not None:
        get_rag = AsyncMock(side_effect=rag_error)
    else:
        get_rag = AsyncMock(return_value=rag or MagicMock())
    return (
        patch(f"{_MOD}.get_context_service", return_value=ctx_service),
        patch(f"{_MOD}.get_client_rag", get_rag),
    )


@pytest.mark.asyncio
async def test_consulta_happy_path():
    rag = MagicMock()
    rag.aquery = AsyncMock(return_value="-----Entities-----\nacme_corp: cliente Tech")
    p1, p2 = _patches(rag=rag)
    with p1, p2:
        result = await _consultar_grafo_conhecimento_logic(
            query="quem é a acme?", ctx=None, client_id=TEST_CLIENT_ID
        )

    assert "acme_corp" in result
    rag.aquery.assert_awaited_once()
    # retrieval-only: only_need_context=True no QueryParam
    param = rag.aquery.await_args.kwargs["param"]
    assert param.only_need_context is True
    assert param.mode == "mix"


@pytest.mark.asyncio
async def test_consulta_modo_invalido():
    with pytest.raises(ToolError, match="modo inválido"):
        await _consultar_grafo_conhecimento_logic(
            query="x", ctx=None, client_id=TEST_CLIENT_ID, modo="turbo"
        )


@pytest.mark.asyncio
async def test_consulta_query_vazia():
    with pytest.raises(ToolError, match="query é obrigatória"):
        await _consultar_grafo_conhecimento_logic(
            query="  ", ctx=None, client_id=TEST_CLIENT_ID
        )


@pytest.mark.asyncio
async def test_consulta_sem_client_id():
    with pytest.raises(ToolError, match="client_id"):
        await _consultar_grafo_conhecimento_logic(query="x", ctx=None, client_id=None)


@pytest.mark.asyncio
async def test_consulta_client_id_invalido():
    with pytest.raises(ToolError, match="ID de cliente inválido"):
        await _consultar_grafo_conhecimento_logic(
            query="x", ctx=None, client_id="not-a-uuid"
        )


@pytest.mark.asyncio
async def test_consulta_lightrag_indisponivel():
    p1, p2 = _patches(rag_error=RAGClientError("pg down"))
    with p1, p2:
        with pytest.raises(ToolError, match="indisponível"):
            await _consultar_grafo_conhecimento_logic(
                query="x", ctx=None, client_id=TEST_CLIENT_ID
            )


@pytest.mark.asyncio
async def test_consulta_contexto_vazio_retorna_mensagem_amigavel():
    rag = MagicMock()
    rag.aquery = AsyncMock(return_value="")
    p1, p2 = _patches(rag=rag)
    with p1, p2:
        result = await _consultar_grafo_conhecimento_logic(
            query="x", ctx=None, client_id=TEST_CLIENT_ID
        )

    assert "Nenhum contexto encontrado" in result


# ---------------------------------------------------------------------------
# Compatibilidade com o lightrag-hku REAL
# ---------------------------------------------------------------------------


def test_real_lightrag_ainsert_custom_kg_signature():
    """O contrato usado pelo sbm_to_lightrag_synthesis liga na assinatura real."""
    from lightrag import LightRAG

    sig = inspect.signature(LightRAG.ainsert_custom_kg)
    # deve aceitar (self, custom_kg_dict) posicionalmente
    sig.bind(
        MagicMock(),
        {"chunks": [], "entities": [], "relationships": []},
    )


def test_real_lightrag_constructor_accepts_isolation_kwargs():
    """workspace / embedding_func / llm_model_func existem no dataclass real."""
    from lightrag import LightRAG

    fields = {f.name for f in LightRAG.__dataclass_fields__.values()}
    assert {"workspace", "embedding_func", "llm_model_func"} <= fields


def test_real_lightrag_queryparam_modes():
    from lightrag import QueryParam

    p = QueryParam(mode="mix", only_need_context=True)
    assert p.only_need_context is True


@pytest.mark.asyncio
async def test_factory_passes_workspace_and_funcs():
    """_create_lightrag_instance isola o tenant via workspace=client_{id}."""
    from tool_pool_api.server.utils import lightrag_client as lc

    captured: dict = {}

    class FakeLightRAG:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def initialize_storages(self):
            return None

    with patch("lightrag.LightRAG", FakeLightRAG):
        await lc._create_lightrag_instance("abc-123")

    assert captured["workspace"] == "client_abc-123"
    assert captured["kv_storage"] == "PGKVStorage"
    assert captured["vector_storage"] == "PGVectorStorage"
    assert captured["graph_storage"] == "NetworkXStorage"
    assert captured["embedding_func"].embedding_dim == 384
    assert callable(captured["llm_model_func"])
