# services/clients_api/tests/unit/test_client_service.py
from unittest.mock import MagicMock
from clients_api.services.client_service import ClienteVizuService
from vizu_models.cliente_vizu import ClienteVizuCreate
from vizu_db_connector.models.cliente_vizu import ClienteVizu

def test_create_cliente_vizu_service():
    """
    Testa a lógica de criação de cliente no serviço em total isolamento.
    """
    # 1. Preparação (Arrange)
    # Criamos um "dublê" para a sessão do banco de dados.
    mock_db_session = MagicMock()

    # Criamos uma instância do nosso serviço.
    service = ClienteVizuService(ClienteVizu)

    # Criamos os dados de entrada.
    cliente_in = ClienteVizuCreate(
        nome_empresa="Teste Unitário SA",
        tipo_cliente="externo",
        tier="sme"
    )

    # 2. Ação (Act)
    # Executamos a função que queremos testar.
    result = service.create_cliente_vizu(db_session=mock_db_session, cliente_in=cliente_in)

    # 3. Verificação (Assert)
    # Verificamos se a função se comportou como esperado.

    # O resultado deve ter a API Key não-criptografada.
    assert hasattr(result, 'api_key')
    assert len(result.api_key) == 64 # 32 bytes em hexadecimal

    # Verificamos se o serviço tentou salvar no banco.
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()