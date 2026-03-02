# src/atendente_core/core/state.py
from typing import Annotated, Any
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class PendingElicitation(TypedDict):
    """
    Elicitation pendente aguardando resposta do usuário.

    Armazena o estado necessário para retomar a execução do tool
    após receber a resposta do usuário.
    """

    elicitation_id: str  # ID único para correlacionar resposta
    type: str  # confirmation, selection, text_input, date_time
    message: str  # Mensagem para o usuário
    options: list[dict[str, Any]] | None  # Opções para selection
    tool_name: str  # Nome do tool que requisitou
    tool_args: dict[str, Any]  # Argumentos originais do tool
    metadata: dict[str, Any] | None  # Dados adicionais


class AgentState(TypedDict):
    """
    Estado do agente LangGraph.

    SEGURANÇA: O estado pode ser serializado e logado. Apenas dados
    mínimos devem estar aqui para evitar trace bloat.

    OTIMIZAÇÃO: Contextos (vizu_context, safe_context, _internal_context)
    são buscados on-demand no supervisor_node usando cliente_id.
    Isso reduz o tamanho do estado serializado em traces.

    MEMÓRIA: O campo `messages` usa add_messages como reducer,
    que acumula mensagens entre invocações da mesma thread_id.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    tools: list
    # Override do modelo LLM para este request específico
    model_override: str | None

    # --- PHASE 5: Prompt Management ---
    # ID do cliente para buscar contexto e prompts customizados on-demand
    cliente_id: UUID | None

    # --- AUTH ---
    # JWT token for tool auth propagation
    user_jwt: str | None

    # --- ELICITATION FIELDS ---
    # Elicitation pendente aguardando resposta do usuário
    pending_elicitation: PendingElicitation | None
    # Resposta do usuário para elicitation pendente
    elicitation_response: dict[str, Any] | None

    # --- STRUCTURED DATA (from SQL queries) ---
    # Rich tabular data for interactive display (sorting, filtering, export)
    structured_data: dict[str, Any] | None

    # --- CONVERSATION CONTROL ---
    ended: bool  # Whether conversation has ended
    turn_count: int  # Current turn number

    # --- CACHED SYSTEM PROMPT (OPT-7) ---
    # Avoids rebuilding the prompt on supervisor loop (tools → supervisor)
    _cached_system_prompt: str | None

    # --- CACHED TOOLS (OPT) ---
    # Avoids re-filtering and re-sanitizing tools on subsequent supervisor calls
    _cached_tools: list | None
