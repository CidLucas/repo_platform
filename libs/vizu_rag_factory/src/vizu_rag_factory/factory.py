import logging
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
1
# Dependências de outras libs Vizu
from vizu_shared_models.cliente_vizu import VizuClientContext
from vizu_qdrant_client.client import VizuQdrantClient # Nossa lib de cliente Qdrant
from vizu_llm_service.client import get_embedding_model # <--- ADICIONADO


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
    if not docs:
        return "Nenhum contexto encontrado."
    return "\n\n---\n\n".join([d.page_content for d in docs])

def create_rag_runnable(
    contexto: VizuClientContext,
    llm: BaseChatModel,
) -> Optional[Runnable]:
    """
    Factory agnóstica para criar um Runnable de RAG.
    ...
    """

    if not contexto.ferramenta_rag_habilitada:
        # ... (logging)
        return None

    collection_name = str(contexto.id)
    logger.info(f"contexto.id (coleção: {collection_name})...")

    try:
        # --- 2. Configuração do Retriever (Agora Limpo) ---

        # Obtém o modelo de embedding da service lib,
        # sem saber qual implementação está sendo usada.
        embedding_model = get_embedding_model() # <--- REFATORADO

        qdrant_client = VizuQdrantClient()

        retriever = qdrant_client.get_langchain_retriever(
            collection_name=collection_name,
            embeddings=embedding_model,
            search_k=4
        )

        # --- 3. Criação da Cadeia (Runnable) ---
        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

        rag_chain = (
            {
                "context": retriever | _format_docs,
                "question": RunnablePassthrough()
            }
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
import logging
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.base import Runnable
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
1
# Dependências de outras libs Vizu
from vizu_shared_models.cliente_vizu import VizuClientContext
from vizu_qdrant_client.client import VizuQdrantClient # Nossa lib de cliente Qdrant
from vizu_llm_service.client import get_embedding_model # <--- ADICIONADO


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
    if not docs:
        return "Nenhum contexto encontrado."
    return "\n\n---\n\n".join([d.page_content for d in docs])

def create_rag_runnable(
    contexto: VizuClientContext,
    llm: BaseChatModel,
) -> Optional[Runnable]:
    """
    Factory agnóstica para criar um Runnable de RAG.
    ...
    """

    if not contexto.ferramenta_rag_habilitada:
        # ... (logging)
        return None

    collection_name = str(contexto.collection_rag)
    logger.info(f"contexto.id (coleção: {collection_name})...")

    try:
        # --- 2. Configuração do Retriever (Agora Limpo) ---

        # Obtém o modelo de embedding da service lib,
        # sem saber qual implementação está sendo usada.
        embedding_model = get_embedding_model() # <--- REFATORADO

        qdrant_client = VizuQdrantClient()

        retriever = qdrant_client.get_langchain_retriever(
            collection_name=collection_name,
            embeddings=embedding_model,
            search_k=4
        )

        # --- 3. Criação da Cadeia (Runnable) ---
        prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

        rag_chain = (
            {
                "context": retriever | _format_docs,
                "question": RunnablePassthrough()
            }
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