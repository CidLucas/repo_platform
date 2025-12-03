# services/clients_api/tests/integration/test_clients_api.py
from fastapi.testclient import TestClient


def test_create_and_read_cliente(test_client: TestClient):
    """
    Testa o fluxo completo: criar um cliente e depois lê-lo da lista.
    """
    # 1. Criação do Cliente (POST)
    response_create = test_client.post(
        "/api/v1/clientes",
        json={
            "nome_empresa": "Teste de Integração Inc.",
            "tipo_cliente": "externo",
            "tier": "enterprise",
        },
    )
    assert response_create.status_code == 201
    created_data = response_create.json()
    assert created_data["nome_empresa"] == "Teste de Integração Inc."
    assert "id" in created_data
    assert (
        "api_key" not in created_data
    )  # Verifica se a API key NÃO é exposta na resposta

    # 2. Leitura da Lista (GET)
    response_read = test_client.get("/api/v1/clientes")
    assert response_read.status_code == 200
    read_data = response_read.json()

    # Verifica se o cliente que acabamos de criar está na lista retornada
    assert len(read_data) > 0
    assert any(cliente["id"] == created_data["id"] for cliente in read_data)

    # Verifica se a API key NÃO é exposta no endpoint de listagem
    assert "api_key" not in read_data[0]


def test_health_check(test_client: TestClient):
    """Testa o endpoint de health check."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
