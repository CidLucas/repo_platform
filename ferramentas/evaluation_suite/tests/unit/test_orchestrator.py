import pytest
import pandas as pd
import asyncio
import uuid  # <-- ADICIONE O IMPORT DE UUID
from unittest.mock import AsyncMock, MagicMock, patch

# O componente que estamos testando
from evaluation_suite.core.orchestrator import EvaluationOrchestrator
from evaluation_suite.clients.api_client import APIClient

# --- Fixtures e Mocks ---

@pytest.fixture
def mock_db_session():
    """Cria um mock para a sessão do banco de dados SQLAlchemy."""
    session = MagicMock()
    # Mock para o objeto de query
    session.query.return_value.filter.return_value.all.return_value = []
    return session

@pytest.fixture
def mock_api_client():
    """Cria um mock assíncrono para o nosso APIClient."""
    client = AsyncMock(spec=APIClient)
    # CORREÇÃO: Define o valor de retorno como None para evitar o 'coroutine not awaited'
    client.send_message.return_value = None
    return client

@pytest.fixture
def sample_dataset_path(tmp_path):
    """
    Cria um arquivo CSV de dataset temporário para os testes
    e retorna o caminho para ele, AGORA COM UUIDs VÁLIDOS.
    """
    # CORREÇÃO: Geramos UUIDs válidos para o teste
    data = {
        "clientevizu_id": [str(uuid.uuid4()), str(uuid.uuid4())],
        "message": ["Olá, qual o status?", "Preciso de ajuda com a fatura"]
    }
    df = pd.DataFrame(data)

    p = tmp_path / "test_dataset.csv"
    df.to_csv(p, index=False)
    return str(p), data # Retorna os dados também para validação

# --- Testes ---

@pytest.mark.asyncio
async def test_orchestrator_run_evaluation_success(
    mock_db_session, mock_api_client, sample_dataset_path
):
    """
    Testa o caminho feliz completo da execução da avaliação.
    Verifica se o dataset é lido, as mensagens são enviadas e os resultados coletados.
    """
    path, test_data = sample_dataset_path # Desempacota os dados de teste

    orchestrator = EvaluationOrchestrator(
        db_session=mock_db_session,
        assistant_client=mock_api_client
    )

    # Mocka o método de coletar resultados para não depender do DB real
    with patch.object(orchestrator, '_collect_results_from_db') as mock_collect:
        run_id = await orchestrator.run_evaluation(
            dataset_path=path,
            assistant_version="test-v1"
        )

        assert run_id is not None

        # Validação do banco de dados
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

        # Validação da API (agora deve ser 2)
        assert mock_api_client.send_message.call_count == 2

        # Verifica se as chamadas foram feitas com os dados corretos do CSV
        mock_api_client.send_message.assert_any_call(
            clientevizu_id=test_data["clientevizu_id"][0],
            message=test_data["message"][0]
        )
        mock_api_client.send_message.assert_any_call(
            clientevizu_id=test_data["clientevizu_id"][1],
            message=test_data["message"][1]
        )

        mock_collect.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_handles_dataset_not_found(
    mock_db_session, mock_api_client
):
    """
    Testa o tratamento de erro quando o arquivo CSV do dataset não é encontrado.
    """
    orchestrator = EvaluationOrchestrator(
        db_session=mock_db_session,
        assistant_client=mock_api_client
    )

    with pytest.raises(FileNotFoundError):
        await orchestrator.run_evaluation(
            dataset_path="/caminho/para/arquivo/inexistente.csv",
            assistant_version="test-fail"
        )

    mock_api_client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_handles_api_client_error(
    mock_db_session, mock_api_client, sample_dataset_path
):
    """
    Testa o tratamento de erro quando o cliente da API levanta uma exceção.
    """
    path, _ = sample_dataset_path # Pegamos só o caminho

    mock_api_client.send_message.side_effect = Exception("Falha na conexão com a API")

    orchestrator = EvaluationOrchestrator(
        db_session=mock_db_session,
        assistant_client=mock_api_client
    )

    await orchestrator.run_evaluation(
        dataset_path=path,
        assistant_version="test-api-fail"
    )

    # A lógica de enviar mensagens foi chamada (agora o dataset é válido)
    assert mock_api_client.send_message.called

    # Valida se o status da run foi marcado como FAILED
    # (Verifica a segunda chamada ao commit, que é a de falha)
    assert mock_db_session.commit.call_count >= 2