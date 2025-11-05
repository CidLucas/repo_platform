# Em: services/tool_pool_api/tests/unit/conftest.py

import pytest
import uuid
from unittest.mock import MagicMock

@pytest.fixture
def mock_mcp_context():
    """
    Fornece um mock simples do fastmcp.Context.

    Nossa lógica de tool atual não o utiliza diretamente,
    então um mock padrão é suficiente.
    """
    return MagicMock()

@pytest.fixture
def mock_vizu_context():
    """
    Fornece um mock do VizuClientContext com os campos mínimos
    necessários para que os testes das tools passem.

    Isso é o que esperamos que 'load_context_from_token' retorne.
    """
    mock_ctx = MagicMock()

    # --- Atributos de Identificação ---
    mock_ctx.id = uuid.uuid4()
    mock_ctx.nome_empresa = "Cliente de Teste LTDA"

    # --- Atributos de Permissão (CRUCIAL para os testes) ---
    # Seu teste falharia no 'if' se estes não fossem True.
    mock_ctx.ferramenta_rag_habilitada = True
    mock_ctx.ferramenta_sql_habilitada = True

    # --- Atributos de Configuração ---
    mock_ctx.collection_rag = "colecao_de_teste_rag"

    # (Adicione outros campos do VizuClientContext conforme
    # sua lógica de tool for precisando deles)

    return mock_ctx