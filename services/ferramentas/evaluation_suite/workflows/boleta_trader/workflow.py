# services/ferramentas/evaluation_suite/workflows/boleta_trader/workflow.py

import time
from typing import TypedDict, Optional, Literal, List, Annotated, Dict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
import difflib

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_community.chat_models import ChatOllama

# --- 1. Definição dos Modelos e Estado ---

class DadosNegociacao(BaseModel):
    """Schema para os dados numéricos de uma negociação."""
    valor_cotacao: float = Field(description="A cotação EXATA do dólar acordada (ex: 5.125, 5.145).")
    valor_total: float = Field(description="O volume total em dólares da operação (ex: 5000.0, 20000.0).")

class TradingState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    negociacao_em_aberto: bool
    participante_1_id: Optional[str]
    participante_2_id: Optional[str]
    horario_abertura: Optional[float]
    contexto_relevante: Optional[str]
    dados_extraidos: Optional[Dict]
    boleta_formatada: Optional[str]

# --- 2. Setup ---
KEYWORDS_GATILHO = ['trava', 'fecha', 'fechado', 'fechamos','vendo', 'compro', 'cotaçao', 'travo', 'fecho']
JANELA_DE_OPORTUNIDADE_SEGUNDOS = 900.0
PHONE_TO_NAME_MAP = {
    "interlocutor_1": "João", "interlocutor_2": "Carlos",
    "interlocutor_3": "Maria", "interlocutor_4": "Ana"
}
llm = ChatOllama(model="qwen", temperature=0, base_url="http://localhost:11434", request_timeout=120.0)

# --- 3. Nós do Grafo ---

def gatekeeper_node(state: TradingState) -> dict:
    print("--- Nó: Gatekeeper ---")
    last_message = state['messages'][-1]

    if not isinstance(last_message, HumanMessage): return {"messages": [AIMessage(content="[System] Gatilho ignorado (duplicado/expirado).", name="System")]}

    sender_id = last_message.name
    message_content = last_message.content.lower().strip()
    is_trigger = any(difflib.get_close_matches(w, KEYWORDS_GATILHO, n=1, cutoff=0.8) for w in message_content.split())
    negociacao_aberta = state.get('negociacao_em_aberto', False)

    if not is_trigger:
        return {"boleta_formatada": None} if not negociacao_aberta else {"messages": [AIMessage(content="[System] Gatilho ignorado (duplicado/expirado).", name="System")]}

    if negociacao_aberta:
        participante_1_id = state['participante_1_id']
        tempo_decorrido = time.time() - state['horario_abertura']

        if sender_id != participante_1_id and tempo_decorrido <= JANELA_DE_OPORTUNIDADE_SEGUNDOS:
            print(f">> Par formado entre '{participante_1_id}' e '{sender_id}'.")

            all_messages = state['messages']
            last_system_msg_index = -1
            for i in range(len(all_messages) - 2, -1, -1):
                if isinstance(all_messages[i], AIMessage):
                    last_system_msg_index = i
                    break

            context_slice = all_messages[last_system_msg_index + 1:]
            contexto_formatado = "\n".join(
                f"{PHONE_TO_NAME_MAP.get(msg.name, msg.name)}: {msg.content}"
                for msg in context_slice if isinstance(msg, HumanMessage)
            )

            return { "participante_2_id": sender_id, "contexto_relevante": contexto_formatado }
        else:
            return {"messages": [AIMessage(content="[System] Gatilho ignorado (duplicado/expirado).", name="System")]}
    else: # Abre uma nova negociação
        print(f">> Negociação aberta por '{sender_id}'.")
        return {
            "negociacao_em_aberto": True,
            "participante_1_id": sender_id,
            "horario_abertura": time.time(),
            "boleta_formatada": None
        }

def extract_boleta_node(state: TradingState) -> dict:
    print("--- Nó: Extrator de Boleta ---")
    # REVERSÃO PARA O PARSER EXPLÍCITO, compatível com ChatOllama
    parser = PydanticOutputParser(pydantic_object=DadosNegociacao)

    prompt_template = """Você é um especialista em extração de dados de conversas.
Analise o texto a seguir e extraia os valores para `valor_cotacao` e `valor_total` da negociação mais recente.

{format_instructions}

Siga estas regras estritas:
1.  Foque **APENAS** na negociação mais recente no texto. Ignore todas as negociações anteriores.
2.  Extraia os números com todas as casas decimais.
3.  Sua resposta deve ser **SOMENTE** o objeto JSON.

CONVERSA PARA ANÁLISE:
---
{contexto}
---

JSON:
"""
    prompt = ChatPromptTemplate.from_template(template=prompt_template)
    chain = prompt | llm | parser
    try:
        dados_obj = chain.invoke({
            "contexto": state['contexto_relevante'],
            "format_instructions": parser.get_format_instructions()
        })
        dados_dict = dados_obj.dict()
        print(f">> Dados numéricos extraídos: {dados_dict}")
        return {"dados_extraidos": dados_dict}
    except Exception as e:
        error_message = f"Falha na extração ou validação. Erro: {type(e).__name__}. Detalhes: {e}"
        print(f">> ERRO: {error_message}")
        return {"dados_extraidos": {"error": error_message}}

def format_boleta_node(state: TradingState) -> dict:
    print("--- Nó: Formatador de Boleta ---")
    try:
        dados = state.get('dados_extraidos')
        if not dados or "error" in dados:
            raise ValueError(f"Formatação abortada. Causa: {dados.get('error', 'dados ausentes')}")

        dados_obj = DadosNegociacao(**dados)
        vendedor_id = state['participante_1_id']
        comprador_id = state['participante_2_id']
        vendedor_nome = PHONE_TO_NAME_MAP.get(vendedor_id, vendedor_id)
        comprador_nome = PHONE_TO_NAME_MAP.get(comprador_id, comprador_id)

        texto_boleta = (f"✅ **BOLETA DE CONFIRMAÇÃO** ✅\n"
                        f"**Vendedor:** {vendedor_nome}\n"
                        f"**Comprador:** {comprador_nome}\n"
                        f"**Cotação:** R$ {dados_obj.valor_cotacao:.3f}\n"
                        f"**Volume:** ${dados_obj.valor_total:,.2f}")
        print(f">> Mensagem final formatada:\n{texto_boleta}")

        return {
            "boleta_formatada": texto_boleta,
            "messages": [AIMessage(content=texto_boleta, name="System")],
            "negociacao_em_aberto": False, "participante_1_id": None, "participante_2_id": None,
            "contexto_relevante": None, "dados_extraidos": None, "horario_abertura": None
        }
    except Exception as e:
        error_msg = f"Erro ao formatar boleta. Detalhes: {e}"
        print(f">> ERRO: {error_msg}")
        return {
            "messages": [AIMessage(content=f"[System] {error_msg}", name="System")],
            "negociacao_em_aberto": False, "participante_1_id": None, "participante_2_id": None,
            "contexto_relevante": None, "dados_extraidos": None, "horario_abertura": None,
            "boleta_formatada": None
        }

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