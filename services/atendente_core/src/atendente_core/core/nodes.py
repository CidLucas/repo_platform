import asyncio
import logging
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

if TYPE_CHECKING:
    from blu_context_service import ContextService

# Stream error handling for MCP reconnection
from anyio import BrokenResourceError, ClosedResourceError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, create_model

from atendente_core.core.config import get_settings
from atendente_core.core.state import AgentState
from atendente_core.core.worker_factory import _is_transient_llm_error

# Hierarchical multi-agent: worker delegation infrastructure
from atendente_core.core.worker_registry import WorkerRegistry
from atendente_core.core.worker_tools import build_worker_tools, is_delegation_tool_call

# Importamos o gerenciador de conexão MCP
from atendente_core.services.mcp_client import mcp_manager

# Phase 3: Use blu_elicitation_service instead of local module
from blu_elicitation_service import (
    ElicitationRequired,
    format_elicitation_for_llm,
    validate_elicitation_response,
)

# Importa o cliente LLM centralizado
from blu_llm_service import ModelTier, TokenBudget, get_model

# Context 2.0: Import ContextSection for selective injection
from blu_models.enums import ContextSection

# Importa o contexto seguro para tipagem
from blu_models.safe_client_context import SafeClientContext

# Context 2.0: Import BluClientContext for full context access
from blu_models.blu_client_context import BluClientContext

# PHASE 3+5: Use blu_prompt_management unified dynamic builder
from blu_prompt_management import (
    build_prompt,
    compose_prompt,
)

# PHASE 3: Use blu_tool_registry for tool filtering
from blu_tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

# Maximum number of supervisor→tools→supervisor cycles before forcing a final response.
# Prevents runaway tool loops when the LLM keeps retrying failed queries.
MAX_TOOL_TURNS = 3

# ---------------------------------------------------------------------------
# Module-level ContextService holder for Redis-cached prompts (OPT-3).
# Set by service.py before graph.ainvoke() so supervisor_node can access it
# without threading non-serializable objects through LangGraph state.
# ---------------------------------------------------------------------------
_node_context_service: "ContextService | None" = None


def set_node_context_service(ctx: "ContextService | None") -> None:
    global _node_context_service
    _node_context_service = ctx
    _clear_supervisor_context_cache()
    # Also clear worker prompt cache on new request
    from atendente_core.core.worker_factory import clear_worker_cache
    clear_worker_cache()


def get_node_context_service() -> "ContextService | None":
    return _node_context_service


# ---------------------------------------------------------------------------
# Per-request context cache for supervisor_node (avoids re-fetching context
# from Redis/DB on every supervisor call within the same request).
# Cleared when a new request sets the context_service via set_node_context_service.
# ---------------------------------------------------------------------------
_supervisor_context_cache: dict[UUID, tuple] = {}


def _clear_supervisor_context_cache() -> None:
    global _supervisor_context_cache
    _supervisor_context_cache = {}


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
        sample_text = "\n".join([f"  Exemplo {i+1}: {row}" for i, row in enumerate(sample_rows)])
        summary_parts.append(f"\nPrimeiros 3 registros:\n{sample_text}")

    # Try to add aggregated stats for numeric columns
    if rows and columns:
        numeric_stats = _calculate_numeric_stats(rows, columns)
        if numeric_stats:
            summary_parts.append(f"\nEstatísticas: {numeric_stats}")

    # Add truncation note
    if total_rows > 3:
        summary_parts.append(
            f"\n(Mostrando 3 de {total_rows}. Dados completos exibidos na tabela para o usuário.)"
        )

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
    Remove internal parameters from tool schemas before exposing to LLM.

    Tools should NOT have cliente_id or user_jwt visible to the LLM - these
    are injected server-side via mcp_inject_cliente_id decorator.

    This function actively removes internal params from the tool's JSON schema
    to prevent the LLM from seeing/generating them.

    Args:
        tool: Tool from MCP

    Returns:
        Tool with internal params stripped from schema
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
    if not exposed_params:
        return tool  # No internal params, return as-is

    # Log warning - tools should be fixed at the source
    logger.warning(
        f"[SECURITY] Tool '{tool.name}' exposes internal params {exposed_params} - stripping from schema"
    )

    # Strip internal params from the tool's schema
    # For Pydantic models, we need to modify the JSON schema representation
    try:
        if hasattr(schema, "model_json_schema"):
            # Pydantic v2 model - modify the generated JSON schema
            json_schema = schema.model_json_schema()
            if "properties" in json_schema:
                for param in exposed_params:
                    json_schema["properties"].pop(param, None)
                if "required" in json_schema:
                    json_schema["required"] = [
                        r for r in json_schema["required"] if r not in INTERNAL_PARAMS
                    ]
            # Override tool's schema property to use cleaned version
            tool._args_schema_json = json_schema
        elif isinstance(schema, dict) and "properties" in schema:
            # Raw dict schema
            for param in exposed_params:
                schema["properties"].pop(param, None)
            if "required" in schema:
                schema["required"] = [r for r in schema["required"] if r not in INTERNAL_PARAMS]
    except Exception as e:
        logger.error(f"[SECURITY] Failed to strip params from '{tool.name}': {e}")

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
# Phase 3: Uses blu_tool_registry instead of hardcoded mapping
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

    Phase 3: Uses blu_tool_registry for validation.

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

    if enabled_tool_names:
        # Explicit whitelist: only allow tools in enabled_tools that pass tier check
        available_tools = ToolRegistry.get_available_tools(
            enabled_tools=enabled_tool_names,
            tier=tier,
            include_google=True,
        )
        available_names = {t.name for t in available_tools}
    else:
        # No enabled_tools configured: grant ALL tools accessible at client's tier
        logger.info(
            f"No enabled_tools configured for {safe_context.nome_empresa} — "
            f"granting all tools for tier {tier}"
        )
        available_names = {t.name for t in ToolRegistry.get_tools_for_tier(tier)}

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
    context_service: "ContextService | None" = None,
    blu_context: BluClientContext | None = None,
) -> str:
    """
    Build the supervisor system prompt using lightweight routing fragments.

    The supervisor is a thin routing layer — it delegates data/knowledge/report
    questions to specialist workers and only handles greetings/clarifications
    directly. SQL schema, SQL rules, RAG rules, and tool-usage fragments are
    NOT included here; they live inside the workers.

    Fragments: supervisor-role, supervisor-workers, supervisor-rules, response-format.

    Falls back to the old monolithic prompt if fragment composition fails.

    Args:
        safe_context: Safe client context with permissions
        available_tools: List of tools (worker meta-tools + public tools)
        context_service: Optional ContextService for Redis caching
        blu_context: Full BluClientContext with all sections (Context 2.0)

    Returns:
        Rendered system prompt
    """
    nome_empresa = safe_context.nome_empresa if safe_context else "Blu"
    tier = _get_tier_from_context(safe_context)

    # Build workers description from registry (tier-filtered)
    workers_description = WorkerRegistry.build_workers_description(tier)

    # Context 2.0: Build modular context sections (includes business hours, policies, etc.)
    context_sections_text = ""
    if blu_context:
        logger.info("[PROMPT_BUILD] blu_context available, converting to safe context")
        llm_safe_context = blu_context.to_safe_context()
        logger.info(
            f"[PROMPT_BUILD] Safe context loaded_sections: {llm_safe_context.loaded_sections}"
        )

        respond_sections = [
            ContextSection.COMPANY_PROFILE,
            ContextSection.DATA_SCHEMA,
        ]

        context_sections_text = llm_safe_context.get_compiled_context(
            sections=respond_sections,
            include_header=False,
        )
        logger.info(
            f"[PROMPT_BUILD] Context 2.0: Compiled {len(respond_sections)} sections ({len(context_sections_text)} chars)"
        )
    else:
        logger.warning(
            "[PROMPT_BUILD] No blu_context provided - prompt will rely on Langfuse template"
        )

    variables = {
        "nome_empresa": nome_empresa,
        "workers_description": workers_description,
        "context_sections": context_sections_text,
        # Keep tools_description for backward compat (used by response-format fragment)
        "tools_description": "",
    }

    # Supervisor fragments — no SQL/RAG/tool-usage fragments
    fragments = [
        "fragment/supervisor-role",
        "fragment/supervisor-workers",
        "fragment/supervisor-rules",
        "fragment/response-format",
    ]

    logger.info(
        f"[PROMPT_BUILD] Composing {len(fragments)} supervisor fragments: {fragments}"
    )

    try:
        prompt = await compose_prompt(
            fragments=fragments,
            variables=variables,
            context_service=context_service,
        )
        if prompt and prompt.strip():
            return prompt
        logger.warning("[PROMPT_BUILD] compose_prompt returned empty, falling back to monolithic")
    except Exception as e:
        logger.warning(f"[PROMPT_BUILD] Fragment composition failed: {e}, falling back to monolithic")

    # Fallback: use monolithic prompt if fragment composition fails
    logger.info("[PROMPT_BUILD] Falling back to monolithic prompt: atendente/default")
    return await build_prompt(
        name="atendente/default",
        variables=variables,
        context_service=context_service,
    )


def get_llm(model_override: str | None = None):
    """
    Configura o cliente LLM usando o blu_llm_service.

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

    # 1. Obtém o contexto do cliente ON-DEMAND usando cliente_id
    # OTIMIZAÇÃO: Contexto não é armazenado no state para evitar trace bloat
    model_override = state.get("model_override")
    cliente_id = state.get("cliente_id")

    # Fetch context on-demand using ContextService (cached per-request)
    context_service = get_node_context_service()
    safe_ctx = None
    blu_ctx = None

    if cliente_id and cliente_id in _supervisor_context_cache:
        blu_ctx, safe_ctx = _supervisor_context_cache[cliente_id]
        logger.debug(f"[SUPERVISOR] Using cached context for cliente_id={cliente_id}")
    elif cliente_id and context_service:
        try:
            blu_ctx = await context_service.get_client_context_by_id(cliente_id)
            if blu_ctx:
                from blu_models.safe_client_context import InternalClientContext

                internal_ctx = InternalClientContext.from_blu_client_context(blu_ctx)
                safe_ctx = internal_ctx.get_safe_context()
                _supervisor_context_cache[cliente_id] = (blu_ctx, safe_ctx)
                logger.debug(
                    f"[SUPERVISOR] Fetched context for cliente_id={cliente_id}: {blu_ctx.nome_empresa}"
                )
            else:
                logger.warning(f"[SUPERVISOR] No context found for cliente_id={cliente_id}")
        except Exception as e:
            logger.error(f"[SUPERVISOR] Failed to fetch context for cliente_id={cliente_id}: {e}")
    else:
        logger.warning(
            f"[SUPERVISOR] No cliente_id ({cliente_id}) or context_service ({context_service is not None})"
        )

    # DEBUG: Log context state (demoted to DEBUG level for production)
    logger.debug(f"[SUPERVISOR] safe_context present: {safe_ctx is not None}")
    logger.debug(f"[SUPERVISOR] blu_context present: {blu_ctx is not None}")
    if blu_ctx:
        logger.debug(
            f"[SUPERVISOR] blu_context.nome_empresa: {getattr(blu_ctx, 'nome_empresa', 'N/A')}"
        )

    # 2+3. Get tools (use cached on subsequent supervisor calls within same request)
    # Hierarchical architecture: supervisor binds worker meta-tools + public MCP tools.
    # Specialist MCP tools (SQL, RAG, OCR) are NOT bound here — workers own them.
    cached_tools = state.get("_cached_tools")
    if cached_tools:
        validated_tools = cached_tools
        available_tools = cached_tools
        logger.debug(f"[SUPERVISOR] Using cached tools ({len(cached_tools)})")
    else:
        tier = _get_tier_from_context(safe_ctx)
        nome_empresa = safe_ctx.nome_empresa if safe_ctx else "Blu"

        # Context 2.0: compile context sections for worker prompts
        context_sections_text = ""
        if blu_ctx:
            llm_safe_ctx = blu_ctx.to_safe_context()
            respond_sections = [ContextSection.COMPANY_PROFILE, ContextSection.DATA_SCHEMA]
            context_sections_text = llm_safe_ctx.get_compiled_context(
                sections=respond_sections, include_header=False,
            )

        # Build worker delegation tools (tier-filtered)
        context_service = get_node_context_service()
        worker_meta_tools = build_worker_tools(
            tier=tier,
            session_id=state.get("cliente_id", "default"),
            cliente_id=state.get("cliente_id"),
            nome_empresa=nome_empresa,
            context_sections=context_sections_text,
            context_service=context_service,
        )

        # Supervisor only sees worker delegation tools — specialist tools
        # (SQL, RAG, OCR, etc.) are owned by workers, not exposed here.
        available_tools = worker_meta_tools

        if not available_tools:
            logger.warning("Nenhuma ferramenta disponível (workers)")

        validated_tools = list(worker_meta_tools)

        logger.info(
            f"[SUPERVISOR] Tools: {len(worker_meta_tools)} workers bound"
        )

    # 4. PHASE 2 + 5 + Context 2.0: Constrói system prompt dinâmico com seções modulares
    # OPT-7: Use cached prompt on subsequent supervisor calls (tools → supervisor loop)
    cached_prompt = state.get("_cached_system_prompt")
    if cached_prompt:
        system_prompt = cached_prompt
        logger.debug(f"[SUPERVISOR] Using cached system prompt ({len(system_prompt)} chars)")
    else:
        logger.debug(
            f"[SUPERVISOR] Building system prompt with blu_context={blu_ctx is not None}"
        )
        system_prompt = await build_dynamic_system_prompt(
            safe_ctx,
            available_tools,
            context_service=get_node_context_service(),
            blu_context=blu_ctx,
        )
        logger.debug(f"[SUPERVISOR] System prompt generated: {len(system_prompt)} chars")

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
    # Uses shared TokenBudget from blu_llm_service
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

    if validated_tools:
        llm = llm.bind_tools(validated_tools)
        logger.debug(f"Bound {len(validated_tools)} tools to LLM")

    # 6. Invoca o Modelo (with retry for transient errors)
    response = None
    for _retry in range(3):
        try:
            response = await llm.ainvoke(messages)
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
            break
        except Exception as e:
            if _retry < 2 and _is_transient_llm_error(e):
                logger.warning(f"Transient LLM error (retry {_retry+1}/2): {e}")
                await asyncio.sleep(1.0 * (_retry + 1))
                continue
            logger.error(f"Erro ao invocar LLM: {e}")
            return {
                "messages": [
                    AIMessage(content="Ocorreu um erro interno ao processar sua solicitação.")
                ],
            }

    if response is None:
        return {
            "messages": [
                AIMessage(content="Ocorreu um erro interno ao processar sua solicitação.")
            ],
        }

    # Increment turn_count when processing tool results (each tools→supervisor cycle)
    current_turn_count = state.get("turn_count", 0)
    if is_processing_tool_results:
        current_turn_count += 1

    # Only clear structured_data when NOT processing tool results
    # When processing tool results, we preserve it so the frontend receives the table
    if is_processing_tool_results:
        # Keep structured_data from execute_tools_node - don't override it
        return {
            "messages": [response],
            "turn_count": current_turn_count,
            "_cached_system_prompt": system_prompt,
            "_cached_tools": validated_tools,
        }
    else:
        # New user turn without tools - clear any previous structured_data
        return {
            "messages": [response],
            "turn_count": current_turn_count,
            "structured_data": None,
            "structured_data_list": None,
            "_cached_system_prompt": system_prompt,
            "_cached_tools": validated_tools,
        }


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
    # Include both MCP tools AND worker delegation meta-tools from cached state
    tools = mcp_manager.tools
    tool_map = {t.name: t for t in tools}

    # Add cached tools (worker meta-tools) so delegation calls can be resolved
    cached_tools = state.get("_cached_tools") or []
    for ct in cached_tools:
        if hasattr(ct, "name") and ct.name not in tool_map:
            tool_map[ct.name] = ct

    # 2. Prepara contexto compartilhado
    elicitation_response = state.get("elicitation_response")
    pending = state.get("pending_elicitation")

    # X-Cliente-Id header is set in service.py before ensure_mcp_connected(),
    # so no need to set it again here (avoids triggering reconnection)
    cliente_id = state.get("cliente_id")
    if not cliente_id:
        logger.warning("[Tools] No cliente_id in state! Tools may fail auth.")

    async def execute_single_tool(
        tool_call: dict, retry_on_stream_error: bool = True
    ) -> tuple[ToolMessage, dict | None]:
        """Executa uma única tool e retorna (ToolMessage, structured_data | None)."""
        nonlocal tool_map
        tool_name = tool_call["name"]
        tool_call_id = tool_call["id"]

        try:
            tool = tool_map.get(tool_name)
            if not tool:
                return ToolMessage(
                    content=f"Ferramenta '{tool_name}' não encontrada.",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ), None

            # --- Worker delegation tools (delegate_to_*) ---
            # These are StructuredTool instances that run a full worker loop
            # in-process. They return JSON with summary + optional structured_data.
            if is_delegation_tool_call(tool_name):
                logger.info(f"[Tools] Delegation call: {tool_name}")
                args_to_pass = dict(tool_call.get("args") or {})
                task = args_to_pass.get("task", "")

                try:
                    # Invoke the StructuredTool's async coroutine
                    output = await tool.ainvoke({"task": task})
                except Exception as e:
                    logger.exception(f"[Tools] Delegation error for '{tool_name}': {e}")
                    return ToolMessage(
                        content=f"Worker error: {e}",
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    ), None

                # Extract structured_data from worker JSON response
                tool_structured_data: dict | None = None
                try:
                    import json as _json
                    parsed_delegation = _json.loads(output) if isinstance(output, str) else output
                    if isinstance(parsed_delegation, dict) and parsed_delegation.get("structured_data"):
                        tool_structured_data = parsed_delegation["structured_data"]
                        # Tag with source worker for multi-delegation traceability
                        tool_structured_data["source_worker"] = parsed_delegation.get(
                            "worker_slug", tool_name.replace("delegate_to_", "")
                        )
                        logger.info(
                            f"[Tools] Extracted structured_data from worker '{tool_name}': "
                            f"{len(tool_structured_data.get('rows', []))} rows"
                        )
                        # Remove structured_data from LLM context (frontend shows it)
                        summary = parsed_delegation.get("summary", output)
                        tools_used = parsed_delegation.get("tools_used", [])
                        if tools_used:
                            summary += f"\n(Worker used: {', '.join(tools_used)})"
                        output = summary
                except (ValueError, TypeError):
                    pass

                output_str = str(output)[:4000]
                return ToolMessage(content=output_str, tool_call_id=tool_call_id, name=tool_name), tool_structured_data

            # --- Regular MCP tools (public tools handled by supervisor) ---
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
            if elicitation_response and pending and pending.get("tool_name") == tool_name:
                args_to_pass["_elicitation_response"] = elicitation_response.get("response")

            # Executa a ferramenta via MCP (auth via JWT in connection headers)
            output = await mcp_manager.call_tool(tool_name, args_to_pass)

            # Extract content from MCP result
            if hasattr(output, "content") and output.content:
                # MCP returns CallToolResult with content list
                output = "\n".join(
                    item.text if hasattr(item, "text") else str(item) for item in output.content
                )

            logger.info(f"Tool '{tool_name}' resultado (primeiros 300 chars): {str(output)[:300]}")

            # Extract structured_data BEFORE truncating (it may be large)
            # Frontend gets 20 rows max, LLM gets summary + 3 sample rows
            tool_structured_data: dict | None = None
            try:
                import json

                parsed_output = json.loads(output) if isinstance(output, str) else output
                if isinstance(parsed_output, dict) and parsed_output.get("structured_data"):
                    full_data = parsed_output["structured_data"]

                    # Limit rows for frontend display (20 rows, 10 per page)
                    frontend_data = full_data.copy()
                    if frontend_data.get("rows") and len(frontend_data["rows"]) > 20:
                        frontend_data["rows"] = frontend_data["rows"][:20]
                        frontend_data["truncated"] = True
                        frontend_data["total_rows"] = len(full_data["rows"])
                    frontend_data["source_tool"] = tool_name
                    tool_structured_data = frontend_data
                    logger.info(
                        f"[Tools] Extracted structured_data from '{tool_name}': {len(full_data.get('rows', []))} total rows, {len(frontend_data.get('rows', []))} for frontend"
                    )

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
            MAX_TOOL_OUTPUT_CHARS = 4000  # ~1000 tokens (LLM gets summary, full data cached in Redis)
            output_str = str(output)
            if len(output_str) > MAX_TOOL_OUTPUT_CHARS:
                output_str = (
                    output_str[:MAX_TOOL_OUTPUT_CHARS]
                    + "\n\n[Output truncated. Full data available via cache_ref_id.]"
                )
                logger.info(
                    f"Tool '{tool_name}' output truncated from {len(str(output))} to {MAX_TOOL_OUTPUT_CHARS} chars"
                )

            return ToolMessage(content=output_str, tool_call_id=tool_call_id, name=tool_name), tool_structured_data

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
                    return await execute_single_tool(tool_call, retry_on_stream_error=False)
                except Exception as reconnect_err:
                    logger.exception(f"Failed to reconnect MCP after stream error: {reconnect_err}")
                    return ToolMessage(
                        content=f"Erro de conexão com serviço de ferramentas: {str(stream_err)}",
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    ), None
            else:
                logger.exception(f"MCP stream error on retry for '{tool_name}': {stream_err}")
                return ToolMessage(
                    content=f"Erro de conexão persistente com serviço de ferramentas: {str(stream_err)}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                ), None

        except ElicitationRequired as elicit:
            nonlocal pending_elicitation
            logger.info(f"Tool '{tool_name}' requires elicitation: {elicit.message}")
            pending_elicitation = elicit.to_pending_elicitation()
            elicitation_msg = format_elicitation_for_llm(pending_elicitation)
            return ToolMessage(
                content=f"[ELICITATION REQUIRED] {elicitation_msg}",
                tool_call_id=tool_call_id,
                name=tool_name,
            ), None

        except Exception as e:
            logger.exception(f"Erro ao executar '{tool_name}': {e}")
            return ToolMessage(
                content=f"Erro ao executar ferramenta: {str(e)}",
                tool_call_id=tool_call_id,
                name=tool_name,
            ), None

    # 3. Executa TODAS as tools em PARALELO
    if len(tool_calls) > 1:
        logger.info(
            f"Executando {len(tool_calls)} tools em paralelo: {[tc['name'] for tc in tool_calls]}"
        )

    raw_results = await asyncio.gather(*[execute_single_tool(tc) for tc in tool_calls])

    # Separate ToolMessages from structured_data (collected after gather to avoid race conditions)
    messages_list: list[ToolMessage] = []
    all_structured_data: list[dict] = []
    for msg, sd in raw_results:
        messages_list.append(msg)
        if sd is not None:
            all_structured_data.append(sd)

    # Build return dict
    return_dict = {"messages": messages_list}

    # Populate structured_data (first result for backward compat) and structured_data_list (all)
    if all_structured_data:
        return_dict["structured_data"] = all_structured_data[0]
        return_dict["structured_data_list"] = all_structured_data
        logger.info(
            f"[Tools] Passing {len(all_structured_data)} structured_data result(s) to state"
        )

    # PHASE 3: If we have pending elicitation, add it to state
    if pending_elicitation:
        return_dict["pending_elicitation"] = pending_elicitation
        logger.info(f"Setting pending_elicitation: {pending_elicitation.get('elicitation_id')}")
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
        turn_count = state.get("turn_count", 0)
        if turn_count >= MAX_TOOL_TURNS:
            logger.warning(
                f"[LOOP_GUARD] Max tool turns reached ({turn_count}/{MAX_TOOL_TURNS}). "
                f"Forcing end to prevent runaway loop."
            )
            return "__end__"
        return "execute_tools"

    # Caso contrário, devolvemos a resposta final ao usuário
    return "__end__"


def fan_out_tool_calls(
    state: AgentState,
) -> list:
    """
    Fan-out dispatcher: returns Send objects for parallel tool execution.

    Uses LangGraph's Send API to dispatch each tool call to its own
    execute_single_tool_fanout node instance. All instances run in parallel
    and results are aggregated via reducers.

    Returns:
        - List of Send objects for parallel execution
        - Or a list with single string for non-tool-call routes
    """
    from langgraph.types import Send

    # Check for pending elicitation first
    pending = state.get("pending_elicitation")
    if pending:
        logger.info(
            f"[fan-out] Elicitation pending - pausing for user input: {pending.get('elicitation_id')}"
        )
        return [Send("await_elicitation", state)]

    last_message = state["messages"][-1]

    # If the LLM decided to call tools, fan-out via Send
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        turn_count = state.get("turn_count", 0)
        if turn_count >= MAX_TOOL_TURNS:
            logger.warning(
                f"[LOOP_GUARD] Max tool turns reached ({turn_count}/{MAX_TOOL_TURNS}). "
                f"Forcing end to prevent runaway loop."
            )
            return "__end__"

        tool_calls = last_message.tool_calls
        sends = []
        for tc in tool_calls:
            sends.append(
                Send(
                    "execute_single_tool_fanout",
                    {
                        **state,
                        "_tool_call": tc,
                    },
                )
            )

        logger.info(
            f"[fan-out] Dispatching {len(sends)} parallel tool calls: "
            f"{[tc['name'] for tc in tool_calls]}"
        )
        return sends

    # No tool calls - end the graph
    return "__end__"


async def execute_single_tool_fanout(state: AgentState) -> dict:
    """
    Execute a single tool call dispatched via Send (fan-out).

    This node receives the full AgentState plus a _tool_call field
    containing the single tool call to execute. Results are aggregated
    back via the messages reducer (add_messages).
    """
    tool_call = state.get("_tool_call")
    if not tool_call:
        logger.warning("[fan-out] No _tool_call in state")
        return {"messages": []}

    tool_name = tool_call["name"]
    tool_call_id = tool_call["id"]

    # Reuse the tool execution logic from execute_tools_node
    tools = mcp_manager.tools
    tool_map = {t.name: t for t in tools}

    # Add cached tools (worker meta-tools)
    cached_tools = state.get("_cached_tools") or []
    for ct in cached_tools:
        if hasattr(ct, "name") and ct.name not in tool_map:
            tool_map[ct.name] = ct

    elicitation_response = state.get("elicitation_response")
    pending = state.get("pending_elicitation")
    pending_elicitation = None

    cliente_id = state.get("cliente_id")
    if not cliente_id:
        logger.warning("[fan-out] No cliente_id in state! Tools may fail auth.")

    try:
        tool = tool_map.get(tool_name)

        # Fuzzy match delegation tools — local models sometimes hallucinate
        # names like "delegate_to_data_analysis" instead of "delegate_to_data_analyst".
        if not tool and tool_name.startswith("delegate_to_"):
            delegation_tools = {k: v for k, v in tool_map.items() if k.startswith("delegate_to_")}
            if delegation_tools:
                from difflib import get_close_matches
                matches = get_close_matches(tool_name, delegation_tools.keys(), n=1, cutoff=0.75)
                if matches:
                    matched_name = matches[0]
                    logger.warning(
                        f"[fan-out] Fuzzy match: LLM called '{tool_name}' → resolved to '{matched_name}'"
                    )
                    tool = delegation_tools[matched_name]
                    tool_name = matched_name  # use corrected name for ToolMessage

        if not tool:
            return {
                "messages": [
                    ToolMessage(
                        content=f"Ferramenta '{tool_name}' não encontrada.",
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                ]
            }

        # --- Worker delegation tools ---
        if is_delegation_tool_call(tool_name):
            logger.info(f"[fan-out] Delegation call: {tool_name}")
            args_to_pass = dict(tool_call.get("args") or {})
            task = args_to_pass.get("task", "")

            try:
                output = await tool.ainvoke({"task": task})
            except Exception as e:
                logger.exception(f"[fan-out] Delegation error for '{tool_name}': {e}")
                return {
                    "messages": [
                        ToolMessage(
                            content=f"Worker error: {e}",
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                    ]
                }

            tool_structured_data = None
            try:
                import json as _json
                parsed_delegation = _json.loads(output) if isinstance(output, str) else output
                if isinstance(parsed_delegation, dict) and parsed_delegation.get("structured_data"):
                    tool_structured_data = parsed_delegation["structured_data"]
                    tool_structured_data["source_worker"] = parsed_delegation.get(
                        "worker_slug", tool_name.replace("delegate_to_", "")
                    )
                    summary = parsed_delegation.get("summary", output)
                    tools_used = parsed_delegation.get("tools_used", [])
                    if tools_used:
                        summary += f"\n(Worker used: {', '.join(tools_used)})"
                    output = summary
            except (ValueError, TypeError):
                pass

            output_str = str(output)[:4000]
            result = {"messages": [ToolMessage(content=output_str, tool_call_id=tool_call_id, name=tool_name)]}
            if tool_structured_data:
                result["structured_data"] = tool_structured_data
                result["structured_data_list"] = [tool_structured_data]
            return result

        # --- Regular MCP tools ---
        args_to_pass = dict(tool_call.get("args") or {})

        for internal_param in ("cliente_id", "user_jwt"):
            if internal_param in args_to_pass:
                logger.warning(f"Removing '{internal_param}' from LLM-generated args for '{tool_name}'")
                args_to_pass.pop(internal_param)

        if elicitation_response and pending and pending.get("tool_name") == tool_name:
            args_to_pass["_elicitation_response"] = elicitation_response.get("response")

        output = await mcp_manager.call_tool(tool_name, args_to_pass)

        if hasattr(output, "content") and output.content:
            output = "\n".join(
                item.text if hasattr(item, "text") else str(item) for item in output.content
            )

        logger.info(f"[fan-out] Tool '{tool_name}' result (first 300 chars): {str(output)[:300]}")

        tool_structured_data = None
        try:
            import json
            parsed_output = json.loads(output) if isinstance(output, str) else output
            if isinstance(parsed_output, dict) and parsed_output.get("structured_data"):
                full_data = parsed_output["structured_data"]
                frontend_data = full_data.copy()
                if frontend_data.get("rows") and len(frontend_data["rows"]) > 20:
                    frontend_data["rows"] = frontend_data["rows"][:20]
                    frontend_data["truncated"] = True
                    frontend_data["total_rows"] = len(full_data["rows"])
                frontend_data["source_tool"] = tool_name
                tool_structured_data = frontend_data

                llm_summary = _create_llm_data_summary(full_data, parsed_output)
                parsed_output["output"] = llm_summary
                del parsed_output["structured_data"]
                output = json.dumps(parsed_output, ensure_ascii=False)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"[fan-out] Could not parse output as JSON: {e}")

        MAX_TOOL_OUTPUT_CHARS = 4000
        output_str = str(output)
        if len(output_str) > MAX_TOOL_OUTPUT_CHARS:
            output_str = (
                output_str[:MAX_TOOL_OUTPUT_CHARS]
                + "\n\n[Output truncated. Full data available via cache_ref_id.]"
            )

        result = {"messages": [ToolMessage(content=output_str, tool_call_id=tool_call_id, name=tool_name)]}
        if tool_structured_data:
            result["structured_data"] = tool_structured_data
            result["structured_data_list"] = [tool_structured_data]
        return result

    except (ClosedResourceError, BrokenResourceError) as stream_err:
        logger.warning(f"[fan-out] MCP stream error on '{tool_name}': {stream_err}. Reconnecting...")
        try:
            await mcp_manager.disconnect()
            await mcp_manager.connect()
            # Retry by re-invoking with updated tool map
            return {
                "messages": [
                    ToolMessage(
                        content=f"Erro de conexão com serviço de ferramentas (reconectando): {str(stream_err)}",
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                ]
            }
        except Exception as reconnect_err:
            logger.exception(f"[fan-out] Failed to reconnect MCP: {reconnect_err}")
            return {
                "messages": [
                    ToolMessage(
                        content=f"Erro de conexão persistente: {str(stream_err)}",
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                ]
            }

    except ElicitationRequired as elicit:
        logger.info(f"[fan-out] Tool '{tool_name}' requires elicitation: {elicit.message}")
        elicitation_data = elicit.to_pending_elicitation()
        elicitation_msg = format_elicitation_for_llm(elicitation_data)
        return {
            "messages": [
                ToolMessage(
                    content=f"[ELICITATION REQUIRED] {elicitation_msg}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ],
            "pending_elicitation": elicitation_data,
        }

    except Exception as e:
        logger.exception(f"[fan-out] Error executing '{tool_name}': {e}")
        return {
            "messages": [
                ToolMessage(
                    content=f"Erro ao executar ferramenta: {str(e)}",
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            ]
        }


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
