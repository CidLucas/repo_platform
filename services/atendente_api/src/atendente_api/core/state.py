# src/atendente_api/core/state.py

# src/atendente_api/core/state.py

from typing import Annotated, List

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

# Importamos o nosso novo modelo de contexto unificado.
from .schemas import VizuClientContext


class AgentState(TypedDict):
    """
    Define a estrutura do estado que persiste durante toda a execução do grafo de conversação.
    É a memória do nosso agente.

    Atributos:
        messages: A lista de mensagens trocadas na conversa.
        contexto_cliente: O nosso objeto de contexto unificado, contendo todas as
                          informações do cliente e suas configurações de negócio.
    """

    messages: Annotated[List[BaseMessage], "message_updater"] #add_messages do langgraph
    contexto_cliente: VizuClientContext