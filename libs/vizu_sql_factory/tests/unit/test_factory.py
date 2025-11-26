import pytest
from unittest.mock import MagicMock, patch
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable

# Código que estamos testando
from vizu_sql_factory.factory import create_sql_agent_runnable, _construir_db_url

# Modelos que usamos
from vizu_models.vizu_client_context import VizuClientContext




def test_sql_factory_success(
    mocker: MagicMock,
    mock_vizu_client_context: VizuClientContext
):
    """
    Testa o 'caminho feliz': cliente tem permissão, factory deve
    chamar 'create_engine' e 'create_sql_agent' e retornar um runnable.
    """
    # 1. Arrange
    mock_llm = mocker.MagicMock(spec=BaseChatModel)

    # Garantir que a ferramenta está habilitada
    mock_vizu_client_context.ferramenta_sql_habilitada = True
    assert mock_vizu_client_context.credenciais is not None

    # Mockamos as chamadas externas que a factory faz
    mock_create_engine = mocker.patch("vizu_sql_factory.factory.create_engine")
    mock_create_agent = mocker.patch("vizu_sql_factory.factory.create_sql_agent")

    # Mockamos SQLDatabase para evitar a necessidade de um engine real
    mock_sql_database = mocker.patch("vizu_sql_factory.factory.SQLDatabase")
    mock_sql_database.return_value.dialect.name = "postgresql" # Simula o dialeto
    mock_sql_database.return_value.get_table_names.return_value = ["mock_table_1", "mock_table_2"]

    # O agente mockado que esperamos receber de volta
    mock_runnable = mocker.MagicMock(spec=Runnable)
    mock_create_agent.return_value = mock_runnable

    # 2. Act
    runnable = create_sql_agent_runnable(mock_vizu_client_context, mock_llm)

    # 3. Assert
    assert runnable is mock_runnable # Retornou o agente

    # Verifica se a engine foi criada com a URL correta
    expected_url = _construir_db_url(mock_vizu_client_context.credenciais[0].credenciais)
    mock_create_engine.assert_called_once()
    assert mock_create_engine.call_args[0][0] == expected_url # Verifica a URL

    # Verifica se o agente foi criado
    mock_create_agent.assert_called_once()


def test_sql_factory_disabled(
    mocker: MagicMock,
    mock_vizu_client_context: VizuClientContext
):
    """Testa se a factory retorna None se a ferramenta está desabilitada."""
    # 1. Arrange
    mock_llm = mocker.MagicMock(spec=BaseChatModel)
    mock_create_agent = mocker.patch("vizu_sql_factory.factory.create_sql_agent")

    # DESABILITA a ferramenta
    mock_vizu_client_context.ferramenta_sql_habilitada = False

    # 2. Act
    runnable = create_sql_agent_runnable(mock_vizu_client_context, mock_llm)

    # 3. Assert
    assert runnable is None
    mock_create_agent.assert_not_called() # Não deve nem tentar criar o agente


def test_sql_factory_no_creds(
    mocker: MagicMock,
    mock_vizu_client_context: VizuClientContext
):
    """Testa se a factory retorna None se a ferramenta está habilitada, mas sem credenciais."""
    # 1. Arrange
    mock_llm = mocker.MagicMock(spec=BaseChatModel)
    mock_create_agent = mocker.patch("vizu_sql_factory.factory.create_sql_agent")

    # HABILITA a ferramenta
    mock_vizu_client_context.ferramenta_sql_habilitada = True
    # REMOVE as credenciais
    mock_vizu_client_context.credenciais = []

    # 2. Act
    runnable = create_sql_agent_runnable(mock_vizu_client_context, mock_llm)

    # 3. Assert
    assert runnable is None
    mock_create_agent.assert_not_called()