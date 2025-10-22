# test_tool_pool.py (Adaptado para httpx.AsyncClient)
import uuid
from unittest.mock import AsyncMock, MagicMock, patch # Adicionado patch

import pytest
from httpx import AsyncClient # Importa o cliente HTTP

# Importa os tipos que vamos mockar
# from vizu_context_service.context_service import ContextService # Não precisa mais
from vizu_shared_models.cliente_vizu import VizuClientContext

# Marca todos os testes neste arquivo como asyncio
pytestmark = pytest.mark.asyncio

# As fixtures fake_sql_agent e fake_rag_runnable permanecem iguais

async def test_session_happy_path_all_tools_enabled(
    client: AsyncClient, # Agora recebe o AsyncClient HTTP
    mock_context_service: AsyncMock,
    mock_factories: dict,
    fake_vizu_context_factory: callable,
    fake_sql_agent: MagicMock,
    fake_rag_runnable: MagicMock,
):
    """
    TESTE 1 (Happy Path - Adaptado para HTTP):
    Valida se um cliente com ID válido consegue chamar as ferramentas via HTTP.
    """
    # --- Arrange ---
    valid_cliente_id = uuid.uuid4()
    fake_context = fake_vizu_context_factory(
        ferramenta_sql_habilitada=True, ferramenta_rag_habilitada=True
    )
    mock_context_service.get_client_context_by_id.return_value = fake_context
    mock_factories["sql"].return_value = fake_sql_agent
    mock_factories["rag"].return_value = fake_rag_runnable

    # --- Act ---

    # Simula a chamada da ferramenta SQL via HTTP
    # NOTA: O endpoint '/VizuToolPool/executar_sql_cliente' é um EXEMPLO.
    # Você precisa verificar qual endpoint o FastMCP(transport='streamable-http')
    # realmente cria para chamadas de ferramenta.
    headers = {"X-MCP-Client-ID": str(valid_cliente_id)} # Passa o ID no header (ou onde o MCP esperar)
    sql_response = await client.post(
        "/VizuToolPool/executar_sql_cliente", # Endpoint hipotético
        json={"query": "SELECT * FROM users"},
        headers=headers
    )

    # Simula a chamada da ferramenta RAG via HTTP
    rag_response = await client.post(
        "/VizuToolPool/executar_rag_cliente", # Endpoint hipotético
        json={"query": "O que é a Vizu?"},
        headers=headers
    )

    # --- Assert ---
    # 1. Verifica status codes HTTP
    assert sql_response.status_code == 200
    assert rag_response.status_code == 200

    # 2. Verifica se o ContextService foi chamado (pode ser chamado uma vez por request agora)
    # Ajuste a asserção conforme a implementação exata da sessão MCP no streamable-http
    # Pode ser chamado uma vez no início ou a cada chamada de ferramenta.
    # Exemplo: assert mock_context_service.get_client_context_by_id.call_count >= 1
    mock_context_service.get_client_context_by_id.assert_called()


    # 3. Verifica se as Factories foram chamadas
    mock_factories["sql"].assert_called_once_with(fake_context)
    mock_factories["rag"].assert_called_once_with(fake_context)

    # 4. Verifica se os agentes/runnables falsos foram invocados
    fake_sql_agent.invoke.assert_called_once_with({"input": "SELECT * FROM users"})
    fake_rag_runnable.invoke.assert_called_once_with({"input": "O que é a Vizu?"})

    # 5. Verifica o CONTEÚDO da resposta HTTP
    assert sql_response.json() == {"output": "SQL EXECUTADO COM SUCESSO"}
    assert rag_response.json() == {"output": "RAG EXECUTADO COM SUCESSO"} # Ajuste conforme o retorno real da ferramenta

# --- Adaptações similares seriam necessárias para os outros testes ---

async def test_session_auth_fail_context_not_found(
    client: AsyncClient, # Recebe o AsyncClient HTTP
    mock_context_service: AsyncMock,
):
    """
    TESTE 2 (Auth Fail - Not Found - Adaptado para HTTP):
    Valida se a chamada da ferramenta falha com um erro HTTP apropriado
    se o 'cliente_id' for inválido.
    """
    # --- Arrange ---
    invalid_cliente_id = uuid.uuid4()
    mock_context_service.get_client_context_by_id.return_value = None
    headers = {"X-MCP-Client-ID": str(invalid_cliente_id)}

    # --- Act ---
    response = await client.post(
        "/VizuToolPool/executar_sql_cliente", # Endpoint hipotético
        json={"query": "SELECT 1"},
        headers=headers
    )

    # --- Assert ---
    # Verifica se o status code é 401 Unauthorized ou 404 Not Found,
    # dependendo de como você implementou o erro no session_manager.
    # Idealmente, seria 401 ou 403 Forbidden.
    assert response.status_code in [401, 403, 404] # Ajuste conforme sua implementação
    # Verifica se a mensagem de erro está no corpo da resposta
    assert "Contexto não encontrado" in response.text # Ou response.json()['detail']

    mock_context_service.get_client_context_by_id.assert_called_once_with(
        cliente_id=invalid_cliente_id
    )

async def test_session_auth_fail_no_cliente_id(
    client: AsyncClient, # Recebe o AsyncClient HTTP
    mock_context_service: AsyncMock,
):
    """
    TESTE 2.1 (Auth Fail - Bad Request - Adaptado para HTTP):
    Valida se a chamada da ferramenta falha com erro HTTP se 'cliente_id'
    não for fornecido no header (ou onde for esperado).
    """
    # --- Act ---
    response = await client.post(
        "/VizuToolPool/executar_sql_cliente", # Endpoint hipotético
        json={"query": "SELECT 1"},
        # Sem header X-MCP-Client-ID
    )

    # --- Assert ---
    # Verifica se o status code é 400 Bad Request ou 401/403.
    assert response.status_code in [400, 401, 403] # Ajuste conforme sua implementação
    assert "obrigatório" in response.text # Ou response.json()['detail']

    mock_context_service.get_client_context_by_id.assert_not_called()

async def test_session_tool_disabled(
    client: AsyncClient, # Recebe o AsyncClient HTTP
    mock_context_service: AsyncMock,
    mock_factories: dict,
    fake_vizu_context_factory: callable,
):
    """
    TESTE 3 (Tool Disabled - Adaptado para HTTP):
    Valida se a chamada a uma ferramenta desabilitada retorna o erro
    amigável dentro de uma resposta HTTP 200 OK.
    """
    # --- Arrange ---
    valid_cliente_id = uuid.uuid4()
    fake_context = fake_vizu_context_factory(
        ferramenta_sql_habilitada=False, # SQL desabilitado
        ferramenta_rag_habilitada=True
    )
    mock_context_service.get_client_context_by_id.return_value = fake_context
    mock_factories["sql"].return_value = None # Factory retorna None
    mock_factories["rag"].return_value = MagicMock() # RAG funciona
    headers = {"X-MCP-Client-ID": str(valid_cliente_id)}

    # --- Act ---
    response = await client.post(
        "/VizuToolPool/executar_sql_cliente", # Endpoint hipotético da ferramenta SQL
        json={"query": "SELECT * FROM users"},
        headers=headers
    )

    # --- Assert ---
    # 1. A resposta HTTP foi bem-sucedida (200 OK)
    assert response.status_code == 200

    # 2. O corpo da resposta contém o erro específico da ferramenta
    assert response.json() == {
        "error": "Ferramenta SQL não habilitada para este cliente."
    }

    # 3. O ContextService foi chamado
    mock_context_service.get_client_context_by_id.assert_called() # Pode ser > 1 dependendo da implementação

    # 4. A factory de SQL foi chamada (e retornou None)
    mock_factories["sql"].assert_called_once_with(fake_context)