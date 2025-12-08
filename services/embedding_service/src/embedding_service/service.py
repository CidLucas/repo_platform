# services/embedding_service/src/service.py
"""
Serviço de Embedding.

Carrega e serve modelos de embedding HuggingFace.
Suporta modelos E5 que requerem prefixo "query: " ou "passage: ".

NOTE: Using sentence-transformers directly instead of langchain-huggingface
to avoid pulling in unnecessary dependencies.
"""

from functools import lru_cache
from typing import List
from sentence_transformers import SentenceTransformer
from .config import get_embedding_settings, EmbeddingSettings


class E5EmbeddingWrapper:
    """
    Wrapper para modelos E5 que requerem prefixos específicos.

    Modelos E5 (intfloat/multilingual-e5-*) performam melhor quando:
    - Queries usam prefixo "query: "
    - Documentos usam prefixo "passage: "

    Este wrapper aplica automaticamente o prefixo correto.
    """

    def __init__(self, model: SentenceTransformer, model_name: str):
        self.model = model
        self.model_name = model_name
        self.is_e5_model = "e5" in model_name.lower()

    def _add_prefix(self, texts: List[str], prefix: str) -> List[str]:
        """Adiciona prefixo se for modelo E5."""
        if self.is_e5_model:
            return [f"{prefix}{text}" for text in texts]
        return texts

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds documentos (para armazenamento no Qdrant)."""
        prefixed = self._add_prefix(texts, "passage: ")
        embeddings = self.model.encode(prefixed, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """Embeds uma query (para busca no Qdrant)."""
        prefixed = self._add_prefix([text], "query: ")[0]
        embedding = self.model.encode(prefixed, convert_to_numpy=True)
        return embedding.tolist()

    def embed_queries(self, texts: List[str]) -> List[List[float]]:
        """Embeds múltiplas queries (para buscas em lote)."""
        prefixed = self._add_prefix(texts, "query: ")
        embeddings = self.model.encode(prefixed, convert_to_numpy=True)
        return embeddings.tolist()


@lru_cache
def get_model_singleton() -> E5EmbeddingWrapper:
    """
    Carrega o modelo de embedding na memória e o retorna.

    O @lru_cache(maxsize=1) garante que esta função seja executada
    apenas uma vez, e o resultado (o modelo carregado) seja
    armazenado em cache e retornado em todas as chamadas futuras.
    """
    settings = get_embedding_settings()

    print(f"INFO: Carregando modelo de embedding '{settings.EMBEDDING_MODEL_NAME}'...")
    print(f"INFO: Dispositivo de inferência: '{settings.EMBEDDING_MODEL_DEVICE}'")
    print(f"INFO: Dimensão esperada: {settings.EMBEDDING_VECTOR_SIZE}")

    try:
        # Instancia o modelo usando sentence-transformers diretamente
        # O download será feito automaticamente pelo HuggingFace se o modelo não estiver em cache.
        model = SentenceTransformer(
            settings.EMBEDDING_MODEL_NAME,
            device=settings.EMBEDDING_MODEL_DEVICE
        )

        # Wrappa com suporte a E5
        wrapper = E5EmbeddingWrapper(model, settings.EMBEDDING_MODEL_NAME)

        print("INFO: Modelo de embedding carregado com sucesso.")
        if wrapper.is_e5_model:
            print("INFO: Modelo E5 detectado - prefixos 'query:' e 'passage:' serão aplicados automaticamente.")

        return wrapper

    except Exception as e:
        # Se o modelo falhar ao carregar, o serviço não pode funcionar.
        print(f"ERRO CRÍTICO: Falha ao carregar modelo de embedding: {e}")
        # Propaga a exceção para que o serviço falhe ao iniciar.
        raise