import uuid

import pytest

from vizu_models.credencial_servico_externo import CredencialServicoExternoBase
from vizu_models.vizu_client_context import VizuClientContext


@pytest.fixture
def mock_vizu_client_context() -> VizuClientContext:
    """Retorna uma instância de modelo Pydantic VizuClientContext."""
    return VizuClientContext(
        id=uuid.uuid4(),
        nome_empresa="test_empresa",
        enabled_tools=["executar_rag_cliente"],
        credenciais=[CredencialServicoExternoBase(nome_servico="sql_service_mock")],
    )
