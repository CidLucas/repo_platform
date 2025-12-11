"""
MCP Prompts Registration - Phase 3: Simplified using vizu_prompt_management.

This module registers all MCP prompts using the centralized prompt management library.
The hardcoded templates have been moved to vizu_prompt_management.templates.

Prompts MCP permitem:
- Versionamento de prompts
- Parametrização dinâmica
- Reutilização entre diferentes fluxos
- Descoberta pelo cliente MCP
- Loading from database with client-specific overrides

Referência: https://fastmcp.mintlify.app/servers/prompts
"""

import logging

from fastmcp import FastMCP

from tool_pool_api.server.dependencies import get_context_service

# Use centralized prompt management library
from vizu_prompt_management import PromptLoader
from vizu_prompt_management.mcp_builder import MCPPromptBuilder

logger = logging.getLogger(__name__)


def register_prompts(mcp: FastMCP) -> None:
    """
    Register all MCP prompts using vizu_prompt_management.

    This replaces the previous hardcoded prompts with the centralized
    prompt management system. Prompts are loaded from:
    1. Database (if available, with client-specific overrides)
    2. Built-in templates in vizu_prompt_management.templates

    Args:
        mcp: FastMCP server instance
    """
    try:
        # Create loader without db session for now
        # Database prompts will be loaded dynamically when accessed
        loader = PromptLoader()

        # Build and register prompts
        builder = MCPPromptBuilder(
            mcp=mcp,
            loader=loader,
            context_service_factory=get_context_service,
        )

        # Register all standard prompts from vizu_prompt_management.templates
        registered = builder.register_standard_prompts()

        # Register the generic db/render prompt for dynamic rendering
        builder.register_db_render()

        # Register context-aware prompts that auto-load client variables
        builder.register_context_prompt(
            name="atendente/personalized",
            description="System prompt with client context auto-loaded",
        )

        logger.info(
            f"[MCP Prompts] Registered {len(registered)} standard prompts "
            "via vizu_prompt_management"
        )

    except ImportError as e:
        logger.warning(f"[MCP Prompts] vizu_prompt_management not available: {e}")
        _register_fallback_prompts(mcp)
    except Exception as e:
        logger.error(f"[MCP Prompts] Error registering prompts: {e}", exc_info=True)
        _register_fallback_prompts(mcp)


def _register_fallback_prompts(mcp: FastMCP) -> None:
    """
    Fallback prompt registration if vizu_prompt_management is not available.

    This provides basic prompts to keep the service functional.
    """
    from fastmcp.prompts import Message

    logger.warning("[MCP Prompts] Using fallback prompt registration")

    @mcp.prompt(name="atendente/system/v1")
    def atendente_system_v1(nome_empresa: str = "Empresa") -> list:
        """System prompt básico para o agente atendente."""
        content = f"""Você é um assistente virtual da empresa {nome_empresa}.

## Ferramentas Disponíveis
Você tem acesso à ferramenta `executar_rag_cliente` para buscar informações.

## Comportamento
- Quando o usuário perguntar sobre produtos, serviços ou informações do negócio,
  USE A FERRAMENTA `executar_rag_cliente` ANTES de responder.
- Forneça respostas claras e objetivas baseadas nas informações encontradas.
- Se não encontrar informação relevante, informe educadamente.
- Nunca invente informações.
"""
        return [Message(role="system", content=content)]

    @mcp.prompt(name="atendente/system/v2")
    def atendente_system_v2(
        nome_empresa: str = "Empresa",
        prompt_personalizado: str = "",
        horario_formatado: str = "",
    ) -> list:
        """System prompt v2 com personalização."""
        content = f"""Você é o assistente virtual oficial da empresa {nome_empresa}.

{prompt_personalizado}

## Horário de Funcionamento
{horario_formatado}

Use as ferramentas disponíveis para responder com precisão.
"""
        return [Message(role="system", content=content)]

    @mcp.prompt(name="confirmacao-agendamento")
    def confirmacao_agendamento(
        servico: str = "",
        data: str = "",
        horario: str = "",
    ) -> list:
        """Prompt para confirmação de agendamento."""
        content = f"""Por favor, confirme os dados do agendamento:

- **Serviço**: {servico}
- **Data**: {data}
- **Horário**: {horario}

Os dados estão corretos? (Sim/Não)
"""
        return [Message(role="user", content=content)]

    @mcp.prompt(name="esclarecimento")
    def esclarecimento(pergunta: str = "", opcoes: str = "") -> list:
        """Prompt genérico para solicitar esclarecimento."""
        content = f"{pergunta}"
        if opcoes:
            content += f"\n\nOpções: {opcoes}"
        return [Message(role="user", content=content)]

    @mcp.prompt(name="rag/query")
    def rag_query(question: str = "", context: str = "") -> list:
        """Formata uma query para o sistema RAG."""
        if context:
            content = f"Contexto: {context}\n\nPergunta: {question}"
        else:
            content = question
        return [Message(role="user", content=content)]

    @mcp.prompt(name="db/render")
    def db_render_prompt(
        name: str = "",
        variables: str = "{}",
        version: str | None = None,
        cliente_id: str | None = None,
    ) -> list:
        """Renderiza um prompt do banco de dados com variáveis."""
        # This is a fallback - full implementation uses vizu_prompt_management
        return [
            Message(
                role="system",
                content=f"⚠️ Prompt '{name}' - use vizu_prompt_management for full support.",
            )
        ]

    logger.info(
        "[MCP Prompts] Fallback prompts registered: "
        "atendente/system/v1, v2, confirmacao-agendamento, esclarecimento, "
        "rag/query, db/render"
    )
