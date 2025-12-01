import logging
from typing import Optional
from operator import itemgetter

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# Dependências de outras libs Vizu
from vizu_models.vizu_client_context import VizuClientContext
from vizu_qdrant_client import get_qdrant_client  # Usa o singleton
from vizu_llm_service.client import get_embedding_model


logger = logging.getLogger(__name__)

# Template de prompt padrão para RAG
RAG_PROMPT_TEMPLATE = """
Você é um assistente da Vizu. Use os seguintes trechos de contexto para responder à pergunta.
O contexto é soberano. Se você não sabe a resposta com base no contexto,
apenas diga que não sabe. Não tente inventar uma resposta.

CONTEXTO:
{context}

---

PERGUNTA:
{question}

RESPOSTA:
"""

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
) -> Optional[Runnable]:
    """
    Factory agnóstica para criar um Runnable de RAG.

    Args:
        contexto: Contexto do cliente Vizu com collection_rag
        llm: Modelo de linguagem para responder (obrigatório)

    Returns:
        Runnable configurado ou None se não for possível criar

    Raises:
        ValueError: Se llm for None
    """

    # Validação do LLM (obrigatório)
    if llm is None:
        logger.error(f"LLM não fornecido para create_rag_runnable do cliente {contexto.id}. "
                     "Utilize get_model() do vizu_llm_service para obter um LLM.")
        raise ValueError("llm é obrigatório para create_rag_runnable")

    if not contexto.ferramenta_rag_habilitada:
        # ... (logging)
        return None

    # Usa o collection_rag definido no contexto do cliente para garantir isolamento
    # Se não estiver definido, usa um fallback baseado no ID do cliente
    collection_name = contexto.collection_rag or str(contexto.id)
    logger.info(f"Criando RAG runnable para cliente {contexto.id} com coleção: {collection_name}...")

    try:
        # --- 2. Configuração do Retriever ---

        # Obtém o modelo de embedding da service lib
        embedding_model = get_embedding_model()

        # Usa o cliente singleton do Qdrant
        qdrant_client = get_qdrant_client()

        # Verifica se a coleção existe
        if not qdrant_client.collection_exists(collection_name):
            logger.warning(f"Coleção '{collection_name}' não existe no Qdrant para cliente {contexto.id}")
            # Ainda assim tenta criar o retriever (pode ser que seja criada depois)

        retriever = qdrant_client.get_langchain_retriever(
            collection_name=collection_name,
            embeddings=embedding_model,
            search_k=4
        )

        # --- 3. Criação da Cadeia (Runnable) ---
        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

        # O chain recebe {"question": "..."} e:
        # 1. Extrai a pergunta
        # 2. Busca documentos relevantes no Qdrant
        # 3. Formata o contexto e gera a resposta

        def retrieve_and_format(input_dict):
            """Busca documentos e formata o contexto."""
            question = input_dict.get("question", "")
            logger.info(f"RAG: Buscando documentos para query: '{question[:100]}...'")

            try:
                docs = retriever.invoke(question)
                logger.info(f"RAG: Recuperados {len(docs)} documentos")
                return _format_docs(docs)
            except Exception as e:
                logger.error(f"RAG: Erro na busca: {e}")
                return "Erro ao buscar informações."

        rag_chain = (
            # Adiciona o contexto recuperado mantendo a question original
            RunnablePassthrough.assign(
                context=RunnableLambda(retrieve_and_format)
            )
            | prompt
            | llm
            | StrOutputParser()
        )

        logger.info(f"Runnable RAG criado com sucesso para {contexto.id}.")
        return rag_chain

    except Exception as e:
        logger.error(
            f"Falha grave ao criar o runnable RAG para {contexto.id} "
            f"(coleção {collection_name}): {e}"
        )
        return None