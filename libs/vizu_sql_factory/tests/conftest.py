import pytest
import uuid
from vizu_models.vizu_client_context import VizuClientContext
from vizu_models.credencial_servico_externo import CredencialServicoExternoCreate

@pytest.fixture
def mock_vizu_client_context() -> VizuClientContext:
    """Retorna uma instância de modelo Pydantic VizuClientContext."""
    cliente_id = uuid.uuid4()
    return VizuClientContext(
        id=cliente_id,
        api_key="test_api_key",
        nome_empresa="test_empresa",
        prompt_base="test_prompt",
        horario_funcionamento={},
        ferramenta_rag_habilitada=True,
        ferramenta_sql_habilitada=True,
        credenciais=[
            CredencialServicoExternoCreate(
                nome_servico="sql_service_mock",
                cliente_vizu_id=cliente_id,
                credenciais={
                    "db_dialeto": "postgresql",
                    "db_user": "user_mock",
                    "db_password": "pass_mock",
                    "db_host": "host.mock.com",
                    "db_port": 5432,
                    "db_name": "db_mock"
                }
            )
        ]
    )