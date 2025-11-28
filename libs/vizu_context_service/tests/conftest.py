import pytest
import uuid
from unittest.mock import MagicMock
from vizu_models.vizu_client_context import VizuClientContext

from vizu_models.configuracao_negocio import ConfiguracaoNegocioBase
from vizu_models.credencial_servico_externo import CredencialServicoExternoBase
# Criamos fixtures reutilizáveis para nossos dados de mock
# (Este arquivo pode ser copiado para as outras libs de factory)

@pytest.fixture
def mock_cliente_id() -> uuid.UUID:
    return uuid.UUID("123e4567-e89b-12d3-a456-426614174000")

@pytest.fixture
def mock_configuracao() -> ConfiguracaoNegocioBase:
    return ConfiguracaoNegocioBase(
        ferramenta_sql_habilitada=True,
        ferramenta_rag_habilitada=True,
        schema_sql="schema_mock"
    )

@pytest.fixture
def mock_credencial_sql() -> CredencialServicoExternoBase:
    return CredencialServicoExternoBase(
        db_dialeto="postgresql",
        db_user="user_mock",
        db_password="pass_mock",
        db_host="host.mock.com",
        db_port=5432,
        db_name="db_mock"
    )

@pytest.fixture
def mock_vizu_client_context(
    mock_cliente_id: uuid.UUID,
    mock_configuracao: ConfiguracaoNegocioBase,
    mock_credencial_sql: CredencialServicoExternoBase
) -> VizuClientContext:
    """Retorna uma instância de modelo Pydantic VizuClientContext."""
    return VizuClientContext(
        cliente_id=mock_cliente_id,
        api_key_hash="hash_mock",
        ativo=True,
        configuracao=mock_configuracao,
        credencial_sql=mock_credencial_sql
    )

@pytest.fixture
def mock_vizu_client_context_dict(
    mock_vizu_client_context: VizuClientContext
) -> dict:
    """Retorna a representação em dict do contexto (como viria do Redis)."""
    return mock_vizu_client_context.model_dump()