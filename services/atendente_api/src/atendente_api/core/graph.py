# src/atendente_api/core/graph.py

from langgraph.graph import StateGraph, END

# --- CORREÇÃO APLICADA AQUI ---
# Usamos uma importação relativa para importar de um arquivo no mesmo diretório.
from .state import AgentState
from .nodes import supervisor_node, execute_tools_node, should_continue


def create_agent_graph() -> StateGraph:
    """
    Cria e compila o grafo do agente LangGraph.
    """
    workflow = StateGraph(AgentState)

    # Adiciona os nós ao grafo
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("execute_tools", execute_tools_node)

    # Define as arestas (fluxo de controle)
    workflow.set_entry_point("supervisor")

    # Aresta condicional: decide se executa ferramentas ou termina
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {
            "execute_tools": "execute_tools",
            "__end__": END,
        },
    )

    # Aresta de volta: após executar uma ferramenta, volta para o supervisor decidir o próximo passo
    workflow.add_edge("execute_tools", "supervisor")

    # Compila o grafo em um objeto executável
    agent_graph = workflow.compile()

    return agent_graph