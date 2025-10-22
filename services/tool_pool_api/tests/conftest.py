import uuid
from typing import AsyncGenerator, Callable, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport  # Importa o ASGITransport

# Importa o app MCP REAL para o cliente de teste se conectar
# Este caminho funciona pois 'src' está no pythonpath (via pyproject.toml)
from tool_pool_api.server.mcp_server import mcp
from tool_pool_api.core.config import Settings, get_settings

# Importa os schemas reais do vizu_shared_models
from vizu_shared_models.cliente_vizu import VizuClientContext
from vizu_shared_models.credencial_servico_externo import CredencialServicoExternoBase
from vizu_context_service.context_service import ContextService # Adicionado para resolver NameError


# REMOVIDA a fixture event_loop (DeprecationWarning)
# pytest-asyncio gerencia o loop automaticamente

@pytest.fixture(autouse=True)
def mock_settings(mocker):
    """
    Mocka as configurações da aplicação para os testes.
    Garante que DATABASE_URL e REDIS_URL estejam sempre presentes.
    """
    mock_settings_instance = Settings(
        DATABASE_URL="sqlite:///./test.db",
        REDIS_URL="redis://localhost:6379/0",
        VIZU_ENV="test"
    )
    mocker.patch("tool_pool_api.core.config.get_settings", return_value=mock_settings_instance)
    return mock_settings_instance


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture para criar um cliente de teste HTTP assíncrono para a aplicação MCP.

    Usa o transporte ASGI para testar a app 'streamable-http' (FastAPI) em memória,
    seguindo a sintaxe moderna do httpx (evitando o DeprecationWarning).
    """
    # Usa o transporte ASGI explícito em vez do atalho 'app='
    async with AsyncClient(
        transport=ASGITransport(app=mcp.http_app()),
        base_url="http://testserver"
    ) as test_client:
        yield test_client


@pytest.fixture
def mock_context_service(mocker, mock_settings) -> AsyncMock:
    """
    Mocka o get_context_service para que os testes possam controlar o ContextService.
    """
    mock_context_service_instance = AsyncMock(spec=ContextService) # Mocka a instância do serviço
    mocker.patch(
        "tool_pool_api.server.dependencies.get_context_service",
        return_value=mock_context_service_instance,
    )
    return mock_context_service_instance


@pytest.fixture(autouse=True) # Adicionado autouse para garantir que o mock seja aplicado
def mock_session_module(mocker):
    """
    Mocka o módulo session para evitar AttributeError ao tentar acessá-lo.
    """
    import sys
    sys.modules["tool_pool_api.server.session"] = mocker.MagicMock()


@pytest.fixture
def mock_factories(mocker) -> Dict[str, MagicMock]:
    """Mocka as fábricas de ferramentas importadas no session.py."""
    # Mockamos a função create_sql_agent no módulo session.py onde ela é importada
    mock_sql = mocker.patch(
        "tool_pool_api.server.session.create_sql_agent",
        return_value=MagicMock(invoke=MagicMock(return_value={"output": "SQL OK"})),
    )
    # Mockamos a função create_rag_runnable no módulo session.py
    mock_rag = mocker.patch(
        "tool_pool_api.server.session.create_rag_runnable",
        return_value=MagicMock(invoke=MagicMock(return_value={"output": "RAG OK"})),
    )
    # Retorna um dicionário para fácil acesso nos testes
    return {"sql": mock_sql, "rag": mock_rag}


@pytest.fixture
def fake_vizu_context_factory() -> Callable[..., VizuClientContext]:
    """
    Retorna uma função (factory) para criar um VizuClientContext falso e
    personalizável para os testes, usando o schema REAL (plano).
    """

    def _create_context(
        ferramenta_sql_habilitada: bool = True,
        ferramenta_rag_habilitada: bool = True,
    ) -> VizuClientContext:

        cliente_vizu_id = uuid.uuid4()

        # Mock de credenciais (simples, usando a classe Base)
        credenciais_mock = [
            CredencialServicoExternoBase(nome_servico="sql_db_mock", tipo_credencial="database_url", credenciais={"url": "sqlite:///:memory:"}),
            CredencialServicoExternoBase(nome_servico="qdrant_db_mock", tipo_credencial="api_key", credenciais={"api_key": "fake_qdrant_key"}),
        ]

        # Instancia o VizuClientContext REAL (plano)
        return VizuClientContext(
            id=cliente_vizu_id,
            api_key=f"api_key_mock_{cliente_vizu_id.hex}",
            nome_empresa="Empresa Teste Mock",

            # Configurações de Negócio
            prompt_base="Seja um assistente Vizu prestativo.",
            horario_funcionamento={"seg-sex": "09:00-18:00"},

            # Flags de Ferramentas
            ferramenta_rag_habilitada=ferramenta_rag_habilitada,
            ferramenta_sql_habilitada=ferramenta_sql_habilitada,

            # Credenciais
            credenciais=credenciais_mock
        )

    return _create_context