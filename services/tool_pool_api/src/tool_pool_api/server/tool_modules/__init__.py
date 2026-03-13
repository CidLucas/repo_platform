# tool_pool_api/server/tool_modules/__init__.py
"""
Tool Modules Registry - Phase 4: Server Composition

Este pacote organiza tools em módulos por domínio, permitindo:
1. Melhor organização e manutenibilidade
2. Lazy loading de dependências pesadas
3. Facilidade para adicionar novos domínios
4. Preparação para futura composição de servidores MCP

Estrutura:
- rag/       → Tools de RAG e knowledge base
- sql/       → Tools de SQL Agent
- scheduling/→ Tools de agendamento (futuro)
- internal/  → Tools de diagnóstico interno

Uso:
    from tool_pool_api.server.tool_modules import register_all_tools
    register_all_tools(mcp)
"""

import logging
from collections.abc import Callable
from typing import List

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Registry de módulos de tools
# Cada módulo exporta uma função register_tools(mcp: FastMCP) -> List[str]
# que retorna os nomes das tools registradas
_MODULE_REGISTRY: list[Callable[[FastMCP], list[str]]] = []


def register_module(register_fn: Callable[[FastMCP], list[str]]):
    """
    Decorator para registrar um módulo de tools.

    Exemplo:
        @register_module
        def register_tools(mcp: FastMCP) -> List[str]:
            mcp.tool(name="minha_tool")(minha_funcao)
            return ["minha_tool"]
    """
    _MODULE_REGISTRY.append(register_fn)
    return register_fn


def register_all_tools(mcp: FastMCP) -> dict:
    """
    Registra todas as tools de todos os módulos.

    Returns:
        Dict com estatísticas: {"total": N, "modules": [...], "tools": [...]}
    """
    all_tools = []
    modules_loaded = []

    # Importa módulos para trigger os decorators
    from . import (
        common_module,
        config_helper_module,
        csv_module,
        prompt_module,
        rag_module,
        sql_module,
        web_monitor_module,
    )

    # Optional Google module (integration)
    try:
        from . import google_module  # noqa: F401
    except Exception as e:
        logger.warning(f"Google module not available at import time: {e}")

    for register_fn in _MODULE_REGISTRY:
        try:
            module_name = register_fn.__module__.split(".")[-1]
            tool_names = register_fn(mcp)
            all_tools.extend(tool_names)
            modules_loaded.append(module_name)
            logger.info(f"Módulo '{module_name}' carregado: {tool_names}")
        except Exception as e:
            logger.error(f"Erro ao carregar módulo: {e}")

    logger.info(f"Total: {len(all_tools)} tools de {len(modules_loaded)} módulos")

    return {"total": len(all_tools), "modules": modules_loaded, "tools": all_tools}


# Metadata sobre os módulos disponíveis
AVAILABLE_MODULES = {
    "rag": {
        "description": "RAG e Knowledge Base",
        "tools": ["executar_rag_cliente"],
        "requires_auth": True,
    },
    "sql": {
        "description": "SQL Agent para dados estruturados",
        "tools": ["executar_sql_agent"],
        "requires_auth": True,
    },
    "csv": {
        "description": "CSV analytics with DuckDB",
        "tools": [
            "execute_csv_query",
            "list_csv_datasets",
        ],
        "requires_auth": True,
    },
    "config_helper": {
        "description": "Config Helper tools for standalone agent setup",
        "tools": [
            "check_config_completeness",
            "save_config_field",
            "get_agent_requirements",
            "finalize_config",
            "peek_csv_columns",
        ],
        "requires_auth": True,
    },
    "common": {
        "description": "Ferramentas públicas e utilitários",
        "tools": ["ferramenta_publica_de_teste"],
        "requires_auth": False,
    },
    "monitoring": {
        "description": "Monitoramento web com crawl4ai e expansão semântica",
        "tools": ["monitor_feature", "monitor_keywords", "monitor_company"],
        "requires_auth": False,
    },
    "google": {
        "description": "Google Suite integrations (Sheets, Gmail, Calendar)",
        "tools": ["write_to_sheet", "read_emails", "query_calendar"],
        "requires_auth": True,
    },
    "prompts": {
        "description": "Native MCP prompts for dynamic prompt generation",
        "prompts": ["atendente_system", "text_to_sql_system", "rag_context", "elicitation"],
        "requires_auth": False,  # Prompts are public, auth is handled at variable level
    },
    # Futuros módulos:
    # "scheduling": {
    #     "description": "Agendamento de compromissos",
    #     "tools": ["agendar_servico", "consultar_agenda", "cancelar_agendamento"],
    #     "requires_auth": True,
    #     "requires_elicitation": True  # Usa confirmação
    # },
}
