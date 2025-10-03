# src/atendente_api/tools/rag_tool.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Nossos módulos e bibliotecas do monorepo
from atendente_api.core.schemas import VizuClientContext
from vizu_qdrant_client import VizuQdrantClient
from langchain_qdrant import Qdrant


def create_rag_chain(context: VizuClientContext) -> Runnable:
    """
    Cria e retorna uma cadeia de RAG (Retrieval-Augmented Generation) para um cliente.

    A cadeia é configurada para usar a coleção Qdrant específica do cliente e
    o seu prompt base customizado.
    """
    # 1. Verifica se a ferramenta está habilitada para o cliente
    if not context.ferramenta_rag_habilitada:
        raise ValueError(f"Ferramenta RAG não habilitada para o cliente {context.nome_empresa}")

    # 2. Configura o cliente Qdrant e o Retriever
    # A coleção no Qdrant deve seguir um padrão, ex: usando o ID do cliente
    collection_name = f"cliente-{context.id}"
    qdrant_client = VizuQdrantClient().client # Acessa o cliente Qdrant bruto

    vectorstore = Qdrant(
        client=qdrant_client,
        collection_name=collection_name,
        embeddings=OpenAIEmbeddings(),
    )
    retriever = vectorstore.as_retriever()

    # 3. Define o template do prompt, usando o prompt base do cliente
    prompt_template = f"""
    Você é um assistente prestativo da empresa {context.nome_empresa}.
    Responda a pergunta do usuário com base apenas no seguinte contexto.
    Se a informação não estiver no contexto, diga que você não sabe a resposta.

    Contexto da Base de Conhecimento:
    {{context}}

    Pergunta do Usuário:
    {{question}}

    Instruções Adicionais da Empresa:
    {context.prompt_base or "Seja sempre cordial e prestativo."}
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)

    # 4. Monta e retorna a cadeia RAG completa
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain