# services/ferramentas/evaluation_suite/workflows/boleta_trader/workflow.py

import time
from typing import TypedDict, Optional, Literal, List, Annotated, Dict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
import difflib

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.chat_models import ChatOllama

# --- 1. Definição dos Modelos e Estado ---
class DadosNegociacao(BaseModel):
    """Schema para os dados numéricos de uma negociação."""
    valor_cotacao: float = Field(description="A cotação do dólar acordada (ex: 5.145).")
    valor_total: float = Field(description="O volume total em dólares da operação (ex: 20000.0).")

class TradingState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    negociacao_em_aberto: bool
    vendedor_id: Optional[str]
    comprador_id: Optional[str]
    horario_abertura: Optional[float]
    contexto_relevante: Optional[str]
    dados_extraidos: Optional[Dict]
    boleta_formatada: Optional[str]

# --- 2. Setup ---
KEYWORDS_GATILHO = ['trava', 'fecha', 'fechado', 'fechamos', 'travo', 'fecho']
JANELA_DE_OPORTUNIDADE_SEGUNDOS = 900.0
PHONE_TO_NAME_MAP = {
    "+5521999990001": "João", "+5521999990002": "Maria",
    "+5521999990003": "Carlos", "+5521999990004": "Ana"
}
llm = ChatOllama(model="qwen", temperature=0, base_url="http://localhost:11434", request_timeout=120.0)

# --- 3. Definição dos Nós do Grafo ---

def gatekeeper_node(state: TradingState) -> dict:
    # (Este nó, da sua versão, está perfeito. Sem alterações)
    print("--- Nó: Gatekeeper ---")
    last_message = state['messages'][-1]
    if not isinstance(last_message, HumanMessage): return {"messages": [AIMessage(content="[System] Ignorando.", name="System")]}
    sender_phone = last_message.name
    words = last_message.content.lower().strip().split()
    is_trigger = any(difflib.get_close_matches(w, KEYWORDS_GATILHO, n=1, cutoff=0.8) for w in words)
    if not is_trigger: return {"messages": [AIMessage(content="[System] Ignorando (sem gatilho).", name="System")]}
    negociacao_aberta = state.get('negociacao_em_aberto', False)
    horario_atual = time.time()
    if negociacao_aberta:
        vendedor_id = state['vendedor_id']
        tempo_decorrido = horario_atual - state['horario_abertura']
        if sender_phone != vendedor_id and tempo_decorrido <= JANELA_DE_OPORTUNIDADE_SEGUNDOS:
            print(f">> Par formado. Enviando para extração.")
            contexto_filtrado = "\n".join([f"{PHONE_TO_NAME_MAP.get(msg.name, msg.name)}: {msg.content}" for msg in state['messages'] if isinstance(msg, HumanMessage)])
            return {"negociacao_em_aberto": False, "comprador_id": sender_phone, "contexto_relevante": contexto_filtrado}
        else: return {"messages": [AIMessage(content="[System] Gatilho ignorado (duplicado/expirado).", name="System")]}
    else:
        print(">> Negociação aberta.")
        return {"negociacao_em_aberto": True, "vendedor_id": sender_phone, "horario_abertura": horario_atual}

def extract_boleta_node(state: TradingState) -> dict:
    # (Este nó, da sua versão, está perfeito. Sem alterações)
    print("--- Nó: Extrator de Boleta ---")
    parser = JsonOutputParser(pydantic_object=DadosNegociacao)
    prompt_template = """Você é um boletador de um grupo de whatsapp que transaciona dólares.
Sua tarefa é analisar a conversa e extrair os dados de valor_total e valor_cotaçao e retorná-los EXATAMENTE conforme o JSON Schema.
Sua resposta DEVE conter APENAS o objeto JSON e NADA MAIS.
JSON Schema: {format_instructions}
Texto:
---
{contexto}
---
"""
    prompt = ChatPromptTemplate.from_template(template=prompt_template)
    chain = prompt | llm | parser
    try:
        contexto = state['contexto_relevante']
        dados_dict = chain.invoke({"contexto": contexto, "format_instructions": parser.get_format_instructions()})
        print(f">> Dados numéricos extraídos: {dados_dict}")
        return {"dados_extraidos": dados_dict, "contexto_relevante": None}
    except Exception as e:
        raw_output = getattr(e, 'llm_output', str(e))
        error_message = f"Falha na extração. Erro: {type(e).__name__}. Saída do LLM: {raw_output}"
        print(f">> ERRO: {error_message}")
        return {"dados_extraidos": {"error": error_message}, "contexto_relevante": None}

def format_boleta_node(state: TradingState) -> dict:
    """Nó de formatação determinístico. Monta a boleta final sem usar LLM."""
    print("--- Nó: Formatador de Boleta ---")
    dados = state.get('dados_extraidos')
    if not dados or "error" in dados:
        print(">> Formatação abortada: Extração falhou.")
        return {"messages": [AIMessage(content="[System] Formatação abortada.", name="System")]}
    try:
        # AJUSTE FINAL: Torna a busca de nomes robusta, ignorando o '+'
        vendedor_id_clean = state['vendedor_id'].replace('+', '')
        comprador_id_clean = state['comprador_id'].replace('+', '')
        vendedor_nome = next((name for key, name in PHONE_TO_NAME_MAP.items() if vendedor_id_clean in key), state['vendedor_id'])
        comprador_nome = next((name for key, name in PHONE_TO_NAME_MAP.items() if comprador_id_clean in key), state['comprador_id'])

        dados_obj = DadosNegociacao(**dados)
        texto_boleta = (f"✅ **BOLETA DE CONFIRMAÇÃO** ✅\n"
                        f"**Vendedor:** {vendedor_nome}\n"
                        f"**Comprador:** {comprador_nome}\n"
                        f"**Cotação:** R$ {dados_obj.valor_cotacao:.3f}\n"
                        f"**Volume:** ${dados_obj.valor_total:,.2f}")
        print(f">> Mensagem final formatada:\n{texto_boleta}")
        return {"boleta_formatada": texto_boleta, "messages": [AIMessage(content=texto_boleta, name="System")], "vendedor_id": None, "comprador_id": None}
    except Exception as e:
        error_msg = f"Erro ao formatar boleta. Dados inválidos. Detalhes: {e}"
        print(f">> ERRO: {error_msg}")
        return {"messages": [AIMessage(content=f"[System] {error_msg}", name="System")]}

# --- 4. Arestas e 5. Montagem (sem alterações) ---
def should_proceed_to_extraction(state: TradingState) -> Literal["extractor", "__end__"]:
    return "extractor" if state.get("contexto_relevante") else "__end__"

def get_workflow(checkpointer=None):
    workflow = StateGraph(TradingState)
    workflow.add_node("gatekeeper", gatekeeper_node)
    workflow.add_node("extractor", extract_boleta_node)
    workflow.add_node("formatter", format_boleta_node)
    workflow.set_entry_point("gatekeeper")
    workflow.add_conditional_edges("gatekeeper", should_proceed_to_extraction, {"extractor": "extractor", "__end__": END})
    workflow.add_edge("extractor", "formatter")
    workflow.add_edge("formatter", END)
    return workflow.compile(checkpointer=checkpointer)