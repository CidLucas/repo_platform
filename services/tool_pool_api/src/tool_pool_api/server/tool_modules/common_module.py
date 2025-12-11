# tool_pool_api/server/tool_modules/common_module.py
"""
Módulo Common - Ferramentas Públicas/Comuns

Este módulo contém tools públicas disponíveis para todos os clientes.

NOTA: Ferramentas de diagnóstico (ping, server_info) foram movidas para
endpoints HTTP determinísticos em mcp_server.py:
  - GET /health → health check para k8s/load balancers
  - GET /info   → metadata do servidor para admin/debug

Apenas ferramentas úteis para a LLM ficam aqui.
"""

import logging

from fastmcp import FastMCP

from . import register_module

logger = logging.getLogger(__name__)


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


def _ferramenta_publica_de_teste_logic() -> str:
    """
    Ferramenta de teste para verificar conectividade MCP.
    Útil para validar que o agente consegue executar tools.

    Returns:
        Mensagem de confirmação
    """
    logger.info("[Common] Ferramenta pública de teste executada.")
    return "Ferramenta pública executada com sucesso!"


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo Common."""

    @mcp.tool(
        name="ferramenta_publica_de_teste",
        description=(
            "[USO INTERNO] Ferramenta de diagnóstico para testes de conectividade. "
            "NÃO use para responder clientes."
        ),
    )
    def ferramenta_publica_de_teste() -> str:
        return _ferramenta_publica_de_teste_logic()

    logger.info("[Common Module] Ferramentas registradas.")
    return ["ferramenta_publica_de_teste"]
