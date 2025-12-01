# services/embedding_service/src/main.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from typing import List, Union, Any
import json
from .service import get_model_singleton
from .config import get_embedding_settings

# ---- Schemas (Contratos) da API ----

class EmbedRequest(BaseModel):
    """O que a API espera receber no body de um POST"""
    texts: List[str]
    mode: str = "document"  # "document" ou "query" - controla o prefixo E5

    @validator('texts', pre=True)
    def ensure_list_of_strings(cls, v):
        """Garante que todos os elementos sejam strings."""
        if not isinstance(v, list):
            raise ValueError("texts deve ser uma lista")
        return [str(item) if not isinstance(item, str) else item for item in v]

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


@app.get("/info", summary="Retorna informações sobre o modelo de embedding")
def read_info():
    """Retorna configurações do modelo carregado."""
    settings = get_embedding_settings()
    return {
        "model_name": settings.EMBEDDING_MODEL_NAME,
        "vector_size": settings.EMBEDDING_VECTOR_SIZE,
        "device": settings.EMBEDDING_MODEL_DEVICE,
        "status": "loaded"
    }

@app.post("/embed",
          response_model=EmbedResponse,
          summary="Gera embeddings para uma lista de textos")
async def create_embeddings(request: Request):
    """
    Recebe uma lista de textos e retorna uma lista de vetores (embeddings).
    Aceita body flexível para compatibilidade.
    """
    try:
        body = await request.json()
        print(f"DEBUG /embed: raw body keys = {body.keys() if isinstance(body, dict) else type(body)}")
    except Exception as e:
        print(f"ERRO: Não foi possível parsear o body JSON: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}")

    # Extrai textos de diferentes formatos
    texts = []
    if isinstance(body, dict):
        if "texts" in body:
            texts = body["texts"]
        elif "input" in body:
            # Formato alternativo (OpenAI-like)
            input_data = body["input"]
            if isinstance(input_data, str):
                texts = [input_data]
            else:
                texts = input_data
        else:
            print(f"ERRO: Body sem 'texts' ou 'input': {list(body.keys())}")
            raise HTTPException(status_code=422, detail="Body deve conter 'texts' ou 'input'")
    elif isinstance(body, list):
        texts = body
    else:
        print(f"ERRO: Tipo de body inesperado: {type(body)}")
        raise HTTPException(status_code=422, detail=f"Tipo de body inesperado: {type(body)}")

    # Garante que todos os elementos são strings
    texts = [str(t) if not isinstance(t, str) else t for t in texts]

    # Extrai o modo (document ou query)
    mode = "document"
    if isinstance(body, dict):
        mode = body.get("mode", "document")

    print(f"DEBUG /embed: Processando {len(texts)} textos no modo '{mode}'")

    if not texts:
        return {"embeddings": []}

    try:
        # Pega o modelo já carregado da memória (cache do @lru_cache)
        model = get_model_singleton()

        # Gera os embeddings usando o método correto para o modo
        if mode == "query":
            embeddings = model.embed_queries(texts)
        else:
            embeddings = model.embed_documents(texts)

        print(f"DEBUG /embed: Gerados {len(embeddings)} embeddings")
        return {"embeddings": embeddings}

    except Exception as e:
        print(f"ERRO: Falha durante a vetorização: {e}")
        # Se algo der errado *durante* a vetorização, retorna um erro 500.
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao processar os embeddings: {str(e)}"
        )