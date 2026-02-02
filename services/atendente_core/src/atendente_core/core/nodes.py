import asyncio
import logging
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

if TYPE_CHECKING:
    from vizu_context_service import ContextService

# Stream error handling for MCP reconnection
from anyio import BrokenResourceError, ClosedResourceError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, create_model

from atendente_core.core.config import get_settings
from atendente_core.core.state import AgentState

# Importamos o gerenciador de conexão MCP
from atendente_core.services.mcp_client import mcp_manager

# Phase 3: Use vizu_elicitation_service instead of local module
from vizu_elicitation_service import (
    ElicitationRequired,
    format_elicitation_for_llm,
    validate_elicitation_response,
)

# Importa o cliente LLM centralizado
from vizu_llm_service import ModelTier, TokenBudget, get_model

# Context 2.0: Import ContextSection for selective injection
from vizu_models.enums import ContextSection

# Importa o contexto seguro para tipagem
from vizu_models.safe_client_context import SafeClientContext

# Context 2.0: Import VizuClientContext for full context access
from vizu_models.vizu_client_context import VizuClientContext

# PHASE 3+5: Use vizu_prompt_management unified dynamic builder
from vizu_prompt_management import (
    build_prompt,
    build_tools_description,
    filter_prompt_tools,
    format_horario,
)

# PHASE 3: Use vizu_tool_registry for tool filtering
from vizu_tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def sanitize_tool_for_llm(tool: BaseTool) -> BaseTool:
    """
    Remove cliente_id and user_jwt from tool schema for LLM binding.

    MCP tools accept cliente_id/user_jwt for backend injection, but these
    should NOT be visible to the LLM. This function creates a new tool with
    a sanitized schema that excludes internal parameters.

    Args:
        tool: Original tool from MCP with full schema

    Returns:
        New tool with sanitized schema (cliente_id/user_jwt removed)
    """
    # Skip if tool has no args_schema
    if not hasattr(tool, "args_schema") or tool.args_schema is None:
        return tool

    # Get model fields
    if not hasattr(tool.args_schema, "model_fields"):
        return tool

    original_fields = tool.args_schema.model_fields

    # Check if cliente_id or user_jwt exist
    has_internal_params = "cliente_id" in original_fields or "user_jwt" in original_fields
    if not has_internal_params:
        return tool

    # Create new schema without internal params
    sanitized_fields = {}
    for field_name, field_info in original_fields.items():
        if field_name not in ("cliente_id", "user_jwt"):
            # Preserve field type and metadata
            sanitized_fields[field_name] = (
                field_info.annotation,
                field_info,
            )

    # Create new Pydantic model with sanitized fields
    SanitizedSchema = create_model(
        f"{tool.args_schema.__name__}Sanitized",
        **sanitized_fields,
    )

    # Create new tool with sanitized schema
    sanitized_tool = StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=SanitizedSchema,
        func=tool.func if hasattr(tool, "func") else None,
        coroutine=tool.coroutine if hasattr(tool, "coroutine") else None,
    )

    logger.debug(
        f"Sanitized tool '{tool.name}': removed cliente_id/user_jwt from LLM schema"
    )

    return sanitized_tool


def sanitize_tools_for_llm(tools: list[BaseTool]) -> list[BaseTool]:
    """
    Sanitize all tools to hide internal parameters from LLM.

    Args:
        tools: List of tools from MCP

    Returns:
        List of tools with sanitized schemas
    """
    return [sanitize_tool_for_llm(tool) for tool in tools]


# ============================================================================
# TOOL FILTERING - Dynamic tool availability based on client permissions
# Phase 3: Uses vizu_tool_registry instead of hardcoded mapping
# ============================================================================


def _get_enabled_tools_from_context(safe_context: SafeClientContext | None) -> list[str]:
    """
    Get enabled tools from client context.

    Supports both:
    - New `enabled_tools` list field
    - Legacy boolean flags

    Args:
        safe_context: SafeClientContext from the client

    Returns:
        List of enabled tool names
    """
    if not safe_context:
        return []

    # Only use the authoritative `enabled_tools` list. Legacy booleans are
    # removed by migration.
    return getattr(safe_context, "enabled_tools", []) or []


def _get_tier_from_context(safe_context: SafeClientContext | None) -> str:
    """Get tier from client context."""
    if safe_context and hasattr(safe_context, "tier") and safe_context.tier:
        return safe_context.tier
    return "BASIC"


def filter_tools_for_client(
    all_tools: list[BaseTool], safe_context: SafeClientContext | None
) -> list[BaseTool]:
    """
    Filtra as ferramentas disponíveis baseado nas permissões do cliente.

    Phase 3: Uses vizu_tool_registry for validation.

    Args:
        all_tools: Lista de todas as ferramentas do MCP
        safe_context: Contexto seguro do cliente com flags de permissão

    Returns:
        Lista de ferramentas que o cliente tem permissão de usar
    """
    if not safe_context:
        # Sem contexto, retorna apenas tools públicas (tier FREE)
        logger.warning("Sem contexto de cliente - retornando apenas tools públicas")
        public_tools = ToolRegistry.get_tools_for_tier("FREE")
        public_names = {t.name for t in public_tools}
        return [t for t in all_tools if t.name in public_names]

    # Get enabled tools and tier from context
    enabled_tool_names = _get_enabled_tools_from_context(safe_context)
    tier = _get_tier_from_context(safe_context)

    # Get available tools from registry (validates against tier)
    available_tools = ToolRegistry.get_available_tools(
        enabled_tools=enabled_tool_names,
        tier=tier,
        include_google=True,
    )
    available_names = {t.name for t in available_tools}

    # Also always include public tools (tier FREE)
    public_tools = ToolRegistry.get_tools_for_tier("FREE")
    public_names = {t.name for t in public_tools}

    allowed_names = available_names | public_names

    # Filter actual MCP tools
    filtered = [t for t in all_tools if t.name in allowed_names]

    logger.info(
        f"Tools disponíveis para {safe_context.nome_empresa} (tier {tier}): {[t.name for t in filtered]}"
    )
    return filtered


async def build_dynamic_system_prompt(
    safe_context: SafeClientContext | None,
    available_tools: list[BaseTool],
    cliente_id: UUID | None = None,
    context_service: "ContextService | None" = None,
    vizu_context: VizuClientContext | None = None,
) -> str:
    """
    Build system prompt dynamically using vizu_prompt_management.

    Context 2.0: Now supports modular context sections for selective injection.
    Uses the unified build_prompt() function from dynamic_builder,
    which handles caching via context_service and fallback to builtin.

    Args:
        safe_context: Safe client context with permissions (legacy)
        available_tools: List of filtered tools for this client
        cliente_id: Client UUID for client-specific prompts
        context_service: Optional ContextService for Redis caching
        vizu_context: Full VizuClientContext with all sections (Context 2.0)

    Returns:
        Rendered system prompt
    """
    nome_empresa = safe_context.nome_empresa if safe_context else "Vizu"
    available_tool_names = {t.name for t in available_tools} if available_tools else set()

    # Build tools description using unified function
    tools_description = build_tools_description(available_tools, ToolRegistry)

    # Format business hours using unified function (Context 2.0 compatible)
    horario_formatado = ""
    if vizu_context:
        business_hours = vizu_context.get_business_hours()
        if business_hours:
            horario_formatado = business_hours
        elif safe_context and safe_context.horario_funcionamento:
            horario_formatado = format_horario(safe_context.horario_funcionamento)
    elif safe_context:
        horario_formatado = format_horario(safe_context.horario_funcionamento)

    # Context 2.0: Build modular context sections
    context_sections_text = ""
    if vizu_context:
        logger.info("[PROMPT_BUILD] vizu_context available, converting to safe context")
        # Convert to SafeClientContext for LLM-safe exposure
        llm_safe_context = vizu_context.to_safe_context()
        logger.info(f"[PROMPT_BUILD] Safe context loaded_sections: {llm_safe_context.loaded_sections}")

        # Define which sections the respond node needs
        respond_sections = [
            ContextSection.BRAND_VOICE,
            ContextSection.CURRENT_MOMENT,
            ContextSection.POLICIES,
            ContextSection.COMPANY_PROFILE,
            ContextSection.TEAM_STRUCTURE,
        ]
        logger.info(f"[PROMPT_BUILD] Requesting sections: {[s.value for s in respond_sections]}")

        # Compile only loaded sections
        context_sections_text = llm_safe_context.get_compiled_context(
            sections=respond_sections,
            include_header=False,  # Header included separately
        )
        logger.info(f"[PROMPT_BUILD] Context 2.0: Compiled {len(respond_sections)} sections ({len(context_sections_text)} chars)")
        if context_sections_text:
            logger.info(f"[PROMPT_BUILD] Sections preview: {context_sections_text[:300]}...")
        else:
            logger.warning("[PROMPT_BUILD] No context sections compiled! Check if sections are loaded in DB")
    else:
        logger.warning("[PROMPT_BUILD] No vizu_context provided - using legacy prompt_base only")

    # Get prompt base (Context 2.0 compatible)
    if vizu_context:
        raw_prompt_base = vizu_context.get_default_prompt() or ""
    elif safe_context:
        raw_prompt_base = safe_context.prompt_base or ""
    else:
        raw_prompt_base = ""

    # Filter prompt_base to only reference enabled tools using unified function
    prompt_base = filter_prompt_tools(raw_prompt_base, available_tool_names)

    variables = {
        "nome_empresa": nome_empresa,
        "prompt_personalizado": prompt_base or "",
        "horario_formatado": horario_formatado,
        "tools_description": tools_description,
        # Context 2.0: Add compiled context sections
        "context_sections": context_sections_text,
    }

    # Use unified build_prompt which handles caching internally
    return await build_prompt(
        name="atendente/system/v3",
        variables=variables,
        cliente_id=cliente_id,
        context_service=context_service,
    )


def get_llm(model_override: str | None = None):
    """
    Configura o cliente LLM usando o vizu_llm_service.

    Args:
        model_override: Nome do modelo a usar (sobrescreve o padrão).
                       Se None, usa o modelo padrão do provider configurado.

    Returns:
        BaseChatModel configurado
    """
    settings = get_settings()

    # Se há override, passa o nome específico do modelo
    if model_override:
        logger.info(f"Usando modelo override: {model_override}")
        return get_model(model_name=model_override)

    # Caso contrário, usa o modelo padrão do tier DEFAULT
    return get_model(tier=ModelTier.DEFAULT)


async def supervisor_node(state: AgentState) -> dict:
    """
    Nó Supervisor (Agente Principal).
    Decide o próximo passo usando o LLM e as ferramentas do MCP.

    PHASE 2: Dynamic Personalized Context
    - Filtra tools baseado nas permissões do cliente
    - Gera system prompt dinâmico baseado no contexto

    PHASE 3: Elicitation Support
    - Detecta se há elicitation pendente
    - Se usuário respondeu, permite resumir execução do tool
    """
    # Only clear structured_data on NEW user turns, not when processing tool results.
    # When processing tool results, the last message is a ToolMessage - preserve structured_data.
    # When it's a new user message (HumanMessage), clear it to avoid repeating previous tables.
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    is_processing_tool_results = isinstance(last_msg, ToolMessage)

    # Don't clear structured_data when we're about to generate the final response after tools
    # (that's when we need it to be sent to the frontend)

    # Check for pending elicitation with response
    pending = state.get("pending_elicitation")
    elicitation_response = state.get("elicitation_response")

    if pending and elicitation_response:
        # Usuário respondeu a uma elicitation - informar LLM do contexto
        logger.info(
            f"Elicitation response received for {pending.get('tool_name')}: {elicitation_response}"
        )

        # Valida a resposta
        is_valid, error = validate_elicitation_response(
            pending, elicitation_response.get("response")
        )
        if not is_valid:
            error_msg = f"Resposta inválida: {error}. Por favor, tente novamente."
            return {"messages": [AIMessage(content=error_msg)], "structured_data": None}

        # Adiciona contexto da resposta para a LLM
        context_msg = (
            f"O usuário respondeu '{elicitation_response.get('response')}' "
            f"à pergunta: {pending.get('message')}"
        )
        logger.info(f"Adding elicitation context to conversation: {context_msg}")

        # Inject elicitation context into messages for LLM awareness
        messages = list(messages)  # Make a copy to avoid mutating state
        messages.append(HumanMessage(content=context_msg))

    # 1. Obtém o contexto do cliente
    safe_ctx = state.get("safe_context")
    vizu_ctx = state.get("vizu_context")  # Context 2.0: Full context with sections
    model_override = state.get("model_override")
    cliente_id = state.get("cliente_id")  # PHASE 5: para buscar prompt customizado

    # DEBUG: Log context state (demoted to DEBUG level for production)
    logger.debug(f"[SUPERVISOR] safe_context present: {safe_ctx is not None}")
    logger.debug(f"[SUPERVISOR] vizu_context present: {vizu_ctx is not None}")
    if vizu_ctx:
        logger.debug(f"[SUPERVISOR] vizu_context type: {type(vizu_ctx).__name__}")
        logger.debug(f"[SUPERVISOR] vizu_context.nome_empresa: {getattr(vizu_ctx, 'nome_empresa', 'N/A')}")

    # 2. Obtém TODAS as tools do MCP
    all_tools = mcp_manager.tools

    if not all_tools:
        logger.warning("Nenhuma ferramenta MCP disponível no momento.")
        return {
            "messages": [
                AIMessage(
                    content="Sinto muito, minhas ferramentas de busca estão temporariamente indisponíveis."
                )
            ],
            "structured_data": None,
        }

    # 3. PHASE 2: Filtra tools baseado nas permissões do cliente
    available_tools = filter_tools_for_client(all_tools, safe_ctx)

    logger.debug(f"[SUPERVISOR] Available tools count: {len(available_tools)}")
    logger.debug(f"[SUPERVISOR] Tool names: {[t.name for t in available_tools[:5]]}...")  # First 5

    if not available_tools:
        logger.warning(
            f"Cliente {safe_ctx.nome_empresa if safe_ctx else 'desconhecido'} não tem tools habilitadas"
        )
        # Permite continuar sem tools - o agente responderá apenas com conhecimento base

    # 4. PHASE 2 + 5 + Context 2.0: Constrói system prompt dinâmico com seções modulares
    logger.debug(f"[SUPERVISOR] Building system prompt with vizu_context={vizu_ctx is not None}")
    system_prompt = await build_dynamic_system_prompt(
        safe_ctx, available_tools, cliente_id=cliente_id, vizu_context=vizu_ctx
    )

    # Log para debug (demoted to DEBUG level for production)
    logger.debug(f"[SUPERVISOR] System prompt generated: {len(system_prompt)} chars")
    logger.debug(f"[SUPERVISOR] Prompt preview: {system_prompt[:500]}...")

    # FULL PROMPT DEBUG - Enable with LOG_LEVEL=DEBUG to inspect complete LLM input
    logger.debug(f"=== SUPERVISOR FULL SYSTEM PROMPT ===")
    logger.debug(system_prompt)
    logger.debug(f"=== END SUPERVISOR SYSTEM PROMPT ===")

    # Constrói a lista de mensagens com o System Message no início
    # Limita a janela de histórico enviada ao LLM para evitar que o state
    # cresça indefinidamente (reduzindo o tamanho dos spans/trace exports).
    history_window = getattr(get_settings(), "SESSION_HISTORY_WINDOW", 6)
    past_messages = state.get("messages", []) or []
    recent_msgs = past_messages[-history_window:]

    # Apply token budgeting to prevent "prompt too long" errors
    # Uses shared TokenBudget from vizu_llm_service
    token_budget = TokenBudget(
        max_tokens=getattr(get_settings(), "MAX_PROMPT_TOKENS", 120000),
        chars_per_token=getattr(get_settings(), "CHARS_PER_TOKEN", 4),
    )
    budget_result = token_budget.apply(recent_msgs, system_prompt)
    recent_msgs = budget_result.messages

    messages = [SystemMessage(content=system_prompt)] + recent_msgs

    # FULL MESSAGE LIST DEBUG - Enable with LOG_LEVEL=DEBUG to inspect complete conversation
    logger.debug(f"=== SUPERVISOR FULL MESSAGE LIST ({len(messages)} messages) ===")
    for i, msg in enumerate(messages):
        logger.debug(f"Message {i} [{type(msg).__name__}]: {str(msg.content)[:200]}...")
    logger.debug(f"=== END SUPERVISOR MESSAGE LIST ===")

    # 5. Bind das Tools filtradas no Modelo
    llm = get_llm(model_override=model_override)

    if available_tools:
        # CRITICAL: Sanitize tool schemas to hide cliente_id/user_jwt from LLM
        # The LLM should NOT see these internal parameters
        sanitized_tools = sanitize_tools_for_llm(available_tools)
        llm = llm.bind_tools(sanitized_tools)
        logger.debug(f"Bound {len(sanitized_tools)} sanitized tools to LLM")

    # 6. Invoca o Modelo
    try:
        response = llm.invoke(messages)
        # Log para debug - ver se há tool_calls
        logger.info(f"LLM response type: {type(response)}")
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(
                f"LLM escolheu chamar tools: {[tc.get('name') for tc in response.tool_calls]}"
            )
        else:
            logger.info(
                f"LLM não chamou nenhuma tool. Content (primeiros 200 chars): {str(response.content)[:200]}"
            )
    except Exception as e:
        logger.error(f"Erro ao invocar LLM: {e}")
        return {
            "messages": [
                AIMessage(
                    content="Ocorreu um erro interno ao processar sua solicitação."
                )
            ],
        }

    # Only clear structured_data when NOT processing tool results
    # When processing tool results, we preserve it so the frontend receives the table
    if is_processing_tool_results:
        # Keep structured_data from execute_tools_node - don't override it
        return {"messages": [response]}
    else:
        # New user turn without tools - clear any previous structured_data
        return {"messages": [response], "structured_data": None}


async def execute_tools_node(state: AgentState) -> dict:
    """
    Nó Executor de Ferramentas.
    Executa TODAS as tools solicitadas em PARALELO usando asyncio.gather.

    PHASE 3: Elicitation Support
    - Captura ElicitationRequired exceptions
    - Configura pending_elicitation no state para pausar execução
    """
    last_message = state["messages"][-1]

    # Validação de segurança para garantir que temos chamadas para fazer
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return {"messages": []}

    tool_calls = last_message.tool_calls
    pending_elicitation = None

    # 1. Mapeia as ferramentas disponíveis para acesso rápido
    tools = mcp_manager.tools
    tool_map = {t.name: t for t in tools}

    # 2. Prepara contexto compartilhado
    internal_ctx = state.get("_internal_context")
    cliente_id = internal_ctx.get_client_id_for_tools() if internal_ctx else None
    elicitation_response = state.get("elicitation_response")
    pending = state.get("pending_elicitation")

    async def execute_single_tool(
        tool_call: dict, retry_on_stream_error: bool = True
    ) -> ToolMessage:
        """Executa uma única tool e retorna ToolMessage."""
        nonlocal tool_map  # Allow updating tool_map after reconnection
        tool_name = tool_call["name"]
        tool_call_id = tool_call["id"]

        try:
            tool = tool_map.get(tool_name)
            if not tool:
                return ToolMessage(
                    content=f"Ferramenta '{tool_name}' não encontrada.",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )

            # Prepara argumentos
            args_to_pass = dict(tool_call.get("args") or {})

            # Remove cliente_id se a LLM tentar passar (segurança)
            if "cliente_id" in args_to_pass:
                logger.warning(
                    f"LLM tentou passar cliente_id para '{tool_name}' - removendo"
                )
                args_to_pass.pop("cliente_id")

            # Check if tool accepts cliente_id parameter before injecting
            # Known tools that accept cliente_id (MCP middleware-wrapped tools
            # don't always expose this in their schema, so we maintain a list)
            TOOLS_ACCEPTING_CLIENTE_ID = {
                "executar_sql_agent",
                "executar_rag_cliente",
                "list_google_accounts_wrapper",
                "write_to_sheet_wrapper",
                "read_emails_wrapper",
                "query_calendar_wrapper",
            }

            tool_accepts_cliente_id = tool_name in TOOLS_ACCEPTING_CLIENTE_ID
            tool_accepts_user_jwt = False

            # Also try schema detection as fallback
            if not tool_accepts_cliente_id:
                try:
                    # LangChain tools have args_schema or get_input_schema()
                    if hasattr(tool, "args_schema") and tool.args_schema:
                        schema_fields = tool.args_schema.model_fields if hasattr(tool.args_schema, "model_fields") else {}
                        tool_accepts_cliente_id = "cliente_id" in schema_fields
                    elif hasattr(tool, "get_input_schema"):
                        schema = tool.get_input_schema()
                        if hasattr(schema, "model_fields"):
                            tool_accepts_cliente_id = "cliente_id" in schema.model_fields
                        elif hasattr(schema, "schema"):
                            props = schema.schema().get("properties", {})
                            tool_accepts_cliente_id = "cliente_id" in props
                            tool_accepts_user_jwt = "user_jwt" in props
                except Exception:
                    # If we can't determine, don't inject to avoid errors
                    pass

            # Injeta cliente_id validado only if tool accepts it
            if cliente_id and tool_accepts_cliente_id:
                args_to_pass["cliente_id"] = cliente_id
                logger.debug(f"Injected cliente_id into '{tool_name}'")
            elif cliente_id and not tool_accepts_cliente_id:
                logger.debug(f"Tool '{tool_name}' does not accept cliente_id - not injecting")

            # Inject user JWT to tools that accept it (so server-side helpers
            # like load_context_from_token can work when tools support user_jwt)
            user_jwt = state.get("user_jwt") if state else None
            if user_jwt and tool_accepts_user_jwt:
                args_to_pass["user_jwt"] = user_jwt

            # NOTE: removed forced fallback injection for RAG tools to avoid
            # silently overriding tool auth flows. Tools should rely on explicit
            # `cliente_id` injection or token-based auth via `user_jwt`.

            # Injeta elicitation response se aplicável
            if (
                elicitation_response
                and pending
                and pending.get("tool_name") == tool_name
            ):
                args_to_pass["_elicitation_response"] = elicitation_response.get(
                    "response"
                )

            # Executa a ferramenta
            if hasattr(tool, "ainvoke"):
                output = await tool.ainvoke(args_to_pass)
            elif hasattr(tool, "arun"):
                output = await tool.arun(args_to_pass)
            elif asyncio.iscoroutinefunction(getattr(tool, "invoke", None)):
                output = await tool.invoke(args_to_pass)
            elif hasattr(tool, "invoke"):
                output = await asyncio.to_thread(tool.invoke, args_to_pass)
            else:
                raise RuntimeError("Tool has no callable invocation method")

            logger.info(
                f"Tool '{tool_name}' resultado (primeiros 300 chars): {str(output)[:300]}"
            )
            return ToolMessage(
                content=str(output), tool_call_id=tool_call_id, name=tool_name
            )

        except (ClosedResourceError, BrokenResourceError) as stream_err:
            # MCP stream died - reconnect and retry once
            if retry_on_stream_error:
                logger.warning(
                    f"MCP stream error on '{tool_name}': {stream_err}. Reconnecting and retrying..."
                )
                try:
                    await mcp_manager.disconnect()
                    await mcp_manager.connect()
                    # Refresh tool map after reconnection
                    tool_map = {t.name: t for t in mcp_manager.tools}
                    # Retry without allowing another reconnect attempt
                    return await execute_single_tool(
                        tool_call, retry_on_stream_error=False
                    )
                except Exception as reconnect_err:
                    logger.exception(
                        f"Failed to reconnect MCP after stream error: {reconnect_err}"
                    )
                    return ToolMessage(
                        content=f"Erro de conexão com serviço de ferramentas: {str(stream_err)}",
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
            else:
                logger.exception(
                    f"MCP stream error on retry for '{tool_name}': {stream_err}"
                )
                return ToolMessage(
                    content=f"Erro de conexão persistente com serviço de ferramentas: {str(stream_err)}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )

        except ElicitationRequired as elicit:
            nonlocal pending_elicitation
            logger.info(f"Tool '{tool_name}' requires elicitation: {elicit.message}")
            pending_elicitation = elicit.to_pending_elicitation()
            elicitation_msg = format_elicitation_for_llm(pending_elicitation)
            return ToolMessage(
                content=f"[ELICITATION REQUIRED] {elicitation_msg}",
                tool_call_id=tool_call_id,
                name=tool_name,
            )

        except Exception as e:
            logger.exception(f"Erro ao executar '{tool_name}': {e}")
            return ToolMessage(
                content=f"Erro ao executar ferramenta: {str(e)}",
                tool_call_id=tool_call_id,
                name=tool_name,
            )

    # 3. Executa TODAS as tools em PARALELO
    if len(tool_calls) > 1:
        logger.info(
            f"Executando {len(tool_calls)} tools em paralelo: {[tc['name'] for tc in tool_calls]}"
        )

    results = await asyncio.gather(*[execute_single_tool(tc) for tc in tool_calls])

    # Build return dict
    return_dict = {"messages": list(results)}

    # Extract structured_data from tool results (if any)
    # SQL tools return JSON with {"output": ..., "structured_data": {...}}
    structured_data = None
    for result in results:
        if isinstance(result, ToolMessage) and result.content:
            try:
                import json
                # Try to parse as JSON to extract structured_data
                parsed = json.loads(result.content)
                if isinstance(parsed, dict) and parsed.get("structured_data"):
                    structured_data = parsed["structured_data"]
                    logger.info(f"Extracted structured_data from tool '{result.name}'")
                    break  # Use first tool with structured_data
            except (json.JSONDecodeError, TypeError):
                # Not JSON, skip
                pass

    if structured_data:
        return_dict["structured_data"] = structured_data

    # PHASE 3: If we have pending elicitation, add it to state
    if pending_elicitation:
        return_dict["pending_elicitation"] = pending_elicitation
        logger.info(
            f"Setting pending_elicitation: {pending_elicitation.get('elicitation_id')}"
        )
    else:
        # Clear any previous elicitation state
        return_dict["pending_elicitation"] = None
        return_dict["elicitation_response"] = None

    return return_dict


def should_continue(
    state: AgentState,
) -> Literal["execute_tools", "await_elicitation", "__end__"]:
    """
    Define a próxima aresta do grafo baseada na última mensagem.

    PHASE 3: Elicitation Support
    - Detecta pending_elicitation e pausa para aguardar input
    """
    # PHASE 3: Check for pending elicitation
    pending = state.get("pending_elicitation")
    if pending:
        logger.info(
            f"Elicitation pending - pausing for user input: {pending.get('elicitation_id')}"
        )
        return "await_elicitation"

    last_message = state["messages"][-1]

    # Se o LLM decidiu chamar ferramentas, vamos para o nó executor
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "execute_tools"

    # Caso contrário, devolvemos a resposta final ao usuário
    return "__end__"


def await_elicitation_node(state: AgentState) -> dict:
    """
    Nó de espera por elicitation.

    Este nó é alcançado quando um tool precisa de input do usuário.
    O grafo pausa aqui e a API retorna o estado com pending_elicitation.

    Quando o usuário responde (via /chat com elicitation_response),
    o grafo é retomado com a resposta injetada no state.
    """
    pending = state.get("pending_elicitation")

    if not pending:
        logger.warning("await_elicitation_node called without pending elicitation")
        return {}

    # Gera uma mensagem AI informando que precisamos de input
    message = pending.get("message", "Por favor, confirme para continuar.")

    # Formata opções se houver
    options = pending.get("options")
    if options:
        options_text = "\n".join([f"- {opt.get('label')}" for opt in options])
        message = f"{message}\n\nOpções:\n{options_text}"

    logger.info(f"Awaiting elicitation response: {message}")

    # Retorna mensagem para o usuário
    return {"messages": [AIMessage(content=message)]}
