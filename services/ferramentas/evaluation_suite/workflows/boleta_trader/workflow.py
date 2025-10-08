# services/ferramentas/evaluation_suite/workflows/boleta_trader/workflow.py

import time
from typing import TypedDict, Optional, Literal, List, Annotated, Dict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
import difflib

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.chat_models import ChatOllama

# --- 1. Definição do Estado e Modelos (sem alterações) ---
class Boleta(BaseModel):
    vendedor: str
    comprador: str
    valor_cotacao: float
    valor_total: float

class TradingState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    negociacao_em_aberto: bool
    interlocutor_abertura: Optional[str]
    horario_abertura: Optional[float]
    interlocutor_fechamento: Optional[str]
    contexto_relevante: Optional[str]
    boleta_extraida: Optional[Dict]
    boleta_formatada: Optional[str]

# --- 2. Setup (sem alterações) ---
KEYWORDS_GATILHO = ['trava', 'fecha', 'fechado', 'fechamos', 'travo', 'fecho']
JANELA_DE_OPORTUNIDADE_SEGUNDOS = 900.0
PHONE_TO_NAME_MAP = {"+5521999990001": "João", "+5521999990002": "Maria"}
llm = ChatOllama(model="qwen", base_url="http://localhost:11434")

# --- 3. Definição dos Nós (sem alterações) ---
def gatekeeper_node(state: TradingState) -> dict:
    print("--- Nó: Gatekeeper ---")
    last_message = state['messages'][-1]
    sender_phone = last_message.name
    words = last_message.content.lower().split()
    is_trigger = any(difflib.get_close_matches(w, KEYWORDS_GATILHO, n=1, cutoff=0.8) for w in words)
    if not is_trigger: return {"messages": [AIMessage(content="[Status] Mensagem não acionável.")]}
    negociacao_aberta = state.get('negociacao_em_aberto', False)
    horario_atual = time.time()
    if negociacao_aberta:
        interlocutor_1 = state['interlocutor_abertura']
        horario_abertura_negociacao = state['horario_abertura']
        tempo_decorrido = horario_atual - horario_abertura_negociacao
        is_different_interlocutor = sender_phone != interlocutor_1
        is_within_time_window = tempo_decorrido <= JANELA_DE_OPORTUNIDADE_SEGUNDOS
        if is_different_interlocutor and is_within_time_window:
            print(f">> Par formado em {tempo_decorrido:.1f}s. Prosseguindo para extração.")
            all_messages_in_thread = state['messages']
            interlocutores = [interlocutor_1, sender_phone]
            contexto_filtrado = [f"{PHONE_TO_NAME_MAP.get(msg.name, msg.name)}: {msg.content}" for msg in all_messages_in_thread if msg.name in interlocutores]
            return {"negociacao_em_aberto": False, "interlocutor_abertura": None, "horario_abertura": None, "interlocutor_fechamento": sender_phone, "contexto_relevante": "\n".join(contexto_filtrado)}
        elif not is_within_time_window:
            print(">> Janela de oportunidade expirou. Iniciando nova negociação.")
            return {"negociacao_em_aberto": True, "interlocutor_abertura": sender_phone, "horario_abertura": horario_atual}
        else:
            return {"messages": [AIMessage(content="[Status] Gatilho duplicado.")]}
    print(">> Negociação aberta. Aguardando segundo interlocutor.")
    return {"negociacao_em_aberto": True, "interlocutor_abertura": sender_phone, "horario_abertura": horario_atual}

def extract_boleta_node(state: TradingState) -> dict:
    print("--- Nó: Extrator de Boleta ---")
    parser = JsonOutputParser(pydantic_object=Boleta)
    prompt = PromptTemplate(template="Analise a negociação de dólar abaixo. Sua tarefa é extrair os dados e formatar sua resposta como um JSON que corresponda EXATAMENTE ao schema abaixo.\n\nHistórico da Negociação:\n---\n{contexto}\n---\n\nJSON Schema (siga este formato à risca):\n{format_instructions}\n", input_variables=["contexto"], partial_variables={"format_instructions": parser.get_format_instructions()},)
    chain = prompt | llm | parser
    try:
        # Mapeia os números de telefone para nomes no contexto antes de enviar para o LLM
        contexto_com_nomes = state['contexto_relevante']
        for phone, name in PHONE_TO_NAME_MAP.items():
            contexto_com_nomes = contexto_com_nomes.replace(phone, name)

        boleta_dict = chain.invoke({"contexto": contexto_com_nomes})
        print(f">> Boleta extraída com sucesso: {boleta_dict}")
        return {"boleta_extraida": boleta_dict}
    except Exception as e:
        print(f">> ERRO na extração com parser: {e}")
        return {"messages": [AIMessage(f"Falha ao extrair boleta: {e}")]}

def format_boleta_node(state: TradingState) -> dict:
    # Este nó não precisa de alterações.
    print("--- Nó: Formatador de Boleta ---")
    boleta_dict = state.get('boleta_extraida')
    if not boleta_dict:
        return {"messages": [AIMessage(content="[Status] Formatação abortada.")]}
    texto_boleta = (f"✅ **BOLETA DE CONFIRMAÇÃO** ✅\n"
                    f"**Vendedor:** {boleta_dict['vendedor']}\n"
                    f"**Comprador:** {boleta_dict['comprador']}\n"
                    f"**Cotação:** R$ {boleta_dict['valor_cotacao']:.3f}\n"
                    f"**Volume:** ${boleta_dict['valor_total']:,.2f}")
    print(f">> Mensagem final formatada:\n{texto_boleta}")
    return {"boleta_formatada": texto_boleta, "messages": [AIMessage(content=texto_boleta)]}


# --- 4. Roteamento (sem alterações) ---
def should_proceed(state: TradingState) -> Literal["extractor", "__end__"]:
    # Corrigido para "extractor"
    if state.get("interlocutor_fechamento"): return "extractor"
    return "__end__"

# --- 5. Montagem do Grafo (COM ALTERAÇÃO) ---
def get_workflow(checkpointer=None): # <-- Aceita o checkpointer como argumento
    workflow = StateGraph(TradingState)
    workflow.add_node("gatekeeper", gatekeeper_node)
    workflow.add_node("extractor", extract_boleta_node)
    workflow.add_node("formatter", format_boleta_node)
    workflow.set_entry_point("gatekeeper")
    workflow.add_conditional_edges("gatekeeper", should_proceed, {"extractor": "extractor", "__end__": END})
    workflow.add_edge("extractor", "formatter")
    workflow.add_edge("formatter", END)
    # Compila o grafo COM o checkpointer
    return workflow.compile(checkpointer=checkpointer)