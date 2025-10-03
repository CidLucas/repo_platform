# src/atendente_api/core/nodes.py

from typing import Callable, Dict, Literal

from langchain.agents import create_tool_calling_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from ..core.state import AgentState
from ..tools.rag_tool import create_rag_chain
from ..tools.sql_tool import create_sql_toolkit, get_sql_database_engine_for_client

# --- 1. Tool Registry: A Fábrica de Ferramentas Dinâmicas ---
# Mapeia o nome da ferramenta para a função que sabe como construí-la
# e executá-la a partir do estado atual do agente.
# Este é o coração da nossa arquitetura de ferramentas agnóstica e extensível.

TOOL_REGISTRY: Dict[str, Callable[[AgentState], Runnable]] = {
    "sql_agent_executor": lambda state: create_sql_toolkit(
        engine=get_sql_database_engine_for_client(state["contexto_cliente"])
    ).get_agent_executor(),
    "rag_chain": lambda state: create_rag_chain(state["contexto_cliente"]),
}


# --- 2. Definição dos Nós do Grafo ---

def supervisor_node(state: AgentState) -> dict:
    """
    Nó Supervisor (ou Agente).
    Responsabilidade: Analisar a conversa e decidir a próxima ação.
    - Pode responder diretamente ao usuário.
    - Pode chamar uma ou mais ferramentas.
    """
    # A LLM e o prompt podem ser mais elaborados e vir de uma fábrica
    # para injetar o `prompt_base` do cliente, por exemplo.
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Você é um assistente prestativo."),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    # Extrai as ferramentas disponíveis do nosso registro
    # O `create_tool_calling_agent` precisa apenas dos nomes e schemas, não da implementação.
    available_tools = [
        # Aqui, poderíamos carregar os schemas das ferramentas dinamicamente
        # para passar ao `bind_tools`. Por simplicidade, assumimos que
        # o LLM saberá quando chamar "sql_agent_executor" ou "rag_chain".
    ]

    agent_runnable = create_tool_calling_agent(llm, available_tools, prompt)

    # O `agent_runnable` retorna um AIMessage com ou sem `tool_calls`
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
    Responsabilidade: Executar a ferramenta decidida pelo supervisor.
    É dinâmico e agnóstico à ferramenta específica.
    """
    last_message: AIMessage = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]

    if tool_name not in TOOL_REGISTRY:
        error_message = f"Erro: Ferramenta '{tool_name}' não registrada ou disponível."
        tool_output = ToolMessage(content=error_message, tool_call_id=tool_call["id"])
        return {"messages": [tool_output]}

    try:
        # 1. Busca a função de criação da ferramenta no registro
        tool_factory = TOOL_REGISTRY[tool_name]

        # 2. Cria a ferramenta sob demanda, injetando o estado (que contém o contexto)
        tool_runnable = tool_factory(state)

        # 3. Invoca a ferramenta com os argumentos corretos
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
    Função de roteamento.
    Responsabilidade: Direcionar o fluxo do grafo.
    - Se a última mensagem for uma chamada de ferramenta, continua para o nó executor.
    - Caso contrário, termina o fluxo, retornando a resposta ao usuário.
    """
    last_message: AIMessage = state["messages"][-1]
    if last_message.tool_calls:
        return "execute_tools"
    return "__end__"