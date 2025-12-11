"""
Vendas Agent - Sales agent using proper MCP client integration.

This agent uses the same MCP approach as atendente_core:
1. Connects to MCP server via StreamableHTTP
2. Binds tools to LLM
3. Executes tools when LLM requests them
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

from vizu_agent_framework import MCPConnectionManager

# Lazy imports for faster startup
if TYPE_CHECKING:
    from vizu_models import VizuClientContext

logger = logging.getLogger(__name__)


class VendasAgent:
    """
    Sales agent for B2C order processing.

    Uses StreamableHTTP MCP client for tool execution.
    """

    def __init__(
        self,
        cliente_context: "VizuClientContext",
        mcp_manager: MCPConnectionManager,
        llm_client: Any | None = None,
    ):
        """
        Initialize the sales agent.

        Args:
            cliente_context: Client context with enabled_tools and tier
            mcp_manager: Connected MCP connection manager
            llm_client: Optional LLM client override
        """
        self.cliente_context = cliente_context
        self.mcp_manager = mcp_manager

        # Lazy import for LLM
        if llm_client is None:
            from vizu_llm_service import ModelTier, get_model
            self.llm_client = get_model(tier=ModelTier.DEFAULT)
        else:
            self.llm_client = llm_client

        # Get enabled tools from context
        self.enabled_tools = self._get_enabled_tools_list()
        self.tier = getattr(cliente_context, 'tier', 'BASIC') or 'BASIC'
        self.cliente_id = str(cliente_context.id) if hasattr(cliente_context, 'id') else ""

        logger.info(
            f"VendasAgent initialized for {getattr(cliente_context, 'nome_empresa', 'unknown')} "
            f"with enabled_tools={self.enabled_tools}"
        )

    def _get_enabled_tools_list(self) -> list[str]:
        """Get enabled tools from client context."""
        # Lazy import
        from vizu_tool_registry import ToolRegistry

        if hasattr(self.cliente_context, 'get_enabled_tools_list'):
            return self.cliente_context.get_enabled_tools_list()

        if hasattr(self.cliente_context, 'enabled_tools') and self.cliente_context.enabled_tools:
            return self.cliente_context.enabled_tools

        # Fallback to legacy boolean flags
        return ToolRegistry.get_tool_names_for_legacy_flags(
            rag_enabled=getattr(self.cliente_context, 'ferramenta_rag_habilitada', False),
            sql_enabled=getattr(self.cliente_context, 'ferramenta_sql_habilitada', False),
            scheduling_enabled=getattr(self.cliente_context, 'ferramenta_agendamento_habilitada', False),
        )

    def _filter_tools_for_client(self, all_tools: list[BaseTool]) -> list[BaseTool]:
        """Filter MCP tools based on client permissions."""
        # Lazy import
        from vizu_tool_registry import ToolRegistry

        if not self.enabled_tools:
            # No tools enabled - return empty
            logger.warning("No tools enabled for client")
            return []

        # Get available tools from registry (validates against tier)
        available_from_registry = ToolRegistry.get_available_tools(
            enabled_tools=self.enabled_tools,
            tier=self.tier,
            include_google=True,
        )
        available_names = {t.name for t in available_from_registry}

        # Also include public tools
        public_tools = ToolRegistry.get_tools_for_tier("FREE")
        public_names = {t.name for t in public_tools}

        allowed_names = available_names | public_names

        # Filter MCP tools
        filtered = [t for t in all_tools if t.name in allowed_names]

        logger.info(
            f"Tools disponíveis para vendas_agent (tier {self.tier}): {[t.name for t in filtered]}"
        )
        return filtered

    def _build_system_prompt(self, available_tools: list[BaseTool]) -> str:
        """Build system prompt for sales agent."""
        nome_empresa = getattr(self.cliente_context, 'nome_empresa', 'Vizu')
        prompt_base = getattr(self.cliente_context, 'prompt_base', '')

        prompt_parts = [
            f"Você é um representante de vendas da empresa {nome_empresa}.",
            "",
            "## SEU PAPEL",
            "Você é especialista em atendimento ao cliente e vendas.",
            "Seu objetivo é ajudar o cliente a encontrar os produtos/serviços ideais para suas necessidades.",
            "",
        ]

        if prompt_base:
            prompt_parts.append("## INSTRUÇÕES DO CLIENTE")
            prompt_parts.append(prompt_base)
            prompt_parts.append("")

        if available_tools:
            prompt_parts.append("## FERRAMENTAS DISPONÍVEIS")
            for tool in available_tools:
                prompt_parts.append(f"- **{tool.name}**: {tool.description or 'Sem descrição'}")
            prompt_parts.append("")
            prompt_parts.append("## COMPORTAMENTO OBRIGATÓRIO")
            if any(t.name == "executar_rag_cliente" for t in available_tools):
                prompt_parts.append("- SEMPRE use `executar_rag_cliente` para buscar informações sobre produtos, serviços e preços ANTES de responder.")
            prompt_parts.append("- Use a resposta das ferramentas para formular sua resposta final.")
            prompt_parts.append("- Se nenhuma ferramenta encontrar informações, informe ao cliente educadamente.")
            prompt_parts.append("- Nunca invente informações - use apenas o que as ferramentas retornarem.")
        else:
            prompt_parts.append("## AVISO")
            prompt_parts.append("Nenhuma ferramenta está disponível. Responda com base apenas no conhecimento geral.")

        prompt_parts.extend([
            "",
            "## ESTILO DE COMUNICAÇÃO",
            "- Seja cordial e profissional",
            "- Ofereça ajuda proativa",
            "- Destaque benefícios dos produtos/serviços",
            "- Facilite o processo de compra",
        ])

        return "\n".join(prompt_parts)

    async def _execute_tools(
        self,
        tool_calls: list[dict[str, Any]],
        tool_map: dict[str, BaseTool],
    ) -> list[ToolMessage]:
        """Execute tool calls and return results."""
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_call_id = tool_call.get("id")
            args = dict(tool_call.get("args") or {})

            tool = tool_map.get(tool_name)
            if not tool:
                results.append(ToolMessage(
                    content=f"Ferramenta '{tool_name}' não encontrada.",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))
                continue

            try:
                # Remove cliente_id if LLM tried to pass it (security)
                if "cliente_id" in args:
                    logger.warning(f"LLM tentou passar cliente_id para '{tool_name}' - removendo")
                    args.pop("cliente_id")

                # Inject validated cliente_id
                if self.cliente_id:
                    args["cliente_id"] = self.cliente_id

                # Execute the tool
                logger.info(f"Executando tool '{tool_name}' com args: {list(args.keys())}")

                if hasattr(tool, "ainvoke"):
                    output = await tool.ainvoke(args)
                elif hasattr(tool, "arun"):
                    output = await tool.arun(args)
                elif asyncio.iscoroutinefunction(getattr(tool, "invoke", None)):
                    output = await tool.invoke(args)
                elif hasattr(tool, "invoke"):
                    output = await asyncio.to_thread(tool.invoke, args)
                else:
                    raise RuntimeError("Tool has no callable invocation method")

                logger.info(f"Tool '{tool_name}' resultado (primeiros 300 chars): {str(output)[:300]}")

                results.append(ToolMessage(
                    content=str(output),
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))

            except Exception as e:
                logger.exception(f"Erro ao executar '{tool_name}': {e}")
                results.append(ToolMessage(
                    content=f"Erro ao executar ferramenta: {str(e)}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ))

        return results

    async def process_message(
        self,
        message: str,
        session_id: str,
        elicitation_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process a user message.

        Args:
            message: User message text
            session_id: Session identifier
            elicitation_response: Optional response to pending elicitation

        Returns:
            Dict with response, model_used, etc.
        """
        # 1. Ensure MCP is connected and get tools
        await self.mcp_manager.ensure_connected()
        all_tools = self.mcp_manager.tools

        if not all_tools:
            logger.warning("No MCP tools available")
            return {
                "response": "Desculpe, minhas ferramentas de busca estão temporariamente indisponíveis.",
                "model_used": "fallback",
                "pending_elicitation": None,
                "tool_calls": [],
            }

        # 2. Filter tools for this client
        available_tools = self._filter_tools_for_client(all_tools)
        tool_map = {t.name: t for t in available_tools}

        # 3. Build system prompt
        system_prompt = self._build_system_prompt(available_tools)

        # 4. Bind tools to LLM
        llm = self.llm_client
        if available_tools:
            llm = llm.bind_tools(available_tools)

        # 5. Build messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message),
        ]

        # 6. Invoke LLM
        try:
            response = llm.invoke(messages)
            logger.info(f"LLM response type: {type(response)}")
        except Exception as e:
            logger.exception(f"Erro ao invocar LLM: {e}")
            return {
                "response": "Ocorreu um erro interno ao processar sua solicitação.",
                "model_used": "error",
                "pending_elicitation": None,
                "tool_calls": [],
            }

        # 7. Check if LLM wants to call tools
        tool_results = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"LLM escolheu chamar tools: {[tc.get('name') for tc in response.tool_calls]}")

            # Execute tools
            tool_messages = await self._execute_tools(response.tool_calls, tool_map)
            tool_results = [{"tool_name": tm.name, "result": tm.content} for tm in tool_messages]

            # Add tool results to conversation and get final response
            messages.append(response)
            messages.extend(tool_messages)

            # Get final response from LLM with tool results
            try:
                final_response = llm.invoke(messages)
                response_text = getattr(final_response, "content", str(final_response))
            except Exception as e:
                logger.exception(f"Erro ao gerar resposta final: {e}")
                # Use tool results as fallback
                response_text = "\n\n".join([f"Resultado de {tr['tool_name']}: {tr['result'][:500]}" for tr in tool_results])
        else:
            # No tool calls - use direct response
            response_text = getattr(response, "content", str(response))

        return {
            "response": response_text,
            "model_used": "openai:gpt-4o-mini",  # TODO: Get from LLM client
            "pending_elicitation": None,
            "tool_calls": tool_results,
        }
