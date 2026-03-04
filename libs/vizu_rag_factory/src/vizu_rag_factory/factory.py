import logging
import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.runnables.base import Runnable

# Dependências de outras libs Vizu
from vizu_models.vizu_client_context import VizuClientContext
from vizu_prompt_management.templates import RAG_TOOL_PROMPT
from vizu_rag_factory.retriever import SupabaseVectorRetriever

logger = logging.getLogger(__name__)

# Use centralized prompt from vizu_prompt_management
# Convert Jinja2 syntax {{ var }} to LangChain syntax {var}
RAG_PROMPT_TEMPLATE = RAG_TOOL_PROMPT.content.replace("{{ context }}", "{context}").replace(
    "{{ question }}", "{question}"
)


def _format_docs(docs):
    """Helper para formatar os documentos recuperados em uma string."""
    logger.debug(f"Formatando {len(docs) if docs else 0} documentos recuperados")
    if not docs:
        return "Nenhum contexto encontrado."
    formatted = "\n\n---\n\n".join([d.page_content for d in docs])
    logger.debug(f"Contexto formatado (primeiros 500 chars): {formatted[:500]}...")
    return formatted


def create_rag_runnable(
    contexto: VizuClientContext,
    llm: BaseChatModel,
) -> Runnable | None:
    """
    Factory agnóstica para criar um Runnable de RAG.

    Uses SupabaseVectorRetriever to search document chunks stored in
    ``vector_db.document_chunks`` via the ``search-documents`` Edge Function.

    Args:
        contexto: Contexto do cliente Vizu (client_id used for RLS)
        llm: Modelo de linguagem para responder (obrigatório)

    Returns:
        Runnable configurado ou None se não for possível criar

    Raises:
        ValueError: Se llm for None
    """

    # Validação do LLM (obrigatório)
    if llm is None:
        logger.error(
            f"LLM não fornecido para create_rag_runnable do cliente {contexto.id}. "
            "Utilize get_model() do vizu_llm_service para obter um LLM."
        )
        raise ValueError("llm é obrigatório para create_rag_runnable")

    enabled = getattr(contexto, "enabled_tools", []) or []
    if "executar_rag_cliente" not in enabled:
        return None

    # Read search config from available_tools (top_k, score_threshold)
    search_config: dict | None = None
    if contexto.available_tools:
        search_config = contexto.available_tools.get("rag_search_config")

    logger.debug(f"Creating RAG runnable for client {contexto.id}")

    try:
        # --- Retriever: Supabase vector_db via Edge Function ---
        retriever = SupabaseVectorRetriever(
            supabase_url=os.environ["SUPABASE_URL"],
            supabase_service_key=os.environ["SUPABASE_SERVICE_KEY"],
            client_id=str(contexto.id),
            match_count=search_config.get("top_k", 5) if search_config else 5,
            match_threshold=(search_config.get("score_threshold", 0.5) if search_config else 0.5),
        )

        # --- Criação da Cadeia (Runnable) ---
        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

        # O chain recebe {"question": "..."} e:
        # 1. Extrai a pergunta
        # 2. Busca documentos relevantes no Supabase vector_db
        # 3. Formata o contexto e gera a resposta

        def retrieve_and_format(input_dict):
            """Busca documentos e formata o contexto."""
            question = input_dict.get("question", "")
            logger.debug(f"RAG search: '{question[:100]}...'")

            try:
                docs = retriever.invoke(question)
                logger.debug(f"RAG retrieved {len(docs)} documents")
                formatted_context = _format_docs(docs)

                # FULL CONTEXT DEBUG - Enable with LOG_LEVEL=DEBUG to inspect retrieved RAG context
                logger.debug(f"=== RAG RETRIEVED CONTEXT ({len(docs)} docs) ===")
                logger.debug(formatted_context)
                logger.debug("=== END RAG CONTEXT ===")

                return formatted_context
            except Exception as e:
                logger.error(f"RAG: Erro na busca: {e}")
                return "Erro ao buscar informações."

        rag_chain = (
            # Adiciona o contexto recuperado mantendo a question original
            RunnablePassthrough.assign(context=RunnableLambda(retrieve_and_format))
            | prompt
            | llm
            | StrOutputParser()
        )

        logger.debug(f"RAG runnable created for {contexto.id}")
        return rag_chain

    except Exception as e:
        logger.error(f"Falha grave ao criar o runnable RAG para {contexto.id}: {e}")
        return None
