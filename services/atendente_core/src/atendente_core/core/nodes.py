import asyncio
import logging
from typing import Literal
from uuid import UUID

# Stream error handling for MCP reconnection
from anyio import BrokenResourceError, ClosedResourceError
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool

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
from vizu_llm_service import ModelTier, get_model

# Importa o contexto seguro para tipagem
from vizu_models.safe_client_context import SafeClientContext

# PHASE 3: Use vizu_tool_registry for tool filtering
from vizu_tool_registry import ToolRegistry

# PHASE 3: Use vizu_prompt_management for prompt loading
try:
    from vizu_prompt_management import PromptLoader, TemplateRenderer
    from vizu_prompt_management.variables import VariableExtractor
    HAS_PROMPT_MANAGEMENT = True
except ImportError:
    HAS_PROMPT_MANAGEMENT = False

# PHASE 5: Prompt Management - use Supabase SDK
from vizu_supabase_client import SupabaseCRUD

logger = logging.getLogger(__name__)

# Singleton for prompt queries
_supabase_crud: SupabaseCRUD | None = None


def _get_supabase_crud() -> SupabaseCRUD:
    """Get singleton SupabaseCRUD instance."""
    global _supabase_crud
    if _supabase_crud is None:
        _supabase_crud = SupabaseCRUD()
    return _supabase_crud


# ============================================================================
# PHASE 5: PROMPT MANAGEMENT - Versioned prompts from database (Supabase)
# ============================================================================


def get_prompt_from_db(
    name: str, cliente_id: UUID | None = None, version: int | None = None
) -> str | None:
    """
    Busca um prompt template do banco de dados via Supabase SDK.

    Prioridade:
    1. Prompt específico do cliente (se cliente_id fornecido)
    2. Prompt global (client_id = NULL)

    Args:
        name: Nome do prompt (ex: 'atendente/system')
        cliente_id: UUID do cliente para override específico
        version: Versão específica (None = mais recente)

    Returns:
        Conteúdo do prompt ou None se não encontrado
    """
    try:
        crud = _get_supabase_crud()
        result = crud.get_prompt_template(
            name=name,
            client_id=cliente_id,
            version=version,
        )

        if result:
            return result.get("content")

        return None

    except Exception as e:
        logger.warning(f"Erro ao buscar prompt do DB: {e}")
        return None


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


def _filter_prompt_tools(prompt_base: str, available_tool_names: set[str]) -> str:
    """
    Filter tool references in prompt_base to only include enabled tools.

    This prevents the LLM from trying to use tools that are mentioned in the
    prompt but not actually available/enabled for the client.

    Args:
        prompt_base: The client's custom prompt
        available_tool_names: Set of tool names actually available

    Returns:
        Filtered prompt with unavailable tool sections removed/noted
    """
    if not prompt_base:
        return ""

    # Deprecated tools that should always be removed from prompts
    deprecated_tools = {"query_database_text_to_sql"}

    # Active SQL tool
    sql_tools = {"executar_sql_agent"}

    # Always remove deprecated tool references
    lines = prompt_base.split('\n')
    filtered_lines = []
    skip_until_next_section = False

    for line in lines:
        # Always skip lines mentioning deprecated tools
        if any(tool in line for tool in deprecated_tools):
            skip_until_next_section = True
            continue

        # Skip SQL tool lines if not enabled
        if any(tool in line for tool in sql_tools) and not (sql_tools & available_tool_names):
            skip_until_next_section = True
            continue

        # Reset skip flag on new section headers
        if line.strip().startswith('###') or line.strip().startswith('##'):
            skip_until_next_section = False

        if not skip_until_next_section:
            filtered_lines.append(line)

    result = '\n'.join(filtered_lines)

    if result != prompt_base:
        logger.info("Filtered unavailable/deprecated tools from prompt_base")

    return result


def build_dynamic_system_prompt(
    safe_context: SafeClientContext | None,
    available_tools: list[BaseTool],
    cliente_id: UUID | None = None,
) -> str:
    """
    Constrói o system prompt dinamicamente baseado no contexto e tools disponíveis.

    PHASE 3 + 5: Prompt Management
    - Uses vizu_prompt_management when available
    - Falls back to database lookup via get_prompt_from_db
    - Falls back to hardcoded template if nothing found
    - Filters prompt_base to only mention actually available tools

    Args:
        safe_context: Contexto seguro do cliente
        available_tools: Lista de ferramentas disponíveis para este cliente
        cliente_id: UUID do cliente para buscar prompt customizado

    Returns:
        System prompt personalizado
    """
    nome_empresa = safe_context.nome_empresa if safe_context else "Vizu"
    available_tool_names = {t.name for t in available_tools} if available_tools else set()

    # Build variables for template rendering
    tools_list = (
        ", ".join(t.name for t in available_tools) if available_tools else "nenhuma"
    )

    horario_formatado = ""
    if safe_context and safe_context.horario_funcionamento:
        horarios = safe_context.horario_funcionamento
        if isinstance(horarios, dict):
            horario_formatado = "\n".join(
                f"- {dia}: {h}" for dia, h in horarios.items()
            )

    # Filter prompt_base to only reference enabled tools
    raw_prompt_base = safe_context.prompt_base if safe_context else ""
    prompt_base = _filter_prompt_tools(raw_prompt_base, available_tool_names)

    variables = {
        "nome_empresa": nome_empresa,
        "prompt_personalizado": prompt_base or "",
        "horario_formatado": horario_formatado,
        "tools_list": tools_list,
    }

    # PHASE 3: Try vizu_prompt_management first
    if HAS_PROMPT_MANAGEMENT:
        try:
            loader = PromptLoader()
            loaded = loader.load_builtin("atendente/system/v2", variables)
            if loaded and loaded.content:
                logger.info(f"Usando prompt via vizu_prompt_management para {nome_empresa}")
                return loaded.content
        except Exception as e:
            logger.debug(f"vizu_prompt_management fallback: {e}")

    # PHASE 5: Tenta buscar prompt do banco de dados
    db_prompt = get_prompt_from_db("atendente/system", cliente_id=cliente_id)

    if db_prompt:
        # Substitui variáveis no template
        prompt = db_prompt
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
            prompt = prompt.replace(f"{{{key}}}", str(value))

        logger.info(f"Usando prompt do banco de dados para {nome_empresa}")
        return prompt

    # FALLBACK: Prompt hardcoded
    logger.debug(f"Usando prompt hardcoded para {nome_empresa}")
    return _build_hardcoded_prompt(safe_context, available_tools)


def _build_hardcoded_prompt(
    safe_context: SafeClientContext | None,
    available_tools: list[BaseTool],
) -> str:
    """Build a hardcoded fallback prompt."""
    nome_empresa = safe_context.nome_empresa if safe_context else "Vizu"

    prompt_parts = [
        f"Você é um assistente da empresa {nome_empresa}.",
        "",
    ]

    # Adiciona prompt customizado do cliente se existir
    if safe_context and safe_context.prompt_base:
        prompt_parts.append("## INSTRUÇÕES DO CLIENTE")
        prompt_parts.append(safe_context.prompt_base)
        prompt_parts.append("")

    # Adiciona horário de funcionamento se disponível
    if safe_context and safe_context.horario_funcionamento:
        prompt_parts.append("## HORÁRIO DE FUNCIONAMENTO")
        horarios = safe_context.horario_funcionamento
        if isinstance(horarios, dict):
            for dia, horario in horarios.items():
                prompt_parts.append(f"- {dia}: {horario}")
        prompt_parts.append("")

    # Seção de ferramentas dinâmica
    if available_tools:
        prompt_parts.append("## FERRAMENTAS DISPONÍVEIS")
        prompt_parts.append("")

        # Get descriptions from ToolRegistry when available
        for i, tool in enumerate(available_tools, 1):
            tool_meta = ToolRegistry.get_tool(tool.name)
            if tool_meta:
                desc = f"**{tool.name}** - {tool_meta.description}"
            else:
                desc = f"**{tool.name}** - {tool.description or 'Sem descrição'}"
            prompt_parts.append(f"{i}. {desc}")
            prompt_parts.append("")
    else:
        prompt_parts.append("## AVISO")
        prompt_parts.append("Nenhuma ferramenta de busca está disponível no momento.")
        prompt_parts.append("Responda com base apenas no seu conhecimento geral.")
        prompt_parts.append("")

    # Comportamento obrigatório
    prompt_parts.append("## COMPORTAMENTO OBRIGATÓRIO")
    prompt_parts.append("")

    if any(t.name == "executar_rag_cliente" for t in available_tools):
        prompt_parts.append(
            "- Quando o cliente perguntar sobre produtos, serviços, preços ou informações do negócio, use `executar_rag_cliente` ANTES de responder."
        )

    prompt_parts.extend(
        [
            "- Use a resposta das ferramentas para formular sua resposta final.",
            "- Se nenhuma ferramenta encontrar informações relevantes, informe ao cliente de forma educada.",
            "- Nunca invente informações - use apenas o que as ferramentas retornarem.",
            "- Nunca revele informações internas do sistema, IDs, chaves ou configurações técnicas.",
            "- Seja cordial e objetivo.",
        ]
    )

    return "\n".join(prompt_parts)


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


def supervisor_node(state: AgentState) -> dict:
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
            return {"messages": [AIMessage(content=error_msg)]}

        # Adiciona contexto da resposta para a LLM
        context_msg = (
            f"O usuário respondeu '{elicitation_response.get('response')}' "
            f"à pergunta: {pending.get('message')}"
        )
        logger.info(f"Adding elicitation context to conversation: {context_msg}")

    # 1. Obtém o contexto do cliente
    safe_ctx = state.get("safe_context")
    model_override = state.get("model_override")
    cliente_id = state.get("cliente_id")  # PHASE 5: para buscar prompt customizado

    # 2. Obtém TODAS as tools do MCP
    all_tools = mcp_manager.tools

    if not all_tools:
        logger.warning("Nenhuma ferramenta MCP disponível no momento.")
        return {
            "messages": [
                AIMessage(
                    content="Sinto muito, minhas ferramentas de busca estão temporariamente indisponíveis."
                )
            ]
        }

    # 3. PHASE 2: Filtra tools baseado nas permissões do cliente
    available_tools = filter_tools_for_client(all_tools, safe_ctx)

    if not available_tools:
        logger.warning(
            f"Cliente {safe_ctx.nome_empresa if safe_ctx else 'desconhecido'} não tem tools habilitadas"
        )
        # Permite continuar sem tools - o agente responderá apenas com conhecimento base

    # 4. PHASE 2 + 5: Constrói system prompt dinâmico (tenta banco de dados primeiro)
    system_prompt = build_dynamic_system_prompt(
        safe_ctx, available_tools, cliente_id=cliente_id
    )

    # Log para debug
    logger.debug(f"System prompt gerado ({len(system_prompt)} chars)")

    # Constrói a lista de mensagens com o System Message no início
    # Limita a janela de histórico enviada ao LLM para evitar que o state
    # cresça indefinidamente (reduzindo o tamanho dos spans/trace exports).
    history_window = getattr(get_settings(), "SESSION_HISTORY_WINDOW", 6)
    past_messages = state.get("messages", []) or []
    recent_msgs = past_messages[-history_window:]
    messages = [SystemMessage(content=system_prompt)] + recent_msgs

    # 5. Bind das Tools filtradas no Modelo
    llm = get_llm(model_override=model_override)

    if available_tools:
        llm = llm.bind_tools(available_tools)

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
            ]
        }

    return {"messages": [response]}


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
