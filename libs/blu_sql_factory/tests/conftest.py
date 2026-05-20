import uuid

import pytest

from blu_models.credencial_servico_externo import CredencialServicoExternoCreate
from blu_models.blu_client_context import BluClientContext


@pytest.fixture
def mock_blu_client_context() -> BluClientContext:
    """Retorna uma instância de modelo Pydantic BluClientContext."""
    client_id = uuid.uuid4()
    return BluClientContext(
        id=client_id,
        api_key="test_api_key",
        nome_empresa="test_empresa",
        prompt_base="test_prompt",
        horario_funcionamento={},
        ferramenta_rag_habilitada=True,
        ferramenta_sql_habilitada=True,
        credenciais=[
            CredencialServicoExternoCreate(
                nome_servico="sql_service_mock",
                client_id=client_id,
                credenciais={
                    "db_dialeto": "postgresql",
                    "db_user": "user_mock",
                    "db_password": "pass_mock",
                    "db_host": "host.mock.com",
                    "db_port": 5432,
                    "db_name": "db_mock",
                },
            )
        ],
    )
