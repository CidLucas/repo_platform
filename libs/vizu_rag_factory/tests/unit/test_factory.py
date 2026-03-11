from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable

# Modelos que usamos
from vizu_models.vizu_client_context import VizuClientContext

# Código que estamos testando
from vizu_rag_factory.factory import create_rag_runnable


@pytest.mark.asyncio
async def test_rag_factory_success(mocker: MagicMock, mock_vizu_client_context: VizuClientContext):
    """
    Testa o 'caminho feliz': factory deve criar um SupabaseVectorRetriever
    e retornar um runnable.
    """
    # 1. Arrange
    mock_llm = mocker.MagicMock(spec=BaseChatModel)

    # Garantir que a ferramenta está habilitada (já definida no fixture via enabled_tools)
    assert "executar_rag_cliente" in mock_vizu_client_context.enabled_tools

    # Mock environment variables needed by the retriever
    mocker.patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-service-key",
        },
    )

    # Mock build_prompt to avoid Langfuse dependency in tests
    mocker.patch(
        "vizu_rag_factory.factory.build_prompt",
        new_callable=AsyncMock,
        return_value="You are an assistant.\n\nCONTEXT:\n{context}\n\nQUESTION:\n{question}\n\nRESPONSE:",
    )

    # 2. Act
    runnable = await create_rag_runnable(mock_vizu_client_context, mock_llm)

    # 3. Assert
    assert isinstance(runnable, Runnable)  # O LCEL constrói um Runnable real


@pytest.mark.asyncio
async def test_rag_factory_disabled(mocker: MagicMock, mock_vizu_client_context: VizuClientContext):
    """Testa se a factory retorna None se a ferramenta está desabilitada."""
    # 1. Arrange
    mock_llm = mocker.MagicMock(spec=BaseChatModel)

    # DESABILITA a ferramenta removendo do enabled_tools
    mock_vizu_client_context.enabled_tools = []

    # 2. Act
    runnable = await create_rag_runnable(mock_vizu_client_context, mock_llm)

    # 3. Assert
    assert runnable is None
