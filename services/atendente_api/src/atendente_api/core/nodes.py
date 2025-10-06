# services/atendente_api/src/atendente_api/core/nodes.py

from typing import Dict, Callable, Literal

from langchain.agents import create_tool_calling_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

# Importa o nosso novo serviço centralizado de LLM
from vizu_llm_service import get_model

# Importa os componentes do nosso agente
from ..core.state import AgentState
from ..tools.rag_tool import create_rag_chain
from ..tools.sql_tool import create_sql_toolkit, get_sql_database_engine_for_client


# --- 1. Tool Registry: A Fábrica de Ferramentas Dinâmicas ---
# Mapeia o nome da ferramenta (conforme o LLM é treinado para chamar)
# para a função que sabe como construir e executar essa ferramenta.
TOOL_REGISTRY: Dict[str, Callable[[AgentState], Runnable]] = {
    "sql_agent_executor": lambda state: create_sql_toolkit(
        engine=get_sql_database_engine_for_client(state["contexto_cliente"])
    ).get_agent_executor(),
    "rag_chain": lambda state: create_rag_chain(state["contexto_cliente"]),
}


# --- 2. Definição dos Nós do Grafo ---

def supervisor_node(state: AgentState) -> dict:
    """
    Nó Supervisor (Agente Principal).

    Responsabilidade: Analisar o estado da conversa e decidir a próxima ação,
    seja respondendo diretamente ao usuário ou chamando uma ferramenta.
    """
    # --- LÓGICA DO MVP ---
    # Pedimos o modelo padrão ao serviço centralizado.
    # Toda a complexidade de qual modelo usar (Ollama, OpenAI, etc.)
    # está encapsulada e resolvida dentro do `vizu_llm_service`.
    llm = get_model()

    # Define o prompt do agente. No futuro, o prompt do sistema pode ser
    # enriquecido com o `prompt_base` do contexto do cliente.
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Você é um assistente prestativo da Vizu."),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    # As ferramentas disponíveis para o agente podem ser carregadas dinamicamente
    # com base nas feature flags do cliente no futuro.
    available_tools = [] # Por enquanto, o agente decide o fluxo sem ferramentas explícitas.

    agent_runnable = create_tool_calling_agent(llm, available_tools, prompt)

    response = agent_runnable.invoke(
        {
            "input": state["messages"][-1].content,
            "chat_history": state["messages"][:-1],
        }
    )
    return {"messages": [response]}


def execute_tools_node(state: AgentState) -> dict:
    """
    Nó Executor de Ferramentas.

    Responsabilidade: Executar a ferramenta decidida pelo supervisor,
    usando o Tool Registry para construir a ferramenta sob demanda.
    """
    last_message: AIMessage = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]

    if tool_name not in TOOL_REGISTRY:
        error_message = f"Erro: Ferramenta '{tool_name}' não registrada ou indisponível."
        tool_output = ToolMessage(content=error_message, tool_call_id=tool_call["id"])
        return {"messages": [tool_output]}

    try:
        tool_factory = TOOL_REGISTRY[tool_name]
        tool_runnable = tool_factory(state)

        input_data = tool_args.get("query") or tool_args.get("input") or tool_args
        output = tool_runnable.invoke(input_data)

        tool_output = ToolMessage(content=str(output), tool_call_id=tool_call["id"])

    except Exception as e:
        error_message = f"Erro ao executar a ferramenta {tool_name}: {e}"
        tool_output = ToolMessage(content=error_message, tool_call_id=tool_call["id"])

    return {"messages": [tool_output]}


# --- 3. Lógica Condicional (Arestas do Grafo) ---

def should_continue(state: AgentState) -> Literal["execute_tools", "__end__"]:
    """
    Função de roteamento que direciona o fluxo do grafo.
    """
    last_message: AIMessage = state["messages"][-1]
    if last_message.tool_calls:
        return "execute_tools"
    return "__end__"