import logging
import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.runnables.base import Runnable

# Dependências de outras libs Vizu
from vizu_models.knowledge_base_config import RagSearchConfig
from vizu_models.vizu_client_context import VizuClientContext
from vizu_prompt_management.templates import RAG_TOOL_PROMPT
from vizu_rag_factory.reranker import CrossEncoderReranker, LLMReranker
from vizu_rag_factory.retriever import HybridRetriever, SupabaseVectorRetriever

logger = logging.getLogger(__name__)

# Use centralized prompt from vizu_prompt_management
# Convert Jinja2 syntax {{ var }} to LangChain syntax {var}
RAG_PROMPT_TEMPLATE = RAG_TOOL_PROMPT.content.replace("{{ context }}", "{context}").replace(
    "{{ question }}", "{question}"
)


def _format_docs(docs):
    """Helper para formatar os documentos recuperados em uma string com metadados.

    Supports both legacy (similarity-only) and hybrid (combined_score) results.
    """
    logger.debug(f"Formatando {len(docs) if docs else 0} documentos recuperados")
    if not docs:
        return "Nenhum contexto encontrado."
    parts = []
    for doc in docs:
        source = doc.metadata.get("file_name") or doc.metadata.get("source_file", "desconhecido")
        combined = doc.metadata.get("combined_score")
        similarity = doc.metadata.get("similarity", 0)
        scope = doc.metadata.get("scope", "client")

        score_str = (
            f"Relevância: {combined:.0%}"
            if combined is not None
            else f"Relevância: {similarity:.0%}"
        )
        header = f"[Fonte: {source} | {score_str} | Escopo: {scope}]"
        parts.append(f"{header}\n{doc.page_content}")
    formatted = "\n\n---\n\n".join(parts)
    logger.debug(f"Contexto formatado (primeiros 500 chars): {formatted[:500]}...")
    return formatted


def create_rag_runnable(
    contexto: VizuClientContext,
    llm: BaseChatModel,
    document_ids: list[str] | None = None,
) -> Runnable | None:
    """
    Factory agnóstica para criar um Runnable de RAG.

    Uses SupabaseVectorRetriever to search document chunks stored in
    ``vector_db.document_chunks`` via the ``search-documents`` Edge Function.

    Args:
        contexto: Contexto do cliente Vizu (client_id used for RLS)
        llm: Modelo de linguagem para responder (obrigatório)
        document_ids: Optional list of document UUIDs to scope search to specific documents

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

    # Read search config from available_tools — parse through RagSearchConfig
    # for validated defaults instead of manual .get() with repeated fallbacks.
    raw_config: dict | None = None
    if contexto.available_tools:
        raw_config = contexto.available_tools.get("rag_search_config")
    cfg = RagSearchConfig(**(raw_config or {}))

    logger.debug(f"Creating RAG runnable for client {contexto.id}")

    try:
        # --- Retriever: select based on search_mode config ---
        if cfg.search_mode == "semantic":
            # Legacy path — pure cosine similarity
            retriever = SupabaseVectorRetriever(
                supabase_url=os.environ["SUPABASE_URL"],
                supabase_service_key=os.environ["SUPABASE_SERVICE_KEY"],
                client_id=str(contexto.id),
                match_count=cfg.top_k,
                match_threshold=cfg.score_threshold,
                document_ids=document_ids,
            )
        else:
            # Hybrid path — semantic + keyword fusion (Phase 3)
            retriever = HybridRetriever(
                supabase_url=os.environ["SUPABASE_URL"],
                supabase_service_key=os.environ["SUPABASE_SERVICE_KEY"],
                client_id=str(contexto.id),
                match_count=cfg.top_k,
                match_threshold=cfg.score_threshold,
                document_ids=document_ids,
                search_mode=cfg.search_mode,
                fusion_strategy=cfg.fusion_strategy,
                keyword_weight=cfg.keyword_weight,
                vector_weight=cfg.vector_weight,
                scope=cfg.scope,
                categories=cfg.categories,
            )

        logger.debug(
            f"Using {'HybridRetriever' if cfg.search_mode != 'semantic' else 'SupabaseVectorRetriever'} "
            f"(mode={cfg.search_mode}) for client {contexto.id}"
        )

        # --- Optional reranker ---
        reranker = None
        if cfg.rerank:
            if cfg.reranker_type == "cross-encoder":
                reranker = CrossEncoderReranker()
                logger.debug(
                    f"Using CrossEncoderReranker (model={reranker.model_name}) "
                    f"for client {contexto.id}"
                )
            else:
                # Fallback: LLM-based reranker
                reranker = LLMReranker(llm=llm)
                logger.debug(f"Using LLMReranker for client {contexto.id}")

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

                # Optional reranking step
                if reranker and docs:
                    docs = reranker.rerank(question, docs, top_k=cfg.rerank_top_k)
                    logger.debug(f"RAG reranked to {len(docs)} documents")

                formatted_context = _format_docs(docs)

                # FULL CONTEXT DEBUG - Enable with LOG_LEVEL=DEBUG to inspect retrieved RAG context
                logger.debug(f"=== RAG RETRIEVED CONTEXT ({len(docs)} docs) ===")
                logger.debug(formatted_context)
                logger.debug("=== END RAG CONTEXT ===")

                return formatted_context
            except Exception as e:
                logger.error(f"RAG: Erro na busca: {e}")
                return "Erro ao buscar informações."

        async def aretrieve_and_format(input_dict):
            """Busca assíncrona de documentos e formata o contexto."""
            question = input_dict.get("question", "")
            logger.debug(f"RAG async search: '{question[:100]}...'")

            try:
                docs = await retriever.ainvoke(question)
                logger.debug(f"RAG async retrieved {len(docs)} documents")

                # Optional async reranking step
                if reranker and docs:
                    docs = await reranker.arerank(question, docs, top_k=cfg.rerank_top_k)
                    logger.debug(f"RAG async reranked to {len(docs)} documents")

                formatted_context = _format_docs(docs)

                logger.debug(f"=== RAG ASYNC RETRIEVED CONTEXT ({len(docs)} docs) ===")
                logger.debug(formatted_context)
                logger.debug("=== END RAG ASYNC CONTEXT ===")

                return formatted_context
            except Exception as e:
                logger.error(f"RAG: Erro na busca assíncrona: {e}")
                return "Erro ao buscar informações."

        # Build the chain using async-aware retrieval
        # RunnableLambda supports both sync and async callables
        retrieval_runnable = RunnableLambda(retrieve_and_format, afunc=aretrieve_and_format)

        rag_chain = (
            # Adiciona o contexto recuperado mantendo a question original
            RunnablePassthrough.assign(context=retrieval_runnable)
            | prompt
            | llm
            | StrOutputParser()
        )

        logger.debug(f"RAG runnable created for {contexto.id}")
        return rag_chain

    except Exception as e:
        logger.error(f"Falha grave ao criar o runnable RAG para {contexto.id}: {e}")
        return None
