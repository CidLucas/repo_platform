# services/embedding_service/src/service.py

from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings
from .config import get_embedding_settings, EmbeddingSettings

@lru_cache
def get_model_singleton() -> HuggingFaceEmbeddings:
    """
    Carrega o modelo de embedding na memória e o retorna.

    O @lru_cache(maxsize=1) garante que esta função seja executada
    apenas uma vez, e o resultado (o modelo carregado) seja
    armazenado em cache e retornado em todas as chamadas futuras.
    """
    settings = get_embedding_settings()

    print(f"INFO: Carregando modelo de embedding '{settings.EMBEDDING_MODEL_NAME}'...")
    print(f"INFO: Dispositivo de inferência: '{settings.EMBEDDING_MODEL_DEVICE}'")

    try:
        # Define os argumentos para o modelo
        model_kwargs = {'device': settings.EMBEDDING_MODEL_DEVICE}

        # Instancia o modelo. O download será feito automaticamente
        # pelo HuggingFace se o modelo não estiver em cache.
        model = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL_NAME,
            model_kwargs=model_kwargs
        )
        print("INFO: Modelo de embedding carregado com sucesso.")
        return model

    except Exception as e:
        # Se o modelo falhar ao carregar, o serviço não pode funcionar.
        print(f"ERRO CRÍTICO: Falha ao carregar modelo de embedding: {e}")
        # Propaga a exceção para que o serviço falhe ao iniciar.
        raise