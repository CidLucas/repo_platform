import pytest
import uuid
from qdrant_client import QdrantClient

# Importamos nosso cliente
from vizu_qdrant_client.client import VizuQdrantClient

# Define um nome de coleção único para cada execução de teste, evitando conflitos
# O uso de `scope="session"` significa que esta fixture será executada uma vez por sessão de teste.
@pytest.fixture(scope="session")
def test_collection_name():
    """Gera um nome de coleção único para a sessão de testes."""
    return f"test_collection_{uuid.uuid4().hex}"

@pytest.fixture(scope="session")
def qdrant_client(test_collection_name):
    """
    Fixture principal: inicializa nosso VizuQdrantClient e gerencia o ciclo de vida
    da coleção de teste.
    """
    # Inicializa nosso cliente
    client = VizuQdrantClient()

    # Força a exclusão da coleção caso ela exista de algum teste anterior que falhou
    client.client.delete_collection(collection_name=test_collection_name)

    # Disponibiliza o cliente para os testes
    yield client

    # Limpeza (Teardown): executa após todos os testes da sessão terminarem
    print(f"\nLimpando a coleção de teste: {test_collection_name}")
    client.client.delete_collection(collection_name=test_collection_name)