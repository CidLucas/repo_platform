from unittest.mock import MagicMock

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable

# Modelos que usamos
from vizu_models.vizu_client_context import VizuClientContext

# Código que estamos testando
from vizu_rag_factory.factory import create_rag_runnable


def test_rag_factory_success(mocker: MagicMock, mock_vizu_client_context: VizuClientContext):
    """
    Testa o 'caminho feliz': factory deve criar um SupabaseVectorRetriever
    e retornar um runnable.
    """
    # 1. Arrange
    mock_llm = mocker.MagicMock(spec=BaseChatModel)

    # Garantir que a ferramenta está habilitada
    mock_vizu_client_context.ferramenta_rag_habilitada = True

    # Mock environment variables needed by the retriever
    mocker.patch.dict(
        "os.environ",
        {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-service-key",
        },
    )

    # 2. Act
    runnable = create_rag_runnable(mock_vizu_client_context, mock_llm)

    # 3. Assert
    assert isinstance(runnable, Runnable)  # O LCEL constrói um Runnable real


def test_rag_factory_disabled(mocker: MagicMock, mock_vizu_client_context: VizuClientContext):
    """Testa se a factory retorna None se a ferramenta está desabilitada."""
    # 1. Arrange
    mock_llm = mocker.MagicMock(spec=BaseChatModel)

    # DESABILITA a ferramenta
    mock_vizu_client_context.ferramenta_rag_habilitada = False

    # 2. Act
    runnable = create_rag_runnable(mock_vizu_client_context, mock_llm)

    # 3. Assert
    assert runnable is None
