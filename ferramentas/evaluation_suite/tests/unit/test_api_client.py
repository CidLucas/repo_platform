import json

import httpx
import pytest

# O componente que estamos testando
from evaluation_suite.clients.api_client import APIClient

# URL base para os testes
BASE_URL = "http://test-api.vizu.local"

@pytest.mark.asyncio
async def test_api_client_send_message_success(httpx_mock):
    """
    Testa o caminho feliz: o cliente envia uma mensagem e a API retorna 200 OK.
    """
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/atendente/",
        status_code=200,
        json={"status": "recebido"}
    )

    client = APIClient(base_url=BASE_URL)

    try:
        await client.send_message(
            clientevizu_id="test-client-id",
            message="Olá, mundo!"
        )
    finally:
        await client.close()

    requests = httpx_mock.get_requests()
    assert len(requests) == 1

    # CORREÇÃO: Removidas as asserções antigas. Apenas esta validação de dicionário permanece.
    request_payload_dict = json.loads(requests[0].read())
    assert request_payload_dict["clientevizu_id"] == "test-client-id"
    assert request_payload_dict["mensagem"] == "Olá, mundo!"


@pytest.mark.asyncio
async def test_api_client_handles_http_error(httpx_mock):
    """
    Testa o tratamento de erro: o cliente tenta enviar uma mensagem,
    mas a API retorna um erro 500 (Internal Server Error).
    """
    # Configura o mock para responder com um status de erro
    httpx_mock.add_response(
        method="POST",
        url=f"{BASE_URL}/atendente/",
        status_code=500,
        text="Erro interno no servidor"
    )

    client = APIClient(base_url=BASE_URL)

    # O teste espera que uma exceção do tipo httpx.HTTPStatusError seja levantada.
    # O bloco `with pytest.raises(...)` captura e valida essa exceção.
    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        try:
            await client.send_message(
                clientevizu_id="test-client-id",
                message="Mensagem de teste"
            )
        finally:
            await client.close()

    # Validações adicionais sobre a exceção capturada
    assert excinfo.value.response.status_code == 500


def test_api_client_instantiation_fails_without_base_url():
    """
    Testa a validação no construtor: o cliente não pode ser
    instanciado sem uma URL base.
    """
    with pytest.raises(ValueError, match="A URL base da API é obrigatória."):
        APIClient(base_url="")
