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
from vizu_prompt_management import build_prompt
from vizu_rag_factory.diversity import MMRDiversifier
from vizu_rag_factory.query_preprocessor import QueryPreprocessor
from vizu_rag_factory.reranker import CohereReranker, CrossEncoderReranker, LLMReranker
from vizu_rag_factory.retriever import HybridRetriever, SupabaseVectorRetriever

logger = logging.getLogger(__name__)


def _get_display_score(doc) -> float:
    """Extract the best available relevance score for display.

    Priority: rerank_score (Cohere 0-1) > combined_score (RRF) > similarity (cosine).
    Mirrors ``diversity._get_score()`` so the LLM sees meaningful percentages.
    """
    rerank = doc.metadata.get("rerank_score")
    if rerank is not None:
        return max(0.0, min(1.0, float(rerank)))

    combined = doc.metadata.get("combined_score")
    if combined is not None:
        return float(combined)

    return float(doc.metadata.get("similarity", 0.0))


def _format_docs(docs):
    """Helper para formatar os documentos recuperados em uma string com metadados.

    Supports legacy (similarity-only), hybrid (combined_score), and reranked
    (rerank_score) results.  Display score priority follows
    ``rerank_score > combined_score > similarity`` so the LLM sees a meaningful
    relevance percentage (e.g. 85 %) instead of a tiny RRF number (e.g. 2 %).
    """
    logger.debug(f"Formatando {len(docs) if docs else 0} documentos recuperados")
    if not docs:
        return "Nenhum contexto encontrado."
    parts = []
    for doc in docs:
        source = doc.metadata.get("file_name") or doc.metadata.get("source_file", "desconhecido")
        scope = doc.metadata.get("scope", "client")
        display_score = _get_display_score(doc)

        score_str = f"Relevância: {display_score:.0%}"
        header = f"[Fonte: {source} | {score_str} | Escopo: {scope}]"
        parts.append(f"{header}\n{doc.page_content}")
    formatted = "\n\n---\n\n".join(parts)
    logger.debug(f"Contexto formatado (primeiros 500 chars): {formatted[:500]}...")
    return formatted


async def create_rag_runnable(
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
        # --- Load RAG prompt from Langfuse (with builtin fallback) ---
        # Pass LangChain placeholders as variable values so Jinja2 {{var}} → {var}
        rag_prompt_template = await build_prompt(
            name="tool/rag-query",
            variables={"context": "{context}", "question": "{question}"},
        )

        # --- Pool size: fetch more candidates for reranking + diversity ---
        pool_size = int(cfg.top_k * cfg.retrieval_pool_multiplier)

        # --- Retriever: select based on search_mode config ---
        if cfg.search_mode == "semantic":
            # Legacy path — pure cosine similarity
            retriever = SupabaseVectorRetriever(
                supabase_url=os.environ["SUPABASE_URL"],
                supabase_service_key=os.environ["SUPABASE_SERVICE_KEY"],
                client_id=str(contexto.id),
                match_count=pool_size,
                match_threshold=cfg.score_threshold,
                document_ids=document_ids,
            )
        else:
            # Hybrid path — semantic + keyword fusion (Phase 3)
            retriever = HybridRetriever(
                supabase_url=os.environ["SUPABASE_URL"],
                supabase_service_key=os.environ["SUPABASE_SERVICE_KEY"],
                client_id=str(contexto.id),
                match_count=pool_size,
                match_threshold=cfg.score_threshold,
                document_ids=document_ids,
                search_mode=cfg.search_mode,
                fusion_strategy=cfg.fusion_strategy,
                keyword_weight=cfg.keyword_weight,
                vector_weight=cfg.vector_weight,
                scope=cfg.scope,
                categories=cfg.categories,
                themes=cfg.themes,
            )

        logger.debug(
            f"Using {'HybridRetriever' if cfg.search_mode != 'semantic' else 'SupabaseVectorRetriever'} "
            f"(mode={cfg.search_mode}, pool={pool_size}) for client {contexto.id}"
        )

        # --- Optional reranker ---
        reranker = None
        if cfg.rerank:
            if cfg.reranker_type == "cohere":
                reranker = CohereReranker()
                logger.debug(
                    f"Using CohereReranker (model={reranker.model}) for client {contexto.id}"
                )
            elif cfg.reranker_type == "cross-encoder":
                reranker = CrossEncoderReranker()
                logger.debug(
                    f"Using CrossEncoderReranker (model={reranker.model_name}) "
                    f"for client {contexto.id}"
                )
            else:
                # Fallback: LLM-based reranker
                rerank_prompt_text = await build_prompt(
                    name="rag/rerank",
                    variables={"question": "{question}", "passage": "{passage}"},
                )
                reranker = LLMReranker(llm=llm, rerank_prompt=rerank_prompt_text)
                logger.debug(f"Using LLMReranker for client {contexto.id}")

        # --- Optional query preprocessor (Phase 3 — RAG Overhaul) ---
        preprocessor: QueryPreprocessor | None = None
        if cfg.query_preprocessing:
            from vizu_llm_service.client import ModelTier, get_model

            try:
                preprocessor_prompt = await build_prompt(
                    name="tool/rag-query-rewrite",
                    variables={},
                )
                fast_llm = get_model(tier=ModelTier.FAST)
                preprocessor = QueryPreprocessor(llm=fast_llm, system_prompt=preprocessor_prompt)
                logger.debug(f"Using QueryPreprocessor (FAST tier) for client {contexto.id}")
            except Exception:
                logger.warning(
                    f"Failed to create QueryPreprocessor for client {contexto.id} — "
                    "queries will not be preprocessed",
                    exc_info=True,
                )

        # --- MMR diversity selector ---
        diversifier = MMRDiversifier()

        # --- Criação da Cadeia (Runnable) ---
        prompt = ChatPromptTemplate.from_template(rag_prompt_template)

        # O chain recebe {"question": "..."} e:
        # 1. Extrai a pergunta
        # 2. Busca documentos relevantes no Supabase vector_db
        # 3. Formata o contexto e gera a resposta

        def retrieve_and_format(input_dict):
            """Preprocess → retrieve → rerank → diversify → format."""
            question = input_dict.get("question", "")
            logger.debug(f"RAG search: '{question[:100]}...'")

            try:
                # 0. Query preprocessing — rewrite for better retrieval
                if preprocessor:
                    question = preprocessor.rewrite(question)
                    logger.debug(f"RAG preprocessed query: '{question[:100]}...'")

                # 1. Retrieve expanded candidate pool
                docs = retriever.invoke(question)
                logger.debug(f"RAG retrieved {len(docs)} candidates (pool)")

                # 2. Rerank — re-score by relevance, keep top rerank_top_k
                if reranker and docs:
                    docs = reranker.rerank(question, docs, top_k=cfg.rerank_top_k)
                    logger.debug(f"RAG reranked to {len(docs)} documents")

                # 3. MMR diversity — select final top_k balancing relevance + novelty
                if docs and len(docs) > cfg.top_k:
                    docs = diversifier.select(docs, top_k=cfg.top_k, lambda_=cfg.diversity_lambda)
                    logger.debug(f"RAG diversified to {len(docs)} documents")

                # Score diagnostics — log all score dimensions for top-3 docs
                for i, d in enumerate(docs[:3]):
                    logger.debug(
                        f"RAG doc[{i}] scores: "
                        f"rerank={d.metadata.get('rerank_score')}, "
                        f"combined={d.metadata.get('combined_score')}, "
                        f"similarity={d.metadata.get('similarity')}, "
                        f"display={_get_display_score(d):.4f}, "
                        f"source={d.metadata.get('file_name', '?')}"
                    )

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
            """Async preprocess → retrieve → rerank → diversify → format."""
            question = input_dict.get("question", "")
            logger.debug(f"RAG async search: '{question[:100]}...'")

            try:
                # 0. Query preprocessing — rewrite for better retrieval
                if preprocessor:
                    question = await preprocessor.arewrite(question)
                    logger.debug(f"RAG async preprocessed query: '{question[:100]}...'")

                # 1. Retrieve expanded candidate pool
                docs = await retriever.ainvoke(question)
                logger.debug(f"RAG async retrieved {len(docs)} candidates (pool)")

                # 2. Rerank — re-score by relevance, keep top rerank_top_k
                if reranker and docs:
                    docs = await reranker.arerank(question, docs, top_k=cfg.rerank_top_k)
                    logger.debug(f"RAG async reranked to {len(docs)} documents")

                # 3. MMR diversity — select final top_k balancing relevance + novelty
                if docs and len(docs) > cfg.top_k:
                    docs = diversifier.select(docs, top_k=cfg.top_k, lambda_=cfg.diversity_lambda)
                    logger.debug(f"RAG async diversified to {len(docs)} documents")

                # Score diagnostics — log all score dimensions for top-3 docs
                for i, d in enumerate(docs[:3]):
                    logger.debug(
                        f"RAG doc[{i}] scores: "
                        f"rerank={d.metadata.get('rerank_score')}, "
                        f"combined={d.metadata.get('combined_score')}, "
                        f"similarity={d.metadata.get('similarity')}, "
                        f"display={_get_display_score(d):.4f}, "
                        f"source={d.metadata.get('file_name', '?')}"
                    )

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
