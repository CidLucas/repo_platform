# tool_pool_api/server/tools.py
"""
Tool Registration - Phase 4: Server Composition

Este módulo é o ponto de entrada para registro de todas as tools.
Delega para o sistema de módulos em tool_modules/.

Arquitetura:
    tools.py → tool_modules/ → [rag_module, sql_module, common_module, ...]

Cada módulo:
1. Define a lógica de negócio (_*_logic functions)
2. Registra suas tools via @register_module decorator
3. Retorna lista de tools registradas

Benefícios:
- Separação de concerns por domínio
- Lazy loading de dependências pesadas
- Facilidade para adicionar novos módulos
- Preparação para composição de servidores MCP
"""

import logging
import sys

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token

# Importa o registry de módulos
from tool_pool_api.server.tool_modules import AVAILABLE_MODULES, register_all_tools

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP) -> None:
    """
    Registra todas as tools de todos os módulos no servidor FastMCP.

    Esta função é chamada pelo mcp_server.py durante a inicialização.
    Delega para tool_modules.register_all_tools() que carrega cada módulo.

    Args:
        mcp: Instância do servidor FastMCP
    """
    logger.info("Iniciando registro de tools via sistema de módulos...")

    stats = register_all_tools(mcp)

    logger.info(
        f"Ferramentas Vizu registradas com sucesso: "
        f"{stats['total']} tools de {len(stats['modules'])} módulos "
        f"({', '.join(stats['modules'])})"
    )


def get_available_modules() -> dict:
    """
    Retorna metadata sobre os módulos disponíveis.
    Útil para introspection e documentação.

    Returns:
        Dict com informações sobre cada módulo
    """
    return AVAILABLE_MODULES


# Namespace package normalization for tests importing via the `src.` prefix.
sys.modules.setdefault(
    "src.tool_pool_api.server.tools", sys.modules[__name__]
)

# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================
# As funções _*_logic foram movidas para seus respectivos módulos:
# - _executar_rag_cliente_logic → tool_modules/rag_module.py
# - _executar_sql_agent_logic → tool_modules/sql_module.py
# - _ferramenta_publica_de_teste_logic → tool_modules/common_module.py
#
# Se você precisa importar diretamente (ex: testes), use:
#   from tool_pool_api.server.tool_modules.rag_module import _executar_rag_cliente_logic
#   from tool_pool_api.server.tool_modules.sql_module import _executar_sql_agent_logic
#   from tool_pool_api.server.tool_modules.common_module import _ferramenta_publica_de_teste_logic

from tool_pool_api.server.dependencies import (
    get_context_service,
    load_context_from_token,
)
from tool_pool_api.server.tool_modules.common_module import _ferramenta_publica_de_teste_logic  # noqa: F401
from tool_pool_api.server.tool_modules.rag_module import _executar_rag_cliente_logic  # noqa: F401
from tool_pool_api.server.tool_modules.sql_module import _executar_sql_agent_logic  # noqa: F401
from vizu_rag_factory.factory import create_rag_runnable
