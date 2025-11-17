# services/embedding_service/src/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from .service import get_model_singleton
from .config import get_embedding_settings

# ---- Schemas (Contratos) da API ----

class EmbedRequest(BaseModel):
    """O que a API espera receber no body de um POST"""
    texts: List[str]

class EmbedResponse(BaseModel):
    """O que a API retorna"""
    embeddings: List[List[float]]

# ---- Inicialização da Aplicação ----

app = FastAPI(
    title="Vizu Embedding Service",
    description="Microserviço para gerar embeddings de texto usando HuggingFace.",
    version="0.1.0"
)

# ---- Eventos de Startup ----

@app.on_event("startup")
def startup_event():
    """
    No startup, "esquenta" o modelo chamando o singleton
    pela primeira vez. Isso garante que o modelo esteja na
    memória antes de qualquer requisição.
    """
    print("INFO: Servidor FastAPI iniciando...")
    try:
        get_embedding_settings() # Carrega as settings
        get_model_singleton()    # Carrega o modelo na memória
        print("INFO: Modelo de embedding pronto para servir.")
    except Exception as e:
        print(f"ERRO FATAL: Falha ao carregar o modelo no startup: {e}")
        # Se o modelo não carregar, o serviço não deve iniciar.
        raise

# ---- Endpoints da API ----

@app.get("/health", summary="Verifica a saúde do serviço")
def read_health():
    """Endpoint de health check básico."""
    return {"status": "ok"}

@app.post("/embed",
          response_model=EmbedResponse,
          summary="Gera embeddings para uma lista de textos")
def create_embeddings(request: EmbedRequest):
    """
    Recebe uma lista de textos e retorna uma lista de vetores (embeddings).
    """
    if not request.texts:
        return {"embeddings": []}

    try:
        # Pega o modelo já carregado da memória (cache do @lru_cache)
        model = get_model_singleton()

        # Gera os embeddings
        embeddings = model.embed_documents(request.texts)

        return {"embeddings": embeddings}

    except Exception as e:
        print(f"ERRO: Falha durante a vetorização do request: {e}")
        # Se algo der errado *durante* a vetorização, retorna um erro 500.
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao processar os embeddings: {str(e)}"
        )