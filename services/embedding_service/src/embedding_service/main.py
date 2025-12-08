# services/embedding_service/src/main.py

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from typing import List, Union, Any, Optional
import json
import io
from .service import get_model_singleton
from .config import get_embedding_settings

# Import chunking utilities
from vizu_parsers import parse_and_chunk, chunk_text, ChunkingStrategy

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


class ChunkRequest(BaseModel):
    """Request body for text chunking"""
    text: str
    chunk_size: int = 512
    chunk_overlap: int = 50
    strategy: str = "semantic"  # semantic, by_sentence, by_paragraph, by_char
    min_chunk_size: int = 100
    metadata: Optional[dict] = None


class ChunkResponse(BaseModel):
    """Response for text chunking"""
    chunks: List[dict]
    total_chunks: int
    original_length: int


class ProcessRequest(BaseModel):
    """Request body for combined parse+chunk+embed"""
    text: Optional[str] = None
    chunk_size: int = 512
    chunk_overlap: int = 50
    strategy: str = "semantic"
    embed: bool = True  # Whether to also generate embeddings
    mode: str = "document"  # Embedding mode


class ProcessResponse(BaseModel):
    """Response for combined processing"""
    chunks: List[dict]
    embeddings: Optional[List[List[float]]] = None
    total_chunks: int
    original_length: int

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


# ---- Chunking Endpoints ----

def _get_strategy(strategy_str: str) -> ChunkingStrategy:
    """Convert string to ChunkingStrategy enum."""
    strategy_map = {
        "semantic": ChunkingStrategy.SEMANTIC,
        "by_sentence": ChunkingStrategy.BY_SENTENCE,
        "by_paragraph": ChunkingStrategy.BY_PARAGRAPH,
        "by_char": ChunkingStrategy.BY_CHAR,
    }
    return strategy_map.get(strategy_str, ChunkingStrategy.SEMANTIC)


@app.post("/chunk",
          response_model=ChunkResponse,
          summary="Divide texto em chunks para RAG")
async def chunk_text_endpoint(request: ChunkRequest):
    """
    Divide um texto em chunks usando a estratégia especificada.
    Útil para preparar documentos para indexação no Qdrant.
    """
    try:
        strategy = _get_strategy(request.strategy)

        chunks = chunk_text(
            text=request.text,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            strategy=strategy,
            min_chunk_size=request.min_chunk_size,
            metadata=request.metadata,
        )

        chunk_dicts = [c.to_dict() for c in chunks]

        print(f"DEBUG /chunk: Criados {len(chunk_dicts)} chunks de {len(request.text)} chars")

        return ChunkResponse(
            chunks=chunk_dicts,
            total_chunks=len(chunk_dicts),
            original_length=len(request.text),
        )

    except Exception as e:
        print(f"ERRO: Falha ao fazer chunking: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar chunks: {str(e)}"
        )


@app.post("/process",
          response_model=ProcessResponse,
          summary="Processa texto: chunk + embed em uma única chamada")
async def process_text_endpoint(request: ProcessRequest):
    """
    Processa texto em um único passo: divide em chunks e opcionalmente gera embeddings.
    Ideal para pipelines de ingestão RAG.
    """
    if not request.text:
        raise HTTPException(status_code=422, detail="text é obrigatório")

    try:
        strategy = _get_strategy(request.strategy)

        # 1. Divide em chunks
        chunks = chunk_text(
            text=request.text,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            strategy=strategy,
        )

        chunk_dicts = [c.to_dict() for c in chunks]

        # 2. Opcionalmente gera embeddings
        embeddings = None
        if request.embed and chunks:
            model = get_model_singleton()
            chunk_texts = [c.text for c in chunks]

            if request.mode == "query":
                embeddings = model.embed_queries(chunk_texts)
            else:
                embeddings = model.embed_documents(chunk_texts)

            print(f"DEBUG /process: Gerados {len(embeddings)} embeddings para {len(chunks)} chunks")

        return ProcessResponse(
            chunks=chunk_dicts,
            embeddings=embeddings,
            total_chunks=len(chunk_dicts),
            original_length=len(request.text),
        )

    except Exception as e:
        print(f"ERRO: Falha ao processar texto: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar texto: {str(e)}"
        )


@app.post("/process-file",
          response_model=ProcessResponse,
          summary="Processa arquivo: parse + chunk + embed")
async def process_file_endpoint(
    file: UploadFile = File(...),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(50),
    strategy: str = Form("semantic"),
    embed: bool = Form(True),
    mode: str = Form("document"),
):
    """
    Faz upload de um arquivo (PDF, CSV, TXT), extrai texto, divide em chunks
    e opcionalmente gera embeddings. Pipeline completo de ingestão RAG.

    Formatos suportados: .pdf, .csv, .txt
    """
    try:
        # Lê o conteúdo do arquivo
        content = await file.read()
        file_stream = io.BytesIO(content)

        strategy_enum = _get_strategy(strategy)

        # Parse e chunk usando vizu_parsers
        chunks = parse_and_chunk(
            file_stream=file_stream,
            filename=file.filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=strategy_enum,
            metadata={"source_file": file.filename},
        )

        if not chunks:
            raise HTTPException(
                status_code=422,
                detail=f"Não foi possível extrair texto do arquivo: {file.filename}"
            )

        chunk_dicts = [c.to_dict() for c in chunks]
        original_length = sum(c.length for c in chunks)

        # Opcionalmente gera embeddings
        embeddings = None
        if embed and chunks:
            model = get_model_singleton()
            chunk_texts = [c.text for c in chunks]

            if mode == "query":
                embeddings = model.embed_queries(chunk_texts)
            else:
                embeddings = model.embed_documents(chunk_texts)

            print(f"DEBUG /process-file: {file.filename} -> {len(chunks)} chunks, {len(embeddings)} embeddings")

        return ProcessResponse(
            chunks=chunk_dicts,
            embeddings=embeddings,
            total_chunks=len(chunk_dicts),
            original_length=original_length,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERRO: Falha ao processar arquivo {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar arquivo: {str(e)}"
        )