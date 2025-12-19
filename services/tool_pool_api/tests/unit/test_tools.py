# tests/unit/test_tools.py
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

# --- CORREÇÃO AQUI ---
# Importe as funções de LÓGICA, não as "tools"
from src.tool_pool_api.server.tools import _executar_rag_cliente_logic

# ... (outros imports de mocks)


@pytest.mark.asyncio
async def test_executar_rag_cliente_sucesso(
    mock_mcp_context,  # Mock do Context do FastMCP
    mock_vizu_context,  # Mock do seu VizuClientContext
):
    """
    Testa o caminho feliz do 'executar_rag_cliente_logic'.
    """

    # 1. Mockar as dependências que serão chamadas DENTRO da tool
    mock_ctx_service = MagicMock()
    mock_token = MagicMock(claims={"sub": "user-123", "email": "test@vizu.ai"})
    mock_load_context = AsyncMock(return_value=mock_vizu_context)
    # 1. Crie o mock do runnable
    mock_rag_runnable = AsyncMock()

    # 2. Configure o *método .ainvoke()* dele para retornar a string
    mock_rag_runnable.ainvoke.return_value = "Resposta do RAG"

    # 3. Configure o factory para retornar o mock do runnable (como antes)
    mock_create_rag = MagicMock(return_value=mock_rag_runnable)

    # 2. Aplicar os patches para interceptar as chamadas
    # O path DEVE ser 'src.tool_pool_api.server.tools.NOME_DA_FUNCAO'
    with patch(
        "src.tool_pool_api.server.tools.get_context_service",
        return_value=mock_ctx_service,
    ) as p_ctx_svc, patch(
        "src.tool_pool_api.server.tools.get_access_token", return_value=mock_token
    ) as p_token, patch(
        "src.tool_pool_api.server.tools.load_context_from_token", mock_load_context
    ) as p_load_ctx, patch(
        "src.tool_pool_api.server.tools.create_rag_runnable", mock_create_rag
    ) as p_create_rag:
        # 3. Executar a função LÓGICA
        resultado = await _executar_rag_cliente_logic(
            query="Qual o faturamento?", ctx=mock_mcp_context
        )

        # 4. Validar
        assert resultado == "Resposta do RAG"
        p_load_ctx.assert_called_once_with(mock_ctx_service, mock_token)
        p_create_rag.assert_called_once_with(mock_vizu_context, llm=ANY)
        mock_rag_runnable.ainvoke.assert_called_once_with(
            {"question": "Qual o faturamento?"}
        )
