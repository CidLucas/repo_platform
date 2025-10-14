import uuid
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Não precisamos mais importar a 'app' aqui!
# from clientes_finais_api.main import app

from vizu_db_connector.models.cliente_vizu import ClienteVizu
from vizu_shared_models.cliente_vizu import TipoCliente, TierCliente
from clientes_finais_api.api.dependencies import get_cliente_vizu_id_from_token

def test_create_cliente_final_api(api_client: TestClient, db_session: Session):
    """Testa a criação bem-sucedida de um cliente final."""
    # ARRANGE
    test_cliente_vizu_id = uuid.uuid4()
    db_cliente_vizu = ClienteVizu(
        id=test_cliente_vizu_id,
        nome_empresa="Cliente de Teste LTDA",
        tipo_cliente=TipoCliente.EXTERNO, tier=TierCliente.SME,
    )
    db_session.add(db_cliente_vizu)
    db_session.commit()

    # Sobrescreve a dependência de autenticação diretamente no cliente de teste
    api_client.app.dependency_overrides[get_cliente_vizu_id_from_token] = lambda: test_cliente_vizu_id

    # ACT
    response = api_client.post("/clientes-finais/", json={
        "id_externo": "integ-test-1", "nome": "Cliente de Integração"
    })

    # ASSERT
    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["cliente_vizu_id"] == str(test_cliente_vizu_id)

    # Limpa o override específico deste teste
    del api_client.app.dependency_overrides[get_cliente_vizu_id_from_token]


def test_list_clientes_finais_api(api_client: TestClient, db_session: Session):
    """Testa a listagem, garantindo o isolamento entre os testes."""
    # ARRANGE
    test_cliente_vizu_id = uuid.uuid4()
    db_cliente_vizu = ClienteVizu(
        id=test_cliente_vizu_id,
        nome_empresa="Outro Cliente SA",
        tipo_cliente=TipoCliente.INTERNO, tier=TierCliente.ENTERPRISE,
    )
    db_session.add(db_cliente_vizu)
    db_session.commit()
    api_client.app.dependency_overrides[get_cliente_vizu_id_from_token] = lambda: test_cliente_vizu_id

    api_client.post("/clientes-finais/", json={"id_externo": "id_1", "nome": "Cliente 1"})

    # ACT
    response = api_client.get("/clientes-finais/")

    # ASSERT
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1

    del api_client.app.dependency_overrides[get_cliente_vizu_id_from_token]