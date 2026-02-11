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
)

# PHASE 3: Use vizu_tool_registry for tool filtering
from vizu_tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def _create_llm_data_summary(structured_data: dict, full_output: dict) -> str:
    """
    Create a concise LLM-friendly summary of SQL results.

    The LLM should NOT receive all rows - just:
    - Total count
    - Column names
    - 3 sample rows for context
    - Aggregated stats if numeric columns exist

    Args:
        structured_data: Full structured_data with all rows
        full_output: Full tool output dict (has row_count, sql, etc.)

    Returns:
        Formatted string summary for LLM context
    """
    rows = structured_data.get("rows", [])
    columns = structured_data.get("columns", [])
    total_rows = full_output.get("row_count", len(rows))
    sql = full_output.get("sql", "")

    # Build summary
    summary_parts = [f"{total_rows} registros encontrados."]

    if columns:
        summary_parts.append(f"Colunas: {', '.join(columns)}")

    # Add 3 sample rows for context
    if rows:
        sample_rows = rows[:3]
        sample_text = "\n".join([
            f"  Exemplo {i+1}: {row}"
            for i, row in enumerate(sample_rows)
        ])
        summary_parts.append(f"\nPrimeiros 3 registros:\n{sample_text}")

    # Try to add aggregated stats for numeric columns
    if rows and columns:
        numeric_stats = _calculate_numeric_stats(rows, columns)
        if numeric_stats:
            summary_parts.append(f"\nEstatísticas: {numeric_stats}")

    # Add truncation note
    if total_rows > 3:
        summary_parts.append(f"\n(Mostrando 3 de {total_rows}. Dados completos exibidos na tabela para o usuário.)")

    return "\n".join(summary_parts)


def _calculate_numeric_stats(rows: list[dict], columns: list[str]) -> str | None:
    """
    Calculate basic stats for numeric columns.

    Returns:
        String with stats like "total_valor: R$123.456, avg: R$1.234"
    """
    import statistics

    stats_parts = []

    for col in columns:
        try:
            # Extract numeric values
            values = []
            for row in rows:
                val = row.get(col)
                if val is not None:
                    if isinstance(val, int | float):
                        values.append(float(val))
                    elif isinstance(val, str):
                        # Try to parse numeric string
                        cleaned = val.replace("R$", "").replace(".", "").replace(",", ".").strip()
                        if cleaned.replace("-", "").replace(".", "").isdigit():
                            values.append(float(cleaned))

            if values and len(values) >= 3:
                total = sum(values)
                avg = statistics.mean(values)

                # Format based on magnitude
                if total > 1000:
                    stats_parts.append(f"{col}: total={total:,.2f}, média={avg:,.2f}")
        except (ValueError, TypeError, statistics.StatisticsError):
            continue

    return "; ".join(stats_parts) if stats_parts else None


def sanitize_tool_for_llm(tool: BaseTool) -> BaseTool:
    """
    Validate that tool schemas do not expose internal parameters to the LLM.

    Tools should NOT have cliente_id or user_jwt in their schemas - these
    should be handled via backend authentication (JWT tokens).

    If a tool exposes internal params, this logs an error but returns the tool
    as-is to avoid breaking the system. The fix should be in the tool definition.

    Args:
        tool: Tool from MCP

    Returns:
        The same tool (validation only, no modification)
    """
    INTERNAL_PARAMS = {"cliente_id", "user_jwt"}

    # Skip if tool has no args_schema
    if not hasattr(tool, "args_schema") or tool.args_schema is None:
        return tool

    schema = tool.args_schema

    # Check for internal params in schema
    fields = set()
    if hasattr(schema, "model_fields"):
        fields = set(schema.model_fields.keys())
    elif isinstance(schema, dict):
        fields = set(schema.get("properties", {}).keys())

    exposed_params = INTERNAL_PARAMS & fields
    if exposed_params:
        logger.error(
            f"[SECURITY] Tool '{tool.name}' exposes internal params {exposed_params} to LLM! "
            f"Fix the tool definition to remove these from the signature."
        )

    return tool


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

    # Build tools description using unified function
    tools_description = build_tools_description(available_tools, ToolRegistry)

    # Context 2.0: Build modular context sections (includes business hours, policies, etc.)
    context_sections_text = ""
    if vizu_context:
        logger.info("[PROMPT_BUILD] vizu_context available, converting to safe context")
        # Convert to SafeClientContext for LLM-safe exposure
        llm_safe_context = vizu_context.to_safe_context()
        logger.info(f"[PROMPT_BUILD] Safe context loaded_sections: {llm_safe_context.loaded_sections}")

        # Define which sections the respond node needs
        # SIMPLIFIED: Only essential sections for data analyst role
        respond_sections = [
            ContextSection.COMPANY_PROFILE,  # Basic company context
            ContextSection.DATA_SCHEMA,      # Schema for SQL queries
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
        logger.warning("[PROMPT_BUILD] No vizu_context provided - prompt will rely on Langfuse template")

    variables = {
        "nome_empresa": nome_empresa,
        "tools_description": tools_description,
        "context_sections": context_sections_text,
    }

    # Use unified build_prompt which handles caching internally
    # Fetches prompt "atendente/default" from Langfuse, with builtin fallback
    return await build_prompt(
        name="atendente/default",
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
    logger.debug("=== SUPERVISOR FULL SYSTEM PROMPT ===")
    logger.debug(system_prompt)
    logger.debug("=== END SUPERVISOR SYSTEM PROMPT ===")

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
    logger.debug("=== END SUPERVISOR MESSAGE LIST ===")

    # 5. Bind das Tools filtradas no Modelo
    llm = get_llm(model_override=model_override)

    if available_tools:
        # Validate tools don't expose internal params (logs error if they do)
        validated_tools = sanitize_tools_for_llm(available_tools)
        llm = llm.bind_tools(validated_tools)
        logger.debug(f"Bound {len(validated_tools)} tools to LLM")

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
    elicitation_response = state.get("elicitation_response")
    pending = state.get("pending_elicitation")

    # Pass cliente_id to MCP via X-Cliente-Id header
    # JWT was already validated in atendente_core, cliente_id is resolved
    # This is more efficient than passing JWT (no duplicate validation/lookup)
    cliente_id = state.get("cliente_id")
    if cliente_id:
        mcp_manager.set_cliente_id(str(cliente_id))
        logger.debug(f"[Tools] Set X-Cliente-Id header: {cliente_id}")
    else:
        logger.warning("[Tools] No cliente_id in state! Tools may fail auth.")

    # Variable to capture structured_data from tool results (before truncation)
    extracted_structured_data: dict | None = None

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

            # Security: remove any auth params that LLM might have generated
            # Tools should not expose these in their schemas, but defense in depth
            for internal_param in ("cliente_id", "user_jwt"):
                if internal_param in args_to_pass:
                    logger.warning(
                        f"Removing '{internal_param}' from LLM-generated args for '{tool_name}'"
                    )
                    args_to_pass.pop(internal_param)

            # Injeta elicitation response se aplicável
            if (
                elicitation_response
                and pending
                and pending.get("tool_name") == tool_name
            ):
                args_to_pass["_elicitation_response"] = elicitation_response.get(
                    "response"
                )

            # Executa a ferramenta via MCP (auth via JWT in connection headers)
            output = await mcp_manager.call_tool(tool_name, args_to_pass)

            # Extract content from MCP result
            if hasattr(output, "content") and output.content:
                # MCP returns CallToolResult with content list
                output = "\n".join(
                    item.text if hasattr(item, "text") else str(item)
                    for item in output.content
                )

            logger.info(
                f"Tool '{tool_name}' resultado (primeiros 300 chars): {str(output)[:300]}"
            )

            # Extract structured_data BEFORE truncating (it may be large)
            # Frontend gets 20 rows max, LLM gets summary + 3 sample rows
            try:
                import json
                parsed_output = json.loads(output) if isinstance(output, str) else output
                if isinstance(parsed_output, dict) and parsed_output.get("structured_data"):
                    full_data = parsed_output["structured_data"]

                    # Store in nonlocal for later extraction (with row limit for frontend)
                    nonlocal extracted_structured_data
                    if extracted_structured_data is None:
                        # Limit rows for frontend display (20 rows, 10 per page)
                        frontend_data = full_data.copy()
                        if frontend_data.get("rows") and len(frontend_data["rows"]) > 20:
                            frontend_data["rows"] = frontend_data["rows"][:20]
                            frontend_data["truncated"] = True
                            frontend_data["total_rows"] = len(full_data["rows"])
                        extracted_structured_data = frontend_data
                        logger.info(f"[Tools] Extracted structured_data from '{tool_name}': {len(full_data.get('rows', []))} total rows, {len(frontend_data.get('rows', []))} for frontend")

                    # Create LLM-friendly summary (aggregated + 3 sample rows)
                    llm_summary = _create_llm_data_summary(full_data, parsed_output)
                    parsed_output["output"] = llm_summary
                    # Remove full structured_data from LLM context (it's too big)
                    del parsed_output["structured_data"]
                    output = json.dumps(parsed_output, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"[Tools] Could not parse output as JSON: {e}")

            # Truncate tool output to prevent context bloat
            # Full data is already cached in Redis (via ToolResultCache in sql_module)
            MAX_TOOL_OUTPUT_CHARS = 8000  # ~2000 tokens
            output_str = str(output)
            if len(output_str) > MAX_TOOL_OUTPUT_CHARS:
                output_str = output_str[:MAX_TOOL_OUTPUT_CHARS] + "\n\n[Output truncated. Full data available via cache_ref_id.]"
                logger.info(f"Tool '{tool_name}' output truncated from {len(str(output))} to {MAX_TOOL_OUTPUT_CHARS} chars")

            return ToolMessage(
                content=output_str, tool_call_id=tool_call_id, name=tool_name
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

    # Use structured_data extracted before truncation (already limited to 20 rows for frontend)
    if extracted_structured_data:
        return_dict["structured_data"] = extracted_structured_data
        logger.info(f"[Tools] Passing structured_data to frontend: {len(extracted_structured_data.get('rows', []))} rows")

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
