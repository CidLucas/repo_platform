from unittest.mock import Mock
import uuid

from clientes_finais_api.services.cliente_final_service import ClienteFinalService
from clientes_finais_api.schemas.cliente_final_schemas import ClienteFinalCreate


def test_create_cliente_final_service():
    """
    Testa a criação de um cliente final na camada de serviço,
    simulando (mockando) a interação com o banco de dados.
    """
    # ARRANGE
    mock_db_session = Mock()
    service = ClienteFinalService(db_session=mock_db_session)
    cliente_vizu_id = uuid.uuid4()
    cliente_data = ClienteFinalCreate(
        id_externo="whatsapp:12345", nome="Cliente Teste Unitário"
    )

    # ACT
    service.create_cliente_final(
        cliente_in=cliente_data, cliente_vizu_id=cliente_vizu_id
    )

    # ASSERT - Verifica o novo comportamento esperado
    mock_db_session.add.assert_called_once()
    mock_db_session.flush.assert_called_once()  # DEVE chamar flush
    mock_db_session.refresh.assert_called_once()
    mock_db_session.commit.assert_not_called()  # NÃO DEVE mais chamar commit
