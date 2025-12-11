# ferramentas/evaluation_suite/workflows/boleta_trader/workflow.py
"""
Boleta Trader Workflow - LangGraph pipeline for extracting trading tickets.

This workflow processes WhatsApp trading conversations and extracts:
- Trade confirmations (boletas)
- Quote values (cotação)
- Volume amounts

Graph Flow:
  gatekeeper -> validator -> extractor -> formatter -> END
"""

import difflib
import os
import re
import time
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

# --- 1. Schema Definitions ---

class DadosNegociacao(BaseModel):
    """Schema for extracted trade data."""
    valor_cotacao: float = Field(
        description="The EXACT agreed-upon dollar quote (e.g., 5.125, 5.4930)."
    )
    valor_total: float = Field(
        description="The total dollar volume of the operation (e.g., 5000.0, 130000.0)."
    )


class ValidacaoNegociacao(BaseModel):
    """Schema to validate if a trade was completed."""
    negociacao_concluida: bool = Field(
        description="True if conversation indicates a trade was closed/locked/confirmed."
    )
    justificativa: str = Field(
        description="Detailed description of findings with participants, volume, and quote."
    )


class TradingState(TypedDict):
    """State schema for the trading workflow."""
    messages: Annotated[list[BaseMessage], add_messages]
    negociacao_em_aberto: bool
    participante_1_id: str | None
    participante_2_id: str | None
    horario_abertura: float | None
    contexto_relevante: str | None
    negociacao_concluida: bool
    dados_validacao: dict | None
    dados_extraidos: dict | None
    boleta_formatada: str | None


# --- 2. Configuration ---

KEYWORDS_GATILHO = ['trava', 'fecha', 'fechado', 'fechamos', 'travo', 'fecho']
JANELA_DE_OPORTUNIDADE_SEGUNDOS = 900.0

# Mapping from anonymized interlocutors to display names
PHONE_TO_NAME_MAP = {
    "interlocutor_1": "João",
    "interlocutor_2": "Carlos",
    "interlocutor_3": "Maria",
    "interlocutor_4": "Ana",
    "interlocutor_5": "Lucas",
    "interlocutor_6": "Pedro",
    "interlocutor_7": "Rose",
    "interlocutor_8": "Bruno",
}

# LLM Configuration - uses Ollama (configurable via env)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

llm = ChatOllama(
    model=OLLAMA_MODEL,
    temperature=0.3,
    base_url=OLLAMA_BASE_URL,
    request_timeout=120.0,
    format="json"
)

# Regex patterns for noise removal
NOISE_PATTERNS = [
    re.compile(r'<LOCATION>'),
    re.compile(r'<PERSON>'),
    re.compile(r'<ORGANIZATION>'),
    re.compile(r'<PHONE_NUMBER>'),
    re.compile(r'<MEDICAL_LICENSE>'),
    re.compile(r'\b[a-f0-9]{64}\b'),  # Transaction hashes
]


def clean_message_content(content: str) -> str:
    """Remove known noise patterns from message content."""
    clean_content = content
    for pattern in NOISE_PATTERNS:
        clean_content = pattern.sub('', clean_content)
    return clean_content.strip()


# --- 3. Graph Nodes ---

def gatekeeper_node(state: TradingState) -> dict:
    """
    Entry node that detects trigger keywords and extracts context.

    Activates the pipeline when trigger words like "fecha" are detected.
    """
    print("--- Node: Gatekeeper ---")
    last_message = state['messages'][-1]

    if not isinstance(last_message, HumanMessage):
        return {
            "messages": [AIMessage(content="[System] Ignored (not a human msg).", name="System")]
        }

    sender_id = last_message.name
    message_content = last_message.content.lower().strip()

    # Check for trigger keywords with fuzzy matching
    is_trigger = any(
        difflib.get_close_matches(w, KEYWORDS_GATILHO, n=1, cutoff=0.8)
        for w in message_content.split()
    )

    if is_trigger:
        print(f">> Trigger ACTIVATED by '{sender_id}'.")

        # Extract context from recent messages
        all_messages = state['messages']
        human_messages = [msg for msg in all_messages if isinstance(msg, HumanMessage)]
        context_slice = human_messages[-15:]

        cleaned_messages = []
        for msg in context_slice:
            cleaned_content = clean_message_content(msg.content)
            if cleaned_content:
                display_name = PHONE_TO_NAME_MAP.get(msg.name, msg.name)
                cleaned_messages.append(f"{display_name}: {cleaned_content}")

        contexto_formatado = "\n".join(cleaned_messages)
        print(f">> Context extracted ({len(context_slice)} messages)")

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
            "messages": [AIMessage(content="[System] Trigger ignored.", name="System")],
            "boleta_formatada": None
        }


def check_negotiation_node(state: TradingState) -> dict:
    """
    Validation node that determines if a trade was completed.

    Uses LLM to analyze conversation context and determine if a deal was closed.
    """
    print("--- Node: Negotiation Validator ---")
    contexto = state.get('contexto_relevante')
    parser = PydanticOutputParser(pydantic_object=ValidacaoNegociacao)

    prompt_template = """
    You are a senior trade analyst.
    You know that the quote of dollars in BRL always begins with '5.' (e.g., 5.125, 5.4930).
    Traders often use 4-digits decimals shorthand (e.g., '4930' means '5.4930').
    You will read a conversation snippet where it may have multiple trades going on.
    Your objective is to determine which is the **LATEST** trade on negotiation that was actually COMPLETED.

    If a trade is completed:
    1. Set `negociacao_concluida` to `true`.
    2. In `justificativa`, describe the *specific* completed transaction, including the participants, the volume, and the quote.

    If a trade is NOT completed (it's an inquiry, question, or still in progress):
    1. Set `negociacao_concluida` to `false`.
    2. In `justificativa`, explain *why* it's not completed.

    "Completed" means a 'price' (quote) AND a 'volume' (total_amount) were agreed upon and explicitly confirmed (e.g., "ok", "closed", "lock it", "fecha").
    **CRITICAL RULE:** ALWAYS Focus on the last values negotiated, look for the values that are closer to the bottom of the conversation.

    {format_instructions}

    **CRITICAL:** Your response must be *only* the JSON object, starting with '{{' and ending with '}}'.

    *** EXAMPLES ***
    ---
    [Example 1: Inquiry - NOT completed]
    "Ana: cotação pfvr?
    Joao: 5.105
    Joao: Quanto?
    Ana: apenas consultando
    Joao: blz"

    {{"negociacao_concluida": false, "justificativa": "This is an inquiry. Ana asks for a quote but says 'apenas consultando' (just checking) and no deal is confirmed."}}
    ---
    [Example 2: Multiple Trades - Focus on last]
    "Jorge: 50k valeu!
    Ana: alguém na mesa?
    Jorge: BRL 548,200.00
    Ana: Cota 100k novamente
    Pedro: 4810
    Ana: fecha"

    {{"negociacao_concluida": true, "justificativa": "A deal was closed between Ana and Pedro for 100k USD at a quote of 4810 (which implies 5.4810)."}}
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
            print(f">> Validation: COMPLETED. {validacao_obj.justificativa}")
            return {
                "negociacao_concluida": True,
                "dados_validacao": validacao_obj.dict()
            }
        else:
            print(f">> Validation: NOT COMPLETED. {validacao_obj.justificativa}")
            return {
                "negociacao_concluida": False,
                "dados_validacao": validacao_obj.dict(),
                "boleta_formatada": None,
                "negociacao_em_aberto": False
            }

    except Exception as e:
        error_message = f"Validation failed: {type(e).__name__}: {e}"
        print(f">> ERROR: {error_message}")
        return {
            "negociacao_concluida": False,
            "dados_validacao": {"error": error_message},
            "boleta_formatada": None,
            "negociacao_em_aberto": False
        }


def extract_boleta_node(state: TradingState) -> dict:
    """
    Extraction node that pulls numeric data from validated trades.

    Extracts valor_cotacao (quote) and valor_total (volume) from conversation.
    """
    print("--- Node: Boleta Extractor ---")
    parser = PydanticOutputParser(pydantic_object=DadosNegociacao)

    prompt_template = """You are an expert in data extraction. Analyze the validated trade conversation and extract `valor_cotacao` (the USD quote) and `valor_total` (the USD volume) for the **most recent** completed trade.

    {format_instructions}

    Follow these strict rules:
    1.  **Use the Validation Guide.** The guide describes the correct trade. Extract *those* numbers.
    2.  `valor_cotacao`: Is the price for USD unit (e.g., "5.125").
    3.  **4-DIGIT RULE:** If the context mentions a 4-digit number like `4930`, interpret it as `5.4930`.
    4.  `valor_total`: Is the USD volume (e.g., 100000, 100k means 100000).
    5.  **IGNORE BRL:** Ignore BRL (Reais) values like BRL 730.000.

    **CRITICAL:** Your response must be *only* the JSON object.

    **VALIDATION GUIDE:**
    {justificativa_validacao}

    **FULL CONVERSATION:**
    {contexto}
    """

    prompt = ChatPromptTemplate.from_template(template=prompt_template)
    chain = prompt | llm | parser

    try:
        justificativa = state.get('dados_validacao', {}).get('justificativa', 'No justification provided.')

        dados_obj = chain.invoke({
            "contexto": state['contexto_relevante'],
            "justificativa_validacao": justificativa,
            "format_instructions": parser.get_format_instructions()
        })

        dados_dict = dados_obj.dict()
        print(f">> Extracted: {dados_dict}")
        return {"dados_extraidos": dados_dict}

    except Exception as e:
        error_message = f"Extraction failed: {type(e).__name__}: {e}"
        print(f">> ERROR: {error_message}")
        return {"dados_extraidos": {"error": error_message}}


def format_boleta_node(state: TradingState) -> dict:
    """
    Formatter node that creates the final boleta message.
    """
    print("--- Node: Boleta Formatter ---")
    try:
        dados = state.get('dados_extraidos')
        if not dados or "error" in dados:
            raise ValueError(f"Formatting aborted: {dados.get('error', 'missing data')}")

        dados_obj = DadosNegociacao(**dados)
        trigger_user_id = state.get('participante_1_id')
        trigger_user_name = PHONE_TO_NAME_MAP.get(trigger_user_id, trigger_user_id)

        texto_boleta = (
            f"✅ **CONFIRMATION TICKET** ✅\n"
            f"*(Triggered by: {trigger_user_name})*\n"
            f"**Quote:** R$ {dados_obj.valor_cotacao:.4f}\n"
            f"**Volume:** ${dados_obj.valor_total:,.2f}"
        )
        print(f">> Boleta formatted:\n{texto_boleta}")

        return {
            "boleta_formatada": texto_boleta,
            "messages": [AIMessage(content=texto_boleta, name="System")],
            "negociacao_em_aberto": False,
            "participante_1_id": None,
            "participante_2_id": None,
            "contexto_relevante": None,
            "dados_extraidos": None,
            "horario_abertura": None,
            "negociacao_concluida": False,
            "dados_validacao": None
        }

    except Exception as e:
        error_msg = f"Formatting error: {e}"
        print(f">> ERROR: {error_msg}")
        return {
            "messages": [AIMessage(content=f"[System] {error_msg}", name="System")],
            "negociacao_em_aberto": False,
            "participante_1_id": None,
            "participante_2_id": None,
            "contexto_relevante": None,
            "dados_extraidos": None,
            "horario_abertura": None,
            "boleta_formatada": None,
            "negociacao_concluida": False,
            "dados_validacao": None
        }


# --- 4. Conditional Edges ---

def should_proceed_to_validation(state: TradingState) -> Literal["validator", "__end__"]:
    """Route to validator if context was extracted."""
    if state.get("contexto_relevante"):
        return "validator"
    return "__end__"


def should_proceed_to_extraction(state: TradingState) -> Literal["extractor", "__end__"]:
    """Route to extractor if trade was validated as completed."""
    if state.get("negociacao_concluida", False):
        print(">> Routing: Validation OK -> Extractor")
        return "extractor"
    print(">> Routing: Validation Failed -> END")
    return "__end__"


# --- 5. Graph Builder ---

def get_workflow(checkpointer=None):
    """
    Build and compile the trading workflow graph.

    Args:
        checkpointer: Optional LangGraph checkpointer for state persistence

    Returns:
        Compiled LangGraph workflow
    """
    workflow = StateGraph(TradingState)

    # Add nodes
    workflow.add_node("gatekeeper", gatekeeper_node)
    workflow.add_node("validator", check_negotiation_node)
    workflow.add_node("extractor", extract_boleta_node)
    workflow.add_node("formatter", format_boleta_node)

    # Set entry point
    workflow.set_entry_point("gatekeeper")

    # Add conditional edges
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

    # Add direct edges
    workflow.add_edge("extractor", "formatter")
    workflow.add_edge("formatter", END)

    return workflow.compile(checkpointer=checkpointer)
