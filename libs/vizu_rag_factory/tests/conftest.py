import pytest
import uuid
from vizu_models.vizu_client_context import VizuClientContext
from vizu_models.credencial_servico_externo import CredencialServicoExternoBase

@pytest.fixture
def mock_vizu_client_context() -> VizuClientContext:
    """Retorna uma instância de modelo Pydantic VizuClientContext."""
    return VizuClientContext(
        id=uuid.uuid4(),
        api_key="test_api_key",
        nome_empresa="test_empresa",
        prompt_base="test_prompt",
        horario_funcionamento={},
        ferramenta_rag_habilitada=True,
        ferramenta_sql_habilitada=True,
        credenciais=[
            CredencialServicoExternoBase(
                nome_servico="sql_service_mock"
            )
        ]
    )