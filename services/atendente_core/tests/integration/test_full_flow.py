# tests/integration/test_full_flow.py

import uuid
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.orm import Session

# Importa apenas os modelos
from vizu_models import ClienteVizu, TipoCliente, TierCliente


@pytest.mark.integration
def test_e2e_flow_with_db_and_redis_cache(
    test_client_db_session: Session,  # Recebe a sessão unificada
    test_client,  # Recebe o cliente da API e do Redis
):
    """
    Testa o fluxo completo de ponta a ponta, validando a estratégia "Redis-First".
    """
    db_session = test_client_db_session
    client, redis_client = test_client

    # --- 1. SETUP DO AMBIENTE DE TESTE ---
    redis_client.flushall()

    test_api_key = "test_api_key_12345"
    test_phone_number = "whatsapp:+5521999998888"
    cliente_id = uuid.uuid4()

    novo_cliente = ClienteVizu(
        id=cliente_id,
        api_key=test_api_key,
        nome_empresa="Padaria Teste",
        tipo_cliente=TipoCliente.EXTERNO,
        tier=TierCliente.SME,
    )
    # Populate merged configuration fields directly on the client
    novo_cliente.prompt_base = "Seja um assistente de padaria."
    novo_cliente.ferramenta_rag_habilitada = True
    db_session.add(novo_cliente)
    db_session.commit()

    # --- 2. EXECUÇÃO E VERIFICAÇÃO (PRIMEIRA CHAMADA - CACHE MISS) ---
    # NÃO precisamos mais mockar a query do banco de dados!
    with patch("atendente_core.api.router.agent_graph") as mock_agent_graph:
        mock_agent_graph.invoke.return_value = {
            "messages": [MagicMock(content="Olá! Bem-vindo à Padaria Teste.")]
        }
        response1 = client.post(
            "/api/v1/incoming",
            headers={"X-Vizu-API-Key": test_api_key},
            data={"From": test_phone_number, "Body": "Bom dia"},
        )
        assert response1.status_code == 200
        assert "Padaria Teste" in response1.text
        mock_agent_graph.invoke.assert_called_once()

    redis_key = f"context:client:{test_api_key}"
    assert redis_client.exists(redis_key)
    ttl = redis_client.ttl(redis_key)
    assert 86300 < ttl <= 86400

    # --- 3. EXECUÇÃO E VERIFICAÇÃO (SEGUNDA CHAMADA - CACHE HIT) ---
    with patch("atendente_core.api.router.agent_graph") as mock_agent_graph:
        mock_agent_graph.invoke.return_value = {
            "messages": [MagicMock(content="Pois não?")]
        }
        response2 = client.post(
            "/api/v1/incoming",
            headers={"X-Vizu-API-Key": test_api_key},
            data={"From": test_phone_number, "Body": "Queria um pão"},
        )
        assert response2.status_code == 200
        assert "Pois não?" in response2.text
        mock_agent_graph.invoke.assert_called_once()

    print("\n--- Teste de integração ponta a ponta CONCLUÍDO COM SUCESSO! ---")
