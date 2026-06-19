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

from . import knowledge_graph_sync  # noqa: F401  # T4.3b — internal tool

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
        monday_module,  # noqa: F401
        notion_module,  # noqa: F401
        pm_module,  # noqa: F401
        context_module,  # noqa: F401
        document_intelligence_module,
        ocr_extraction_module,
        platform_module,  # noqa: F401
        prompt_module,
        rag_module,
        report_module,
        rfq_module,
        rfq_whatsapp_module,
        routines_module,  # noqa: F401
        sql_module,
        whatsapp_client_module,
        web_crawl_module,
        web_monitor_module,
        slack_module,  # noqa: F401
        memory_module,
        memory_pre_flight_module,
        version_module,
        diff_module,
    )

    # Optional chart module
    try:
        from . import chart_module  # noqa: F401
    except Exception as e:
        logger.warning(f"Chart module not available: {e}")

    # Optional Google module (integration)
    try:
        from . import google_module  # noqa: F401
    except Exception as e:
        logger.warning(f"Google module not available at import time: {e}")

    # Optional Fiscal module (stub)
    try:
        from . import fiscal_module  # noqa: F401
    except Exception as e:
        logger.warning(f"Fiscal module not available at import time: {e}")

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
    "web_crawl": {
        "description": "Deep website crawling for content extraction and company context building",
        "tools": ["crawl_website", "extract_company_context"],
        "requires_auth": False,
    },
    "google": {
        "description": "Google Suite integrations (Sheets, Gmail, Calendar, Docs)",
        "tools": [
            "write_to_sheet",
            "read_emails",
            "query_calendar",
            "google_docs_create",
            "google_docs_read",
            "google_docs_write",
            "google_docs_list",
            "import_spreadsheet_schedule",
        ],
        "requires_auth": True,
    },
    "prompts": {
        "description": "Native MCP prompts for dynamic prompt generation",
        "prompts": ["atendente_system", "text_to_sql_system", "rag_context", "elicitation"],
        "requires_auth": False,  # Prompts are public, auth is handled at variable level
    },
    "document_intelligence": {
        "description": "Document analysis, structured extraction, and knowledge persistence",
        "tools": [
            "extract_structured_data",
            "compile_time_series",
            "write_summary_to_kb",
        ],
        "requires_auth": True,
    },
    "ocr_extraction": {
        "description": "OCR & structured data extraction with configurable pipeline options",
        "tools": [
            "extract_document_with_ocr",
            "summarize_document_sections",
        ],
        "requires_auth": True,
    },
    "rfq": {
        "description": "Cotação e compras (RFQ/PO)",
        "tools": [
            "parse_buying_list",
            "validate_buying_list",
            "list_suppliers",
            "dispatch_rfq",
            "check_rfq_responses",
            "submit_mock_response",
            "optimize_allocation",
            "generate_po_report",
            "create_purchase_order",
            "approve_purchase_order",
            "suggest_counter_offer",
            "import_buying_list_from_sheets",
            "export_po_to_sheets",
            "add_supplier",
            "update_supplier",
            "remove_supplier",
        ],
        "requires_auth": True,
    },
    "rfq_whatsapp": {
        "description": "WhatsApp integration for RFQ dispatch and reply parsing",
        "tools": [
            "dispatch_rfq_whatsapp",
            "parse_supplier_reply",
        ],
        "requires_auth": True,
    },
    "whatsapp-client": {
        "description": "WhatsApp client/contact messaging tools (non-supplier flow)",
        "tools": [
            "whatsapp_enviar_mensagem",
            "whatsapp_enviar_lote",
            "whatsapp_status_mensagem",
        ],
        "requires_auth": True,
    },
    "routines": {
        "description": "Criação e gestão de rotinas personalizadas e de catálogo via chat",
        "tools": [
            "listar_rotinas_catalogo",
            "listar_rotinas_personalizadas",
            "criar_rotina_personalizada",
            "ativar_rotina_catalogo",
            "enviar_rotina_para_aprovacao",
        ],
        "requires_auth": True,
    },
    "platform": {
        "description": "Rotinas do catálogo e metas do cliente via linguagem natural",
        "tools": [
            "criar_rotina",
            "listar_rotinas_catalogo",
            "definir_meta",
            "listar_metas",
        ],
        "requires_auth": True,
    },
    "context": {
        "description": "Transaction registration, data catalog, schema mapping, and knowledge completeness for the context-gatherer agent",
        "tools": [
            "register_transaction",
            "list_data_sources",
            "query_data_catalog",
            "suggest_column_mapping",
            "update_schema_mapping",
            "get_knowledge_status",
            "update_context_document",
        ],
        "requires_auth": True,
    },
    "monday": {
        "description": "Monday.com project management integration (boards, items, status)",
        "tools": [
            "monday_list_boards",
            "monday_list_items",
            "monday_create_item",
            "monday_update_item_status",
        ],
        "requires_auth": True,
    },
    "slack": {
        "description": "Slack integration for channels, messages and communication",
        "tools": [
            "slack_list_channels",
            "slack_read_channel",
            "slack_summarize_channel",
            "slack_post_message",
        ],
        "requires_auth": True,
    },
    "notion": {
        "description": "Notion integration for pages, documents and knowledge base",
        "tools": [
            "notion_list_pages",
            "notion_read_page",
            "notion_search",
            "notion_create_page",
        ],
        "requires_auth": True,
    },
    "pm": {
        "description": "Project Management integrations — Asana, ClickUp, Linear",
        "tools": [
            "asana_list_projects",
            "asana_get_project_tasks",
            "clickup_list_tasks",
            "clickup_get_task_comments",
            "linear_list_issues",
            "linear_get_project_summary",
        ],
        "requires_auth": True,
    },
    # Futuros módulos:
    # "scheduling": {
    #     "description": "Agendamento de compromissos",
    #     "tools": ["agendar_servico", "consultar_agenda", "cancelar_agendamento"],
    #     "requires_auth": True,
    #     "requires_elicitation": True  # Usa confirmação
    # },
    "fiscal": {
        "description": "Fiscal tools — NF-e/NFS-e data preparation (SEFAZ integration pending)",
        "tools": [
            "fiscal_preparar_dados_nfe",
            "fiscal_status_integracao",
        ],
        "requires_auth": True,
    },
    "memory": {
        "description": "Shared Business Memory -- entity listing, knowledge retrieval, semantic linking, and upsert",
        "tools": [
            "shared_memory_list",
            "shared_memory_read",
            "shared_memory_upsert",
            "shared_memory_link",
            "shared_memory_unlink",
            "shared_memory_get_links",
        ],
        "requires_auth": True,
    },
    "memory_pre_flight": {
        "description": "Pre-flight shared memory context — reads recent agent execution history from shared_business_memory",
        "tools": [
            "shared_memory_pre_flight",
        ],
        "requires_auth": True,
    },
    "version": {
        "description": "Version storage and retrieval — archives and queries historical versions of shared_business_memory facts",
        "tools": [
            "shared_memory_get_versions",
            "shared_memory_get_version",
        ],
        "requires_auth": True,
    },
    "diff": {
        "description": "Diff generation — human-readable line-based diff between two historical versions of shared_business_memory facts",
        "tools": [
            "shared_memory_diff",
        ],
        "requires_auth": True,
    },
}
