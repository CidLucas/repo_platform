# src/atendente_api/core/state.py

# src/atendente_api/core/state.py
from typing import Annotated, Any
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# --- IMPORT CORRIGIDO ---
# Importamos os modelos de contexto seguros da lib compartilhada
from vizu_models.safe_client_context import InternalClientContext, SafeClientContext


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
    seguros devem estar aqui. Dados sensíveis (api_key, cliente_id)
    ficam no InternalClientContext que não é passado para a LLM.

    MEMÓRIA: O campo `messages` usa add_messages como reducer,
    que acumula mensagens entre invocações da mesma thread_id.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    # Contexto seguro para a LLM (sem dados sensíveis)
    safe_context: SafeClientContext | None
    # Contexto interno para operações do servidor (injeção de cliente_id em tools)
    # Este campo NÃO deve ser incluído em prompts
    _internal_context: InternalClientContext | None
    tools: list
    # Override do modelo LLM para este request específico
    model_override: str | None

    # --- PHASE 5: Prompt Management ---
    # ID do cliente para buscar prompts customizados do banco
    cliente_id: UUID | None

    # --- ELICITATION FIELDS ---
    # Elicitation pendente aguardando resposta do usuário
    pending_elicitation: PendingElicitation | None
    # Resposta do usuário para elicitation pendente
    elicitation_response: dict[str, Any] | None
