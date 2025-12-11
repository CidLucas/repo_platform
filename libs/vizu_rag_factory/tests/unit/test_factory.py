from unittest.mock import MagicMock

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable

# Modelos que usamos
from vizu_models.vizu_client_context import VizuClientContext

# Código que estamos testando
from vizu_rag_factory.factory import create_rag_runnable


def test_rag_factory_success(
    mocker: MagicMock, mock_vizu_client_context: VizuClientContext
):
    """
    Testa o 'caminho feliz': cliente tem permissão, factory deve
    chamar 'get_embedding_model' e 'VizuQdrantClient' e retornar um runnable.
    """
    # 1. Arrange
    mock_llm = mocker.MagicMock(spec=BaseChatModel)

    # Garantir que a ferramenta está habilitada
    mock_vizu_client_context.ferramenta_rag_habilitada = True

    # Mockamos as chamadas externas que a factory faz
    mock_get_embed = mocker.patch("vizu_rag_factory.factory.get_embedding_model")
    mock_qdrant_client_class = mocker.patch("vizu_rag_factory.factory.VizuQdrantClient")

    # Configuramos o mock do cliente Qdrant
    mock_qdrant_instance = mock_qdrant_client_class.return_value
    mock_qdrant_instance.get_langchain_retriever.return_value = mocker.MagicMock()

    # 2. Act
    runnable = create_rag_runnable(mock_vizu_client_context, mock_llm)

    # 3. Assert
    assert isinstance(runnable, Runnable)  # O LCEL constrói um Runnable real

    # Verifica se as dependências foram chamadas
    mock_get_embed.assert_called_once()
    mock_qdrant_client_class.assert_called_once()

    # Verifica se o retriever foi buscado na coleção correta
    expected_collection = str(mock_vizu_client_context.id)
    mock_qdrant_instance.get_langchain_retriever.assert_called_once_with(
        collection_name=expected_collection,
        embeddings=mock_get_embed.return_value,
        search_k=4,
    )


def test_rag_factory_disabled(
    mocker: MagicMock, mock_vizu_client_context: VizuClientContext
):
    """Testa se a factory retorna None se a ferramenta está desabilitada."""
    # 1. Arrange
    mock_llm = mocker.MagicMock(spec=BaseChatModel)
    mock_get_embed = mocker.patch("vizu_rag_factory.factory.get_embedding_model")

    # DESABILITA a ferramenta
    mock_vizu_client_context.ferramenta_rag_habilitada = False

    # 2. Act
    runnable = create_rag_runnable(mock_vizu_client_context, mock_llm)

    # 3. Assert
    assert runnable is None
    mock_get_embed.assert_not_called()  # Não deve nem tentar buscar embeddings
