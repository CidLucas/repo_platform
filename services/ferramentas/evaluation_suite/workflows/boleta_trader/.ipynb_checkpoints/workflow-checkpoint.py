# services/ferramentas/evaluation_suite/workflows/boleta_trader/workflow.py

from typing import TypedDict, Optional, Literal, List, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
import difflib

# Importamos diretamente os componentes da LangChain
from langchain_community.chat_models import ChatOllama

# --- 1. Definição do Estado e Modelos de Dados ---

class Boleta(BaseModel):
    vendedor: str
    comprador: str
    valor_cotacao: float
    valor_total: float

class TradingState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    negociacao_em_aberto: bool
    interlocutor_abertura: Optional[str]
    interlocutor_fechamento: Optional[str]
    contexto_relevante: Optional[str]
    boleta_extraida: Optional[Boleta]
    boleta_formatada: Optional[str]

# --- 2. Setup de Constantes e LLM Local ---

KEYWORDS_GATILHO = ['trava', 'fecha', 'fechado', 'fechamos', 'travo', 'fecho']
PHONE_TO_NAME_MAP = {
    "+5521999990001": "João",
    "+5521999990002": "Maria",
}
llm = ChatOllama(model="llama3", base_url="http://localhost:11434")

# --- 3. Definição dos Nós do Grafo ---

def gatekeeper_node(state: TradingState) -> dict:
    """
    Nó de Entrada e Roteamento. Atua como uma máquina de estados.
    """
    print("--- Nó: Gatekeeper ---")
    last_message = state['messages'][-1]
    sender_phone = last_message.name

    words = last_message.content.lower().split()
    is_trigger = any(difflib.get_close_matches(w, KEYWORDS_GATILHO, n=1, cutoff=0.8) for w in words)

    # 👇 A CORREÇÃO ESTÁ AQUI 👇
    if not is_trigger:
        print(">> Nenhuma ação de negociação detectada.")
        # Retornamos uma AIMessage de status para atualizar o estado e melhorar a observabilidade.
        return {"messages": [AIMessage(content="[Status] Mensagem não relacionada a negociação.")]}

    # Lógica da Máquina de Estados
    if not state.get('negociacao_em_aberto'):
        print(f">> Ação: ABRIR negociação por {sender_phone}.")
        return {"negociacao_em_aberto": True, "interlocutor_abertura": sender_phone}

    else:
        interlocutor_abertura = state['interlocutor_abertura']
        if sender_phone == interlocutor_abertura:
            print(">> Nenhuma ação (gatilho duplicado pelo mesmo interlocutor).")
            # Retornamos uma AIMessage para satisfazer a regra de atualização.
            return {"messages": [AIMessage(content="[Status] Gatilho de negociação ignorado (duplicado).")]}

        print(f">> Ação: FECHAR negociação por {sender_phone}.")
        interlocutor_fechamento = sender_phone
        contexto_filtrado = [
            f"{msg.name}: {msg.content}" for msg in state['messages']
            if msg.name in [interlocutor_abertura, interlocutor_fechamento]
        ]

        return {
            "negociacao_em_aberto": False,
            "interlocutor_abertura": None,
            "interlocutor_fechamento": interlocutor_fechamento,
            "contexto_relevante": "\n".join(contexto_filtrado)
        }

def extract_boleta_node(state: TradingState) -> dict:
    """Nó de Extração."""
    print("--- Nó: Extrator de Boleta ---")
    structured_llm_local = llm.with_structured_output(Boleta)

    prompt = f"Analise a negociação abaixo e extraia os dados para a boleta:\n---\n{state['contexto_relevante']}"

    try:
        boleta = structured_llm_local.invoke(prompt)
        print(f">> Boleta extraída com sucesso: {boleta.dict()}")
        return {"boleta_extraida": boleta}
    except Exception as e:
        print(f">> ERRO na extração estruturada: {e}")
        return {"messages": [AIMessage(f"Falha ao extrair boleta: {e}")]}

def format_boleta_node(state: TradingState) -> dict:
    """Nó Final: Formata a boleta."""
    print("--- Nó: Formatador de Boleta ---")
    boleta = state.get('boleta_extraida')
    if not boleta: return {}

    texto_boleta = (f"✅ **BOLETA DE CONFIRMAÇÃO** ✅\n"
                    f"**Vendedor:** {boleta.vendedor}\n"
                    f"**Comprador:** {boleta.comprador}\n"
                    f"**Cotação:** R$ {boleta.valor_cotacao:.3f}\n"
                    f"**Volume:** ${boleta.valor_total:,.2f}")

    print(f">> Mensagem final formatada:\n{texto_boleta}")
    return {
        "boleta_formatada": texto_boleta,
        "messages": [AIMessage(content=texto_boleta)]
    }

# --- 4. Definição do Roteamento ---

def should_proceed(state: TradingState) -> Literal["extract_boleta", "__end__"]:
    """Decide se o fluxo deve prosseguir para a extração."""
    print("--- Roteador ---")
    if state.get("interlocutor_fechamento"):
        print(">> Decisão: Prosseguir para extração.")
        return "extract_boleta"
    else:
        print(">> Decisão: Terminar o fluxo.")
        return "__end__"

# --- 5. Montagem do Grafo ---

def get_workflow(checkpointer=None):
    """Constrói e compila o workflow LangGraph."""
    workflow = StateGraph(TradingState)

    workflow.add_node("gatekeeper", gatekeeper_node)
    workflow.add_node("extractor", extract_boleta_node)
    workflow.add_node("formatter", format_boleta_node)

    workflow.set_entry_point("gatekeeper")
    workflow.add_conditional_edges(
        "gatekeeper",
        should_proceed,
        {"extract_boleta": "extractor", "__end__": END}
    )
    workflow.add_edge("extractor", "formatter")
    workflow.add_edge("formatter", END)

    return workflow.compile(checkpointer=checkpointer)