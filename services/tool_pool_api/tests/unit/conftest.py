# Em: services/tool_pool_api/tests/unit/conftest.py

import sys
import uuid
from unittest.mock import MagicMock

import pytest


# ── Pre-mock heavy server modules that are not needed for unit tests ──────────
# The tool_pool_api.server.__init__ imports mcp_server → resources which pulls
# in blu_tool_registry, blu_prompt_management, etc.  Unit tests that import
# individual tool_modules don't need the full server — mock the heavy chain.
_mock_module_names = [
    "blu_tool_registry",
    "blu_agent_framework",
    "blu_elicitation_service",
    "blu_experiment_service",
    "blu_hitl_service",
    "blu_llm_service",
]
# Submodules that are imported with `from package.module import ...`
_mock_submodule_names = [
    "blu_tool_registry.resource_resolver",
    "blu_tool_registry.registry",
]
for _mod_name in _mock_module_names:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()
for _mod_name in _mock_submodule_names:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()


@pytest.fixture
def mock_mcp_context():
    """
    Fornece um mock simples do fastmcp.Context.

    Nossa lógica de tool atual não o utiliza diretamente,
    então um mock padrão é suficiente.
    """
    return MagicMock()


@pytest.fixture
def mock_blu_context():
    """
    Fornece um mock do BluClientContext com os campos mínimos
    necessários para que os testes das tools passem.

    Isso é o que esperamos que 'load_context_from_token' retorne.
    """
    mock_ctx = MagicMock()

    # --- Atributos de Identificação ---
    mock_ctx.id = uuid.uuid4()
    mock_ctx.nome_empresa = "Cliente de Teste LTDA"

    # --- Atributos de Permissão (CRUCIAL para os testes) ---
    # Substituímos as flags por uma lista autoritativa de tools.
    mock_ctx.enabled_tools = []
    mock_ctx.get_enabled_tools_list = MagicMock(return_value=[
        "executar_rag_cliente",
        "executar_sql_agent",
    ])
    mock_ctx.tier = "BASIC"

    # --- Atributos de Configuração ---
    mock_ctx.collection_rag = "colecao_de_teste_rag"

    return mock_ctx
