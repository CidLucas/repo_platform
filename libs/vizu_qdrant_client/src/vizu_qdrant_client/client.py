import os
from typing import List
from qdrant_client import QdrantClient, models

class VizuQdrantClient:
    """
    Cliente agnóstico para interagir com o Qdrant.
    Configurado via variáveis de ambiente.
    """
    def __init__(self):
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        self.client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
        )

    def create_collection_if_not_exists(self, collection_name: str, vector_size: int):
        try:
            self.client.get_collection(collection_name=collection_name)
            print(f"Coleção '{collection_name}' já existe.")
        except Exception:
            print(f"Coleção '{collection_name}' não encontrada. Criando...")
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )
            print(f"Coleção '{collection_name}' criada com sucesso.")

    def upsert_vectors(self, collection_name: str, points: List[models.PointStruct]):
        self.client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True
        )

    def search(self, collection_name: str, query_vector: List[float], limit: int = 5) -> List[models.ScoredPoint]:
        """
        Realiza uma busca por similaridade em uma coleção.
        """
        # --- CORREÇÃO FINAL ---
        # O argumento para o vetor de busca no método 'search' é 'query_vector'.
        # O método 'recreate_collection' foi usado para garantir um estado limpo.
        hits = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
        return hits