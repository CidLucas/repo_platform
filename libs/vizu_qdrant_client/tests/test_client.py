import uuid

from qdrant_client import models

from vizu_qdrant_client.client import VizuQdrantClient

# Definimos um tamanho de vetor pequeno para os testes
VECTOR_SIZE = 4
DISTANCE = models.Distance.COSINE

def test_create_collection(qdrant_client: VizuQdrantClient, test_collection_name: str):
    """
    Testa se a função de criar coleção funciona corretamente.
    """
    # 1. Chama a função para criar a coleção
    qdrant_client.create_collection_if_not_exists(test_collection_name, VECTOR_SIZE)

    # 2. Verifica se a coleção realmente existe
    collection_info = qdrant_client.client.get_collection(collection_name=test_collection_name)

    # 3. Asserts (CORRIGIDOS)
    assert collection_info is not None
    # O caminho correto para a configuração de vetores
    assert collection_info.config.params.vectors.size == VECTOR_SIZE
    assert collection_info.config.params.vectors.distance == DISTANCE

    # 4. Tenta criar a mesma coleção novamente para garantir que não dê erro
    qdrant_client.create_collection_if_not_exists(test_collection_name, VECTOR_SIZE)


def test_upsert_and_search(qdrant_client: VizuQdrantClient, test_collection_name: str):
    """
    Testa a inserção (upsert) e a busca (search) de vetores.
    """
    # 1. Setup: Garante que a coleção existe
    qdrant_client.create_collection_if_not_exists(test_collection_name, VECTOR_SIZE)

    # 2. Preparação dos dados para inserir
    points_to_insert = [
        models.PointStruct(id=str(uuid.uuid4()), vector=[0.9, 0.1, 0.1, 0.1], payload={"doc": "documento 1"}),
        models.PointStruct(id=str(uuid.uuid4()), vector=[0.1, 0.9, 0.1, 0.1], payload={"doc": "documento 2"}),
        models.PointStruct(id=str(uuid.uuid4()), vector=[0.1, 0.1, 0.9, 0.1], payload={"doc": "documento 3"}),
    ]

    # 3. Execução do Upsert
    qdrant_client.upsert_vectors(test_collection_name, points_to_insert)

    # 4. Verificação do Upsert
    count_result = qdrant_client.client.count(collection_name=test_collection_name, exact=True)
    assert count_result.count == 3

    # 5. Execução da Busca
    query_vector = [0.15, 0.85, 0.1, 0.2]
    search_results = qdrant_client.search(collection_name=test_collection_name, query_vector=query_vector, limit=1)

    # 6. Asserts da Busca
    assert len(search_results) == 1
    top_result = search_results[0]
    assert top_result.payload["doc"] == "documento 2"
    assert top_result.score > 0.95
