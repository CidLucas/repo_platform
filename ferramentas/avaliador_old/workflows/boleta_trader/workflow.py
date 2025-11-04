# services/ferramentas/evaluation_suite/workflows/boleta_trader/workflow.py

import time
import re
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
    valor_cotacao: float = Field(description="The EXACT agreed-upon dollar quote (e.g., 5.125, 5.4930).")
    valor_total: float = Field(description="The total dollar volume of the operation (e.g., 5000.0, 130000.0).")

class ValidacaoNegociacao(BaseModel):
    """Schema to validate if a trade was completed."""
    negociacao_concluida: bool = Field(description="Set to True if the conversation indicates that a trade for a quote AND volume was 'closed', 'locked', or 'confirmed'. Set to False if the trade is still in progress, is just an inquiry, or is unclear.")
    justificativa: str = Field(description="A detailed description of the findings. If a trade is completed, this *must* summarize the participants, volume, and quote (e.g., 'Ana and Maria closed a deal for 100k USD at 5.4810'). If not, it should explain why.")

class TradingState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    negociacao_em_aberto: bool
    participante_1_id: Optional[str]
    participante_2_id: Optional[str]
    horario_abertura: Optional[float]
    contexto_relevante: Optional[str]

    negociacao_concluida: bool
    dados_validacao: Optional[Dict]

    dados_extraidos: Optional[Dict]
    boleta_formatada: Optional[str]

# --- 2. Setup ---
KEYWORDS_GATILHO = ['trava', 'fecha', 'fechado', 'fechamos', 'travo', 'fecho']
JANELA_DE_OPORTUNIDADE_SEGUNDOS = 900.0
PHONE_TO_NAME_MAP = {
    "interlocutor_1": "João", "interlocutor_2": "Carlos",
    "interlocutor_3": "Maria", "interlocutor_4": "Ana",
    "interlocutor_7": "Maria",
    "interlocutor_6": "Pedro",
}
llm = ChatOllama(
    model="llama3.2",
    temperature=0.3,
    base_url="http://localhost:11434",
    request_timeout=120.0,
    format="json"
)

# Regex para limpar ruído
NOISE_PATTERNS = [
    re.compile(r'<LOCATION>'),
    re.compile(r'\b[a-f0-9]{64}\b')
]

def clean_message_content(content: str) -> str:
    """Filtra ruídos conhecidos das mensagens."""
    clean_content = content
    for pattern in NOISE_PATTERNS:
        clean_content = pattern.sub('', clean_content)
    return clean_content.strip()

# --- 3. Nós do Grafo ---

def gatekeeper_node(state: TradingState) -> dict:
    """
    Nó de entrada (gatekeeper) com lógica refatorada.
    """
    print("--- Node: Gatekeeper (Refactored Logic) ---")
    last_message = state['messages'][-1]
    if not isinstance(last_message, HumanMessage):
        return {"messages": [AIMessage(content="[System] Ignored (not a human msg).", name="System")]}

    sender_id = last_message.name
    message_content = last_message.content.lower().strip()
    is_trigger = any(difflib.get_close_matches(w, KEYWORDS_GATILHO, n=1, cutoff=0.8) for w in message_content.split())

    if is_trigger:
        print(f">> Trigger ACTIVATED by '{sender_id}'.")
        all_messages = state['messages']
        human_messages = [msg for msg in all_messages if isinstance(msg, HumanMessage)]
        context_slice = human_messages[-15:]

        cleaned_messages = []
        for msg in context_slice:
            cleaned_content = clean_message_content(msg.content)
            if cleaned_content:
                cleaned_messages.append(
                    f"{PHONE_TO_NAME_MAP.get(msg.name, msg.name)}: {cleaned_content}"
                )

        contexto_formatado = "\n".join(cleaned_messages)

        print(f">> 10-message context extracted and cleaned for analysis.")

        print("\n--- CLEANED CONTEXT SENT TO LLM ---")
        print(contexto_formatado)
        print("-------------------------------------\n")

        return {
            "negociacao_em_aberto": True,
            "participante_1_id": sender_id,
            "horario_abertura": time.time(),
            "contexto_relevante": contexto_formatado,
            "participante_2_id": None,
            "boleta_formatada": None,
            "dados_extraidos": None,
            "negociacao_concluida": False,
            "dados_validacao": None
        }
    else:
        print(f">> Trigger NOT found in msg from '{sender_id}'.")
        return {
            "messages": [AIMessage(content="[System] Trigger ignored (keyword not found).", name="System")],
            "boleta_formatada": None
        }

# --- NÓ DE VALIDAÇÃO OTIMIZADO ---
def check_negotiation_node(state: TradingState) -> dict:
    """
    Validation node.
    Prompt otimizado para gerar uma 'justificativa' descritiva.
    """
    print("--- Node: Negotiation Validator ---")
    contexto = state.get('contexto_relevante')
    parser = PydanticOutputParser(pydantic_object=ValidacaoNegociacao)

    prompt_template = """
    You are a senior trade analyst.
    You know that the quote of dollars in BRL always begins with '5.' (e.g., 5.125, 5.4930).
    Traders often use 4-digits decimals shorthand (e.g., '4930' means '5.4930').
    You will read a conversation snippet where it may have multiple trades going on.
    Your objective is to determine which is the **LASTEST** trade on negotiation that was actually COMPLETED.

    If a trade is completed:
    1. Set `negociacao_concluida` to `true`.
    2. In `justificativa`, describe the *specific* completed transaction, including the participants, the volume, and the quote.

    If a trade is NOT completed (it's an inquiry, question, or still in progress):
    1. Set `negociacao_concluida` to `false`.
    2. In `justificativa`, explain *why* it's not completed. (e.g., "Ana is only asking for a quote. No deal was confirmed.").

    "Completed" means a 'price' (quote) AND a 'volume' (total_amount) were agreed upon and explicitly confirmed (e.g., "ok", "closed", "lock it", "fecha").
    **CRITICAL RULE:** ALWAYS Focus on the last values negotiated, look for the values that are closer to the bottom of the conversation.

    *** READ THE EXAMPLES BELOW CAREFULLY. ***

    {format_instructions}

    **CRITICAL:** Your response must be *only* the JSON object, starting with '{{' and ending with '}}'. Do not add any other text.

    *** EXAMPLES ***
    ---
    [Example 1: Inquiry]
    "Ana: cotação pfvr?
    Joao: 5.105
    Joao: Quanto?
    Ana: apenas consultando
    Joao: blz"

    {{"negociacao_concluida": false, "justificativa": "This is an inquiry. Ana asks for a quote, Joao respond with a quote 5.105 but she gives up, and say 'apenas consultando' (just checking) and no deal is confirmed."}}
    ---
    [Example 2: Multiple Trades - Focus on last]
    "Jorge: 50k valeu!
    Ana: alguém
    Ana: na mesa?
    Jorge: BRL 548,200.00
    Ana: Cota 100k novamente
    Ana: rapidão
    Pedro: 4810
    Ana: fecha"

    {{"negociacao_concluida": true, "justificativa": "A deal was closed between Ana and Pedro for 100k USD at a quote of 4810 (which implies 5.4810)."}}
    ---
    [Example 3: Ignoring Noise]
   "Pedro: 500.000
    Pedro: <LOCATION>
    Lucas: 50.790
    Lucas: cotação
    Rose: 1s
    Rose: 4710
    Lucas: da pra espremer?
    Rose: 4700
    Lucas: fecha"

    {{"negociacao_concluida": true, "justificativa": "A deal was closed between Lucas and Rose for 50.790 USD at a quote of 4700 (5.4700)."}}
    ---

    Now, analyze the following conversation:

    {contexto}

    """

    prompt = ChatPromptTemplate.from_template(template=prompt_template)
    chain = prompt | llm | parser

    try:
        validacao_obj = chain.invoke({
            "contexto": contexto,
            "format_instructions": parser.get_format_instructions()
        })

        if validacao_obj.negociacao_concluida:
            print(f">> Validation: NEGOTIATION COMPLETED. Justification: {validacao_obj.justificativa}")
            return {
                "negociacao_concluida": True,
                "dados_validacao": validacao_obj.dict() # Salva a justificativa no estado
            }
        else:
            print(f">> Validation: NEGOTIATION NOT COMPLETED. Justification: {validacao_obj.justificativa}")
            return {
                "negociacao_concluida": False,
                "dados_validacao": validacao_obj.dict(),
                "boleta_formatada": None,
                "negociacao_em_aberto": False
            }

    except Exception as e:
        error_message = f"Failed validation (Parser Error). Error: {type(e).__name__}. Details: {e}"
        print(f">> ERROR: {error_message}")
        return {
            "negociacao_concluida": False,
            "dados_validacao": {"error": error_message},
            "boleta_formatada": None,
            "negociacao_em_aberto": False
        }

# --- NÓ EXTRATOR OTIMIZADO (com bugfix e prompts melhores) ---
def extract_boleta_node(state: TradingState) -> dict:
    """
    Extraction node.
    Updated to receive the descriptive 'justificativa' from the validator.
    """
    print("--- Node: Boleta Extractor ---")
    parser = PydanticOutputParser(pydantic_object=DadosNegociacao)

    prompt_template = """You are an expert in data extraction. Analyze the validated trade conversation and extract `valor_cotacao` (the USD quote) and `valor_total` (the USD volume) for the **most recent** completed trade.

    You will be given the conversation (in brazilian portuguese) and a "Validation Guide" from the previous step.
    Check if the info in the "Validation Guide" is the information regarding the last deal made, look for the values that are closer to the bottom of the conversation.as the  tells you *which* trade to extract and what the numbers are.

    {format_instructions}

    Follow these strict rules:
    1.  **CRITICAL RULE 1: Use the Validation Guide.** The guide describes the correct trade (e.g., "deal for 100k USD at 5.4810"). Extract *those* numbers.
    2.  `valor_cotacao`: Is the price for USD unit (e.g., "5.125").
    3.  **4-DIGIT RULE:** If the guide or context mentions a 4-digit number like `4930`, interpret it as `5.4930`. If it mentions `4770`, interpret it as `5.4770`.
    4.  `valor_total`: Is the USD volume (e.g., 100000, 100k (100.000), 100.000).
    5.  **IGNORE BRL:** Ignore BRL (Reais) values like BRL 730.000.
    6. Read the examples below carefully.

    **CRITICAL:** Your response must be *only* the JSON object, starting with '{{' and ending with '}}'.

    ---
    *** EXAMPLES ***
    [Example 1: 4-Digit Rule]
    VALIDATION GUIDE (Use this!):
    "A deal was closed between Henrique and Maria for 130k USD at a quote of 4930 (5.4930)."

    FULL CONVERSATION:
    "Cristina: Depois te mando
    Henrique: 130k
    Ana: Valeu!
    Maria: 4930
    Henrique: fecha"

    {{"valor_cotacao": 5.4930, "valor_total": 130000.0}}
    ---
    [Example 2: Ignoring Old Context Rule]
    VALIDATION GUIDE (Use this!):
    "A deal was confirmed between Claudia and Maria at quote 4985 (5.4985). The volume is 44.176,00 from Claudia's message."

    FULL CONVERSATION:
    "Pedro: Meio morto hoje
    Jorge: Quanto to te devendo?
    Pedro: 100.000
    Claudia: Cota 44.176,00
    Maria: 5.4985
    Claudia: Peraí
    Claudia: Dá pra baixar?
    Maria: 4975
    Claudia: fecha"

    {{"valor_cotacao": 5.4975, "valor_total": 44.176.0}}
    ---
    [Example 3: (last quote and volume values)]
    VALIDATION GUIDE (Use this!):
    "A deal was closed between Ana and Jonas for 100k USD at a quote of 4770 (which implies 5.4770)."

    FULL CONVERSATION:
   " Jonas: 4780
    Ana: fecha
    Jonas: BRL 1,369,500.00 // USDT 250.000
    Ana: cota 100k
    Jonas: 4770
    Ana: fecha "

    {{"valor_cotacao": 5.4770, "valor_total": 100000.0}}
    ---

    Now, analyze the following conversation.

    **VALIDATION GUIDE (Use this!):**
    {justificativa_validacao}

    **FULL CONVERSATION:**
    {contexto}

    """
    prompt = ChatPromptTemplate.from_template(template=prompt_template)
    chain = prompt | llm | parser

    try:
        # Pega a justificativa salva no estado pelo nó anterior
        justificativa = state.get('dados_validacao', {}).get('justificativa', 'No justification provided.')

        dados_obj = chain.invoke({
            "contexto": state['contexto_relevante'],
            "justificativa_validacao": justificativa, # Passa a justificativa para o prompt
            "format_instructions": parser.get_format_instructions()
        })
        dados_dict = dados_obj.dict()
        print(f">> Numeric data extracted: {dados_dict}")
        return {"dados_extraidos": dados_dict}
    except Exception as e:
        error_message = f"Failed extraction (Parser Error). Error: {type(e).__name__}. Details: {e}"
        print(f">> ERROR: {error_message}")
        return {"dados_extraidos": {"error": error_message}}

# --- NÓ FORMATADOR (Sem alterações) ---
def format_boleta_node(state: TradingState) -> dict:
    """
    Formats the final boleta message.
    """
    print("--- Node: Boleta Formatter ---")
    try:
        dados = state.get('dados_extraidos')
        if not dados or "error" in dados:
            raise ValueError(f"Formatting aborted. Cause: {dados.get('error', 'missing data')}")

        dados_obj = DadosNegociacao(**dados)
        trigger_user_id = state.get('participante_1_id')
        trigger_user_name = PHONE_TO_NAME_MAP.get(trigger_user_id, trigger_user_id)

        texto_boleta = (f"✅ **CONFIRMATION TICKET** ✅\n"
                        f"*(Triggered by: {trigger_user_name})*\n"
                        f"**Quote:** R$ {dados_obj.valor_cotacao:.4f}\n"
                        f"**Volume:** ${dados_obj.valor_total:,.2f}")
        print(f">> Final message formatted:\n{texto_boleta}")

        # Reset state
        return {
            "boleta_formatada": texto_boleta,
            "messages": [AIMessage(content=texto_boleta, name="System")],
            "negociacao_em_aberto": False, "participante_1_id": None, "participante_2_id": None,
            "contexto_relevante": None, "dados_extraidos": None, "horario_abertura": None,
            "negociacao_concluida": False, "dados_validacao": None
        }
    except Exception as e:
        error_msg = f"Error formatting boleta. Details: {e}"
        print(f">> ERRO: {error_msg}")
        # Reset state
        return {
            "messages": [AIMessage(content=f"[System] {error_msg}", name="System")],
            "negociacao_em_aberto": False, "participante_1_id": None, "participante_2_id": None,
            "contexto_relevante": None, "dados_extraidos": None, "horario_abertura": None,
            "boleta_formatada": None, "negociacao_concluida": False, "dados_validacao": None
        }

# --- 4. Arestas Condicionais (Sem alterações) ---

def should_proceed_to_validation(state: TradingState) -> Literal["validator", "__end__"]:
    if state.get("contexto_relevante"):
        return "validator"
    else:
        return "__end__"

def should_proceed_to_extraction(state: TradingState) -> Literal["extractor", "__end__"]:
    if state.get("negociacao_concluida", False):
        print(">> Routing: Validation OK. Proceeding to Extractor.")
        return "extractor"
    else:
        print(">> Routing: Validation FAILED. Ending flow.")
        return "__end__"

# --- 5. Construtor do Grafo (Sem alterações) ---

def get_workflow(checkpointer=None):
    workflow = StateGraph(TradingState)

    workflow.add_node("gatekeeper", gatekeeper_node)
    workflow.add_node("validator", check_negotiation_node)
    workflow.add_node("extractor", extract_boleta_node)
    workflow.add_node("formatter", format_boleta_node)

    workflow.set_entry_point("gatekeeper")

    workflow.add_conditional_edges(
        "gatekeeper",
        should_proceed_to_validation,
        {"validator": "validator", "__end__": END}
    )

    workflow.add_conditional_edges(
        "validator",
        should_proceed_to_extraction,
        {"extractor": "extractor", "__end__": END}
    )

    workflow.add_edge("extractor", "formatter")
    workflow.add_edge("formatter", END)

    return workflow.compile(checkpointer=checkpointer)