import uuid

import pytest

from blu_models.blu_client_context import BluClientContext
from blu_models.credencial_servico_externo import CredencialServicoExternoBase

# Criamos fixtures reutilizáveis para nossos dados de mock
# (Este arquivo pode ser copiado para as outras libs de factory)


@pytest.fixture
def mock_client_id() -> uuid.UUID:
    return uuid.UUID("123e4567-e89b-12d3-a456-426614174000")


@pytest.fixture
def mock_credencial_sql() -> CredencialServicoExternoBase:
    return CredencialServicoExternoBase(
        nome_servico="sql_mock",
        db_dialeto="postgresql",
        db_user="user_mock",
        db_password="pass_mock",
        db_host="host.mock.com",
        db_port=5432,
        db_name="db_mock",
    )


@pytest.fixture
def mock_blu_client_context(
    mock_client_id: uuid.UUID,
    mock_credencial_sql: CredencialServicoExternoBase,
) -> BluClientContext:
    """Retorna uma instância de modelo Pydantic BluClientContext."""
    return BluClientContext(
        id=mock_client_id,
        nome_empresa="test_empresa",
        available_tools={"enabled_tool_names": ["executar_rag_cliente", "executar_sql_agent"]},
        credenciais=[mock_credencial_sql],
    )


@pytest.fixture
def mock_blu_client_context_dict(mock_blu_client_context: BluClientContext) -> dict:
    """Retorna a representação em dict do contexto (como viria do Redis)."""
    return mock_blu_client_context.model_dump()


@pytest.fixture
def mock_cliente_blu_row(mock_client_id: uuid.UUID) -> dict:
    """Simula a linha retornada pelo Supabase (get_cliente_blu_by_id)."""
    return {
        "client_id": str(mock_client_id),
        "nome_empresa": "test_empresa",
        "cpf_cnpj": None,
        "tipo_cliente": "B2B",
        "tier": "BASIC",
        "company_profile": {"legal_name": "Test Corp"},
        "brand_voice": {"tone": "professional"},
        "team_structure": {"business_hours": "9-18"},
        "policies": {"return_policy": "30 days"},
        "data_schema": {"available_tables": ["orders", "products"]},
        "available_tools": {"enabled_tool_names": ["executar_rag_cliente"]},
    }
