import uuid

import pytest

from blu_models.credencial_servico_externo import CredencialServicoExternoBase
from blu_models.blu_client_context import BluClientContext


@pytest.fixture
def mock_blu_client_context() -> BluClientContext:
    """Retorna uma instância de modelo Pydantic BluClientContext."""
    return BluClientContext(
        id=uuid.uuid4(),
        nome_empresa="test_empresa",
        available_tools={"enabled_tool_names": ["executar_rag_cliente"]},
        credenciais=[CredencialServicoExternoBase(nome_servico="sql_service_mock")],
    )
